"""iCloudEMS scraping code for the Assignment Tracker.

This module owns browser setup, login/session reuse, and assignment extraction.
The selectors are intentionally written with fallbacks because college portals
often change their HTML slightly.
"""

import hashlib
import shutil
import time
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from config import (
    BASE_DIR,
    FIRST_LOGIN_WAIT_SECONDS,
    ICLOUDEMS_HOME_URL,
    SELENIUM_WAIT_SECONDS,
)


REAL_CHROME_DEFAULT_PROFILE = Path(
    r"C:\Users\gauta\AppData\Local\Google\Chrome\User Data\Default"
)
RUNTIME_CHROME_USER_DATA_DIR = BASE_DIR / "chrome_profile_runtime"
RUNTIME_CHROME_DEFAULT_PROFILE = RUNTIME_CHROME_USER_DATA_DIR / "Default"


def create_driver():
    """Create Chrome with a saved profile so logins survive future runs."""
    copy_chrome_default_profile_once()

    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={RUNTIME_CHROME_USER_DATA_DIR}")
    options.add_argument("--profile-directory=Default")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(20)
    return driver


def copy_chrome_default_profile_once():
    """Create the reusable runtime profile from the real Chrome profile once."""
    if RUNTIME_CHROME_USER_DATA_DIR.exists():
        return

    shutil.copytree(REAL_CHROME_DEFAULT_PROFILE, RUNTIME_CHROME_DEFAULT_PROFILE)


def get_chrome_profile_path():
    """Return the absolute Chrome profile folder used on every run."""
    return str(RUNTIME_CHROME_USER_DATA_DIR)


def get_user_data_dir_argument():
    """Return the exact persistent Chrome profile argument Selenium must use."""
    return f"--user-data-dir={RUNTIME_CHROME_USER_DATA_DIR}"


LOWERCASE_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LOWERCASE_TARGET = "abcdefghijklmnopqrstuvwxyz"
LOWER_TEXT = (
    f"translate(normalize-space(), '{LOWERCASE_LETTERS}', '{LOWERCASE_TARGET}')"
)
LOWER_HREF = f"translate(@href, '{LOWERCASE_LETTERS}', '{LOWERCASE_TARGET}')"
LOWER_TITLE = f"translate(@title, '{LOWERCASE_LETTERS}', '{LOWERCASE_TARGET}')"
LOWER_ARIA = f"translate(@aria-label, '{LOWERCASE_LETTERS}', '{LOWERCASE_TARGET}')"
LOWER_CLASS = f"translate(@class, '{LOWERCASE_LETTERS}', '{LOWERCASE_TARGET}')"


# Links that should take the student directly to the assignment list when clicked
# from inside the authenticated dashboard/menu.
ASSIGNMENT_LINK_SELECTORS = [
    (By.XPATH, "//a[contains(@href, 'myassignments.php')]"),
    (By.XPATH, f"//a[contains({LOWER_HREF}, 'assignment')]"),
    (By.XPATH, f"//*[@role='menuitem' and contains({LOWER_TEXT}, 'assignment')]"),
    (By.XPATH, f"//button[contains({LOWER_TEXT}, 'assignment')]"),
]


# Larger dashboard icons/cards/menu buttons that may open the assignment section
# before the real "My Assignments" link becomes visible.
ASSIGNMENT_MENU_SELECTORS = [
    (By.XPATH, f"//a[contains({LOWER_TEXT}, 'assignment')]"),
    (By.XPATH, f"//button[contains({LOWER_TEXT}, 'assignment')]"),
    (By.XPATH, f"//*[@role='button' and contains({LOWER_TEXT}, 'assignment')]"),
    (By.XPATH, f"//*[contains({LOWER_TITLE}, 'assignment')]"),
    (By.XPATH, f"//*[contains({LOWER_ARIA}, 'assignment')]"),
    (By.XPATH, f"//*[contains({LOWER_CLASS}, 'assignment')]"),
]


LOGIN_PAGE_SELECTORS = [
    (By.XPATH, "//input[@type='password']"),
    (By.XPATH, "//input[contains(@name, 'username')]"),
    (By.XPATH, "//input[contains(@name, 'phone')]"),
    (By.XPATH, "//input[contains(@name, 'mobile')]"),
    (By.XPATH, "//input[contains(@autocomplete, 'one-time-code')]"),
    (By.XPATH, f"//button[contains({LOWER_TEXT}, 'sign in')]"),
    (By.XPATH, f"//button[contains({LOWER_TEXT}, 'login')]"),
    (By.XPATH, f"//*[contains({LOWER_TEXT}, 'continue with google')]"),
    (By.XPATH, f"//*[contains({LOWER_TEXT}, 'mobile number')]"),
    (By.XPATH, f"//*[contains({LOWER_TEXT}, 'otp')]"),
]


