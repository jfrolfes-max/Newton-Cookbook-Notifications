# Newton-Cookbook-Notifications
This repo scrapes a spreadsheet of the BO3 Newton Cookbook rotation and sends a daily email with an update of the next seven days of Cookbook offerings.

## How it works

`cookbook_notifier.py` downloads the "Cycle" sheet of the tracked
[Google Sheet](https://docs.google.com/spreadsheets/d/1kW-tmIrov1xx5UjZ8bRvGq6-VcXgspDFrGoiC02XIC0)
as CSV, then uses the cycle's known Day 1 anchor date to compute which of the 36 cycle days
corresponds to today (and the next 6 days). It emails the resulting 7-day schedule, including
each recipe's inputs/quantities and output/quantity.

## Setup

1. `pip install -r requirements.txt`
2. Export your SMTP credentials as environment variables (a Gmail App Password works well with
   the default `smtp.gmail.com` host): `SMTP_USERNAME`, `SMTP_PASSWORD`. These are the only
   values you need to set — SMTP host/port and the recipient address are already set as
   defaults in `cookbook_notifier.py` and can be overridden via `SMTP_HOST`, `SMTP_PORT`, or
   `EMAIL_TO` env vars if needed.
3. Run it:

   ```bash
   export SMTP_USERNAME=your-account@gmail.com
   export SMTP_PASSWORD=your-app-password
   python cookbook_notifier.py
   ```

A GitHub Actions workflow ([.github/workflows/daily-email.yml](.github/workflows/daily-email.yml))
is included to run this automatically once a day using repository secrets
(`SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_FROM`).
