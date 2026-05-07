# Gmail Cleaner - Multi-Account Email Management Tool

A **free**, privacy-focused tool to manage multiple Gmail accounts, search & export emails, bulk unsubscribe, delete by sender, and clean up your inbox efficiently. No subscriptions, no data collection - runs 100% on your machine.

![Python](https://img.shields.io/badge/Python-3.9+-blue?style=flat-square&logo=python)
![Gmail API](https://img.shields.io/badge/Gmail-API-EA4335?style=flat-square&logo=gmail)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

> **No Subscription Required - Free Forever**

## ✨ Features

### 🆕 NEW: Multi-Account Support
- 👥 **Sign in with multiple Gmail accounts** - Switch between accounts instantly
- 🔄 **Account switcher** - Dropdown in the header to add, switch, or remove accounts
- 🔐 **Per-account credentials** - Each account has its own secure token

### 🆕 NEW: Flexible Search & Export
- 🔍 **Search email threads** - Use Gmail's powerful search syntax
- ✅ **Select specific threads** - Checkbox list to pick exactly what you want
- 📥 **Export selected threads** - Download only the threads you chose as a text file

### Email Management
- 📧 **Bulk Unsubscribe** - Find newsletters and unsubscribe with one click
- 🗑️ **Delete by Sender** - Scan and see who sends you the most emails, delete in bulk
- 👁️ **Email Preview** - Preview emails before deletion to avoid mistakes
- ⚡ **Label-Based Unsubscribe** - Apply "Unsubscribe" label in Gmail and process them all at once
- ✉️ **Mark as Read** - Bulk mark thousands of unread emails as read
- 📦 **Archive Emails** - Archive emails from selected senders (remove from inbox)
- ✅ **Enhanced Confirmations** - Detailed confirmation dialogs before bulk operations
- 📊 **Error Tracking** - Track and report partial failures in batch operations

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
- 💾 **Result Persistence** - Scan results cached locally, survive page refreshes
- ♿ **Accessibility** - ARIA labels and keyboard navigation support

## 🎯 Recent Improvements (v2.0)

### Enhanced User Experience
- **Email Preview**: Preview emails before deletion to avoid accidental data loss - click the preview button next to any sender
- **Result Persistence**: Scan results are cached in browser localStorage and survive page refreshes (1-hour cache)
- **Better Loading States**: Clear feedback when operations are already in progress with toast notifications
- **Enhanced Confirmations**: Detailed confirmation dialogs showing exactly what will be affected (email counts, date ranges, recovery info)
- **Accessibility**: Added ARIA labels and improved keyboard navigation for better screen reader support
- **Filter Badge**: Visual indicator showing the number of active filters

### Improved Reliability
- **Error Tracking**: Partial failures in batch operations are now tracked and reported to users
- **Failed Email Count**: See how many emails couldn't be processed during scans in the completion notification
- **Better Error Messages**: More informative error messages with actionable guidance throughout the application
- **Comprehensive Logging**: All failures are logged for debugging and troubleshooting

### Performance & UX
- **Cached Results**: No need to re-scan after page refresh - results persist in your browser
- **Toast Notifications**: Non-intrusive success/error notifications that don't block your workflow
- **Progress Indicators**: Real-time progress bars and status messages for all long-running operations
- **Detailed Stats**: See email counts, date ranges, and sender information before taking action
- **Preview Modal**: Quick preview of recent emails from any sender before bulk deletion

See [IMPROVEMENTS_SUMMARY.md](IMPROVEMENTS_SUMMARY.md) for detailed technical documentation of all improvements.

## 🚀 Quick Start

### Easiest Way: Double-Click Launcher

**macOS:**
1. Double-click **`Gmail Cleaner.app`** in Finder
2. Follow any setup prompts
3. Your browser opens automatically at http://localhost:8766

**Windows:**
1. Double-click **`run-gmail-cleaner.bat`** (or run **`create-windows-shortcut.ps1`** once to create a desktop shortcut)
2. Follow any setup prompts
3. Your browser opens automatically at http://localhost:8766

The launchers will check for:
- ✅ `uv` package manager (and guide you to install it if needed)
- ✅ `credentials.json` (and show setup instructions if missing)
- ✅ Whether the app is already running (just opens browser in that case)

### Prerequisites

1. **Install `uv`** (modern Python package manager - faster than pip):
   ```bash
   # macOS/Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Windows (PowerShell)
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

2. **Get Google OAuth credentials** (see setup below)

### Manual Run (if you prefer Terminal/Command Prompt)

```bash
# Navigate to the project folder
cd gmail-cleaner

# Run the app (uv installs dependencies automatically)
uv run python main.py
```

Then open http://localhost:8766 in your browser.

## 🔑 Google OAuth Setup (One-Time, ~5 minutes)

You need to create your own Google OAuth credentials (free):

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
   - Test users: Add your Gmail address(es)
   - Click "Save and Continue"

4. Back to Create OAuth client ID:
   - Application type: **Desktop app**
   - Name: "Gmail Cleaner Desktop"
   - Click "Create"

5. Download the credentials:
   - Click "Download JSON"
   - **Save as `credentials.json` in the project folder** (same folder as `main.py`)

### Step 4: First Run

1. Run the application (double-click launcher or `uv run python main.py`)
2. Your browser will open for Google sign-in
3. Click your account
4. Click "Continue" on the warning (this is your own app)
5. Grant permissions
6. Done! The app is now authorized

**Note:** The warning about "Google hasn't verified this app" is normal - it's YOUR app, so you can trust it.

## 📖 How to Use

### Multi-Account Sign-In

1. Sign in with your first Gmail account (automatic on first run)
2. Click **Accounts** button in the header
3. Click **Add Account** to sign in with another Gmail account
4. Switch between accounts anytime via the Accounts dropdown
5. Remove accounts you no longer need

**Each account is independent** — your scans, exports, and operations work on the currently active account.

### Search & Export Emails (NEW)

1. Click "Unsubscribe" in the sidebar
2. Find the "Search & Export Emails" section
3. Enter a Gmail search query (e.g., `from:unidays` or `subject:newsletter`)
4. Click **Search** (or press Enter)
5. Results appear as a list — tick the threads you want
6. Click **Export Selected** → downloads `email_export.txt` with full content

**Search Query Examples:**
- `from:example.com` - All emails from a domain
- `from:unidays` - All emails from Unidays
- `subject:newsletter` - All emails with "newsletter" in subject
- `from:sender@example.com older_than:30d` - Old emails from sender
- `is:unread category:promotions` - Unread promotional emails
- `label:Receipts` - All emails with "Receipts" label

### Bulk Unsubscribe

1. Click "Unsubscribe" in the sidebar
2. Scroll to "Scan for Unsubscribe Links"
3. Choose how many emails to scan (100-2000)
4. Click "Scan Emails"
5. Review results sorted by sender
6. Select senders and click "Unsubscribe Selected"

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
5. Select senders and choose:
   - **Delete** - Move to trash (recoverable for 30 days)
   - **Archive** - Remove from inbox, keep in "All Mail"
   - **Label** - Apply a label to organize
   - **Important** - Mark as important
   - **Download** - Export metadata to CSV

### Mark as Read

1. Click "Mark as Read" in sidebar
2. See your unread count
3. Choose how many to mark (50-5000 or all)
4. Click "Mark as Read"

## 🔧 Advanced Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Optional: Change port (default: 8766)
PORT=8766

# Optional: Enable web auth mode for headless/Docker
WEB_AUTH=false

# Optional: OAuth callback settings (for Docker/port mapping)
OAUTH_PORT=8767
OAUTH_HOST=localhost
OAUTH_EXTERNAL_PORT=8767
```

### New Machine Migration Checklist

If you moved this repo to a new computer, use this quick checklist:

1. Install `uv` and run:
   ```bash
   uv sync --group dev
   ```
2. Make sure OAuth credentials are available via either:
   - `credentials.json` in the repo root, or
   - `GOOGLE_CREDENTIALS` in `.env` or `global.env`
3. Keep secrets local only:
   - `global.env`, `.env`, `credentials.json`, `accounts.json`, and `token_*.json` are gitignored and should never be committed.
4. Run a quick smoke test:
   ```bash
   uv run python main.py
   ```
   Then open `http://127.0.0.1:8766`.
5. If authentication behaves oddly after migration, delete local auth cache and re-sign in:
   - `accounts.json`
   - `token_*.json`

Note: extra environment variables in `global.env` are ignored by app settings, so unrelated local env keys will not block startup.

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
- Place it in the project root folder (same folder as `main.py`)

### "uv: command not found"
- Install uv using the commands in Prerequisites section above
- On macOS/Linux, restart your terminal after installing
- On Windows, restart Command Prompt after installing

### "Token has been expired or revoked"
- The app will automatically prompt you to re-authorize
- Alternatively, delete `token_*.json` files and `accounts.json`
- Restart the app and sign in again

### "Port already in use"
- Another instance is running — check http://localhost:8766
- Or change the port: `PORT=8001 uv run python main.py`

### macOS: "Gmail Cleaner.app can't be opened"
- Right-click the app → "Open" → "Open" (to bypass Gatekeeper first time)
- Or run: `xattr -cr "Gmail Cleaner.app"`

### Windows: ".bat file opens and closes immediately"
- Right-click `run-gmail-cleaner.bat` → "Edit" to see error messages
- Or run from Command Prompt to see output

## 📁 Project Structure

```
gmail-cleaner/
├── Gmail Cleaner.app/      # 🆕 macOS clickable launcher
├── app/
│   ├── api/                # API routes
│   │   ├── actions.py      # POST endpoints (search, export, accounts)
│   │   └── status.py       # GET endpoints
│   ├── core/               # Configuration
│   │   ├── config.py       # Settings
│   │   └── state.py        # 🆕 Multi-account state
│   ├── models/             # Data models
│   │   └── schemas.py      # 🆕 New: SearchThreadsRequest, etc.
│   └── services/           # Business logic
│       ├── auth.py         # 🆕 Multi-account authentication
│       └── gmail/          # Gmail operations
│           ├── export.py   # 🆕 Search & export threads
│           ├── unsubscribe.py
│           └── ...
├── static/                 # CSS, JavaScript
│   ├── css/
│   │   └── components.css  # 🆕 Account dropdown styles
│   └── js/
│       ├── accounts.js     # 🆕 Multi-account UI
│       ├── export.js       # 🆕 Search/select/export UI
│       └── ...
├── templates/
│   └── index.html          # 🆕 Updated with account switcher
├── credentials.template.json
├── run-gmail-cleaner.bat   # Windows launcher
├── run.sh                  # Mac/Linux launcher
├── create-windows-shortcut.ps1  # 🆕 Creates desktop shortcut
├── main.py                 # Application entry point
└── README.md               # This file
```

## 🔒 Security & Privacy

### What This App Does
- ✅ Reads your Gmail messages (to find unsubscribe links)
- ✅ Modifies labels (for mark as read, archive, labels)
- ✅ Sends unsubscribe requests (to external unsubscribe URLs)
- ✅ Exports email content (saved locally on your machine)
- ✅ Stores OAuth tokens locally per account

### What This App Does NOT Do
- ❌ Store your emails on any server
- ❌ Send your data anywhere
- ❌ Access your Google password
- ❌ Access other Google services beyond Gmail
- ❌ Share data with third parties

### Files That Are NEVER Committed to Git
- `credentials.json` - Your OAuth credentials
- `token.json` - Legacy single-account token
- `token_*.json` - 🆕 Per-account tokens
- `accounts.json` - 🆕 Account registry
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
