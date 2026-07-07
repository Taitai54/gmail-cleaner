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
        const accountMenu = document.getElementById('accountMenu');

        if (authStatus.logged_in && authStatus.email) {
            const safeEmail = GmailCleaner.UI.escapeHtml(authStatus.email);
            const initial = authStatus.email.charAt(0).toUpperCase();

            if (accountMenu) accountMenu.classList.remove('hidden');

            const emailEl = document.getElementById('activeAccountEmail');
            const avatarEl = document.getElementById('activeAccountAvatar');
            if (emailEl) emailEl.textContent = authStatus.email;
            if (avatarEl) {
                avatarEl.textContent = initial;
                avatarEl.title = authStatus.email;
            }

            GmailCleaner.Filters.showBar(true);
            GmailCleaner.UI.showView('unsubscribe');

            this.loadLabelsForFilter();
            if (GmailCleaner.Accounts) GmailCleaner.Accounts.refresh();
        } else {
            if (accountMenu) {
                accountMenu.classList.add('hidden');
                GmailCleaner.Accounts.closeDropdown();
            }
            GmailCleaner.Filters.showBar(false);
            GmailCleaner.UI.showView('login');
        }
    },

    async loadLabelsForFilter() {
        try {
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

    async signIn(clientType = null) {
        const signInBtn = document.getElementById('signInBtn');

        if (signInBtn) {
            signInBtn.disabled = true;
            signInBtn.innerHTML = '<span class="login-option-text"><strong>Starting sign-in…</strong><span>Complete authorization in your browser</span></span>';
        }

        try {
            const statusResp = await fetch('/api/web-auth-status');
            const status = await statusResp.json();

            const credKey = clientType === 'gmail'
                ? 'has_gmail_credentials'
                : clientType === 'unidays'
                    ? 'has_unidays_credentials'
                    : 'has_credentials';

            if (!status[credKey]) {
                this.resetSignInButton();
                const fileHint = clientType === 'gmail'
                    ? 'credentials_gmail.json'
                    : clientType === 'unidays'
                        ? 'credentials_unidays.json'
                        : 'credentials.json';
                alert(`${fileHint} not found or invalid!\n\nSetup instructions:\n1. Go to https://console.cloud.google.com/\n2. Create project → Enable Gmail API\n3. Create OAuth credentials (Desktop app or Web app with http://127.0.0.1:8767/ redirect)\n4. Download JSON → save as ${fileHint}\n5. Restart the app`);
                return;
            }

            const signInResp = await fetch('/api/sign-in', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ client_type: clientType }),
            });
            const signInResult = await signInResp.json();

            if (signInResult.error) {
                this.resetSignInButton();
                alert('Sign-in error: ' + signInResult.error);
                return;
            }

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
        if (signInBtn) {
            signInBtn.innerHTML = `<span class="login-option-text"><strong>${GmailCleaner.UI.escapeHtml(text)}</strong><span>Complete authorization in your browser</span></span>`;
        }
    },

    async pollStatus(attempts = 0) {
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
                this.resetSignInButton();
                return;
            }

            if (progress) {
                if (progress.state === 'awaiting_browser') {
                    this.setSignInButtonText('Waiting for Google…');
                } else if (progress.state === 'starting') {
                    this.setSignInButtonText('Starting sign-in…');
                } else if (progress.state === 'failed') {
                    this.resetSignInButton();
                    alert('Sign-in failed: ' + (progress.error || 'unknown error'));
                    return;
                } else if (progress.state === 'timeout') {
                    this.resetSignInButton();
                    alert('Sign-in timed out. Please click Sign in to try again.');
                    return;
                } else if (progress.state === 'completed') {
                    this.setSignInButtonText('Finishing sign-in…');
                    const authRecheck = await fetch('/api/auth-status');
                    const authNow = await authRecheck.json();
                    if (authNow.logged_in) {
                        this.updateUI(authNow);
                        this.resetSignInButton();
                        return;
                    }
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
            signInBtn.innerHTML = `
                <span class="login-option-icon" aria-hidden="true">
                    <svg viewBox="0 0 24 24" width="22" height="22">
                        <path fill="currentColor" d="M12.545,10.239v3.821h5.445c-0.712,2.315-2.647,3.972-5.445,3.972c-3.332,0-6.033-2.701-6.033-6.032s2.701-6.032,6.033-6.032c1.498,0,2.866,0.549,3.921,1.453l2.814-2.814C17.503,2.988,15.139,2,12.545,2C7.021,2,2.543,6.477,2.543,12s4.478,10,10.002,10c8.396,0,10.249-7.85,9.426-11.748L12.545,10.239z"/>
                    </svg>
                </span>
                <span class="login-option-text">
                    <strong>Personal Gmail</strong>
                    <span>Standard Google OAuth</span>
                </span>`;
        }
    },

    async checkWebAuthMode() {
        return;
    },

    async signOut() {
        if (!confirm('Sign out of your active Gmail account?')) return;

        try {
            await fetch('/api/sign-out', { method: 'POST' });
            if (typeof GmailCleaner.clearCachedResults === 'function') {
                GmailCleaner.clearCachedResults();
            }
            GmailCleaner.results = [];
            GmailCleaner.deleteResults = [];
            GmailCleaner.Scanner.updateResultsBadge();
            GmailCleaner.Scanner.displayResults();
            const selectAll = document.getElementById('selectAll');
            if (selectAll) selectAll.checked = false;
            this.checkStatus();
        } catch (error) {
            alert('Error signing out: ' + error.message);
        }
    }
};

function signIn(clientType) { GmailCleaner.Auth.signIn(clientType || null); }
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
