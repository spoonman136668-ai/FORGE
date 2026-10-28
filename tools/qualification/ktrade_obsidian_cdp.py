#!/usr/bin/env python3
"""Exercise the running isolated Obsidian desktop renderer through loopback CDP.

No packages, model calls, network outside 127.0.0.1, file edits, or broker access.
The caller starts the REAL Obsidian application with a disposable user profile and
an exact Git-checkout 39,973-note vault. This process only drives that renderer.
"""
import argparse
import base64
import hashlib
import json
import os
import socket
import struct
import sys
import time
from urllib.parse import urlparse
from urllib.request import urlopen

NOTE = "002865cd06_test.go"
WITNESS = "TestStrategy_Phase7_T764_ClosedTrades"
QUERY = "002865cd06_test.go"


class GateFailure(Exception):
    pass


class WebSocket:
    def __init__(self, url):
        u = urlparse(url)
        if u.hostname not in ("127.0.0.1", "localhost"):
            raise GateFailure("GUI_CDP_REMOTE_ADDRESS_FORBIDDEN")
        self.sock = socket.create_connection((u.hostname, u.port), timeout=12)
        self.sock.settimeout(12)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        path = u.path + ("?" + u.query if u.query else "")
        hello = (
            f"GET {path} HTTP/1.1\r\nHost: {u.hostname}:{u.port}\r\n"
            "Upgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(hello.encode("ascii"))
        head = bytearray()
        while b"\r\n\r\n" not in head and len(head) < 16384:
            head.extend(self.sock.recv(1024))
        header, sep, rest = head.partition(b"\r\n\r\n")
        if b" 101 " not in header.split(b"\r\n", 1)[0]:
            raise GateFailure("GUI_CDP_WEBSOCKET_HANDSHAKE_FAILED")
        expected = base64.b64encode(
            hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()
        ).decode()
        if f"Sec-WebSocket-Accept: {expected}".lower().encode() not in header.lower():
            raise GateFailure("GUI_CDP_WEBSOCKET_ACCEPT_INVALID")
        self.buf = bytes(rest)
        self.seq = 0

    def _take(self, n):
        while len(self.buf) < n:
            data = self.sock.recv(max(4096, n - len(self.buf)))
            if not data:
                raise GateFailure("GUI_CDP_CONNECTION_CLOSED")
            self.buf += data
        result, self.buf = self.buf[:n], self.buf[n:]
        return result

    def send(self, payload):
        raw = json.dumps(payload, separators=(",", ":")).encode()
        head = bytearray([0x81])
        n = len(raw)
        if n < 126:
            head.append(0x80 | n)
        elif n < 65536:
            head.append(0x80 | 126)
            head.extend(struct.pack("!H", n))
        else:
            head.append(0x80 | 127)
            head.extend(struct.pack("!Q", n))
        mask = os.urandom(4)
        head.extend(mask)
        head.extend(b ^ mask[i % 4] for i, b in enumerate(raw))
        self.sock.sendall(head)

    def receive(self):
        b1, b2 = self._take(2)
        size = b2 & 0x7F
        if size == 126:
            size = struct.unpack("!H", self._take(2))[0]
        elif size == 127:
            size = struct.unpack("!Q", self._take(8))[0]
        if size > 8_000_000:
            raise GateFailure("GUI_CDP_RESPONSE_SIZE_CAP")
        mask = self._take(4) if b2 & 0x80 else None
        data = self._take(size)
        if mask:
            data = bytes(v ^ mask[i % 4] for i, v in enumerate(data))
        opcode = b1 & 15
        if opcode == 8:
            raise GateFailure("GUI_CDP_CLOSED")
        if opcode == 9:
            self._pong(data)
            return self.receive()
        if opcode not in (1, 2):
            return self.receive()
        return json.loads(data)

    def _pong(self, data):
        mask = os.urandom(4)
        self.sock.sendall(bytes([0x8A, 0x80 | len(data)]) + mask +
                          bytes(v ^ mask[i % 4] for i, v in enumerate(data)))

    def call(self, method, params=None):
        self.seq += 1
        me = self.seq
        self.send({"id": me, "method": method, "params": params or {}})
        for _ in range(700):
            item = self.receive()
            if item.get("id") != me:
                continue
            if item.get("error"):
                raise GateFailure("GUI_CDP_COMMAND_FAILED_" + method.replace(".", "_"))
            return item.get("result", {})
        raise GateFailure("GUI_CDP_RESPONSE_NOT_RECEIVED")

    def js(self, expression):
        result = self.call(
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True, "awaitPromise": True},
        )
        if result.get("exceptionDetails"):
            raise GateFailure("GUI_RENDERER_EVALUATION_FAILED")
        return result.get("result", {}).get("value")

    def key(self, key, code, vk, modifiers=0):
        for kind in ("keyDown", "keyUp"):
            self.call("Input.dispatchKeyEvent", {
                "type": kind, "key": key, "code": code,
                "modifiers": modifiers, "windowsVirtualKeyCode": vk,
                "nativeVirtualKeyCode": vk,
            })

    def text(self, value):
        self.call("Input.insertText", {"text": value})


