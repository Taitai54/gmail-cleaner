/**
 * Gmail Unsubscribe - UI Utilities Module
 */

window.GmailCleaner = window.GmailCleaner || {};

GmailCleaner.UI = {
    setupNavigation() {
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const view = item.dataset.view;
                this.showView(view);
            });
        });
    },

    showView(viewName) {
        GmailCleaner.currentView = viewName;

        // Hide all views
        document.querySelectorAll('.view').forEach(view => {
            view.classList.add('hidden');
        });

        // Show requested view
        const viewId = viewName + 'View';
        const view = document.getElementById(viewId);
        if (view) {
            view.classList.remove('hidden');
        }

        // Update nav active state
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
            if (item.dataset.view === viewName) {
                item.classList.add('active');
            }
        });

        // Filter bar only applies to scan/delete/markread — hide it for Search & Export,
        // Labels, and Restore Archive. We only touch it here when switching away from or to one of those
        // views; Filters.showBar() still owns the logged-in/logged-out transition.
        const hidesFilterBar = viewName === 'search' || viewName === 'labels' || viewName === 'restore';
        const filterBar = document.getElementById('filterBar');
        const mainContent = document.querySelector('.main-content');
        if (filterBar && hidesFilterBar) {
            filterBar.classList.add('hidden');
            if (mainContent) mainContent.classList.remove('with-filters');
        } else if (filterBar && !hidesFilterBar && !filterBar.classList.contains('hidden')) {
            // Already visible — keep it; no change needed.
        } else if (filterBar && !hidesFilterBar) {
            // Switching back from search/labels/restore: restore if user is logged in
            if (GmailCleaner.Filters) GmailCleaner.Filters.showBar(true);
        }

        // Special handling for unsubscribe view
        if (viewName === 'unsubscribe') {
            if (GmailCleaner.results.length === 0) {
                document.getElementById('noResults').classList.remove('hidden');
                document.getElementById('resultsSection').classList.add('hidden');
            } else {
                document.getElementById('noResults').classList.add('hidden');
                document.getElementById('resultsSection').classList.remove('hidden');
            }
        }

        // Refresh unread count when switching to Mark Read view
        if (viewName === 'markread') {
            GmailCleaner.MarkRead.refreshUnreadCount();
        }

        // Load and render the label tree when switching to Labels view
        if (viewName === 'labels') {
            GmailCleaner.Labels.loadAndRenderTree();
        }

        // Initialize restore dropdowns when switching to Restore view
        if (viewName === 'restore' && GmailCleaner.Restore?.init) {
            GmailCleaner.Restore.init();
        }
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    },

    // Format bytes to human-readable size
    formatSize(bytes) {
        if (!bytes || bytes === 0) return '';
        const units = ['B', 'KB', 'MB', 'GB'];
        let size = bytes;
        let unitIndex = 0;
        while (size >= 1024 && unitIndex < units.length - 1) {
            size /= 1024;
            unitIndex++;
        }
        return size.toFixed(unitIndex > 0 ? 1 : 0) + ' ' + units[unitIndex];
    },

    toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        sidebar.classList.toggle('open');
    },

    // Toast notification system
    showToast(message, type = 'success', duration = 5000, tip = null) {
        // Create toast container if it doesn't exist
        let container = document.getElementById('toastContainer');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toastContainer';
            container.className = 'toast-container';
            document.body.appendChild(container);
        }

        // Create toast element
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;

        // Icon based on type
        const icons = {
            success: '<svg viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/></svg>',
            error: '<svg viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41z"/></svg>',
            info: '<svg viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>'
        };

        toast.innerHTML = `
            <div class="toast-icon">${icons[type] || icons.success}</div>
            <div class="toast-content">
                <div class="toast-message">${message}</div>
                ${tip ? `<div class="toast-tip">${tip}</div>` : ''}
            </div>
            <button class="toast-close" onclick="this.parentElement.remove()">
                <svg viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41z"/></svg>
            </button>
        `;

        container.appendChild(toast);

        // Trigger animation
        setTimeout(() => toast.classList.add('show'), 10);

        // Auto remove after duration
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    },

    // Convenience methods
    showSuccessToast(message, tip = null) {
        this.showToast(message, 'success', 5000, tip);
    },

    showErrorToast(message) {
        this.showToast(message, 'error', 6000);
    },

    showInfoToast(message) {
        this.showToast(message, 'info', 4000);
    },

    // Deterministic Sender Avatar Gradients
    getAvatarGradient(str) {
        const gradients = [
            'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)', // Indigo-Violet
            'linear-gradient(135deg, #ec4899 0%, #f43f5e 100%)', // Pink-Rose
            'linear-gradient(135deg, #f59e0b 0%, #ea580c 100%)', // Amber-Orange
            'linear-gradient(135deg, #10b981 0%, #059669 100%)', // Emerald-Teal
            'linear-gradient(135deg, #06b6d4 0%, #0284c7 100%)', // Cyan-Sky
            'linear-gradient(135deg, #8b5cf6 0%, #d946ef 100%)', // Purple-Fuchsia
            'linear-gradient(135deg, #14b8a6 0%, #0d9488 100%)', // Teal-Mint
            'linear-gradient(135deg, #64748b 0%, #475569 100%)'  // Slate
        ];
        let hash = 0;
        const s = String(str || 'U');
        for (let i = 0; i < s.length; i++) {
            hash = s.charCodeAt(i) + ((hash << 5) - hash);
        }
        return gradients[Math.abs(hash) % gradients.length];
    },

    // Theme Management
    initTheme() {
        const savedTheme = localStorage.getItem('gmail_cleaner_theme') || 'indigo';
        this.applyTheme(savedTheme, false);

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            const menu = document.getElementById('themePickerMenu');
            if (menu && !menu.contains(e.target)) {
                const dd = document.getElementById('theme-dropdown');
                if (dd) dd.classList.add('hidden');
            }
        });
    },

    toggleThemePicker() {
        const dd = document.getElementById('theme-dropdown');
        if (dd) {
            dd.classList.toggle('hidden');
        }
    },

    setTheme(themeName) {
        this.applyTheme(themeName, true);
        const dd = document.getElementById('theme-dropdown');
        if (dd) dd.classList.add('hidden');
        this.showSuccessToast(`Switched theme to ${themeName.charAt(0).toUpperCase() + themeName.slice(1)}!`);
    },

    applyTheme(themeName, persist = true) {
        document.documentElement.setAttribute('data-theme', themeName);
        if (persist) {
            localStorage.setItem('gmail_cleaner_theme', themeName);
        }

        // Update active class in dropdown
        const buttons = document.querySelectorAll('.theme-option-btn');
        buttons.forEach(btn => {
            if (btn.getAttribute('data-theme-value') === themeName) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
    }
};

// Global shortcuts
function showView(viewName) { GmailCleaner.UI.showView(viewName); }
function toggleSidebar() { GmailCleaner.UI.toggleSidebar(); }
function showToast(message, type, duration, tip) { GmailCleaner.UI.showToast(message, type, duration, tip); }
window.setTheme = (t) => GmailCleaner.UI.setTheme(t);
window.toggleThemePicker = () => GmailCleaner.UI.toggleThemePicker();

document.addEventListener('DOMContentLoaded', () => {
    try {
        if (window.GmailCleaner && GmailCleaner.UI) {
            GmailCleaner.UI.initTheme();
        }
    } catch (e) {
        console.warn('Theme init warning:', e);
    }
});
