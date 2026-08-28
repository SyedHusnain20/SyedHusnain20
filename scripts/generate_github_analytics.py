
#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import urllib.request
from datetime import date, timedelta
from pathlib import Path

USERNAME = os.environ.get("GITHUB_USERNAME", "SyedHusnain20")
TOKEN = os.environ.get("GITHUB_TOKEN")
OUT = Path("assets")
OUT.mkdir(parents=True, exist_ok=True)

if not TOKEN:
    raise SystemExit("GITHUB_TOKEN is required.")

QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(first: 1, ownerAffiliations: OWNER, privacy: PUBLIC) {
      totalCount
    }
    contributionsCollection {
      totalCommitContributions
      totalIssueContributions
      totalPullRequestContributions
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""

def graphql(query: str, variables: dict) -> dict:
    body = json.dumps({"query": query, "variables": variables}).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2026-03-10",
            "User-Agent": "github-profile-analytics",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if payload.get("errors"):
        raise RuntimeError(json.dumps(payload["errors"], indent=2))
    return payload["data"]["user"]

def esc(value):
    return (
        str(value).replace("&", "&amp;").replace("<", "&lt;")
        .replace(">", "&gt;").replace('"', "&quot;")
    )

def svg_header(width, height, title):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" rx="16" fill="#0d1117" stroke="#30363d"/>
<style>
.title{{font:700 22px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;fill:#c9d1d9}}
.label{{font:600 13px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;fill:#8b949e}}
.value{{font:700 27px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;fill:#58a6ff}}
.small{{font:500 11px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;fill:#8b949e}}
</style>
<text x="28" y="38" class="title">{esc(title)}</text>
"""

def write_stats(stats):
    s = svg_header(820, 280, "GitHub Analytics")
    cards = [
        ("PUBLIC REPOS", stats["repos"]),
        ("STARS RECEIVED", stats["stars"]),
        ("CONTRIBUTIONS", stats["contributions"]),
        ("COMMITS · 1Y", stats["commits"]),
        ("PULL REQUESTS · 1Y", stats["prs"]),
        ("ISSUES · 1Y", stats["issues"]),
    ]
    positions = [(28, 62), (286, 62), (544, 62), (28, 164), (286, 164), (544, 164)]
    for (label, value), (x, y) in zip(cards, positions):
        s += f'<rect x="{x}" y="{y}" width="230" height="78" rx="12" fill="#161b22" stroke="#30363d"/>'
        s += f'<text x="{x+16}" y="{y+25}" class="label">{esc(label)}</text>'
        s += f'<text x="{x+16}" y="{y+58}" class="value">{esc(value)}</text>'
    s += f'<text x="28" y="266" class="small">Updated automatically • @{esc(USERNAME)} • public GitHub activity</text></svg>'
    (OUT / "github-stats.svg").write_text(s, encoding="utf-8")

def write_streak(days):
    ordered = sorted((date.fromisoformat(d), c) for d, c in days.items())
    current = 0
    cursor = date.today()
    while days.get(cursor.isoformat(), 0) > 0:
        current += 1
        cursor -= timedelta(days=1)

    longest = 0
    run = 0
    previous = None
    for d, count in ordered:
        if count > 0:
            run = run + 1 if previous is not None and d == previous + timedelta(days=1) else 1
            longest = max(longest, run)
            previous = d
        else:
            run = 0
            previous = None

    active = sum(1 for c in days.values() if c > 0)
    s = svg_header(820, 230, "Contribution Streak")
    cards = [
        ("CURRENT STREAK", f"{current} days"),
        ("LONGEST STREAK", f"{longest} days"),
        ("ACTIVE DAYS · 1Y", str(active)),
    ]
    for i, (label, value) in enumerate(cards):
        x = 28 + i * 258
        s += f'<rect x="{x}" y="66" width="230" height="92" rx="12" fill="#161b22" stroke="#30363d"/>'
        s += f'<text x="{x+16}" y="94" class="label">{esc(label)}</text>'
        s += f'<text x="{x+16}" y="132" class="value">{esc(value)}</text>'
    s += '<text x="28" y="200" class="small">Calculated from GitHub contribution calendar • updated daily</text></svg>'
    (OUT / "github-streak.svg").write_text(s, encoding="utf-8")

def color(count):
    if count <= 0: return "#161b22"
    if count == 1: return "#0e4429"
    if count <= 3: return "#006d32"
    if count <= 6: return "#26a641"
    return "#39d353"

def write_heatmap(days):
    end = max(date.fromisoformat(d) for d in days)
    start = end - timedelta(days=370)
    while start.weekday() != 6:
        start -= timedelta(days=1)

    weeks = []
    cursor = start
    while cursor <= end:
        week = []
        for _ in range(7):
            week.append(cursor)
            cursor += timedelta(days=1)
        weeks.append(week)

    cell, gap, left, top = 12, 4, 52, 62
    width = left + len(weeks) * (cell + gap) + 20
    height = 7 * (cell + gap) + top + 30

    s = svg_header(width, height, "Contribution Activity — Last Year")
    for row, label in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
        y = top + row * (cell + gap) + 10
        s += f'<text x="8" y="{y}" class="small">{label}</text>'

    for col, week in enumerate(weeks):
        x = left + col * (cell + gap)
        for row, d in enumerate(week):
            count = days.get(d.isoformat(), 0)
            y = top + row * (cell + gap)
            s += f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{color(count)}"><title>{d.isoformat()}: {count} contribution(s)</title></rect>'

    s += f'<text x="8" y="{height-10}" class="small">Less</text>'
    legend_x = 42
    for i, count in enumerate([0, 1, 3, 6, 7]):
        s += f'<rect x="{legend_x+i*18}" y="{height-20}" width="12" height="12" rx="3" fill="{color(count)}"/>'
    s += f'<text x="{legend_x+100}" y="{height-10}" class="small">More</text></svg>'
    (OUT / "contribution-graph.svg").write_text(s, encoding="utf-8")

def write_commit_graph(days):
    end = max(date.fromisoformat(d) for d in days)
    start = end - timedelta(days=365)
    monthly = {}
    cursor = start
    while cursor <= end:
        monthly.setdefault(cursor.strftime("%b"), 0)
        cursor += timedelta(days=1)

    cursor = start
    while cursor <= end:
        monthly[cursor.strftime("%b")] += days.get(cursor.isoformat(), 0)
        cursor += timedelta(days=1)

    labels, values = list(monthly), list(monthly.values())
    max_value = max(values or [1])
    w, h, left, right, top, bottom = 980, 320, 55, 25, 70, 48
    chart_w, chart_h = w-left-right, h-top-bottom
    step = chart_w / max(1, len(values)-1)

    points = []
    for i, value in enumerate(values):
        x = left + i * step
        y = top + chart_h - (value / max_value) * chart_h
        points.append((x, y))

    s = svg_header(w, h, "Commit / Contribution Activity — Last 12 Months")
    for i in range(5):
        y = top + i * chart_h / 4
        s += f'<line x1="{left}" y1="{y:.1f}" x2="{w-right}" y2="{y:.1f}" stroke="#21262d"/>'

    s += '<polyline points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in points) + '" fill="none" stroke="#58a6ff" stroke-width="3"/>'
    for (x, y), value, label in zip(points, values, labels):
        s += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#58a6ff"><title>{label}: {value} contributions</title></circle>'
        s += f'<text x="{x:.1f}" y="{h-22}" text-anchor="middle" class="small">{esc(label)}</text>'
    s += f'<text x="{left}" y="55" class="small">Daily contribution totals aggregated by month</text></svg>'
    (OUT / "commit-activity.svg").write_text(s, encoding="utf-8")

def main():
    user = graphql(QUERY, {"login": USERNAME})
    collection = user["contributionsCollection"]

    days = {}
    for week in collection["contributionCalendar"]["weeks"]:
        for d in week["contributionDays"]:
            days[d["date"]] = d["contributionCount"]

    request = urllib.request.Request(
        f"https://api.github.com/users/{USERNAME}/repos?per_page=100&type=owner",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
            "User-Agent": "github-profile-analytics",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        repo_list = json.load(response)

    public_repos = [r for r in repo_list if not r.get("private", False)]
    stats = {
        "repos": len(public_repos),
        "stars": sum(r.get("stargazers_count", 0) for r in public_repos),
        "contributions": collection["contributionCalendar"]["totalContributions"],
        "commits": collection["totalCommitContributions"],
        "prs": collection["totalPullRequestContributions"],
        "issues": collection["totalIssueContributions"],
    }

    write_stats(stats)
    write_streak(days)
    write_heatmap(days)
    write_commit_graph(days)
    print(json.dumps(stats, indent=2))

if __name__ == "__main__":
    main()
