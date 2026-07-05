# 📧 Gmail Buddy

**Smarter Email. Better Business.**

Gmail Buddy is a desktop app that helps you clean up your Gmail inbox — bulk delete, categorize, and manage emails by sender, with optional AI-powered categorization using Gemini.

---

## ✨ Features

- 📬 **Inbox Manager** — View and manage emails grouped by sender
- 🔴🟡🟢 **Manual Categorization** — Mark senders as Delete / Review / Keep
- 🤖 **AI Categorizer** — Auto-categorize senders using Google Gemini API
- 🗑️ **Bulk Delete / Trash / Archive** — Clean up hundreds of emails at once
- ↩️ **Undo** — Restore trashed emails with one click
- 💾 **Backup / Restore** — SQLite database backup support
- 📤 **Export / Import** — Save and load your category settings
- 👤 **Multi Account** — Switch between multiple Gmail accounts

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.8+
- A Google Cloud project with Gmail API enabled

### 2. Setup Google Credentials

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project
3. Enable **Gmail API** from the Library
4. Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
5. Choose **Desktop app**
6. Download the JSON file and rename it to `credentials.json`
7. Place `credentials.json` in the project folder

### 3. Install & Run

```bash
# Option 1: Double-click setup.bat (Windows)
setup.bat

# Option 2: Manual
pip install -r requirements.txt
python app.py
```

Then open your browser at: `http://localhost:5000`

Or just double-click **start.bat**

---

## 🤖 AI Categorizer (Optional)

1. Get a free Gemini API key at [aistudio.google.com](https://aistudio.google.com/apikey)
2. Open the app → Settings → paste your API key
3. Go to AI Categorizer tab → Run Analysis

---

## 📁 Project Structure

```
Gmail-Buddy/
├── templates/
│   └── index.html        # Frontend UI
├── static/
│   └── logo.png          # App logo
├── app.py                # Flask server
├── database.py           # SQLite database
├── gmail_sync.py         # Gmail API integration
├── requirements.txt      # Dependencies
├── setup.bat             # First-time setup
├── start.bat             # Launch the app
└── credentials.json      # Your Google credentials (not included)
```

---

## ⚠️ Important

- Never share or commit `credentials.json` or `token.json`
- Your `gmail.db` contains your email data — keep it private

---

## 📋 Roadmap

See [ROADMAP_V1_1.md](ROADMAP_V1_1.md) for planned features and version history.

---

## 📄 License

MIT License — free to use and modify.
