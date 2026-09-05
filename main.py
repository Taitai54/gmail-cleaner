#!/usr/bin/env python3
"""
Gmail Bulk Unsubscribe Tool
---------------------------
A fast, Gmail-styled web app to find and unsubscribe from newsletters.

Usage:
    uv run python main.py

Then open http://localhost:8766 in your browser.
"""

import os
import sys
import subprocess
import webbrowser
import threading

import uvicorn

from app.core import settings
from app.main import app


def main():
    print("=" * 60)
    print(f"{settings.app_name}")
    print("=" * 60)

    # Check for credentials (file or settings from .env / global.env)
    has_creds = (
        os.path.exists(settings.credentials_file)
        or os.path.exists("credentials_gmail.json")
        or os.path.exists("credentials_unidays.json")
        or settings.google_credentials
    )

    if not has_creds:
        print(f"\nERROR: OAuth credentials file not found!")
        print("\nSetup instructions:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create project -> Enable Gmail API")
        print("3. Create OAuth credentials (Desktop or Web app)")
        print("4. Download JSON -> rename to credentials.json (or credentials_gmail.json / credentials_unidays.json)")
        print("5. Put credentials file in:", os.getcwd())
        print("\nExiting. Please add credentials and try again.")
        return

    print("OAuth credentials found!")

    port = int(os.environ.get("PORT", settings.port))

    print(f"\nOpening browser at: http://127.0.0.1:{port}")
    print("   (Keep this terminal open)")
    print("\n   Press Ctrl+C to stop\n")

    # Only open browser if running locally (not in cloud and not suppressed by launcher)
    if not os.environ.get("PORT") and os.environ.get("NO_BROWSER") != "1":
        def _open_browser():
            url = f"http://127.0.0.1:{port}"
            if sys.platform == "darwin":
                try:
                    subprocess.run(["open", url], check=False)
                    return
                except Exception:
                    pass
            try:
                webbrowser.open(url)
            except Exception:
                pass
        threading.Timer(0.8, _open_browser).start()

    # Bind to 127.0.0.1 so Docker Desktop cannot intercept localhost traffic
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
