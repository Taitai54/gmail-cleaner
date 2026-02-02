# Gmail Bulk Unsubscribe & Cleanup Tool

A **free**, privacy-focused tool to bulk unsubscribe from emails, delete emails by sender, export email threads, and manage your Gmail inbox efficiently. No subscriptions, no data collection - runs 100% on your machine.

![Python](https://img.shields.io/badge/Python-3.9+-blue?style=flat-square&logo=python)
![Gmail API](https://img.shields.io/badge/Gmail-API-EA4335?style=flat-square&logo=gmail)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

> **No Subscription Required - Free Forever**

## ✨ Features

### Email Management
- 📧 **Bulk Unsubscribe** - Find newsletters and unsubscribe with one click
- 🗑️ **Delete by Sender** - Scan and see who sends you the most emails, delete in bulk
- 📥 **Email Thread Export** - Search and export full email threads to text files
- ⚡ **Label-Based Unsubscribe** - Apply "Unsubscribe" label to emails and process them all at once
- ✉️ **Mark as Read** - Bulk mark thousands of unread emails as read
- 📦 **Archive Emails** - Archive emails from selected senders (remove from inbox)

### Organization Tools
- 🏷️ **Label Management** - Create, delete, and apply/remove labels to emails from specific senders
- ⭐ **Mark Important** - Mark or unmark emails from selected senders as important
- 📊 **Email Download** - Download email metadata for selected senders as CSV

### Advanced Filtering
- 📅 **Date Range** - Filter by custom date ranges or presets (7d, 30d, 90d, etc.)
- 📏 **Size Filter** - Filter emails by size (1MB, 5MB, 10MB, 25MB)
- 📁 **Category Filter** - Filter by Gmail categories (Promotions, Social, Updates, Forums, Primary)
- 👤 **Sender Filter** - Filter by specific email address or domain
- 🎯 **Label Filter** - Filter by Gmail labels

### Privacy & Performance
- 🔒 **Privacy First** - Runs locally, your data never leaves your machine
- ⚡ **Super Fast** - Gmail API with batch requests (100 emails per API call)
- 🎨 **Gmail-style UI** - Clean, familiar interface with real-time progress tracking

## 🚀 Quick Start

### Option 1: Simple Run Scripts (Recommended for Beginners)

**Windows:**
1. Double-click `run.bat`
2. Follow the on-screen instructions

**Mac/Linux:**
1. Open Terminal in the project folder
2. Run: `./run.sh`
3. Follow the on-screen instructions

The script will:
- Check if Python is installed
- Create a virtual environment
- Install dependencies automatically
- Check for credentials.json
- Start the application

### Option 2: Manual Setup

#### Prerequisites
- Python 3.9 or higher
- Google account with Gmail
- Google Cloud Project (free) - see setup below

#### Installation Steps

1. **Clone or download this repository**
   ```bash
   git clone <your-repo-url>
   cd gmail-cleaner
   ```

2. **Create virtual environment**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Mac/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up Google OAuth credentials** (see detailed instructions below)

5. **Run the application**
   ```bash
   # Windows
   python main.py

   # Mac/Linux
   python3 main.py
   ```

6. **Open your browser**
   Navigate to `http://localhost:8000`

## 🔑 Google OAuth Setup (One-Time)

You need to create your own Google OAuth credentials (free and takes ~5 minutes):

### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Enter project name (e.g., "Gmail Cleaner")
4. Click "Create"

### Step 2: Enable Gmail API

1. In your project, go to "APIs & Services" → "Library"
2. Search for "Gmail API"
3. Click "Gmail API" → "Enable"

### Step 3: Create OAuth Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - User Type: **External**
   - App name: "Gmail Cleaner" (or any name)
   - User support email: Your email
   - Developer contact: Your email
   - Click "Save and Continue"
   - Scopes: Skip this (click "Save and Continue")
   - Test users: Add your Gmail address
   - Click "Save and Continue"

4. Back to Create OAuth client ID:
   - Application type: **Desktop app**
   - Name: "Gmail Cleaner Desktop"
   - Click "Create"

5. Download the credentials:
   - Click "Download JSON"
   - Save as `credentials.json` in the project folder

### Step 4: First Run

1. Run the application
2. Your browser will open for Google sign-in
3. Click your account
4. Click "Continue" on the warning (this is your own app)
5. Grant permissions
6. Done! The app is now authorized

**Note:** The warning about "Google hasn't verified this app" is normal - it's YOUR app, so you can trust it.

## 📖 How to Use

### Bulk Unsubscribe
1. Click "Unsubscribe" in the sidebar
2. Scroll to "Scan for Unsubscribe Links"
3. Choose how many emails to scan (100-2000)
4. Click "Scan Emails"
5. Review results and click "Unsubscribe Selected"

### Export Email Threads
1. Click "Unsubscribe" in the sidebar
2. Find "Export Email Threads" section
3. Enter a Gmail search query (e.g., `from:newsletter@example.com`)
4. Click "Export to Text File"
5. Your browser will download a text file with full email content

**Search Query Examples:**
- `from:example.com` - All emails from a domain
- `subject:newsletter` - All emails with "newsletter" in subject
- `from:sender@example.com older_than:30d` - Old emails from sender
- `is:unread category:promotions` - Unread promotional emails

### Label-Based Unsubscribe
1. In Gmail, create a label called "Unsubscribe"
2. Apply this label to emails you want to unsubscribe from
3. In the app, click "Unsubscribe" in sidebar
4. Find "Process 'Unsubscribe' Label" section
5. Click "Process 'Unsubscribe' Label"
6. Confirm the action
7. The app will visit all unsubscribe links and remove the label

### Delete Emails by Sender
1. Click "Delete Emails" in sidebar
2. Choose scan limit
3. Click "Scan Senders"
4. Review who sends you the most emails
5. Select senders and click "Delete"

### Mark as Read
1. Click "Mark as Read" in sidebar
2. See your unread count
3. Choose how many to mark (50-5000 or all)
4. Click "Mark as Read"

## 🔧 Advanced Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Optional: Change port (default: 8000)
PORT=8000

# Optional: Enable web auth mode for headless/Docker
WEB_AUTH=false

# Optional: OAuth callback settings (for Docker)
OAUTH_PORT=8767
OAUTH_HOST=localhost
```

### Filters

All features support advanced filters:
- **Date Range**: Custom dates or presets (7d, 30d, 90d, 180d, 365d)
- **Email Size**: 1MB, 5MB, 10MB, 25MB
- **Category**: Promotions, Social, Updates, Forums, Primary
- **Sender**: Email address or domain
- **Labels**: Any Gmail label

## 🐛 Troubleshooting

### "credentials.json not found"
- Make sure you've downloaded credentials from Google Cloud Console
- Save it as `credentials.json` (not `client_secret_xxx.json`)
- Place it in the project root folder

### "Token has been expired or revoked"
- Delete `token.json`
- Restart the app
- Sign in again

### "Port already in use"
- Change the port in `.env` or run with: `PORT=8001 python main.py`

### "Python not found" (Windows)
- Install Python from [python.org](https://www.python.org/)
- ✅ Check "Add Python to PATH" during installation
- Restart your terminal/command prompt

### "Permission denied" on run.sh (Mac/Linux)
```bash
chmod +x run.sh
./run.sh
```

## 📁 Project Structure

```
gmail-cleaner/
├── app/
│   ├── api/              # API routes
│   ├── core/             # Configuration
│   ├── models/           # Data models
│   └── services/         # Business logic
│       ├── gmail/        # Gmail operations
│       │   ├── export.py       # Email export
│       │   ├── unsubscribe.py  # Unsubscribe logic
│       │   └── ...
│       └── auth.py       # Authentication
├── static/               # CSS, JavaScript
│   ├── css/
│   └── js/
│       ├── export.js     # Export & label processing
│       └── ...
├── templates/            # HTML templates
├── credentials.template.json  # OAuth template
├── run.bat              # Windows launcher
├── run.sh               # Mac/Linux launcher
├── main.py              # Application entry point
└── README.md            # This file
```

## 🔒 Security & Privacy

### What This App Does
- ✅ Reads your Gmail messages (to find unsubscribe links)
- ✅ Modifies labels (for mark as read, archive, labels)
- ✅ Sends unsubscribe requests (to external unsubscribe URLs)
- ✅ Exports email content (saved locally on your machine)

### What This App Does NOT Do
- ❌ Store your emails on any server
- ❌ Send your data anywhere
- ❌ Access your Google password
- ❌ Access other Google services
- ❌ Share data with third parties

### Files That Are NEVER Committed to Git
- `credentials.json` - Your OAuth credentials
- `token.json` - Your access token
- `.env` - Environment variables
- `venv/` - Python virtual environment

These are protected by `.gitignore` and will never be uploaded to GitHub.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

MIT License - see LICENSE file for details

## ⚠️ Disclaimer

This tool is not affiliated with Google or Gmail. Use at your own risk. The developers are not responsible for any data loss or account issues. Always test with a small number of emails first.

## 💖 Support

If you find this tool useful, consider:
- ⭐ Starring the repository
- 🐛 Reporting bugs
- 💡 Suggesting features
- 🔄 Sharing with others

## 🆘 Getting Help

- **Issues**: Open an issue on GitHub
- **Questions**: Check existing issues first
- **Security**: Report security issues privately

---

**Made with ❤️ for Gmail users who value privacy and control**
