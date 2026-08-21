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
2. Run it, passing your email credentials (a Gmail App Password works well with the default
   `smtp.gmail.com` host) inline on the command: `EMAIL_USERNAME`, `EMAIL_PASSWORD`. These are
   the only values you need to set — SMTP host/port and the recipient address are already set
   as defaults in `cookbook_notifier.py` and can be overridden via `SMTP_HOST`, `SMTP_PORT`, or
   `EMAIL_TO` if needed.

   ```bash
   EMAIL_USERNAME=your-account@gmail.com EMAIL_PASSWORD=your-app-password python cookbook_notifier.py
   ```

## Running on a schedule

Keep credentials out of the crontab itself by using the included `run_notifier.sh` wrapper,
which loads them from a `secrets.env` file next to it:

1. `cp secrets.env.example secrets.env` and fill in your real `EMAIL_USERNAME`/`EMAIL_PASSWORD`.
2. `chmod 600 secrets.env` so only your user can read it (it's already git-ignored).
3. Add a crontab entry that just calls the wrapper, e.g. to run daily at 9am:

   ```cron
   0 9 * * * /path/to/run_notifier.sh >> /path/to/cookbook_notifier.log 2>&1
   ```
