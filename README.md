# Payment Reminder

## SkipUntil Feature Guide

The application now supports a "SkipUntil" column in your Excel file that allows you to skip sending reminders to specific customers until a certain date.

### Format Guidelines:
- Use the date format: **DD/MM/YYYY** (e.g., 01/05/2025)
- Leave the cell empty if you want to send reminders normally
- The system will skip sending reminders if the current date is before or equal to the date specified in "SkipUntil"

### Examples:
- If SkipUntil = "01/05/2025", no reminders will be sent until May 1, 2025 (inclusive)
- After May 1, 2025, reminders will resume automatically

The system will log a warning if it encounters an invalid date format in this column.