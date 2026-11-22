#!/usr/bin/env python3
"""
Read the daily contribution counts GitHub already serves for the profile calendar
(github.com/users/<name>/contributions, public, no token) and write
data/contributions.json: the current calendar year's days plus totals, best day and
monthly totals, with streaks taken from the rolling 12 months.

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


def fetch_days(year=None):
    """Without a year: GitHub's default rolling 12 months, ending today.
    With a year: that calendar year, Jan 1 to Dec 31 (days after today count 0)."""
    url = f"https://github.com/users/{USER}/contributions"
    if year:
        url += f"?from={year}-01-01&to={year}-12-31"
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


def summarize(rolling, days):
    """The cards show the calendar year in `days`; streaks come from the rolling
    window so they don't reset on Jan 1."""
    today = rolling[-1]["date"]  # GitHub's own "today"
    cur, longest = streaks(rolling)
    so_far = [d for d in days if d["date"] <= today]
    monthly = {}
    for d in days:
        monthly[d["date"][:7]] = monthly.get(d["date"][:7], 0) + d["count"]
    return {
        "username": USER,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "year": int(today[:4]),
        "today": today,
        "total": sum(d["count"] for d in so_far),
        "active_days": sum(1 for d in so_far if d["count"]),
        "days_so_far": len(so_far),
        "current_streak": cur,
        "longest_streak": longest,
        "best_day": max(so_far, key=lambda d: d["count"]),
        "monthly": [{"month": k, "total": v} for k, v in sorted(monthly.items())],
        "days": days,
    }


if __name__ == "__main__":
    rolling = fetch_days()
    data = summarize(rolling, fetch_days(int(rolling[-1]["date"][:4])))
    with open(OUT, "w") as f:
        json.dump(data, f, indent=1)
    print(f"{data['total']} contributions, streak {data['current_streak']}, longest {data['longest_streak']}")
