# Reminder-Canvas
Canvas Deadline Reminder for JHU students: it pulls assignments from a private Canvas iCal feed, detects due-in-3-days, due-today, and due-in-3-hours deadlines, then sends text alerts through a free Verizon email-to-SMS gateway (or Twilio fallback). Runs automatically in the background on macOS with launchd and dedupes reminders to avoid spam.
