#!/usr/bin/env python3
"""
Read the daily contribution counts GitHub already serves for the profile calendar
(github.com/users/<name>/contributions, public, no token) and write
data/contributions.json: the raw days plus streaks, best day and monthly totals.

Run daily by .github/workflows/update-cards.yml, before render_cards.py.
"""
import datetime
import json
import os
import re
import sys

import requests
from bs4 import BeautifulSoup

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
PROFILE = json.load(open(os.path.join(ROOT, "data", "profile.json")))
USER = os.environ.get("GH_USER", PROFILE["username"])
OUT = os.path.join(ROOT, "data", "contributions.json")


def fetch_days():
    url = f"https://github.com/users/{USER}/contributions"
    resp = requests.get(url, headers={"User-Agent": "profile-cards/1.0"}, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    tips = {t.get("for"): t.get_text(strip=True) for t in soup.find_all("tool-tip")}
    days = []
    for td in soup.select("td.ContributionCalendar-day"):
        date = td.get("data-date")
        if not date:
            continue
        text = tips.get(td.get("id"), "")
        m = re.match(r"(\d[\d,]*)", text)
        count = int(m.group(1).replace(",", "")) if m and "No contributions" not in text else 0
        days.append({"date": date, "count": count})
    if not days:
        sys.exit("no calendar cells found: GitHub's markup may have changed")
    return sorted(days, key=lambda d: d["date"])


def streaks(days):
    counts = [d["count"] for d in days]
    i = len(counts) - 1
    if counts[i] == 0:  # today isn't over yet, so it doesn't break the streak
        i -= 1
    end = i
    while i >= 0 and counts[i] > 0:
        i -= 1
    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    return end - i, longest


def summarize(days):
    cur, longest = streaks(days)
    monthly = {}
    for d in days:
        monthly[d["date"][:7]] = monthly.get(d["date"][:7], 0) + d["count"]
    return {
        "username": USER,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total": sum(d["count"] for d in days),
        "active_days": sum(1 for d in days if d["count"]),
        "current_streak": cur,
        "longest_streak": longest,
        "best_day": max(days, key=lambda d: d["count"]),
        "monthly": [{"month": k, "total": v} for k, v in sorted(monthly.items())],
        "days": days,
    }


if __name__ == "__main__":
    data = summarize(fetch_days())
    with open(OUT, "w") as f:
        json.dump(data, f, indent=1)
    print(f"{data['total']} contributions, streak {data['current_streak']}, longest {data['longest_streak']}")
