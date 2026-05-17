"""WhatsApp Web automation for sending local free alerts.

This module uses WhatsApp Web in Chrome. It does not use Twilio, Telegram,
cloud services, or any paid API.
"""

import sys
import time
from urllib.parse import quote

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import SELENIUM_WAIT_SECONDS, WHATSAPP_PHONE_NUMBER, WHATSAPP_WAIT_SECONDS
from scraper import create_driver


WHATSAPP_HOME_URL = "https://web.whatsapp.com/"
TEST_MESSAGE = "Assignment Tracker setup successful"


def send_whatsapp_messages(messages, driver=None):
    """Open WhatsApp Web and send each message to the configured phone number."""
    if not messages:
        return True

    owns_driver = driver is None

    if owns_driver:
        driver = create_driver()

    try:
        if not ensure_whatsapp_session(driver):
            return False

        if not is_phone_number_configured():
            print("\nWhatsApp phone number is not configured yet.")
            print("Edit WHATSAPP_PHONE_NUMBER in config.py, then run again.")
            print("Messages that would have been sent:")
            for message in messages:
                print_for_console("\n" + message)
            return False

        all_sent = True
        for message in messages:
            if not send_single_message(driver, message):
                all_sent = False
            time.sleep(3)
        return all_sent
    finally:
        if owns_driver:
            driver.quit()


def setup_whatsapp_session():
    """Open WhatsApp Web only, useful for saving QR login before alerts run."""
    driver = create_driver()
    try:
        return ensure_whatsapp_session(driver)
    finally:
        driver.quit()


def is_phone_number_configured():
    """Check that config.py contains a real international phone number."""
    phone = WHATSAPP_PHONE_NUMBER.strip()
    return phone and "X" not in phone and phone.isdigit()


def send_test_message():
    """Send one setup verification message to the configured WhatsApp number."""
    print("Sending WhatsApp setup test message...")
    return send_whatsapp_messages([TEST_MESSAGE])


def ensure_whatsapp_session(driver):
    """Open WhatsApp Web and wait until the saved session is ready."""
    driver.get(WHATSAPP_HOME_URL)
    print("Opening WhatsApp Web...")

    if wait_for_whatsapp_ready(driver, quick_check=True):
        print("WhatsApp Web session detected.")
        return True

    if whatsapp_qr_code_visible(driver):
        print("\nWhatsApp Web login needed.")
        print("Scan the QR code in Chrome. The session will be saved in your Chrome profile.")

    if wait_for_whatsapp_ready(driver):
        print("WhatsApp Web session ready.")
        return True

    print("WhatsApp Web was not ready before the wait time ended.")
    print("Scan the QR code and run the command again if this is the first setup.")
    return False


def wait_for_whatsapp_ready(driver, quick_check=False):
    """Wait until WhatsApp Web shows the logged-in interface."""
    wait_seconds = SELENIUM_WAIT_SECONDS if quick_check else WHATSAPP_WAIT_SECONDS

    try:
        WebDriverWait(driver, wait_seconds).until(
            lambda browser: whatsapp_logged_in(browser)
        )
        return True
    except TimeoutException:
        return False


def whatsapp_logged_in(driver):
    """Detect the normal WhatsApp Web UI after QR login is complete."""
    ready_selectors = [
        (By.XPATH, "//div[@role='textbox']"),
        (By.XPATH, "//div[@aria-label='Search input textbox']"),
        (By.XPATH, "//canvas[@aria-label='Scan this QR code to link a device']"),
        (By.XPATH, "//div[@id='pane-side']"),
        (By.XPATH, "//span[@data-icon='chat']"),
    ]

    for selector in ready_selectors:
        try:
            elements = driver.find_elements(*selector)
        except Exception:
            continue

        visible_elements = [element for element in elements if element.is_displayed()]
        if not visible_elements:
            continue

        # The QR canvas means the page loaded, but the user is not logged in yet.
        if selector[1].startswith("//canvas"):
            continue

        return True

    return False


def whatsapp_qr_code_visible(driver):
    """Return True when WhatsApp Web is asking for QR login."""
    qr_selectors = [
        (By.XPATH, "//canvas[@aria-label='Scan this QR code to link a device']"),
        (By.XPATH, "//*[contains(text(), 'link a device')]"),
        (By.XPATH, "//*[contains(text(), 'Use WhatsApp on your computer')]"),
    ]

    for selector in qr_selectors:
        try:
            elements = driver.find_elements(*selector)
        except Exception:
            continue

        if any(element.is_displayed() for element in elements):
            return True

    return False


def send_single_message(driver, message):
    """Send one message using WhatsApp Web's pre-filled text URL."""
    encoded_message = quote(message)
    whatsapp_url = (
        f"https://web.whatsapp.com/send"
        f"?phone={WHATSAPP_PHONE_NUMBER}&text={encoded_message}"
    )

    driver.get(whatsapp_url)

    if not wait_for_chat_to_load(driver):
        print("WhatsApp chat did not load for the configured phone number.")
        return False

    if click_send_button(driver):
        print("WhatsApp message sent.")
        return True

    print("Could not send automatically.")
    print("If this is the first run, scan the WhatsApp Web QR code and run again.")
    return False


def wait_for_chat_to_load(driver):
    """Wait until the target chat input/send area appears."""
    chat_selectors = [
        (By.XPATH, "//footer//div[@role='textbox']"),
        (By.XPATH, "//div[@contenteditable='true' and @role='textbox']"),
        (By.XPATH, "//span[@data-icon='send']/ancestor::button"),
        (By.XPATH, "//button[@aria-label='Send']"),
    ]

    end_time = time.time() + WHATSAPP_WAIT_SECONDS

    while time.time() < end_time:
        if whatsapp_qr_code_visible(driver):
            print("WhatsApp Web is asking for QR login.")
            return False

        for selector in chat_selectors:
            try:
                elements = driver.find_elements(*selector)
            except Exception:
                continue

            if any(element.is_displayed() for element in elements):
                return True

        time.sleep(1)

    return False


def click_send_button(driver):
    """Wait for the WhatsApp send button and click it."""
    selectors = [
        (By.XPATH, "//button[@aria-label='Send']"),
        (By.XPATH, "//span[@data-icon='send']/ancestor::button"),
        (By.XPATH, "//div[@role='button' and @aria-label='Send']"),
    ]

    end_time = time.time() + WHATSAPP_WAIT_SECONDS

    while time.time() < end_time:
        for selector in selectors:
            try:
                button = WebDriverWait(driver, SELENIUM_WAIT_SECONDS).until(
                    EC.element_to_be_clickable(selector)
                )
                button.click()
                return True
            except TimeoutException:
                continue

    return False


def print_for_console(text):
    """Print Unicode messages safely in older Windows terminals."""
    encoding = sys.stdout.encoding or "utf-8"
    safe_text = text.encode(encoding, errors="replace").decode(encoding)
    print(safe_text)
