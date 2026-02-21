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

// Storage utilities
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

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
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
});