def open_assignments_page(driver):
    """Open iCloudEMS, click Student Login, and use the UI to reach assignments."""
    try:
        driver.get(ICLOUDEMS_HOME_URL)
    except TimeoutException:
        pass
    print(f"Current URL after load: {driver.current_url}")

    click_student_login_if_visible(driver)
    WebDriverWait(driver, FIRST_LOGIN_WAIT_SECONDS).until(
        lambda browser: "student_index.php" in browser.current_url.lower()
    )

    # iCloudEMS rejects direct assignment URLs, so navigate through the dashboard
    # exactly like a student would.
    navigate_to_assignments_from_dashboard(driver)
    wait_for_assignments_page(driver, raise_on_timeout=True)


def navigate_to_assignments_from_dashboard(driver):
    """Click the Assignments icon/menu from the logged-in dashboard."""
    if is_assignments_page_ready(driver):
        return

    WebDriverWait(driver, FIRST_LOGIN_WAIT_SECONDS).until(
        lambda browser: is_logged_in(browser)
    )
    close_common_popups(driver)

    print("Navigating to Assignments through the dashboard UI...")

    # First try direct assignment links that already exist in the dashboard/menu.
    if click_assignment_navigation_element(driver, ASSIGNMENT_LINK_SELECTORS):
        if wait_for_assignments_page(driver, quick_check=True):
            return

    # Some dashboards expose an Assignments icon that opens a submenu first.
    if click_assignment_navigation_element(driver, ASSIGNMENT_MENU_SELECTORS):
        if wait_for_assignments_page(driver, quick_check=True):
            return

        close_common_popups(driver)

        if click_assignment_navigation_element(driver, ASSIGNMENT_LINK_SELECTORS):
            if wait_for_assignments_page(driver, quick_check=True):
                return

    raise RuntimeError(
        "Could not find the Assignments icon/menu on the dashboard. "
        "Open the dashboard and check whether the Assignments menu text changed."
    )


def click_assignment_navigation_element(driver, selectors):
    """Find and click one visible Assignments navigation element."""
    end_time = time.time() + SELENIUM_WAIT_SECONDS

    while time.time() < end_time:
        for selector in selectors:
            elements = driver.find_elements(*selector)

            for element in elements:
                element_description = describe_element(element)
                if safe_click(driver, element):
                    print(f"Clicked Assignments navigation: {element_description}")
                    return True

        time.sleep(0.5)

    return False


def safe_click(driver, element):
    """Click an element using normal click first, then JavaScript as backup."""
    try:
        if not element.is_displayed() or not element.is_enabled():
            return False

        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center', inline: 'center'});",
            element,
        )
        time.sleep(0.2)
        element.click()
        return True
    except Exception:
        try:
            driver.execute_script("arguments[0].click();", element)
            return True
        except Exception:
            return False


def describe_element(element):
    """Return a short description of the clicked menu item for debugging."""
    try:
        text = clean_text(element.text)
        href = element.get_attribute("href") or ""
        title = element.get_attribute("title") or ""
        aria_label = element.get_attribute("aria-label") or ""
    except Exception:
        return "unknown element"

    for value in [text, title, aria_label, href]:
        if value:
            return value[:120]

    return "assignment element"


def click_student_login_if_visible(driver):
    """Click Student Login when it appears on the iCloudEMS home page."""
    wait = WebDriverWait(driver, SELENIUM_WAIT_SECONDS)

    possible_selectors = [
        (By.XPATH, "//a[contains(@href, 'MREI_STUDENT')]"),
        (By.XPATH, "//a[contains(normalize-space(), 'Student Login')]"),
        (By.XPATH, "//button[contains(normalize-space(), 'Student Login')]"),
    ]

    for selector in possible_selectors:
        try:
            button = wait.until(EC.element_to_be_clickable(selector))
            button.click()
            time.sleep(2)
            return True
        except TimeoutException:
            continue

    print("Student Login button was not found. Continuing to assignment page.")
    return False


def wait_for_assignments_page(driver, raise_on_timeout=False, quick_check=False):
    """Wait until the assignment page body/table appears."""
    wait_seconds = SELENIUM_WAIT_SECONDS if quick_check else FIRST_LOGIN_WAIT_SECONDS

    try:
        WebDriverWait(driver, wait_seconds).until(
            lambda browser: is_assignments_page_ready(browser)
        )
        return True
    except TimeoutException:
        if raise_on_timeout:
            raise
        return False


