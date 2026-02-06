/**
 * Gmail Cleaner - Multi-Account Management Module
 * Handles signing in with multiple Gmail accounts and switching between them
 */

window.GmailCleaner = window.GmailCleaner || {};

GmailCleaner.Accounts = {
    /** Cached list of accounts from server */
    accounts: [],

    /**
     * Fetch account list from server and update the UI
     */
    async refresh() {
        try {
            const response = await fetch('/api/accounts');
            const data = await response.json();
            this.accounts = data.accounts || [];
            this.renderAccountDropdown();
        } catch (error) {
            console.error('Failed to fetch accounts:', error);
        }
    },

    /**
     * Render the account dropdown content
     */
    renderAccountDropdown() {
        const container = document.getElementById('account-list');
        if (!container) return;

        container.innerHTML = '';

        this.accounts.forEach(acct => {
            const item = document.createElement('div');
            item.className = 'account-item' + (acct.active ? ' active' : '');

            const safeEmail = GmailCleaner.UI.escapeHtml(acct.email);

            item.innerHTML = `
                <div class="account-item-left">
                    <div class="account-avatar">${acct.email.charAt(0).toUpperCase()}</div>
                    <span class="account-email">${safeEmail}</span>
                    ${acct.active ? '<span class="account-active-badge">Active</span>' : ''}
                </div>
                <div class="account-item-actions">
                    ${!acct.active ? `<button class="btn btn-sm btn-secondary" onclick="GmailCleaner.Accounts.switchTo('${safeEmail}')">Use</button>` : ''}
                    <button class="btn btn-sm account-remove-btn" onclick="GmailCleaner.Accounts.remove('${safeEmail}')">Remove</button>
                </div>
            `;
            container.appendChild(item);
        });
    },

    /**
     * Toggle the account dropdown visibility
     */
    toggleDropdown() {
        const dropdown = document.getElementById('account-dropdown');
        if (!dropdown) return;
        dropdown.classList.toggle('show');
        if (dropdown.classList.contains('show')) {
            this.refresh();
        }
    },

    /**
     * Close the dropdown (called on outside click)
     */
    closeDropdown() {
        const dropdown = document.getElementById('account-dropdown');
        if (dropdown) dropdown.classList.remove('show');
    },

    /**
     * Switch to a different account
     */
    async switchTo(email) {
        try {
            const response = await fetch('/api/accounts/switch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: email })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Switch failed');
            }

            GmailCleaner.UI.showSuccessToast(`Switched to ${email}`);
            this.closeDropdown();

            // Re-check auth status to update the header
            GmailCleaner.Auth.checkStatus();
        } catch (error) {
            console.error('Switch account error:', error);
            alert(`Failed to switch account: ${error.message}`);
        }
    },

    /**
     * Remove (sign out of) a specific account
     */
    async remove(email) {
        if (!confirm(`Remove ${email} from signed-in accounts?`)) return;

        try {
            const response = await fetch('/api/accounts/remove', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: email })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Remove failed');
            }

            const result = await response.json();
            GmailCleaner.UI.showSuccessToast(`Removed ${email}`);

            if (result.active) {
                // Another account is still active
                this.refresh();
                GmailCleaner.Auth.checkStatus();
            } else {
                // No accounts left — back to login
                this.closeDropdown();
                GmailCleaner.Auth.checkStatus();
            }
        } catch (error) {
            console.error('Remove account error:', error);
            alert(`Failed to remove account: ${error.message}`);
        }
    },

    /**
     * Trigger OAuth to add a new (additional) account
     */
    async addAccount() {
        this.closeDropdown();
        try {
            await fetch('/api/sign-in', { method: 'POST' });
            GmailCleaner.UI.showInfoToast('Opening Google sign-in for a new account...');
            // Poll until a new account appears
            GmailCleaner.Auth.pollStatus();
        } catch (error) {
            alert('Failed to start sign-in: ' + error.message);
        }
    }
};

// Close account dropdown on outside click
document.addEventListener('click', function(e) {
    const wrapper = document.getElementById('account-dropdown-wrapper');
    if (wrapper && !wrapper.contains(e.target)) {
        GmailCleaner.Accounts.closeDropdown();
    }
});
