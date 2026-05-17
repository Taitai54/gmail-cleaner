/**
 * Gmail Unsubscribe - Authentication Module
 */

window.GmailCleaner = window.GmailCleaner || {};

GmailCleaner.Auth = {
    async checkStatus() {
        try {
            const response = await fetch('/api/auth-status');
            const status = await response.json();
            this.updateUI(status);
        } catch (error) {
            console.error('Error checking auth status:', error);
            GmailCleaner.UI.showView('login');
        }
    },

    updateUI(authStatus) {
        const userSection = document.getElementById('userSection');
        const accountBanner = document.getElementById('active-account-banner');
        const accountRow = document.getElementById('active-account-row');

        if (authStatus.logged_in && authStatus.email) {
            const safeEmail = GmailCleaner.UI.escapeHtml(authStatus.email);
            const initial = authStatus.email.charAt(0).toUpperCase();
            userSection.innerHTML = `
                <span class="user-email">${safeEmail}</span>
                <div class="user-avatar" onclick="GmailCleaner.Auth.showUserMenu()" title="${safeEmail}">${initial}</div>
                <button class="btn btn-sm btn-secondary" onclick="GmailCleaner.Auth.signOut()">Sign Out</button>
            `;
            GmailCleaner.Filters.showBar(true);
            GmailCleaner.UI.showView('unsubscribe');
            if (accountBanner) {
                accountBanner.innerHTML = `Active account: <strong>${safeEmail}</strong>`;
            }
            if (accountRow) {
                accountRow.classList.remove('hidden');
            }

            // Show account switcher and load labels
            const acctWrapper = document.getElementById('account-dropdown-wrapper');
            if (acctWrapper) acctWrapper.classList.remove('hidden');
            this.loadLabelsForFilter();
            if (GmailCleaner.Accounts) GmailCleaner.Accounts.refresh();
        } else {
            userSection.innerHTML = '';
            GmailCleaner.Filters.showBar(false);
            GmailCleaner.UI.showView('login');
            if (accountBanner) {
                accountBanner.textContent = '';
            }
            if (accountRow) {
                accountRow.classList.add('hidden');
            }
            const acctWrapper = document.getElementById('account-dropdown-wrapper');
            if (acctWrapper) acctWrapper.classList.add('hidden');
        }
    },

    async loadLabelsForFilter() {
        try {
            // Load labels using the Labels module
            const labels = await GmailCleaner.Labels.loadLabels();
            if (labels && labels.user) {
                GmailCleaner.Filters.populateLabelDropdown(labels.user);
                if (GmailCleaner.Export && typeof GmailCleaner.Export.syncCustomLabelOptions === 'function') {
                    GmailCleaner.Export.syncCustomLabelOptions();
                }
            }
        } catch (error) {
            console.error('Error loading labels for filter:', error);
        }
    },

    async signIn() {
        const signInBtn = document.getElementById('signInBtn');

        if (signInBtn) {
            signInBtn.disabled = true;
            signInBtn.innerHTML = '<span>Starting sign-in...</span>';
        }

        try {
            const statusResp = await fetch('/api/web-auth-status');
            const status = await statusResp.json();

            // Check if credentials exist
            if (!status.has_credentials) {
                this.resetSignInButton();
                alert('credentials.json not found!\n\nSetup instructions:\n1. Go to https://console.cloud.google.com/\n2. Create project → Enable Gmail API\n3. Create OAuth credentials (Desktop app)\n4. Download JSON → rename to credentials.json\n5. Put credentials.json in the app folder\n6. Restart the app');
                return;
            }

            const signInResp = await fetch('/api/sign-in', { method: 'POST' });
            const signInResult = await signInResp.json();

            if (signInResult.error) {
                this.resetSignInButton();
                alert('Sign-in error: ' + signInResult.error);
                return;
            }

            // In headless/Docker mode, the URL appears once the OAuth thread starts.
            // Poll briefly for it so the user can copy it into a browser.
            this._headlessUrlOpened = false;
            if (status.web_auth_mode) {
                this._watchForHeadlessUrl();
            }

            this.pollStatus();
        } catch (error) {
            alert('Error signing in: ' + error.message);
            this.resetSignInButton();
        }
    },

    async _watchForHeadlessUrl(attempts = 0) {
        if (this._headlessUrlOpened || attempts > 20) return;
        try {
            const resp = await fetch('/api/web-auth-status');
            const status = await resp.json();
            if (status.pending_auth_url) {
                this._headlessUrlOpened = true;
                window.open(status.pending_auth_url, '_blank');
                return;
            }
        } catch (_) { /* ignore */ }
        setTimeout(() => this._watchForHeadlessUrl(attempts + 1), 500);
    },

    setSignInButtonText(text) {
        const signInBtn = document.getElementById('signInBtn');
        if (signInBtn) signInBtn.innerHTML = `<span>${GmailCleaner.UI.escapeHtml(text)}</span>`;
    },

    async pollStatus(attempts = 0) {
        // 5 minutes (300 polls @ 1s) — matches backend OAuth timeout.
        const maxAttempts = 300;

        try {
            const [authResp, progressResp] = await Promise.all([
                fetch('/api/auth-status'),
                fetch('/api/auth-progress'),
            ]);
            const auth = await authResp.json();
            const progress = progressResp.ok ? await progressResp.json() : null;

            if (auth.logged_in) {
                this.updateUI(auth);
                return;
            }

            // Surface live progress to the user via the button label.
            if (progress) {
                if (progress.state === 'awaiting_browser') {
                    this.setSignInButtonText('Waiting for Google...');
                } else if (progress.state === 'starting') {
                    this.setSignInButtonText('Starting sign-in...');
                } else if (progress.state === 'failed') {
                    this.resetSignInButton();
                    alert('Sign-in failed: ' + (progress.error || 'unknown error'));
                    return;
                } else if (progress.state === 'timeout') {
                    this.resetSignInButton();
                    alert('Sign-in timed out. Please click Sign in to try again.');
                    return;
                }
            }

            if (attempts < maxAttempts) {
                setTimeout(() => this.pollStatus(attempts + 1), 1000);
            } else {
                this.resetSignInButton();
                alert('Sign-in timed out. Please try again.');
            }
        } catch (error) {
            console.error('Error polling auth status:', error);
            if (attempts < maxAttempts) {
                setTimeout(() => this.pollStatus(attempts + 1), 1000);
            } else {
                this.resetSignInButton();
            }
        }
    },

    resetSignInButton() {
        const signInBtn = document.getElementById('signInBtn');
        if (signInBtn) {
            signInBtn.disabled = false;
            signInBtn.innerHTML = `<svg viewBox="0 0 24 24" width="20" height="20">
                <path fill="currentColor" d="M12.545,10.239v3.821h5.445c-0.712,2.315-2.647,3.972-5.445,3.972c-3.332,0-6.033-2.701-6.033-6.032s2.701-6.032,6.033-6.032c1.498,0,2.866,0.549,3.921,1.453l2.814-2.814C17.503,2.988,15.139,2,12.545,2C7.021,2,2.543,6.477,2.543,12s4.478,10,10.002,10c8.396,0,10.249-7.85,9.426-11.748L12.545,10.239z"/>
            </svg>
            Sign in with Google`;
        }
    },

    async checkWebAuthMode() {
        // No longer needed - sign in works everywhere now!
        return;
    },

    async signOut() {
        if (!confirm('Sign out of your Gmail account?')) return;

        try {
            await fetch('/api/sign-out', { method: 'POST' });
            GmailCleaner.results = [];
            GmailCleaner.Scanner.updateResultsBadge();
            GmailCleaner.Scanner.displayResults();
            document.getElementById('selectAll').checked = false;
            this.checkStatus();
        } catch (error) {
            alert('Error signing out: ' + error.message);
        }
    },

    showUserMenu() {
        console.log('User menu clicked');
    }
};

// Global shortcuts for onclick handlers
function signIn() { GmailCleaner.Auth.signIn(); }
function signOut() { GmailCleaner.Auth.signOut(); }

function showAppPasswordInfo() {
    alert(
        'Corporate / App Password notes:\n\n' +
        '1) App passwords usually require 2-Step Verification and may be disabled by Google Workspace policy.\n' +
        '2) App passwords are typically for IMAP/SMTP clients.\n' +
        '3) This app uses Gmail API actions (labeling, unsubscribe helpers, bulk operations), which require OAuth.\n\n' +
        'Recommendation: use OAuth for full functionality.\n' +
        'If you want, we can add a separate IMAP read-only mode as a future component.'
    );
}
