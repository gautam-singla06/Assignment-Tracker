"""Editable settings for the Assignment Tracker.

Change values here instead of hunting through the rest of the code.
"""

from pathlib import Path


# Project folder and local files.
BASE_DIR = Path(__file__).resolve().parent
ASSIGNMENTS_FILE = BASE_DIR / "assignments.json"


# iCloudEMS pages used by the scraper.
ICLOUDEMS_HOME_URL = "https://mrei.icloudems.com/"
WHATSAPP_PHONE_NUMBER = "918587888700"


# Selenium wait times. Increase these if your internet or portal is slow.
SELENIUM_WAIT_SECONDS = 20
FIRST_LOGIN_WAIT_SECONDS = 180
WHATSAPP_WAIT_SECONDS = 180


# Reminder windows for unsubmitted assignments.
REMINDER_HOURS = [24, 6, 1]


RUN_CONTINUOUSLY = True
CHECK_INTERVAL_MINUTES = 60
