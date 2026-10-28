#!/usr/bin/env python3
"""Exercise three independently pinned advisory Obsidian desktop renderers through loopback CDP.

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



def choose_witness(ws):
    return ws.js(r"""(async () => {
      const a = typeof app !== 'undefined' ? app : window.app;
      const files = a?.vault?.getMarkdownFiles?.() || [];
      const filenames = files.map(x => x.basename.toLowerCase());
      const sorted = [...files].sort((x,y) => x.path.localeCompare(y.path)).slice(0,300);
      for (const f of sorted) {
        const choices = [...new Set((f.basename.match(/[A-Za-z][A-Za-z0-9_]{7,48}/g)||[]))];
        for (const word of choices) {
          if (filenames.filter(x => x.includes(word.toLowerCase())).length !== 1) continue;
          const raw=await a.vault.read(f);
          if (raw.length < 28 || raw.length > 60000) continue;
          const lines=raw.split(/\r?\n/).map(x => x.replace(/[^A-Za-z0-9]+/g,' ').trim().toLowerCase());
          const good=lines.find(x => x.length >= 22 && x.length <= 300);
          if (!good) continue;
          window.__advisoryGuiWitness = {path:f.path, basename:f.basename, query:'file:'+word, snippet:good.slice(0,22)};
          return {selected:true, validToken:true, rawLength:raw.length};
        }
      }
      return {selected:false, scanned:sorted.length};
    })()""")


def note_ui(ws):
    return ws.js(r"""(() => {
      const a = typeof app !== 'undefined' ? app : window.app;
      const w=window.__advisoryGuiWitness;
      const active=document.querySelector('.workspace-leaf.mod-active');
      const file=a?.workspace?.getActiveFile?.();
      const root=active?.querySelector('.markdown-view');
      const region=active?.querySelector('.cm-content, .markdown-preview-view');
      const words=(region?.innerText || '').replace(/[^A-Za-z0-9]+/g,' ').toLowerCase();
      const header=Array.from(document.querySelectorAll('.view-header-title'))
        .some(x => x.textContent?.includes(w?.basename || '___missing___'));
      const rect=region?.getBoundingClientRect();
      return {
        activeFile: !!w && file?.path===w.path,
        header,markdownView:!!root,
        noteRegionVisible: !!rect && rect.width>0 && rect.height>0,
        noteBodyWitness:!!w?.snippet && words.includes(w.snippet),
        noteRegionChars:words.length
      };
    })()""")


def search_ui(ws):
    return ws.js(r"""(() => {
      const a=typeof app !== 'undefined' ? app : window.app;
      const w=window.__advisoryGuiWitness;
      const leaf=a?.workspace?.getLeavesOfType?.('search')?.[0];
      const view=leaf?.view;
      const file=a?.vault?.getAbstractFileByPath?.(w?.path || '__missing__');
      const hit=view?.dom?.resultDomLookup;
      const container=view?.containerEl?.querySelector('.search-result-container');
      const input=view?.containerEl?.querySelector('.search-input-container input');
      const rect=view?.containerEl?.getBoundingClientRect();
      const nodes=container?.querySelectorAll('.search-result-file,.tree-item,.search-result-file-title')||[];
      let visibleHit=false;
      for(const el of nodes){
        if(el.textContent?.includes(w?.basename || '__missing__')){
          const r=el.getBoundingClientRect();
          if(r.width>0 && r.height>0){ visibleHit=true; break;}
        }
      }
      return {
        searchLeaf:!!leaf,querySetter:typeof view?.setQuery === 'function',
        plugin:!!a?.internalPlugins?.plugins?.['global-search'],
        inputMatches:!!w && input?.value===w.query,
        nativeHit:!!file && !!hit?.has?.(file),
        hitCount:hit?.size??null,
        resultFilename:!!container && !!w && container.textContent.includes(w.basename),
        visibleHit,
        viewVisible:!!rect && rect.width>0 && rect.height>0,
        nativePluginReopen:typeof a?.internalPlugins?.plugins?.['global-search']?.instance?.openGlobalSearch==='function'
      };
    })()""")


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--port",type=int,required=True)
    parser.add_argument("--project",choices=["FORGE","Wingless","Yggdrasil"],required=True)
    parser.add_argument("--notes",type=int,required=True)
    args=parser.parse_args()
    if not 40000 <= args.port <= 59999:raise GateFailure("GUI_LOCAL_PORT_OUTSIDE_POLICY")
    ws=WebSocket(discover(args.port))
    ws.call("Page.bringToFront")
    def file_count():
        return ws.js("""(() => {
           const a=typeof app !== 'undefined'?app:window.app;
           return a?.vault?.getMarkdownFiles?.().length ?? -1;
        })()""")
    until(lambda: file_count()==args.notes,120,"OBSIDIAN_VAULT_NATIVE_FILE_INDEX_NOT_READY",0.75)
    print("ADVISORY_GUI_"+args.project.upper()+"_NATIVE_INDEX=PASS",flush=True)
    witness=choose_witness(ws)
    if not witness or not witness.get("selected"):raise GateFailure("NO_DETERMINISTIC_FILENAME_CONTENT_WITNESS")
    print("ADVISORY_GUI_"+args.project.upper()+"_SOURCE_NOTE_WITNESS_SELECTED=PASS",flush=True)
    start=time.monotonic()
    opened=ws.js(r"""(async () => {
      const a=typeof app !== 'undefined' ? app : window.app;
      const w=window.__advisoryGuiWitness;
      const f=a?.vault?.getAbstractFileByPath?.(w.path);
      if(!f)return false;
      const leaf=a.workspace.getLeaf(false);
      await leaf.openFile(f);
      await a.workspace.revealLeaf(leaf);
      return true;
    })()""")
    if not opened:raise GateFailure("NATIVE_WORKSPACE_NOTE_OPEN_REJECTED")
    try:
        until(lambda: (lambda s: s.get("activeFile") and s.get("header") and
                 s.get("noteRegionVisible") and s.get("noteBodyWitness"))(note_ui(ws) or {}),
              45,"REAL_MARKDOWN_NOTE_RENDERER_NOT_MATCHING_SOURCE",0.5)
    except GateFailure:
        print("ADVISORY_GUI_NOTE_UI_DIAGNOSTIC="+json.dumps(note_ui(ws),sort_keys=True),flush=True)
        raise
    print("ADVISORY_GUI_"+args.project.upper()+"_REAL_NOTE_BODY=PASS",flush=True)
    print("ADVISORY_GUI_"+args.project.upper()+"_NAV_SECONDS="+str(round(time.monotonic()-start,2)),flush=True)
    start=time.monotonic()
    ws.key("f","KeyF",70,modifiers=3)
    if not (search_ui(ws) or {}).get("searchLeaf"):
        cmd=ws.js("typeof app!=='undefined' && !!app.commands.executeCommandById('global-search:open')")
        if not cmd:raise GateFailure("NATIVE_SEARCH_COMMAND_UNAVAILABLE")
    until(lambda: (search_ui(ws) or {}).get("searchLeaf"),12,"SEARCH_LEAF_NOT_CREATED")
    if not (search_ui(ws) or {}).get("querySetter"):raise GateFailure("SEARCHVIEW_QUERY_SETTER_UNAVAILABLE")
    query=ws.js(r"""(async () => {
      const a=typeof app !== 'undefined'?app:window.app;
      const v=a?.workspace?.getLeavesOfType?.('search')?.[0]?.view;
      const w=window.__advisoryGuiWitness;
      if(!v || !w || typeof v.setQuery!=='function')return false;
      const p=v.setQuery(w.query);
      if(p?.then) await p;
      return true;
    })()""")
    if not query:raise GateFailure("NATIVE_SEARCH_QUERY_NOT_SUBMITTED")
    revealed=ws.js(r"""(async () => {
      const a=typeof app!=='undefined'?app:window.app;
      const leaf=a?.workspace?.getLeavesOfType?.('search')?.[0];
      if(!leaf || typeof a.workspace.revealLeaf!=='function')return false;
      await a.workspace.revealLeaf(leaf);
      return true;
    })()""")
    if not revealed:raise GateFailure("NATIVE_SEARCH_LEAF_NOT_VISIBLE")
    until(lambda: (search_ui(ws) or {}).get("inputMatches"),15,"SEARCH_QUERY_NOT_IN_REAL_INPUT")
    try:
        until(lambda: (lambda s: s.get("nativeHit") and s.get("resultFilename") and
                 s.get("visibleHit") and s.get("inputMatches") and s.get("viewVisible"))(search_ui(ws) or {}),
              70,"NATIVE_SEARCH_RESULT_NOT_RENDERED",0.5)
    except GateFailure:
        print("ADVISORY_GUI_SEARCH_DIAGNOSTIC="+json.dumps(search_ui(ws),sort_keys=True),flush=True)
        raise
    print("ADVISORY_GUI_"+args.project.upper()+"_NATIVE_GLOBAL_SEARCH=PASS",flush=True)
    print("ADVISORY_GUI_"+args.project.upper()+"_SEARCH_SECONDS="+str(round(time.monotonic()-start,2)),flush=True)
    print("ADVISORY_GUI_"+args.project.upper()+"_READ_ONLY_ACCEPTANCE=PASS",flush=True)


if __name__=="__main__":
    try:main()
    except (GateFailure,OSError,ValueError,KeyError,TypeError,TimeoutError) as e:
        print("ADVISORY_GUI_VALIDATION=FAIL:"+(str(e) if isinstance(e,GateFailure) else type(e).__name__),flush=True)
        sys.exit(1)