def is_assignments_page_ready(driver):
    """Return True only when the real assignments page is accessible."""
    current_url = driver.current_url.lower()
    body_text = get_body_text(driver).lower()

    if needs_manual_login(driver):
        return False

    if "direct url access is not allowed" in body_text:
        return False

    if "myassignments.php" not in current_url:
        return False

    assignment_words = ["assignment", "subject", "submission", "deadline", "due"]
    return any(word in body_text for word in assignment_words)


def is_logged_in(driver):
    """Return True when iCloudEMS shows an authenticated student session."""
    current_url = driver.current_url.lower()

    if is_direct_access_blocked(driver):
        return False

    # After mobile OTP login, iCloudEMS commonly lands here:
    # /corecampus/student/student_index.php
    if "student_index.php" in current_url:
        return True

    # Most authenticated student pages live under /student/.
    if "/student/" in current_url and "openid-connect/auth" not in current_url:
        return True

    return dashboard_elements_exist(driver)


def dashboard_elements_exist(driver):
    """Detect common dashboard elements after a successful student login."""
    dashboard_selectors = [
        (By.XPATH, "//*[contains(@href, 'student_index.php')]"),
        (By.XPATH, "//*[contains(translate(normalize-space(), "
                   "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'dashboard')]"),
        (By.XPATH, "//*[contains(translate(normalize-space(), "
                   "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'my courses')]"),
        (By.XPATH, "//*[contains(translate(normalize-space(), "
                   "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'assignments')]"),
    ]

    for selector in dashboard_selectors:
        try:
            elements = driver.find_elements(*selector)
        except Exception:
            continue

        if any(element.is_displayed() for element in elements):
            return True

    return False


def needs_manual_login(driver):
    """Return True only for real login pages that require user action."""
    if is_logged_in(driver):
        return False

    return is_login_page(driver)


def is_login_page(driver):
    """Detect iCloudEMS login pages by URL and login-specific elements."""
    current_url = driver.current_url.lower()
    title = driver.title.lower()
    body_text = get_body_text(driver).lower()

    login_url_parts = [
        "openid-connect/auth",
        "usermanagement.icloudems.com",
        "/login",
    ]

    if any(part in current_url for part in login_url_parts):
        return True

    if "sign in" in title and login_elements_exist(driver):
        return True

    login_text_parts = ["sign in", "mobile number", "forgot password", "otp"]
    if any(part in body_text for part in login_text_parts) and login_elements_exist(driver):
        return True

    return login_elements_exist(driver)


def login_elements_exist(driver):
    """Return True when visible form controls look like a login/OTP page."""
    for selector in LOGIN_PAGE_SELECTORS:
        try:
            elements = driver.find_elements(*selector)
        except Exception:
            continue

        if any(element.is_displayed() for element in elements):
            return True

    return False


def is_direct_access_blocked(driver):
    """Detect the iCloudEMS deep-link rejection page."""
    body_text = get_body_text(driver).lower()
    return "direct url access is not allowed" in body_text


def is_blocked_or_login_page(driver):
    """Detect pages where assignment scraping cannot continue yet."""
    if is_direct_access_blocked(driver):
        return True

    return is_login_page(driver)


def get_body_text(driver):
    """Safely read visible body text from the current page."""
    try:
        return driver.find_element(By.TAG_NAME, "body").text
    except Exception:
        return ""


def scrape_assignments(driver):
    """Scrape assignments from tables first, then fall back to visible blocks."""
    WebDriverWait(driver, SELENIUM_WAIT_SECONDS).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    close_common_popups(driver)

    assignments = scrape_assignment_tables(driver)

    if not assignments:
        assignments = scrape_assignment_blocks(driver)

    return assignments


def close_common_popups(driver):
    """Close simple popups that may cover the assignment table."""
    close_selectors = [
        (By.XPATH, "//button[contains(@class, 'close')]"),
        (By.XPATH, "//button[normalize-space()='×']"),
        (By.XPATH, "//button[normalize-space()='Close']"),
    ]

    for selector in close_selectors:
        for element in driver.find_elements(*selector):
            try:
                if element.is_displayed() and element.is_enabled():
                    element.click()
                    time.sleep(1)
            except Exception:
                # Popup closing is helpful, but scraping can continue if it fails.
                pass


def scrape_assignment_tables(driver):
    """Extract assignment rows from HTML tables using header names when possible."""
    assignments = []

    for table in driver.find_elements(By.CSS_SELECTOR, "table"):
        rows = table.find_elements(By.CSS_SELECTOR, "tr")
        if len(rows) < 2:
            continue

        headers = get_table_headers(rows[0])

        for row in rows[1:]:
            cells = [cell.text.strip() for cell in row.find_elements(By.CSS_SELECTOR, "td")]
            cells = [cell for cell in cells if cell]

            if not cells:
                continue

            assignment = build_assignment_from_cells(headers, cells, row.text)

            if looks_like_assignment(assignment):
                assignments.append(assignment)

    return remove_duplicates(assignments)


