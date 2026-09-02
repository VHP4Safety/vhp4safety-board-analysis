#!/usr/bin/env python3
"""Export a GitHub Projects (v2) organisation board to board.json / board.csv.

Used to produce the VHP4Safety "Scrum@VHP4S" dataset analysed in the
supplementary information of Teunis et al. (2026).

    export GITHUB_TOKEN=<token with read:project + repo scope>
    python3 fetch_board.py --org VHP4Safety --project 7 --redact

Writes data/items_raw.jsonl (raw GraphQL nodes) and data/board.{json,csv}
(flattened, one row per board item).

--redact reduces the export to the seven fields the published figures consume:
content_type, state, repo, created, closed, merged, item_updated. Everything
else is withheld: the project board is an internal consortium resource, and its
titles, contributors, labels, epics, milestones and field values are not
released. Every figure and summary statistic in the supplement reproduces
exactly from the reduced export.
"""
import argparse
import csv
import json
import os
import sys
import urllib.request

API = "https://api.github.com/graphql"

QUERY = """
query($org: String!, $number: Int!, $cursor: String) {
  organization(login: $org) {
    projectV2(number: $number) {
      title
      items(first: 100, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          type
          createdAt
          updatedAt
          isArchived
          fieldValues(first: 30) {
            nodes {
              __typename
              ... on ProjectV2ItemFieldTextValue      { text   field { ... on ProjectV2FieldCommon { name } } }
              ... on ProjectV2ItemFieldNumberValue    { number field { ... on ProjectV2FieldCommon { name } } }
              ... on ProjectV2ItemFieldSingleSelectValue { name field { ... on ProjectV2FieldCommon { name } } }
            }
          }
          content {
            __typename
            ... on DraftIssue { title createdAt updatedAt }
            ... on Issue {
              number title state createdAt closedAt updatedAt
              repository { name }
              author { login }
              assignees(first: 20) { nodes { login } }
              labels(first: 30) { nodes { name } }
              milestone { title }
              comments { totalCount }
            }
            ... on PullRequest {
              number title state createdAt closedAt mergedAt updatedAt
              repository { name }
              author { login }
              assignees(first: 20) { nodes { login } }
              labels(first: 30) { nodes { name } }
              milestone { title }
              comments { totalCount }
            }
          }
        }
      }
    }
  }
}
"""

FIELDS = ["item_id", "item_type", "content_type", "number", "title", "state",
          "repo", "author", "assignees", "n_assignees", "labels", "milestone",
          "created", "closed", "merged", "item_created", "item_updated",
          "status", "priority", "size", "estimate", "epic", "case_study", "event"]

# the only fields released publicly (see --redact in the module docstring)
REDACTED_FIELDS = ["content_type", "state", "repo", "created", "closed",
                   "merged", "item_updated"]

# board custom field name -> output column
CUSTOM = {"Status": "status", "Priority": "priority", "Size": "size",
          "Estimate": "estimate", "Related epic": "epic",
          "Case Study": "case_study", "Event": "event"}


def post(token, variables):
    req = urllib.request.Request(
        API,
        data=json.dumps({"query": QUERY, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}",
                 "Content-Type": "application/json",
                 "User-Agent": "vhp4safety-board-analysis"},
    )
    with urllib.request.urlopen(req) as r:
        payload = json.load(r)
    if "errors" in payload:
        sys.exit(f"GraphQL error: {json.dumps(payload['errors'], indent=2)}")
    return payload["data"]["organization"]["projectV2"]


def fetch(org, number, token):
    nodes, cursor = [], None
    while True:
        proj = post(token, {"org": org, "number": number, "cursor": cursor})
        page = proj["items"]
        nodes.extend(page["nodes"])
        print(f"  fetched {len(nodes)} items", file=sys.stderr)
        if not page["pageInfo"]["hasNextPage"]:
            return proj["title"], nodes
        cursor = page["pageInfo"]["endCursor"]


def flatten(node, redact=False):
    c = node.get("content") or {}
    row = dict.fromkeys(FIELDS)
    row["item_id"] = node["id"]
    row["item_type"] = node["type"]
    row["content_type"] = c.get("__typename")
    row["item_created"] = node["createdAt"]
    row["item_updated"] = node["updatedAt"]
    row["number"] = c.get("number")
    row["state"] = c.get("state")
    row["repo"] = (c.get("repository") or {}).get("name")
    row["created"] = c.get("createdAt")
    row["closed"] = c.get("closedAt")
    row["merged"] = c.get("mergedAt")
    row["milestone"] = (c.get("milestone") or {}).get("title")
    row["labels"] = "|".join(n["name"] for n in (c.get("labels") or {}).get("nodes", []))

    assignees = [n["login"] for n in (c.get("assignees") or {}).get("nodes", [])]
    row["n_assignees"] = len(assignees)
    if not redact:
        row["title"] = c.get("title")
        row["author"] = (c.get("author") or {}).get("login")
        row["assignees"] = "|".join(assignees)

    for fv in (node.get("fieldValues") or {}).get("nodes", []):
        name = (fv.get("field") or {}).get("name")
        col = CUSTOM.get(name)
        if not col:
            continue
        row[col] = fv.get("name") or fv.get("text") or fv.get("number")
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--org", default="VHP4Safety")
    ap.add_argument("--project", type=int, default=7)
    ap.add_argument("--outdir", default="data")
    ap.add_argument("--redact", action="store_true",
                    help="omit title, author and assignee logins")
    args = ap.parse_args()

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        sys.exit("set GITHUB_TOKEN (needs read:project and repo scope)")

    os.makedirs(args.outdir, exist_ok=True)
    title, nodes = fetch(args.org, args.project, token)
    print(f'project "{title}": {len(nodes)} items', file=sys.stderr)

    with open(f"{args.outdir}/items_raw.jsonl", "w") as f:
        for n in nodes:
            f.write(json.dumps(n) + "\n")

    rows = [flatten(n, args.redact) for n in nodes]
    fields = REDACTED_FIELDS if args.redact else FIELDS
    rows = [{k: r[k] for k in fields} for r in rows]

    json.dump(rows, open(f"{args.outdir}/board.json", "w"), indent=1)
    with open(f"{args.outdir}/board.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {args.outdir}/board.json, board.csv ({len(rows)} rows"
          f"{', reduced' if args.redact else ''})", file=sys.stderr)


if __name__ == "__main__":
    main()
