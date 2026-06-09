# 🎓 Assignment Tracker

An automated assignment monitoring system for iCloudEMS that detects newly posted assignments and sends notifications instantly.

## ✨ Features

- 🔍 Automatically checks iCloudEMS assignments
- 📋 Tracks previously seen assignments
- 🚨 Detects newly added assignments
- 💬 WhatsApp notification support
- ⏱️ Scheduled monitoring mode
- 💾 Local assignment database storage
- 🌐 Selenium-powered browser automation
- 🔐 Supports manual OTP authentication flow

---

## 📂 Project Structure

```text
Assignment-Tracker/
│
├── config.py          # Configuration settings
├── main.py            # Main application entry point
├── scraper.py         # iCloudEMS scraping logic
├── storage.py         # Assignment storage management
├── whatsapp.py        # WhatsApp notification module
├── requirements.txt   # Python dependencies
├── assignments.json   # Stored assignment data
│
├── chrome_profile/
├── chrome_profile_runtime/
└── __pycache__/
```

---

## ⚙️ Requirements

- Python 3.10+
- Google Chrome
- ChromeDriver (managed automatically)
- Active iCloudEMS student account

---

## 🚀 Installation

### Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/Assignment-Tracker.git
cd Assignment-Tracker
```

### Create Virtual Environment

```bash
python -m venv .venv
```

### Activate Environment

Windows:

```bash
.venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 🔧 Configuration

Edit:

```python
config.py
```

Configure:

```python
WHATSAPP_PHONE_NUMBER = "YOUR_NUMBER"
RUN_CONTINUOUSLY = True
CHECK_INTERVAL_MINUTES = 60
```

---

## ▶️ Run

```bash
python main.py
```

Or:

```bash
.\.venv\Scripts\python.exe main.py
```

---

## 📈 Workflow

```text
Start
  │
  ▼
Open iCloudEMS
  │
  ▼
Login / OTP Verification
  │
  ▼
Open Assignments Page
  │
  ▼
Scrape Assignments
  │
  ▼
Compare With Stored Data
  │
  ▼
New Assignment Found?
 ├─ No → Wait for next check
 └─ Yes → Send Notification
```

---

## 🔔 Notification System

The tracker compares current assignments with previously stored records.

When a new assignment is detected:

- Assignment details are extracted
- New records are stored
- WhatsApp notification is triggered

---

## 🛠 Technologies Used

- Python
- Selenium
- WebDriver Manager
- JSON Storage
- WhatsApp Automation

---

## 📌 Current Status

- Assignment scraping ✅
- Assignment comparison ✅
- Continuous monitoring ✅
- WhatsApp notification support ✅
- Session persistence support ✅

---

## ⚠️ Disclaimer

This project is intended for educational and personal productivity purposes only.

Users are responsible for complying with their institution's policies and platform terms of service.

---

## 👨‍💻 Author

**Gautam**

Built to automate assignment tracking and reduce manual checking effort.
