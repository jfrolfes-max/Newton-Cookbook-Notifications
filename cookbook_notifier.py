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
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape

import requests

SPREADSHEET_ID = "1kW-tmIrov1xx5UjZ8bRvGq6-VcXgspDFrGoiC02XIC0"
CYCLE_SHEET_GID = "1664926067"  # "Cycle" tab
CYCLE_LENGTH_DAYS = 36
CSV_URL = (
    f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export"
    f"?format=csv&gid={CYCLE_SHEET_GID}"
)

# The sheet's anchor date has drifted 1 day behind the real in-game rotation;
# this manual correction keeps the computed cycle day aligned with reality.
CYCLE_DAY_ADJUSTMENT = 1

# Non-secret defaults, overridable via environment variables. Credentials
# (EMAIL_USERNAME / EMAIL_PASSWORD) are intentionally NOT hardcoded here and
# must always be supplied via environment variables / CI secrets.
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_TO = ["jfrolfes@gmail.com", "clay-smith10@outlook.com"]


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
    day_num = offset + 1 + CYCLE_DAY_ADJUSTMENT
    return (day_num - 1) % CYCLE_LENGTH_DAYS + 1


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


def format_recipe_html(recipe):
    inputs = f"{escape(recipe['qty1'])}x {escape(recipe['input1'])}"
    if recipe["input2"]:
        inputs += f" + {escape(recipe['qty2'])}x {escape(recipe['input2'])}"
    return (
        "<tr>"
        f'<td style="padding:5px 0;color:#4b5563;font-size:14px;white-space:nowrap;">{inputs}</td>'
        '<td style="padding:5px 10px;color:#9ca3af;font-size:14px;">&#8594;</td>'
        '<td style="padding:5px 0;color:#111827;font-size:14px;font-weight:600;">'
        f'{escape(recipe["qty_out"])}x {escape(recipe["output"])}</td>'
        "</tr>"
    )


def build_email_html(recipes_by_day, day1_date, start_date, num_days=7):
    day_cards = []
    for i in range(num_days):
        current_date = start_date + timedelta(days=i)
        day_num = cycle_day_for_date(current_date, day1_date)
        is_today = i == 0
        label = "Today" if is_today else current_date.strftime("%A")

        rows_html = "".join(
            format_recipe_html(recipe) for recipe in recipes_by_day.get(day_num, [])
        )
        card_bg = "#eef2ff" if is_today else "#ffffff"
        border_color = "#6366f1" if is_today else "#e5e7eb"
        badge_bg = "#6366f1" if is_today else "#9ca3af"

        day_cards.append(f"""
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
               style="background:{card_bg};border:1px solid {border_color};border-radius:10px;margin-bottom:14px;">
          <tr>
            <td style="padding:14px 16px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="left" style="font-size:16px;font-weight:700;color:#111827;">{escape(label)}</td>
                  <td align="right" style="font-size:11px;font-weight:700;color:#ffffff;background:{badge_bg};
                             padding:3px 10px;border-radius:999px;">DAY {day_num}</td>
                </tr>
              </table>
              <div style="font-size:12px;color:#6b7280;margin-top:2px;">{current_date.isoformat()}</div>
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:8px;">
                {rows_html}
              </table>
            </td>
          </tr>
        </table>
        """)

    return f"""\
<html>
  <head><meta charset="utf-8"></head>
  <body style="margin:0;padding:0;background:#f3f4f6;font-family:Segoe UI, Roboto, Helvetica, Arial, sans-serif;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:24px 0;">
      <tr>
        <td align="center">
          <table role="presentation" width="600" cellpadding="0" cellspacing="0"
                 style="background:#ffffff;border-radius:12px;overflow:hidden;">
            <tr>
              <td style="background:#111827;padding:20px 24px;">
                <span style="font-size:20px;">🧪</span>
                <span style="font-size:18px;font-weight:700;color:#ffffff;margin-left:6px;">Newton's Cookbook</span>
                <div style="font-size:13px;color:#9ca3af;margin-top:2px;">Next {num_days} days of recipes</div>
              </td>
            </tr>
            <tr>
              <td style="padding:20px 20px 8px 20px;">
                {''.join(day_cards)}
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


def send_email(subject, text_body, html_body, to_addr):
    smtp_host = os.environ.get("SMTP_HOST", SMTP_HOST)
    smtp_port = int(os.environ.get("SMTP_PORT", SMTP_PORT))
    smtp_username = os.environ["EMAIL_USERNAME"]
    smtp_password = os.environ["EMAIL_PASSWORD"]
    from_addr = os.environ.get("EMAIL_FROM", smtp_username)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.sendmail(from_addr, [to_addr], msg.as_string())


def main():
    to_addr = os.environ.get("EMAIL_TO", EMAIL_TO)
    today = datetime.now(timezone.utc).date()

    rows = fetch_cycle_rows()
    recipes_by_day, day1_date = parse_recipes_by_day(rows)
    text_body = build_email_body(recipes_by_day, day1_date, today, num_days=7)
    html_body = build_email_html(recipes_by_day, day1_date, today, num_days=7)

    subject = f"Newton's Cookbook - {today.isoformat()} + next 6 days"
    send_email(subject, text_body, html_body, to_addr)
    print(text_body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
