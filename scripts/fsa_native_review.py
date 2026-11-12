#!/usr/bin/env python3
"""Bounded GitHub source-review collector; GET and read-only GraphQL only."""
import argparse
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

HOST = "https://api.github.com"
GRAPH = """query($owner:String!,$name:String!,$number:Int!,$after:String) {
 repository(owner:$owner,name:$name) {
  pullRequest(number:$number) {
   reviewThreads(first:100,after:$after) {
    nodes { isResolved comments(first:100) {
     nodes { author { login } } pageInfo { hasNextPage } } }
    pageInfo { hasNextPage endCursor } } } } }"""


class Denied(Exception):
    pass


class Source:
    def __init__(self, repo, token="", transport=None):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
            raise Denied("INVALID_REPOSITORY")
        self.repo = repo
        self.owner, self.name = repo.split("/")
        self.token = token
        self.transport = transport or self.http

    def http(self, method, uri, data):
        if not uri.startswith(HOST + "/"):
            raise Denied("UNTRUSTED_API_ORIGIN")
        headers = {"Accept": "application/vnd.github+json",
                   "X-GitHub-Api-Version": "2022-11-28",
                   "User-Agent": "FORGE-R18-read-only"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(uri, method=method, headers=headers,
               data=json.dumps(data).encode() if data is not None else None)
        try:
            with urllib.request.urlopen(req, timeout=15) as res:
                b = res.read(2000001)
                if len(b) > 2000000:
                    raise Denied("RESPONSE_BUDGET_EXCEEDED")
                return json.loads(b), res.headers.get("Link", "")
        except (OSError, ValueError) as exc:
            raise Denied("GITHUB_API_UNAVAILABLE") from exc

    def get(self, suffix):
        path = f"/repos/{self.repo}/{suffix}"
        result, _ = self.transport("GET", HOST + path, None)
        if not isinstance(result, dict):
            raise Denied("INVALID_GITHUB_RECORD")
        return result

    def paged(self, suffix, key=None):
        path = f"/repos/{self.repo}/{suffix}"
        url = HOST + path
        origin = urllib.parse.urlsplit(url)
        origin_query = urllib.parse.parse_qs(origin.query)
        origin_query.pop("page", None)
        items, seen = [], set()
        while url:
            if url in seen or len(seen) >= 5:
                raise Denied("PAGINATION_LOOP")
            seen.add(url)
            data, links = self.transport("GET", url, None)
            current = data.get(key) if key else data
            if not isinstance(current, list):
                raise Denied("INVALID_PAGE")
            items.extend(current)
            if len(items) >= 100:
                raise Denied("INCOMPLETE_OR_UNBOUNDED_PAGE")
            following = []
            for part in links.split(","):
                if 'rel="next"' in part:
                    m = re.fullmatch(r'\s*<([^>]+)>;\s*rel="next"\s*', part)
                    if not m:
                        raise Denied("INVALID_NEXT_LINK")
                    following.append(m.group(1))
            if len(following) > 1:
                raise Denied("MULTIPLE_NEXT_LINKS")
            next_url = following[0] if following else ""
            if next_url:
                u = urllib.parse.urlsplit(next_url)
                query = urllib.parse.parse_qs(u.query)
                next_page = query.pop("page", [])
                if (u.scheme != "https" or u.netloc != "api.github.com"
                    or u.path != origin.path or query != origin_query
                    or len(next_page) != 1 or not next_page[0].isdigit()
                    or int(next_page[0]) <= len(seen)):
                    raise Denied("UNTRUSTED_NEXT_LINK")
            url = next_url
        return items

    def threads(self, number):
        cursor, cursors, records = None, set(), []
        for _ in range(5):
            payload = {"query": GRAPH, "variables": {
                "owner": self.owner, "name": self.name, "number": number,
                "after": cursor}}
            reply, _ = self.transport("POST", HOST + "/graphql", payload)
            if not isinstance(reply, dict) or reply.get("errors"):
                raise Denied("INVALID_GRAPHQL_RESULT")
            try:
                group = reply["data"]["repository"]["pullRequest"]["reviewThreads"]
                for t in group["nodes"]:
                    comments = t["comments"]["nodes"]
                    records.append({"Resolved": bool(t["isResolved"]),
                                    "Complete": (len(comments) > 0 and
                                        len(comments) < 100 and not
                                        t["comments"]["pageInfo"]["hasNextPage"]),
                                    "AllAuthorsTrusted": all(
                                        c.get("author") and c["author"]["login"] in (
                                        "chatgpt-codex-connector[bot]",
                                        "chatgpt-codex-connector") for c in comments)})
                if len(records) >= 100:
                    raise Denied("THREAD_BUDGET_EXCEEDED")
                page = group["pageInfo"]
                if not page["hasNextPage"]:
                    return records
                cursor = page["endCursor"]
                if not cursor or cursor in cursors:
                    raise Denied("THREAD_CURSOR_INVALID")
                cursors.add(cursor)
            except (KeyError, TypeError, IndexError) as exc:
                raise Denied("THREAD_RECORD_INCOMPLETE") from exc
        raise Denied("THREAD_PAGES_INCOMPLETE")

    def collect(self, number):
        if number <= 0:
            raise Denied("BAD_PR_NUMBER")
        original = self.get(f"pulls/{number}")
        try:
            sha = original["head"]["sha"]
            if not re.fullmatch(r"[a-f0-9]{40}", sha):
                raise Denied("BAD_HEAD_OID")
            source = {"Number": original["number"],
                      "Author": original["user"]["login"],
                      "HeadRepo": original["head"]["repo"]["full_name"],
                      "HeadSHA": sha, "SourceBranch": original["head"]["ref"],
                      "BaseRef": original["base"]["ref"], "Draft": original["draft"]}
            files = self.paged(f"pulls/{number}/files?per_page=100")
            reviews = self.paged(f"pulls/{number}/reviews?per_page=100")
            comments = self.paged(f"pulls/{number}/comments?per_page=100")
            runs = self.paged(f"actions/runs?head_sha={sha}&per_page=100", "workflow_runs")
            qualified_runs = []
            for run in runs:
                path = str(run.get("path", "")).split("@")[0]
                if (run["head_sha"] != sha or not (
                    path == ".github/workflows/qualify.yml" or re.fullmatch(
                    r"\.github/workflows/qualify-fsa[\w-]*\.yml", path))):
                    continue
                jobs = self.paged(f"actions/runs/{run['id']}/jobs?per_page=100", "jobs")
                status = {}
                for j in jobs:
                    if j["name"] in status:
                        raise Denied("DUPLICATE_JOB")
                    status[j["name"]] = j.get("conclusion") or ""
                qualified_runs.append({"Name": run["name"], "HeadSHA": run["head_sha"],
                    "Status": run["status"], "Conclusion": run.get("conclusion") or "",
                    "Jobs": status})
            threads = self.threads(number)
            latest = self.get(f"pulls/{number}")
            if (latest["head"]["sha"] != sha
                    or latest["head"]["ref"] != source["SourceBranch"]
                    or latest["base"]["ref"] != source["BaseRef"]
                    or latest["draft"] != source["Draft"]):
                raise Denied("HEAD_OR_STATE_DRIFT")
            return {
              "Repository": self.repo, "PR": source,
              "Files": [{"Path": f["filename"], "Status": f["status"]} for f in files],
              "Runs": qualified_runs,
              "Reviews": [{"Reviewer": r["user"]["login"],
                           "CommitID": r.get("commit_id") or "", "State": r["state"]}
                          for r in reviews],
              "InlineComments": [{"Author": c["user"]["login"],
                                  "CommitID": c.get("commit_id") or "",
                                  "Body": c.get("body") or ""} for c in comments],
              "Threads": threads,
              "Pages": {k: True for k in ("PullRequest", "Files", "WorkflowRuns",
                        "Reviews", "InlineComments", "Threads")}
            }
        except (KeyError, TypeError, IndexError) as exc:
            raise Denied("INCOMPLETE_GITHUB_RECORD") from exc


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pr", type=int, required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    if not os.path.isabs(args.output):
        raise SystemExit("ABSOLUTE_OUTPUT_REQUIRED")
    try:
        record = Source("spoonman136668-ai/FORGE",
                        os.getenv("GH_TOKEN", "")).collect(args.pr)
        with open(args.output, "x", encoding="utf-8") as fp:
            json.dump(record, fp, separators=(",", ":"), sort_keys=True)
        print("AUTHENTIC_GITHUB_READ=PASS")
        print("SOURCE_HEAD_RECHECKED=PASS")
        print("MERGE_AUTHORIZED=FALSE")
    except (OSError, Denied) as exc:
        raise SystemExit("GITHUB_SOURCE_UNQUALIFIED: " + str(exc))


if __name__ == "__main__":
    main()
