"""JSON storage and comparison helpers for the Assignment Tracker."""

import json
from datetime import datetime, timedelta

from config import ASSIGNMENTS_FILE


def load_assignments():
    """Load previous assignments from assignments.json."""
    if not ASSIGNMENTS_FILE.exists() or ASSIGNMENTS_FILE.stat().st_size == 0:
        return []

    with ASSIGNMENTS_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    # Older versions may store just a list. This project intentionally keeps
    # assignments.json as a simple list because it is easy to read while learning.
    if isinstance(data, list):
        return data

    return data.get("assignments", [])


def save_assignments(assignments):
    """Save assignments to assignments.json in a readable format."""
    with ASSIGNMENTS_FILE.open("w", encoding="utf-8") as file:
        json.dump(assignments, file, indent=2, ensure_ascii=False)


def merge_assignments(old_assignments, scraped_assignments):
    """Keep useful old metadata while updating the latest scraped values."""
    now = datetime.now().isoformat(timespec="seconds")
    old_by_id = {assignment.get("id"): assignment for assignment in old_assignments}
    merged = []

    for scraped in scraped_assignments:
        assignment_id = scraped.get("id")
        old = old_by_id.get(assignment_id, {})

        updated = dict(scraped)
        updated["first_seen_at"] = old.get("first_seen_at", now)
        updated["last_seen_at"] = now
        updated["reminder_alerts_sent"] = old.get("reminder_alerts_sent", [])
        updated["due_datetime"] = parse_due_datetime(updated)

        merged.append(updated)

    return merged


def find_new_assignments(old_assignments, latest_assignments):
    """Detect assignments that were not present in the previous JSON file."""
    old_ids = {assignment.get("id") for assignment in old_assignments}
    return [
        assignment
        for assignment in latest_assignments
        if assignment.get("id") not in old_ids
    ]


def find_deadline_reminders(assignments, reminder_hours):
    """Find unsubmitted assignments that are close to their deadlines."""
    now = datetime.now()
    reminder_items = []

    for assignment in assignments:
        if not is_not_submitted(assignment):
            continue

        due_datetime = datetime_from_iso(assignment.get("due_datetime"))
        if not due_datetime:
            continue

        time_left = due_datetime - now
        if time_left <= timedelta(0):
            continue

        reminder_label = choose_reminder_label(time_left, reminder_hours)
        if not reminder_label:
            continue

        sent_labels = assignment.get("reminder_alerts_sent", [])
        if reminder_label not in sent_labels:
            reminder_items.append((assignment, reminder_label))

    return reminder_items


def choose_reminder_label(time_left, reminder_hours):
    """Choose the nearest reminder window that the assignment has entered."""
    for hours in sorted(reminder_hours):
        if time_left <= timedelta(hours=hours):
            return f"{hours}h"

    return ""


def mark_reminder_sent(assignments, assignment_id, reminder_label):
    """Record that a reminder was already sent so it is not repeated."""
    for assignment in assignments:
        if assignment.get("id") != assignment_id:
            continue

        sent_labels = assignment.setdefault("reminder_alerts_sent", [])
        if reminder_label not in sent_labels:
            sent_labels.append(reminder_label)


def is_not_submitted(assignment):
    """Return True when the assignment still appears to need action."""
    status = (assignment.get("submission_status") or "").lower()

    if not status:
        return True

    not_submitted_words = ["not submitted", "pending", "not submit", "unsubmitted"]
    submitted_words = ["submitted", "completed", "graded", "evaluated"]

    if any(word in status for word in not_submitted_words):
        return True

    if any(word in status for word in submitted_words):
        return False

    return True


def parse_due_datetime(assignment):
    """Convert scraped due date and time text into ISO datetime when possible."""
    due_date = assignment.get("due_date", "")
    due_time = assignment.get("due_time", "")

    candidates = []

    if due_date and due_time:
        candidates.append(f"{due_date} {due_time}")

    if due_date:
        candidates.append(due_date)

    # Some portals put date and time together in one column.
    details = assignment.get("details", "")
    if details:
        candidates.append(details)

    for candidate in candidates:
        parsed = try_parse_datetime(candidate)
        if parsed:
            return parsed.isoformat(timespec="seconds")

    return ""


def try_parse_datetime(text):
    """Try several common Indian college portal date/time formats."""
    cleaned = " ".join(str(text).replace(",", " ").split())

    formats = [
        "%d-%m-%Y %H:%M",
        "%d/%m/%Y %H:%M",
        "%d-%m-%Y %I:%M %p",
        "%d/%m/%Y %I:%M %p",
        "%d %b %Y %H:%M",
        "%d %b %Y %I:%M %p",
        "%d %B %Y %H:%M",
        "%d %B %Y %I:%M %p",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %I:%M %p",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d %b %Y",
        "%d %B %Y",
        "%Y-%m-%d",
    ]

    for date_format in formats:
        try:
            parsed = datetime.strptime(cleaned, date_format)

            # If only a date was available, remind before the end of that day.
            if "%H" not in date_format and "%I" not in date_format:
                parsed = parsed.replace(hour=23, minute=59)

            return parsed
        except ValueError:
            continue

    return None


def datetime_from_iso(value):
    """Safely convert an ISO datetime string back into a datetime object."""
    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
