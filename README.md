# Canvas Deadline Text Reminder (JHU)

This project pulls your upcoming Canvas assignments and sends SMS reminders.

## What it does

- Pulls assignment due dates from either:
  - Canvas Calendar Feed (recommended)
  - Canvas API (optional fallback)
- Sends:
  - a daily digest at 8:00 AM local time
  - a 24-hour reminder before each assignment is due
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

### Twilio

1. Create/login at [https://www.twilio.com](https://www.twilio.com)
2. Buy/setup an SMS-capable Twilio number
3. Copy:
   - `TWILIO_ACCOUNT_SID`
   - `TWILIO_AUTH_TOKEN`
   - `TWILIO_FROM_NUMBER`
4. Set your own phone number in `TO_NUMBER`

## 3) Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill Twilio values plus one Canvas source:
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

## Notes

- Keep `.env` out of GitHub (already ignored in `.gitignore`).
- Canvas and Twilio APIs can rate-limit; this MVP is lightweight and polling-based.
- If you want, next step is deploying to Railway/Render so reminders run even when your laptop is off.
