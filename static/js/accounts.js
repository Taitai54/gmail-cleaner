/**
 * Gmail Cleaner - Multi-Account Management Module
 * Handles signing in with multiple Gmail accounts and switching between them
 */

window.GmailCleaner = window.GmailCleaner || {};

GmailCleaner.Accounts = {
    /** Cached list of accounts from server */
    accounts: [],
    _bound: false,

    _ensureBindings() {
        if (this._bound) return;
        this._bound = true;

        const trigger = document.getElementById('accountMenuTrigger');
        if (trigger) {
            trigger.addEventListener('click', (event) => {
                event.stopPropagation();
                this.toggleDropdown();
            });
        }

        const list = document.getElementById('account-list');
        if (list) {
            list.addEventListener('click', (event) => {
                const switchBtn = event.target.closest('[data-action="switch"]');
                const removeBtn = event.target.closest('[data-action="remove"]');
                if (switchBtn) {
                    event.preventDefault();
                    this.switchTo(switchBtn.dataset.email);
                } else if (removeBtn) {
                    event.preventDefault();
                    this.remove(removeBtn.dataset.email);
                }
            });
        }
    },

    /**
     * Fetch account list from server and update the UI
     */
    async refresh() {
        this._ensureBindings();
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

        if (this.accounts.length === 0) {
            container.innerHTML = '<div class="account-empty">No saved accounts yet.</div>';
            return;
        }

        this.accounts.forEach(acct => {
            const item = document.createElement('div');
            item.className = 'account-item' + (acct.active ? ' active' : '');
            item.setAttribute('role', 'menuitem');

            const safeEmail = GmailCleaner.UI.escapeHtml(acct.email);
            const initial = acct.email.charAt(0).toUpperCase();

            const left = document.createElement('div');
            left.className = 'account-item-left';
            left.innerHTML = `
                <div class="account-avatar">${initial}</div>
                <div class="account-item-meta">
                    <span class="account-email">${safeEmail}</span>
                    ${acct.active ? '<span class="account-active-badge">Active</span>' : ''}
                </div>
            `;

            const actions = document.createElement('div');
            actions.className = 'account-item-actions';

            if (!acct.active) {
                const switchBtn = document.createElement('button');
                switchBtn.type = 'button';
                switchBtn.className = 'btn btn-sm btn-primary';
                switchBtn.dataset.action = 'switch';
                switchBtn.dataset.email = acct.email;
                switchBtn.textContent = 'Switch';
                actions.appendChild(switchBtn);
            }

            const removeBtn = document.createElement('button');
            removeBtn.type = 'button';
            removeBtn.className = 'btn btn-sm account-remove-btn';
            removeBtn.dataset.action = 'remove';
            removeBtn.dataset.email = acct.email;
            removeBtn.textContent = 'Remove';
            actions.appendChild(removeBtn);

            item.appendChild(left);
            item.appendChild(actions);
            container.appendChild(item);
        });
    },

    /**
     * Toggle the account dropdown visibility
     */
    toggleDropdown() {
        const dropdown = document.getElementById('account-dropdown');
        const trigger = document.getElementById('accountMenuTrigger');
        if (!dropdown) return;

        const willOpen = !dropdown.classList.contains('show');
        dropdown.classList.toggle('show', willOpen);
        if (trigger) trigger.setAttribute('aria-expanded', willOpen ? 'true' : 'false');

        if (willOpen) {
            this.refresh();
        }
    },

    /**
     * Close the dropdown (called on outside click)
     */
    closeDropdown() {
        const dropdown = document.getElementById('account-dropdown');
        const trigger = document.getElementById('accountMenuTrigger');
        if (dropdown) dropdown.classList.remove('show');
        if (trigger) trigger.setAttribute('aria-expanded', 'false');
    },

    _showSwitchOverlay() {
        const overlay = document.getElementById('account-switch-overlay');
        if (overlay) overlay.classList.remove('hidden');
    },

    _clearClientCaches() {
        if (typeof GmailCleaner.clearCachedResults === 'function') {
            GmailCleaner.clearCachedResults();
        }
        GmailCleaner.results = [];
        GmailCleaner.deleteResults = [];
    },

    /**
     * Switch to a different account
     */
    async switchTo(email) {
        this.closeDropdown();
        this._showSwitchOverlay();

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

            this._clearClientCaches();
            window.location.reload();
        } catch (error) {
            console.error('Switch account error:', error);
            const overlay = document.getElementById('account-switch-overlay');
            if (overlay) overlay.classList.add('hidden');
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
                this._clearClientCaches();
                this.refresh();
                GmailCleaner.Auth.checkStatus();
            } else {
                this.closeDropdown();
                GmailCleaner.Auth.checkStatus();
            }
        } catch (error) {
            console.error('Remove account error:', error);
            alert(`Failed to remove account: ${error.message}`);
        }
    },

    /**
     * Trigger OAuth to add a new (additional) account.
     */
    addAccount() {
        this.closeDropdown();
        this._showModal();
    },

    async _modalPick(clientType) {
        this._hideModal();
        try {
            const response = await fetch('/api/accounts/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ client_type: clientType }),
            });
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to start account add flow');
            }
            GmailCleaner.UI.showInfoToast('Complete Google sign-in in your browser…');
            GmailCleaner.Auth.pollStatus();
        } catch (error) {
            alert('Failed to start sign-in: ' + error.message);
        }
    },

    _modalCancel() {
        this._hideModal();
    },

    _showModal() {
        const modal = document.getElementById('account-type-modal');
        if (modal) modal.hidden = false;
    },

    _hideModal() {
        const modal = document.getElementById('account-type-modal');
        if (modal) modal.hidden = true;
    }
};

document.addEventListener('click', function(e) {
    const menu = document.getElementById('accountMenu');
    if (menu && !menu.contains(e.target)) {
        GmailCleaner.Accounts.closeDropdown();
    }
});
