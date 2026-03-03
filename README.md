# Canvas Deadline Text Reminder (JHU)

This project pulls your upcoming Canvas assignments and sends reminders.

## What it does

- Pulls assignment due dates from either:
  - Canvas Calendar Feed (recommended)
  - Canvas API (optional fallback)
- Sends:
  - a reminder about 3 days before due
  - a reminder when the assignment is due today
  - a reminder about 3 hours before due
- Delivery modes:
  - Email-to-text gateway (free, recommended)
  - Twilio SMS (paid optional fallback)
- Deduplicates reminders with a local SQLite state file (`state.db`).

## 1) Create GitHub repo

```bash
cd /Users/muammerkara/Desktop/ReminderProject
git init
git add .
git commit -m "Initial Canvas SMS reminder MVP"
gh repo create canvas-deadline-reminder --public --source=. --remote=origin --push
```

If you do not use `gh`, create a repo in GitHub UI and then run:

```bash
git remote add origin <your-repo-url>
git branch -M main
git push -u origin main
```

## 2) Get credentials

### Canvas (recommended: Calendar Feed URL)

Use this if JHU blocks personal access tokens.

1. Open [https://canvas.jhu.edu](https://canvas.jhu.edu) and log in
2. Click `Calendar` in the left navigation
3. In the right sidebar, click `Calendar Feed`
4. Copy the long private iCal URL
5. Put it in `.env`:
   - `CANVAS_ICAL_URL=https://...`

Keep this URL secret. Anyone with it can read your assignment calendar.

### Canvas API (optional fallback)

1. Open [https://canvas.jhu.edu](https://canvas.jhu.edu)
2. Go to `Account -> Settings`
3. Under `Approved Integrations`, create a `New Access Token`
4. Copy token to `CANVAS_API_TOKEN`

Use `CANVAS_BASE_URL=https://jhu.instructure.com`.

### Free SMS via Email-to-Text Gateway (recommended)

1. Choose your carrier gateway address for `NOTIFY_TARGET`:
   - AT&T: `number@txt.att.net`
   - Verizon: `number@vtext.com`
   - T-Mobile: `number@tmomail.net`
2. Use an SMTP email account to send the messages (Gmail is easiest):
   - `SMTP_HOST=smtp.gmail.com`
   - `SMTP_PORT=587`
   - `SMTP_USERNAME=your_email@gmail.com`
   - `SMTP_FROM_EMAIL=your_email@gmail.com`
3. Create a Gmail App Password for `SMTP_PASSWORD`:
   - Google Account -> Security -> 2-Step Verification (must be on)
   - Security -> App passwords -> create one for Mail
   - Put that generated password in `.env`
4. Set:
   - `NOTIFIER_MODE=email_gateway`
   - `NOTIFY_TARGET=<your carrier gateway email>`

### Twilio (optional fallback)

1. Create/login at [https://www.twilio.com](https://www.twilio.com)
2. Buy/setup an SMS-capable Twilio number
3. Copy:
   - `TWILIO_ACCOUNT_SID`
   - `TWILIO_AUTH_TOKEN`
   - `TWILIO_FROM_NUMBER`
4. Set:
   - `NOTIFIER_MODE=twilio`
   - `NOTIFY_TARGET=+1...`

## 3) Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill one notification mode plus one Canvas source:
- `NOTIFIER_MODE=email_gateway` with SMTP + gateway address (recommended), or
- `NOTIFIER_MODE=twilio` with Twilio credentials.

For Canvas source use one of:
- `CANVAS_ICAL_URL` (recommended), or
- both `CANVAS_BASE_URL` and `CANVAS_API_TOKEN`.

## 4) Install + run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m src.main --mode once --dry-run
```

If dry run output looks correct:

```bash
python -m src.main --mode once
```

## 5) Keep it running

### Option A: loop mode (quick start)

```bash
python -m src.main --mode loop --interval-minutes 30
```

### Option B: cron (recommended)

Run every 30 minutes:

```bash
*/30 * * * * cd /Users/muammerkara/Desktop/ReminderProject && /Users/muammerkara/Desktop/ReminderProject/.venv/bin/python -m src.main --mode once >> reminder.log 2>&1
```

## 6) Static Website

Your website file is included at:

`web/canvas-reminder.html`

Open it directly in a browser, or run a simple local server:

```bash
cd /Users/muammerkara/Desktop/ReminderProject
python3 -m http.server 8080
```

Then visit:

`http://127.0.0.1:8080/web/canvas-reminder.html`

## Notes

- Keep `.env` out of GitHub (already ignored in `.gitignore`).
- Canvas APIs and carrier gateways can rate-limit; this MVP is lightweight and polling-based.
- If you want, next step is deploying to Railway/Render so reminders run even when your laptop is off.
