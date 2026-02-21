# 🛡️ Prime Avay Verification Bot

A professional and secure Telegram Verification Bot built with Python. This bot is designed for content creators to verify followers' tasks (such as Instagram follows, YouTube subscriptions, and joining groups) via manual screenshot approval.

## ✨ Features

- **🔐 Secure Configuration**: sensitive data like `BOT_TOKEN` and `ADMIN_ID` are hidden using Environment Variables to ensure security.
- **💾 Database Support**: uses SQLite3 to save user progress and verification states, so data isn't lost if the bot restarts.
- **📊 Multi-Step Approval**: requires users to submit 4 screenshots to gain access to the final link (customizable).
- **🛠 Admin Panel**: integrated Inline buttons for the Admin to `Approve` or `Reject` requests directly within Telegram.
- **📂 State Management**: automatically tracks whether a user is in the submission process or already verified.

## 🚀 Setup & Installation

### 1. Prerequisites
Ensure you have Python 3.10 or higher installed.

### 2. Install Dependencies
```bash
pip install -r requirements.txt