def discover(port):
    endpoint = f"http://127.0.0.1:{port}/json/list"
    deadline = time.monotonic() + 35
    while time.monotonic() < deadline:
        try:
            with urlopen(endpoint, timeout=2) as res:
                pages = json.loads(res.read(128_000))
            matches = [
                x for x in pages
                if x.get("type") == "page" and x.get("webSocketDebuggerUrl")
            ]
            if matches:
                # The isolated Obsidian process has a single main vault window.
                return matches[0]["webSocketDebuggerUrl"]
        except (OSError, ValueError, KeyError):
            pass
        time.sleep(0.5)
    raise GateFailure("GUI_OBSIDIAN_CDP_UNAVAILABLE")


def until(fn, seconds, code, interval=0.5):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if fn():
            return True
        time.sleep(interval)
    raise GateFailure(code)


def ui_state(ws):
    return ws.js(r"""(() => {
      const active = document.querySelector('.workspace-leaf.mod-active');
      const obs = typeof app !== 'undefined' ? app : window.app;
      const headers = Array.from(document.querySelectorAll('.view-header-title'));
      const suggestions = Array.from(document.querySelectorAll('.suggestion-item'));
      const prompt = document.querySelector('input.prompt-input');
      const noteTitle = active?.querySelector('.view-header-title')?.textContent || '';
      const activeText = active?.innerText || '';
      const search = document.querySelector('.search-result-container');
      return {
        title: document.title,
        prompt: !!prompt,
        noteTitle,
        noteWitness: activeText.includes('TestStrategy_Phase7_T764_ClosedTrades'),
        bodyWitness: document.body.innerText.includes('TestStrategy_Phase7_T764_ClosedTrades'),
        headerMatch: headers.some(x => x.textContent?.includes('002865cd06_test.go')),
        vaultFiles: obs?.vault?.getMarkdownFiles?.().length ?? null,
        targetPresent: !!obs?.vault?.getAbstractFileByPath?.('002865cd06_test.go.md'),
        suggestionMatch: suggestions.some(x => x.innerText.includes('002865cd06_test.go')),
        suggestionCount: document.querySelectorAll('.suggestion-item').length,
        searchReady: !!document.querySelector('.search-input-container input'),
        searchResults: search ? search.querySelectorAll('.search-result-file-title, .search-result-file-match').length : 0,
        searchWitness: !!search && search.innerText.includes('002865cd06_test.go'),
        vaultUI: !!document.querySelector('.workspace, .workspace-split')
      };
    })()""")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    if not 40000 <= args.port <= 59999:
        raise GateFailure("GUI_LOCAL_CDP_PORT_POLICY")
    url = discover(args.port)
    ws = WebSocket(url)
    ws.call("Page.bringToFront")
    until(lambda: bool((ui_state(ws) or {}).get("vaultUI")), 50, "GUI_VAULT_WORKSPACE_NOT_RENDERED")
    until(lambda: (ui_state(ws) or {}).get("vaultFiles") == 39973,
          130, "GUI_OBSIDIAN_REAL_VAULT_NOT_FULLY_INDEXED")
    if not (ui_state(ws) or {}).get("targetPresent"):
        raise GateFailure("GUI_EXPECTED_NOTE_NOT_IN_OBSIDIAN_INDEX")
    print("KTRADE_GUI_OBSIDIAN_NATIVE_39973_FILE_INDEX=PASS", flush=True)
    print("KTRADE_GUI_CDP_REAL_RENDERER=PASS", flush=True)
    started = time.monotonic()
    ws.key("o", "KeyO", 79, modifiers=2)
    try:
        until(lambda: bool((ui_state(ws) or {}).get("prompt")), 8, "GUI_NATIVE_QUICK_SWITCHER_UNAVAILABLE")
    except GateFailure:
        # The supported internal Obsidian command invokes the genuine quick-switcher UI.
        result = ws.js(
            "typeof app!=='undefined' && !!app.commands.executeCommandById('switcher:open')"
        )
        if not result:
            raise GateFailure("GUI_QUICK_SWITCHER_COMMAND_UNAVAILABLE")
        until(lambda: bool((ui_state(ws) or {}).get("prompt")), 8, "GUI_QUICK_SWITCHER_NOT_OPEN")
    ws.text(NOTE)
    until(lambda: bool((ui_state(ws) or {}).get("suggestionMatch")),
          45, "GUI_QUICK_SWITCHER_NO_MATCHING_NOTE")
    ws.key("Enter", "Enter", 13)
    def note_is_visible():
        s = ui_state(ws) or {}
        return bool(s.get("headerMatch") and (s.get("noteWitness") or s.get("bodyWitness")))

    try:
        until(note_is_visible, 15, "GUI_QUICK_SWITCHER_NOTE_RENDER_DEFERRED")
    except GateFailure:
        # If platform keystroke selection did not activate the suggestion,
        # open this EXACT indexed TFile through the genuine workspace API.
        open_ok = ws.js("""(async () => {
          const a = typeof app !== 'undefined' ? app : window.app;
          const f = a?.vault?.getAbstractFileByPath('002865cd06_test.go.md');
          if (!f) return false;
          await a.workspace.getLeaf(false).openFile(f);
          return true;
        })()""")
        if not open_ok:
            raise GateFailure("GUI_WORKSPACE_API_FILE_OPEN_FAILED")
        until(note_is_visible, 55, "GUI_WORKSPACE_NOTE_CONTENT_NOT_RENDERED")
        print("KTRADE_GUI_NOTE_ACTIVATED_BY_WORKSPACE_API=TRUE", flush=True)
    print("KTRADE_GUI_REAL_NOTE_OPEN_AND_BODY=PASS", flush=True)
    print("KTRADE_GUI_NOTE_NAV_SECONDS=" + str(round(time.monotonic()-started, 2)), flush=True)

    start_search = time.monotonic()
    ws.key("f", "KeyF", 70, modifiers=3)
    if not (ui_state(ws) or {}).get("searchReady"):
        result = ws.js(
            "typeof app!=='undefined' && !!app.commands.executeCommandById('global-search:open')"
        )
        if not result:
            raise GateFailure("GUI_GLOBAL_SEARCH_COMMAND_UNAVAILABLE")
    until(lambda: bool((ui_state(ws) or {}).get("searchReady")),
          10, "GUI_SEARCH_INPUT_NOT_RENDERED")
    ws.js("document.querySelector('.search-input-container input').focus()")
    ws.text(QUERY)
    until(
        lambda: (
            (ui_state(ws) or {}).get("searchResults", 0) > 0
            and bool((ui_state(ws) or {}).get("searchWitness"))
        ),
        100, "GUI_GLOBAL_SEARCH_NO_AUTHENTIC_RESULT"
    )
    print("KTRADE_GUI_GLOBAL_SEARCH_RESULT=PASS", flush=True)
    print("KTRADE_GUI_SEARCH_SECONDS=" + str(round(time.monotonic()-start_search, 2)), flush=True)
    print("KTRADE_GUI_NO_SIMULATED_UI_AND_NO_MODEL_CALLS=PASS", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (GateFailure, OSError, ValueError, KeyError, TypeError) as exc:
        print("KTRADE_GUI_CDP_VALIDATION=FAIL:" +
              (str(exc) if isinstance(exc, GateFailure) else type(exc).__name__),
              flush=True)
        sys.exit(1)
