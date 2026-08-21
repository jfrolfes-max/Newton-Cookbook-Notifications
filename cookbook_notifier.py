#!/usr/bin/env python3
"""Scrape the Newton's Cookbook cycle spreadsheet and email the upcoming 7 days of recipes.

The cycle repeats every 36 days. Day 1 of the currently observed cycle is anchored to the
date found in the "DATE UTC (CURRENT CYCLE)" column of the "Cycle" sheet, and every
subsequent date's position in the cycle is derived with simple modular arithmetic.
"""

import csv
import io
import os
import smtplib
import sys
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText

import requests

SPREADSHEET_ID = "1kW-tmIrov1xx5UjZ8bRvGq6-VcXgspDFrGoiC02XIC0"
CYCLE_SHEET_GID = "1664926067"  # "Cycle" tab
CYCLE_LENGTH_DAYS = 36
CSV_URL = (
    f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export"
    f"?format=csv&gid={CYCLE_SHEET_GID}"
)

# Non-secret defaults, overridable via environment variables. Credentials
# (EMAIL_USERNAME / EMAIL_PASSWORD) are intentionally NOT hardcoded here and
# must always be supplied via environment variables / CI secrets.
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_TO = "jfrolfes@gmail.com"


def fetch_cycle_rows():
    """Download the 'Cycle' sheet and return it as a list of CSV rows (header included)."""
    response = requests.get(CSV_URL, timeout=30)
    response.raise_for_status()
    return list(csv.reader(io.StringIO(response.text)))


def parse_recipes_by_day(rows):
    """Group recipe rows by their cycle DAY (1-36).

    Returns a tuple of (recipes_by_day, day1_date) where day1_date is the calendar
    date that corresponds to Day 1 of the currently tracked cycle.
    """
    header = rows[0]
    idx = {name: i for i, name in enumerate(header)}

    recipes_by_day = {}
    day1_date = None

    for row in rows[1:]:
        if not row or not row[idx["DAY"]].strip():
            continue

        day_num = int(row[idx["DAY"]])
        recipe = {
            "qty1": row[idx["Q1"]].strip(),
            "input1": row[idx["INPUT 1"]].strip(),
            "qty2": row[idx["Q2"]].strip(),
            "input2": row[idx["INPUT 2"]].strip(),
            "qty_out": row[idx["Q3"]].strip(),
            "output": row[idx["OUTPUT"]].strip(),
        }
        recipes_by_day.setdefault(day_num, []).append(recipe)

        if day_num == 1 and day1_date is None:
            day1_date = datetime.strptime(
                row[idx["DATE UTC (CURRENT CYCLE)"]].strip(), "%B %d, %Y"
            ).date()

    if day1_date is None:
        raise ValueError("Could not find a Day 1 anchor date in the 'Cycle' sheet.")

    return recipes_by_day, day1_date


def cycle_day_for_date(target_date, day1_date):
    """Return which day (1-36) of the 36-day cycle falls on target_date."""
    offset = (target_date - day1_date).days % CYCLE_LENGTH_DAYS
    return offset + 1


def format_recipe(recipe):
    inputs = f"{recipe['qty1']}x {recipe['input1']}"
    if recipe["input2"]:
        inputs += f" + {recipe['qty2']}x {recipe['input2']}"
    return f"{inputs} -> {recipe['qty_out']}x {recipe['output']}"


def build_email_body(recipes_by_day, day1_date, start_date, num_days=7):
    lines = []
    for i in range(num_days):
        current_date = start_date + timedelta(days=i)
        day_num = cycle_day_for_date(current_date, day1_date)
        label = "Today" if i == 0 else current_date.strftime("%A")
        lines.append(f"{label} ({current_date.isoformat()}) - Cycle Day {day_num}")
        for recipe in recipes_by_day.get(day_num, []):
            lines.append(f"  - {format_recipe(recipe)}")
        lines.append("")
    return "\n".join(lines).strip()


def send_email(subject, body, to_addr):
    smtp_host = os.environ.get("SMTP_HOST", SMTP_HOST)
    smtp_port = int(os.environ.get("SMTP_PORT", SMTP_PORT))
    smtp_username = os.environ["EMAIL_USERNAME"]
    smtp_password = os.environ["EMAIL_PASSWORD"]
    from_addr = os.environ.get("EMAIL_FROM", smtp_username)

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.sendmail(from_addr, [to_addr], msg.as_string())


def main():
    to_addr = os.environ.get("EMAIL_TO", EMAIL_TO)
    today = datetime.now(timezone.utc).date()

    rows = fetch_cycle_rows()
    recipes_by_day, day1_date = parse_recipes_by_day(rows)
    body = build_email_body(recipes_by_day, day1_date, today, num_days=7)

    subject = f"Newton's Cookbook - {today.isoformat()} + next 6 days"
    send_email(subject, body, to_addr)
    print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
