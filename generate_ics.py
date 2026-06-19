#!/usr/bin/env python3
"""
Generates an ICS calendar feed with one all-day event per day showing
that day's rainfall total, for the previous calendar month, in Fargo, ND.

Data source: Open-Meteo's free Historical Weather API (no API key needed).
https://open-meteo.com/en/docs/historical-weather-api

Designed to be run on a schedule (e.g. via GitHub Actions) so the output
file (rainfall.ics) lives at a stable URL that Google Calendar can
subscribe to ("Other calendars" -> "+" -> "From URL").

Each time it runs, it regenerates the feed for whatever the "previous
month" is relative to today -- so the feed automatically rolls over on
the 1st of each month.
"""

import requests
from datetime import date, datetime, timedelta

# --- Configuration -----------------------------------------------------
LATITUDE = 46.8772
LONGITUDE = -96.7898
TIMEZONE = "America/Chicago"
OUTPUT_FILE = "rainfall.ics"
CALENDAR_NAME = "Fargo Rainfall"
# ------------------------------------------------------------------------


def previous_month_range(today=None):
    """Return (first_day, last_day) of the calendar month before today."""
    today = today or date.today()
    first_of_this_month = today.replace(day=1)
    last_day_prev_month = first_of_this_month - timedelta(days=1)
    first_day_prev_month = last_day_prev_month.replace(day=1)
    return first_day_prev_month, last_day_prev_month


def fetch_daily_precip(start, end):
    """Call Open-Meteo and return a list of (YYYY-MM-DD, inches) tuples."""
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": "precipitation_sum",
        "precipitation_unit": "inch",
        "timezone": TIMEZONE,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    dates = data["daily"]["time"]
    totals = data["daily"]["precipitation_sum"]
    return list(zip(dates, totals))


def build_ics(daily_data, month_label):
    now_stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Seth Rainfall Feed//Fargo ND//EN",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{CALENDAR_NAME} - {month_label}",
        f"X-WR-TIMEZONE:{TIMEZONE}",
    ]

    for day_str, total in daily_data:
        amount = total if total is not None else 0.0
        day = date.fromisoformat(day_str)
        next_day = day + timedelta(days=1)  # DTEND is exclusive for all-day events
        uid = f"rainfall-{day_str}@fargo-rainfall-feed"
        summary = f"\U0001F327\uFE0F {amount:.2f} in rain"

        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_stamp}",
            f"DTSTART;VALUE=DATE:{day.strftime('%Y%m%d')}",
            f"DTEND;VALUE=DATE:{next_day.strftime('%Y%m%d')}",
            f"SUMMARY:{summary}",
            "TRANSP:TRANSPARENT",
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def main():
    start, end = previous_month_range()
    daily = fetch_daily_precip(start, end)
    month_label = start.strftime("%B %Y")
    ics_content = build_ics(daily, month_label)

    with open(OUTPUT_FILE, "w") as f:
        f.write(ics_content)

    print(f"Wrote {OUTPUT_FILE} for {month_label} ({len(daily)} days)")


if __name__ == "__main__":
    main()
