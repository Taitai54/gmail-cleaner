/**
 * Gmail Unsubscribe - Main Entry Point
 * Initializes the application and loads all modules
 */

// Global state
window.GmailCleaner = {
    results: [],
    deleteResults: [],
    scanning: false,
    deleteScanning: false,
    currentView: 'login'
};

// Storage keys
const STORAGE_KEYS = {
    SCAN_RESULTS: 'gmailcleaner_scan_results',
    DELETE_RESULTS: 'gmailcleaner_delete_results',
    SCAN_TIMESTAMP: 'gmailcleaner_scan_timestamp',
    DELETE_TIMESTAMP: 'gmailcleaner_delete_timestamp'
};

// Storage utilities (also exposed for account switching)
const Storage = {
    save(key, data) {
        try {
            localStorage.setItem(key, JSON.stringify({
                data: data,
                timestamp: Date.now()
            }));
        } catch (e) {
            console.warn('Failed to save to localStorage:', e);
        }
    },
    
    load(key, maxAge = 3600000) { // Default 1 hour
        try {
            const item = localStorage.getItem(key);
            if (!item) return null;
            
            const parsed = JSON.parse(item);
            const age = Date.now() - parsed.timestamp;
            
            if (age > maxAge) {
                localStorage.removeItem(key);
                return null;
            }
            
            return parsed.data;
        } catch (e) {
            console.warn('Failed to load from localStorage:', e);
            return null;
        }
    },
    
    clear(key) {
        try {
            localStorage.removeItem(key);
        } catch (e) {
            console.warn('Failed to clear localStorage:', e);
        }
    }
};

GmailCleaner.clearCachedResults = function clearCachedResults() {
    Storage.clear(STORAGE_KEYS.SCAN_RESULTS);
    Storage.clear(STORAGE_KEYS.DELETE_RESULTS);
    Storage.clear(STORAGE_KEYS.SCAN_TIMESTAMP);
    Storage.clear(STORAGE_KEYS.DELETE_TIMESTAMP);
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    dedupeSearchFields();
    GmailCleaner.Auth.checkStatus();
    GmailCleaner.Auth.checkWebAuthMode();
    GmailCleaner.UI.setupNavigation();
    GmailCleaner.Filters.setup();
    
    // Restore cached results
    const cachedScanResults = Storage.load(STORAGE_KEYS.SCAN_RESULTS);
    if (cachedScanResults && cachedScanResults.length > 0) {
        GmailCleaner.results = cachedScanResults;
        GmailCleaner.Scanner.displayResults();
        GmailCleaner.Scanner.updateResultsBadge();
    }
    
    const cachedDeleteResults = Storage.load(STORAGE_KEYS.DELETE_RESULTS);
    if (cachedDeleteResults && cachedDeleteResults.length > 0) {
        GmailCleaner.deleteResults = cachedDeleteResults;
        GmailCleaner.Delete.displayResults();
    }
    
    // Populate email suggestions datalist
    populateEmailSuggestions();
});

function populateEmailSuggestions() {
    const datalist = document.getElementById('email-suggestions');
    if (!datalist) return;
    
    const senders = new Set();
    
    // Extract from scan results
    if (GmailCleaner.results) {
        GmailCleaner.results.forEach(r => {
            if (r.sender && r.sender.email) senders.add(r.sender.email);
            if (r.sender && r.sender.domain) senders.add(r.sender.domain);
        });
    }
    
    // Extract from delete results
    if (GmailCleaner.deleteResults) {
        GmailCleaner.deleteResults.forEach(r => {
            if (r.email) senders.add(r.email);
            if (r.domain) senders.add(r.domain);
        });
    }

    // Extract from export search results (if available)
    if (GmailCleaner.Export && Array.isArray(GmailCleaner.Export.searchResults)) {
        GmailCleaner.Export.searchResults.forEach(r => {
            if (r.sender) {
                const sender = String(r.sender);
                // Keep full sender string and extracted email/domain when possible
                senders.add(sender);
                const emailMatch = sender.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i);
                if (emailMatch) {
                    senders.add(emailMatch[0].toLowerCase());
                    const domain = emailMatch[0].split('@')[1];
                    if (domain) senders.add(domain.toLowerCase());
                }
            }
        });
    }
    
    datalist.innerHTML = '';
    senders.forEach(sender => {
        const option = document.createElement('option');
        option.value = sender;
        datalist.appendChild(option);
    });
}

function dedupeSearchFields() {
    // Keep the first element for each id and remove accidental duplicates.
    const uniqueIds = ['filterSender', 'email-suggestions'];

    uniqueIds.forEach((id) => {
        const nodes = document.querySelectorAll(`#${id}`);
        if (nodes.length <= 1) return;

        nodes.forEach((node, index) => {
            if (index === 0) return;
            if (id === 'email-suggestions') {
                node.remove();
                return;
            }

            const wrapper = node.closest('.form-group');
            if (wrapper) {
                wrapper.remove();
            } else {
                node.remove();
            }
        });
    });
}
