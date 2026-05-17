"""Main workflow for the Assignment Tracker.

This file connects all other modules together:
1. Scrape assignments from iCloudEMS.
2. Compare them with assignments.json.
3. Send WhatsApp Web alerts for new assignments.
"""

import argparse
import time
from datetime import datetime

from config import CHECK_INTERVAL_MINUTES, RUN_CONTINUOUSLY
from scraper import (
    create_driver,
    get_chrome_profile_path,
    get_user_data_dir_argument,
    open_assignments_page,
    scrape_assignments,
)
from storage import (
    find_new_assignments,
    load_assignments,
    merge_assignments,
    save_assignments,
)
from whatsapp import send_test_message, send_whatsapp_messages, setup_whatsapp_session


def build_new_assignment_message(assignment):
    """Create the WhatsApp text for a newly detected assignment."""
    due_text = format_due_text(assignment)

    return (
        "\U0001F6A8 New Assignment\n"
        f"Subject: {assignment.get('subject', 'Unknown')}\n"
        f"Assignment: {assignment.get('assignment_name', 'Unknown')}\n"
        f"Due: {due_text}\n"
        f"Status: {assignment.get('submission_status', 'Unknown')}"
    )


def format_due_text(assignment):
    """Join due date and due time into one readable line."""
    due_date = assignment.get("due_date") or "Unknown date"
    due_time = assignment.get("due_time") or "Unknown time"
    return f"{due_date} {due_time}".strip()


def run_single_check():
    """Run one complete scrape, compare, alert, and save cycle."""
    print("Starting Assignment Tracker check...")

    driver = create_driver()
    try:
        run_assignment_check_with_driver(driver)
    finally:
        driver.quit()


def run_assignment_check_with_driver(driver):
    """Run one complete check using an already-open browser session."""
    # The first run may pause here while you complete Google/mobile login.
    open_assignments_page(driver)
    scraped_assignments = scrape_assignments(driver)

    old_assignments = load_assignments()
    latest_assignments = merge_assignments(old_assignments, scraped_assignments)

    new_assignments = find_new_assignments(old_assignments, latest_assignments)

    messages = []

    for assignment in new_assignments:
        messages.append(build_new_assignment_message(assignment))

    messages_sent = True
    if messages:
        messages_sent = send_whatsapp_messages(messages, driver=driver)

    if messages and not messages_sent:
        print("Some new assignment alerts were not confirmed.")

    save_assignments(latest_assignments)

    print(f"Scraped assignments: {len(scraped_assignments)}")
    print(f"New assignments found: {len(new_assignments)}")
    print(f"Check finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def run_continuously():
    """Keep checking assignments forever with one reused browser session."""
    print("Continuous mode is ON.")
    print(f"Checking every {CHECK_INTERVAL_MINUTES} minute(s).")

    driver = create_driver()

    while True:
        try:
            print("Starting Assignment Tracker check...")
            run_assignment_check_with_driver(driver)
        except RuntimeError as error:
            print(f"\n{error}")
        except Exception as error:
            print(f"\nUnexpected error during assignment check: {error}")

        print(f"Sleeping {CHECK_INTERVAL_MINUTES} minutes...")
        time.sleep(CHECK_INTERVAL_MINUTES * 60)


def main():
    """Start the tracker in either one-shot or continuous mode."""
    print(f"Chrome profile path: {get_chrome_profile_path()}")
    print(f"Chrome user-data-dir option: {get_user_data_dir_argument()}")

    parser = argparse.ArgumentParser(description="Assignment Tracker for iCloudEMS")
    parser.add_argument(
        "--test-whatsapp",
        action="store_true",
        help="send a WhatsApp setup test message without scraping assignments",
    )
    parser.add_argument(
        "--setup-whatsapp",
        action="store_true",
        help="open WhatsApp Web and save the QR login session without sending",
    )
    args = parser.parse_args()

    try:
        if args.setup_whatsapp:
            if setup_whatsapp_session():
                print("WhatsApp Web session is ready.")
            else:
                print("WhatsApp Web session setup did not complete.")
            return

        if args.test_whatsapp:
            if send_test_message():
                print("WhatsApp setup test message sent successfully.")
            else:
                print("WhatsApp setup test message was not sent.")
            return

        if RUN_CONTINUOUSLY:
            run_continuously()
        else:
            run_single_check()
    except RuntimeError as error:
        # Friendly message for expected first-run login/session setup problems.
        # The scraper now treats the student dashboard as a completed login.
        print(f"\n{error}")


if __name__ == "__main__":
    main()
