"""Bounded, GET-only private GitHub source for a pinned BIO evidence preflight.

Reuses the existing FORGE Mind-Palace read-only credential; never accesses
CKB-plane or publishes private source in CI. No background sync or write API.
"""
import base64
import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request

REPO = "spoonman136668-ai/Mind-Palace"
CATALOG = "docs/RESEARCH_EVIDENCE_CATALOG.json"
INDEX = "archive/research/bio/2026-10-23/findings.json"
PATH = re.compile(r"^archive/research/bio/2026-10-23/(original_reports|original_decisions)/[A-Za-z0-9_.-]+$")
SHA = re.compile(r"^[0-9a-f]{40}$")

# The only prospective BIO-73 read in this API. It is executable source
# obtained privately for an isolated source-qualification step, NOT runnable
# content for this reader and NOT scientific first-use authorization.
BIO73_ENV0_COMMIT = "7ad7230a82e3c748aa5336b7288ad2b45d42630c"
BIO73_ENV0_PATH = "archive/research/bio/2026-10-23/bio73/bio73_source_preflight.py"
BIO73_ENV0_BLOB = "d9218e5b1eb7b1da43092f96d91af3a07287ef2c"
BIO73_ENV0_MAX_BYTES = 16384

def blocked(code):
    raise ValueError("PRIVATE_BIO_READ_" + code)

class _DenyRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        blocked("REDIRECT")

class GitHubBIO:
    def __init__(self, token, opener=None):
        if not isinstance(token, str) or not token or token.strip() != token or any(c in token for c in "\r\n\x00 "):
            blocked("TOKEN_REQUIRED")
        self._token = token
        self._open = opener or urllib.request.build_opener(_DenyRedirect()).open
        self._pin = None

    def _get(self, route, maximum):
        url = "https://api.github.com/repos/" + REPO + "/" + route
        req = urllib.request.Request(url, method="GET", headers={
            "Authorization": "Bearer " + self._token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"})
        try:
            with self._open(req, timeout=12) as resp:
                if resp.getcode() != 200:
                    blocked("HTTP_STATUS")
                raw = resp.read(maximum + 1)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ValueError("PRIVATE_BIO_READ_UNAVAILABLE") from None
        if not raw or len(raw) > maximum:
            blocked("HTTP_BOUNDS")
        try:
            return json.loads(raw)
        except (ValueError, UnicodeError):
            blocked("HTTP_JSON")

    def resolve_main(self):
        record = self._get("commits/main", 32768)
        pin = record.get("sha") if isinstance(record, dict) else None
        if not isinstance(pin, str) or not SHA.fullmatch(pin):
            blocked("PIN_UNVERIFIED")
        self._pin = pin
        return pin

    def read_at(self, path, maximum):
        if not self._pin or not SHA.fullmatch(self._pin):
            blocked("NOT_PINNED")
        if not isinstance(path, str) or (
                path != CATALOG and path != INDEX and not PATH.fullmatch(path)):
            blocked("PATH_DENIED")
        if maximum < 1 or maximum > 250000:
            blocked("SIZE_BOUNDS")
        url_path = urllib.parse.quote(path, safe="/")
        payload = self._get("contents/" + url_path + "?ref=" + self._pin,
                            min(2 * maximum + 20480, 550000))
        if not isinstance(payload, dict) or payload.get("type") != "file" or payload.get("encoding") != "base64":
            blocked("FILE_FORMAT")
        declared_size = payload.get("size")
        sha = payload.get("sha")
        encoded = payload.get("content")
        if (type(declared_size) is not int or declared_size < 1 or declared_size > maximum
                or not isinstance(sha, str) or not SHA.fullmatch(sha)
                or not isinstance(encoded, str)):
            blocked("FILE_METADATA")
        try:
            raw = base64.b64decode(encoded, validate=False)
        except (ValueError, Exception):
            blocked("FILE_DECODE")
        if len(raw) != declared_size:
            blocked("FILE_LENGTH")
        obj = b"blob " + str(len(raw)).encode("ascii") + b"\x00" + raw
        if hashlib.sha1(obj).hexdigest() != sha:
            blocked("FILE_GIT_BLOB_SHA")
        return raw

    @staticmethod
    def _verify_frozen_file(payload, expected_sha, maximum):
        """Verify an exact GitHub Contents response; never execute the bytes."""
        if not isinstance(payload, dict) or payload.get("type") != "file" or payload.get("encoding") != "base64":
            blocked("FROZEN_SOURCE_FORMAT")
        size = payload.get("size")
        encoded = payload.get("content")
        if (type(size) is not int or size < 1 or size > maximum or
                payload.get("sha") != expected_sha or not isinstance(encoded, str)):
            blocked("FROZEN_SOURCE_IDENTITY")
        try:
            raw = base64.b64decode("".join(encoded.splitlines()), validate=True)
        except (ValueError, Exception):
            blocked("FROZEN_SOURCE_DECODE")
        if len(raw) != size:
            blocked("FROZEN_SOURCE_SIZE")
        git_blob = b"blob " + str(len(raw)).encode("ascii") + b"\x00" + raw
        if hashlib.sha1(git_blob).hexdigest() != expected_sha:
            blocked("FROZEN_SOURCE_GIT_BLOB_SHA")
        return raw

    def read_frozen_bio73_env0(self):
        """Read ONLY frozen BIO-73 upstream preflight bytes on a private GET.

        No caller-selected path/ref, no code execution, no runner selection,
        no claim of an authorized scientific environment or FSA decision.
        This method does not change the historical BIO reader's main pin.
        """
        route = ("contents/" + urllib.parse.quote(BIO73_ENV0_PATH, safe="/")
                 + "?ref=" + BIO73_ENV0_COMMIT)
        payload = self._get(route, 65536)
        return self._verify_frozen_file(
            payload, BIO73_ENV0_BLOB, BIO73_ENV0_MAX_BYTES)
