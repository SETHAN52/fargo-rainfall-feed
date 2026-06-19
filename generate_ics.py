#!/usr/bin/env python3
"""
Generates an ICS calendar feed with one all-day event per day showing
that day's rainfall total, for a rolling window of the most recent days,
in Fargo, ND.

Data source: Open-Meteo's free Weather Forecast API, using the
"past_days" parameter for seamless access to recent history (no API key
needed). https://open-meteo.com/en/docs

Designed to be run on a schedule (e.g. via GitHub Actions) so the output
file (rainfall.ics) lives at a stable URL that Google Calendar can
subscribe to ("Other calendars" -> "+" -> "From URL").

Each time it runs, the window simply slides forward to "today minus
ROLLING_DAYS" through today, so the feed is always showing the most
recent stretch of days.
"""

import requests
from datetime import date, datetime

# --- Configuration -----------------------------------------------------
LATITUDE = 46.8772
LONGITUDE = -96.7898
TIMEZONE = "America/Chicago"
OUTPUT_FILE = "rainfall.ics"
CALENDAR_NAME = "Fargo Rainfall"
ROLLING_DAYS = 30  # how many past days to include, in addition to today
# ------------------------------------------------------------------------


def fetch_daily_precip(days=ROLLING_DAYS):
    """Return a list of (YYYY-MM-DD, inches) tuples for the last `days`
    days plus today, using Open-Meteo's forecast endpoint with past_days."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "daily": "precipitation_sum",
        "precipitation_unit": "inch",
        "timezone": TIMEZONE,
        "past_days": days,
        "forecast_days": 1,  # just today; we filter out any future days below
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    dates = data["daily"]["time"]
    totals = data["daily"]["precipitation_sum"]

    today_str = date.today().isoformat()
    return [(d, t) for d, t in zip(dates, totals) if d <= today_str]


def build_ics(daily_data):
    now_stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Seth Rainfall Feed//Fargo ND//EN",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{CALENDAR_NAME} - Last {ROLLING_DAYS} Days",
        f"X-WR-TIMEZONE:{TIMEZONE}",
    ]

    from datetime import timedelta

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
    daily = fetch_daily_precip()
    ics_content = build_ics(daily)

    with open(OUTPUT_FILE, "w") as f:
        f.write(ics_content)

    print(f"Wrote {OUTPUT_FILE} covering {len(daily)} days (rolling {ROLLING_DAYS}-day window)")


if __name__ == "__main__":
    main()