def get_table_headers(header_row):
    """Read table headers and normalize them for easier matching."""
    headers = [
        cell.text.strip().lower()
        for cell in header_row.find_elements(By.CSS_SELECTOR, "th,td")
    ]
    return headers


def build_assignment_from_cells(headers, cells, row_text):
    """Map table cells into a consistent assignment dictionary."""
    subject = value_by_header(headers, cells, ["subject", "course", "paper"])
    name = value_by_header(headers, cells, ["assignment", "title", "name", "topic"])
    due_date = value_by_header(headers, cells, ["due date", "deadline", "last date", "submission date"])
    due_time = value_by_header(headers, cells, ["due time", "time"])
    status = value_by_header(headers, cells, ["status", "submission"])

    # Fallback for tables without useful headers.
    if not subject and len(cells) >= 1:
        subject = cells[0]
    if not name and len(cells) >= 2:
        name = cells[1]
    if not due_date and len(cells) >= 3:
        due_date = cells[2]
    if not status and len(cells) >= 4:
        status = cells[-1]

    return make_assignment(subject, name, due_date, due_time, status, row_text, cells)


def value_by_header(headers, cells, keywords):
    """Return the first cell whose table header contains one of the keywords."""
    for index, header in enumerate(headers):
        if index >= len(cells):
            continue

        if any(keyword in header for keyword in keywords):
            return cells[index]

    return ""


def scrape_assignment_blocks(driver):
    """Fallback scraper for card/list layouts when no useful table exists."""
    assignments = []
    possible_blocks = driver.find_elements(
        By.XPATH,
        "//*[contains(translate(normalize-space(), "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'assignment')]",
    )

    for block in possible_blocks:
        text = block.text.strip()
        if not text or len(text) < 15:
            continue

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        subject = find_labeled_line(lines, ["subject", "course"])
        name = find_labeled_line(lines, ["assignment", "title", "name"])
        due_date = find_labeled_line(lines, ["due date", "deadline", "last date"])
        due_time = find_labeled_line(lines, ["due time", "time"])
        status = find_labeled_line(lines, ["status", "submission"])

        if not name and lines:
            name = lines[0]

        assignment = make_assignment(subject, name, due_date, due_time, status, text, lines)

        if looks_like_assignment(assignment):
            assignments.append(assignment)

    return remove_duplicates(assignments)


def find_labeled_line(lines, labels):
    """Find text after labels like 'Subject: Mathematics'."""
    for line in lines:
        lower_line = line.lower()

        for label in labels:
            if lower_line.startswith(label):
                parts = line.split(":", 1)
                return parts[1].strip() if len(parts) == 2 else line

    return ""


def make_assignment(subject, name, due_date, due_time, status, details, raw_columns):
    """Create the normalized assignment dictionary saved to JSON."""
    assignment = {
        "subject": clean_text(subject),
        "assignment_name": clean_text(name),
        "due_date": clean_text(due_date),
        "due_time": clean_text(due_time),
        "submission_status": clean_text(status),
        "details": clean_text(details),
        "raw_columns": raw_columns,
        "scraped_at": datetime.now().isoformat(timespec="seconds"),
    }
    assignment["id"] = make_assignment_id(assignment)
    return assignment


def make_assignment_id(assignment):
    """Create a stable ID from fields that should not change often."""
    key = "|".join(
        [
            assignment.get("subject", "").lower(),
            assignment.get("assignment_name", "").lower(),
            assignment.get("due_date", "").lower(),
            assignment.get("due_time", "").lower(),
        ]
    )
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


def clean_text(value):
    """Remove extra spaces and line breaks from scraped text."""
    if not value:
        return ""
    return " ".join(str(value).split())


def looks_like_assignment(assignment):
    """Skip obvious non-assignment rows such as menu text or empty rows."""
    name = assignment.get("assignment_name", "")
    details = assignment.get("details", "")

    if not name and not details:
        return False

    ignored_words = ["search", "show entries", "no data available"]
    lowered = f"{name} {details}".lower()
    return not any(word in lowered for word in ignored_words)


def remove_duplicates(assignments):
    """Remove duplicate assignments while preserving the first copy found."""
    seen_ids = set()
    unique_assignments = []

    for assignment in assignments:
        assignment_id = assignment.get("id")

        if assignment_id in seen_ids:
            continue

        seen_ids.add(assignment_id)
        unique_assignments.append(assignment)

    return unique_assignments
