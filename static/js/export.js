/**
 * Gmail Cleaner - Export & Label Processing Module
 * Handles email thread search, selective export, and unsubscribe label processing
 */

window.GmailCleaner = window.GmailCleaner || {};

GmailCleaner.Export = {
    // Stores the current search results (thread previews)
    searchResults: [],
    suggestionValues: [],
    activeSuggestionIndex: -1,
    activeSuggestionInputId: null,

    /**
     * Build ranked email/domain suggestions from known sender data.
     */
    updateEmailSuggestions: function(inputValue = '') {
        const datalist = document.getElementById('email-suggestions');
        if (!datalist) return [];

        const term = String(inputValue || '').trim().toLowerCase();
        const candidates = new Set();

        // Scan results
        if (Array.isArray(GmailCleaner.results)) {
            GmailCleaner.results.forEach((r) => {
                if (r?.sender?.email) candidates.add(String(r.sender.email).toLowerCase());
                if (r?.sender?.domain) candidates.add(String(r.sender.domain).toLowerCase());
            });
        }

        // Delete results
        if (Array.isArray(GmailCleaner.deleteResults)) {
            GmailCleaner.deleteResults.forEach((r) => {
                if (r?.email) candidates.add(String(r.email).toLowerCase());
                if (r?.domain) candidates.add(String(r.domain).toLowerCase());
            });
        }

        // Current export search results
        if (Array.isArray(this.searchResults)) {
            this.searchResults.forEach((r) => {
                if (!r?.sender) return;
                const sender = String(r.sender).toLowerCase();
                const emailMatch = sender.match(/[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}/);
                if (emailMatch) {
                    candidates.add(emailMatch[0]);
                    const domain = emailMatch[0].split('@')[1];
                    if (domain) candidates.add(domain);
                } else if (sender.includes('@') || sender.includes('.')) {
                    candidates.add(sender);
                }
            });
        }

        const ranked = Array.from(candidates)
            .filter((v) => v)
            .sort((a, b) => {
                if (!term) return a.localeCompare(b);
                const scoreA = this.getSuggestionScore(a, term);
                const scoreB = this.getSuggestionScore(b, term);
                if (scoreA !== scoreB) return scoreB - scoreA;
                return a.localeCompare(b);
            })
            .filter((v) => !term || this.getSuggestionScore(v, term) > 0.25)
            .slice(0, 20);

        datalist.innerHTML = '';
        ranked.forEach((value) => {
            const option = document.createElement('option');
            option.value = value;
            datalist.appendChild(option);
        });

        this.suggestionValues = ranked;
        return ranked;
    },

    getSuggestionScore: function(candidate, term) {
        if (!term) return 0.5;
        const value = String(candidate || '').toLowerCase();
        if (!value) return 0;
        if (value === term) return 1.0;
        if (value.startsWith(term)) return 0.95;
        if (value.includes(term)) return 0.8;

        const parts = value.split(/[@.\s]+/).filter(Boolean);
        const partStarts = parts.some((p) => p.startsWith(term));
        if (partStarts) return 0.7;

        const dist = this.levenshteinDistance(value, term);
        const ratio = dist / Math.max(value.length, term.length);
        if (ratio <= 0.35) return 0.55;
        if (ratio <= 0.5) return 0.35;
        return 0;
    },

    levenshteinDistance: function(a, b) {
        const s = String(a || '');
        const t = String(b || '');
        const rows = s.length + 1;
        const cols = t.length + 1;
        const dp = Array.from({ length: rows }, () => new Array(cols).fill(0));

        for (let i = 0; i < rows; i += 1) dp[i][0] = i;
        for (let j = 0; j < cols; j += 1) dp[0][j] = j;

        for (let i = 1; i < rows; i += 1) {
            for (let j = 1; j < cols; j += 1) {
                const cost = s[i - 1] === t[j - 1] ? 0 : 1;
                dp[i][j] = Math.min(
                    dp[i - 1][j] + 1,
                    dp[i][j - 1] + 1,
                    dp[i - 1][j - 1] + cost,
                );
            }
        }
        return dp[s.length][t.length];
    },

    showSuggestionDropdown: function(input, values) {
        const dropdown = document.getElementById('email-suggest-dropdown');
        if (!dropdown || !input || !values || values.length === 0) {
            this.hideSuggestionDropdown();
            return;
        }

        const rect = input.getBoundingClientRect();
        dropdown.style.left = `${rect.left}px`;
        dropdown.style.top = `${rect.bottom + 4}px`;
        dropdown.style.width = `${Math.max(rect.width, 260)}px`;
        dropdown.innerHTML = '';

        values.forEach((value, index) => {
            const item = document.createElement('div');
            item.className = 'email-suggest-item';
            item.dataset.index = String(index);
            item.textContent = value;
            item.addEventListener('mousedown', (event) => {
                event.preventDefault();
                this.applySuggestionValue(input, value);
            });
            dropdown.appendChild(item);
        });

        this.activeSuggestionIndex = -1;
        this.activeSuggestionInputId = input.id;
        dropdown.classList.remove('hidden');
    },

    hideSuggestionDropdown: function() {
        const dropdown = document.getElementById('email-suggest-dropdown');
        if (dropdown) {
            dropdown.classList.add('hidden');
            dropdown.innerHTML = '';
        }
        this.activeSuggestionIndex = -1;
        this.activeSuggestionInputId = null;
    },

    moveSuggestionSelection: function(direction) {
        const dropdown = document.getElementById('email-suggest-dropdown');
        if (!dropdown || dropdown.classList.contains('hidden')) return;
        const items = Array.from(dropdown.querySelectorAll('.email-suggest-item'));
        if (items.length === 0) return;

        this.activeSuggestionIndex += direction;
        if (this.activeSuggestionIndex < 0) this.activeSuggestionIndex = items.length - 1;
        if (this.activeSuggestionIndex >= items.length) this.activeSuggestionIndex = 0;

        items.forEach((item) => item.classList.remove('active'));
        const active = items[this.activeSuggestionIndex];
        if (active) {
            active.classList.add('active');
            active.scrollIntoView({ block: 'nearest' });
        }
    },

    applyCurrentSuggestion: function(input) {
        const dropdown = document.getElementById('email-suggest-dropdown');
        if (!dropdown || dropdown.classList.contains('hidden')) return false;
        const items = Array.from(dropdown.querySelectorAll('.email-suggest-item'));
        if (items.length === 0) return false;

        const idx = this.activeSuggestionIndex >= 0 ? this.activeSuggestionIndex : 0;
        const value = items[idx]?.textContent;
        if (!value) return false;
        this.applySuggestionValue(input, value);
        return true;
    },

    applySuggestionValue: function(input, value) {
        if (!input) return;
        input.value = value;
        this.hideSuggestionDropdown();
    },

    /**
     * Wire up intelligent autocomplete behavior for From/To fields.
     */
    initEmailAutocomplete: function() {
        const senderInput = document.getElementById('filterSender');
        const bindInput = (input) => {
            if (!input) return;
            input.addEventListener('input', () => {
                const values = this.updateEmailSuggestions(input.value);
                this.showSuggestionDropdown(input, values);
            });
            input.addEventListener('focus', () => {
                const values = this.updateEmailSuggestions(input.value);
                this.showSuggestionDropdown(input, values);
            });
            input.addEventListener('keydown', (event) => {
                if (event.key === 'ArrowDown') {
                    event.preventDefault();
                    this.moveSuggestionSelection(1);
                } else if (event.key === 'ArrowUp') {
                    event.preventDefault();
                    this.moveSuggestionSelection(-1);
                } else if (event.key === 'Enter') {
                    if (this.applyCurrentSuggestion(input)) {
                        event.preventDefault();
                    }
                } else if (event.key === 'Escape') {
                    this.hideSuggestionDropdown();
                }
            });
            input.addEventListener('blur', () => {
                // Delay to allow mousedown selection on suggestion items.
                setTimeout(() => {
                    if (this.activeSuggestionInputId === input.id) {
                        this.hideSuggestionDropdown();
                    }
                }, 120);
            });
        };

        bindInput(senderInput);
        this.updateEmailSuggestions('');

        document.addEventListener('click', (event) => {
            const dropdown = document.getElementById('email-suggest-dropdown');
            if (!dropdown) return;
            const target = event.target;
            const clickedInput = target && target.id === 'filterSender';
            const clickedDropdown = dropdown.contains(target);
            if (!clickedInput && !clickedDropdown) {
                this.hideSuggestionDropdown();
            }
        });
    },

    /**
     * Search for email threads and display previews for selection
     */
    searchThreads: async function() {
        const senderField = document.getElementById('filterSender')?.value.trim();
        const subjectField = document.getElementById('search-subject')?.value.trim();
        const includesField = document.getElementById('search-includes')?.value.trim();
        const excludesField = document.getElementById('search-excludes')?.value.trim();
        const sizeField = document.getElementById('search-size')?.value.trim();
        const afterDateField = document.getElementById('search-after-date')?.value.trim();
        const beforeDateField = document.getElementById('search-before-date')?.value.trim();
        const hasAttachment = document.getElementById('search-has-attachment')?.checked;
        const excludeChats = document.getElementById('search-exclude-chats')?.checked;

        let queryParts = [];
        if (subjectField) queryParts.push(`subject:(${subjectField})`);
        if (includesField) queryParts.push(`(${includesField})`);
        if (excludesField) queryParts.push(`-(${excludesField})`);
        if (sizeField) queryParts.push(`larger:${sizeField}M`);
        if (afterDateField) queryParts.push(`after:${afterDateField.replaceAll('-', '/')}`);
        if (beforeDateField) queryParts.push(`before:${beforeDateField.replaceAll('-', '/')}`);
        if (hasAttachment) queryParts.push('has:attachment');
        if (excludeChats) queryParts.push('-in:chats');

        const filters = window.GmailCleaner && GmailCleaner.Filters
            ? GmailCleaner.Filters.get()
            : null;
        const btn = document.getElementById('search-threads-btn');
        const resultsContainer = document.getElementById('export-results-container');
        const emptyState = document.getElementById('export-empty-state');

        const initialQuery = queryParts.join(' ');
        const hasFilters = filters && Object.values(filters).some(v => v && v !== '');
        if (!initialQuery && !hasFilters) {
            alert('Please fill out at least one search field or set a global filter');
            return;
        }

        // For export search UX, treat sender as from OR to, not just from.
        // We fold it into the query and clear sender in filters to avoid duplicate / conflicting semantics.
        if (filters && filters.sender) {
            queryParts.unshift(`(from:(${filters.sender}) OR to:(${filters.sender}))`);
            filters.sender = '';
        }

        const finalQuery = queryParts.join(' ');

        btn.disabled = true;
        btn.innerHTML = `
            <svg viewBox="0 0 24 24" width="18" height="18" class="rotating">
                <path fill="currentColor" d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/>
            </svg>
            Searching (fetching all results)...
        `;

        // Hide previous results
        if (resultsContainer) resultsContainer.classList.add('hidden');
        if (emptyState) emptyState.classList.add('hidden');

        try {
            const response = await fetch('/api/search-threads', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: finalQuery,
                    max_results: 500,
                    // Filters are optional; backend handles null/empty dict
                    filters: filters
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Search failed');
            }

            const data = await response.json();
            this.searchResults = data.threads || [];

            if (this.searchResults.length === 0) {
                if (emptyState) {
                    emptyState.textContent = 'No threads found matching your query.';
                    emptyState.classList.remove('hidden');
                }
            } else {
                this.updateEmailSuggestions(senderField || '');
                this.renderSearchResults();
            }

            GmailCleaner.UI.showInfoToast(`Found ${this.searchResults.length} thread(s)`);

        } catch (error) {
            console.error('Search error:', error);
            alert(`Search failed: ${error.message}`);
        } finally {
            btn.disabled = false;
            btn.innerHTML = `
                <svg viewBox="0 0 24 24" width="18" height="18">
                    <path fill="currentColor" d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
                </svg>
                Search
            `;
        }
    },

    /**
     * Render the search results as a selectable list
     */
    renderSearchResults: function() {
        const container = document.getElementById('export-results-list');
        const resultsContainer = document.getElementById('export-results-container');
        const badge = document.getElementById('export-results-badge');

        if (!container || !resultsContainer) return;

        container.innerHTML = '';
        if (badge) badge.textContent = this.searchResults.length;

        this.searchResults.forEach((thread, index) => {
            const item = document.createElement('div');
            item.className = 'result-item';
            item.dataset.index = index;

            const safeSnippet = GmailCleaner.UI.escapeHtml(thread.snippet || '');
            const safeSender = GmailCleaner.UI.escapeHtml(thread.sender || 'Unknown');
            const safeSubject = GmailCleaner.UI.escapeHtml(thread.subject || '(no subject)');
            const safeDate = GmailCleaner.UI.escapeHtml(thread.date || '');
            const msgCount = thread.message_count || 1;

            item.innerHTML = `
                <label class="checkbox-wrapper">
                    <input type="checkbox" class="export-thread-cb" data-index="${index}">
                    <span class="checkmark"></span>
                </label>
                <div class="result-content">
                    <div class="result-sender">${safeSender}</div>
                    <div style="flex:1; min-width:0;">
                        <div class="result-subject">${safeSubject}</div>
                        <div style="font-size:12px; color:#5f6368; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${safeSnippet}</div>
                    </div>
                </div>
                <div class="result-meta">
                    <span class="result-count">${msgCount} msg${msgCount > 1 ? 's' : ''}</span>
                    <span style="font-size:12px; color:#5f6368; white-space:nowrap;">${safeDate}</span>
                </div>
            `;
            container.appendChild(item);
        });

        resultsContainer.classList.remove('hidden');

        // Reset select-all checkbox
        const selectAll = document.getElementById('export-select-all');
        if (selectAll) selectAll.checked = false;
    },

    /**
     * Toggle all checkboxes in the export results
     */
    toggleSelectAll: function() {
        const selectAll = document.getElementById('export-select-all');
        const checkboxes = document.querySelectorAll('.export-thread-cb');
        checkboxes.forEach(cb => { cb.checked = selectAll.checked; });
    },

    /**
     * Export only the selected threads
     */
    exportSelected: async function() {
        const checkboxes = document.querySelectorAll('.export-thread-cb:checked');
        if (checkboxes.length === 0) {
            alert('Please select at least one thread to export');
            return;
        }

        const selectedIds = [];
        checkboxes.forEach(cb => {
            const idx = parseInt(cb.dataset.index, 10);
            if (this.searchResults[idx]) {
                selectedIds.push(this.searchResults[idx].id);
            }
        });

        const formatSelect = document.getElementById('export-format');
        const format = formatSelect ? formatSelect.value : 'text';

        const btn = document.getElementById('export-selected-btn');
        btn.disabled = true;
        btn.innerHTML = `
            <svg viewBox="0 0 24 24" width="18" height="18" class="rotating">
                <path fill="currentColor" d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/>
            </svg>
            Exporting...
        `;

        try {
            const response = await fetch('/api/export-selected', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ thread_ids: selectedIds, format: format })
            });

            if (!response.ok) {
                let errorMsg = 'Export failed';
                try {
                    const error = await response.json();
                    errorMsg = error.detail || errorMsg;
                } catch(e) {}
                throw new Error(errorMsg);
            }

            // Extract filename from Content-Disposition if available, or use default
            let filename = 'email_export';
            if (format === 'text') filename += '.txt';
            else if (format === 'markdown') filename += '.md';
            else if (format === 'pdf') filename += '.pdf';

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            GmailCleaner.UI.showSuccessToast(`Exported ${selectedIds.length} thread(s) successfully!`);

        } catch (error) {
            console.error('Export error:', error);
            alert(`Export failed: ${error.message}`);
        } finally {
            btn.disabled = false;
            btn.innerHTML = `
                <svg viewBox="0 0 24 24" width="18" height="18">
                    <path fill="currentColor" d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/>
                </svg>
                Export Selected
            `;
        }
    },

    /**
     * Process emails with 'Unsubscribe' label
     */
    processUnsubscribeLabel: async function() {
        const btn = document.getElementById('process-unsubscribe-btn');

        const confirmed = confirm(
            "This will process all emails labeled 'Unsubscribe' and visit their unsubscribe links. " +
            "The label will be removed after processing. Continue?"
        );
        if (!confirmed) return;

        btn.disabled = true;
        btn.innerHTML = `
            <svg viewBox="0 0 24 24" width="18" height="18" class="rotating">
                <path fill="currentColor" d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/>
            </svg>
            Processing...
        `;

        try {
            const response = await fetch('/api/process-unsubscribe-label', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ label_name: 'Unsubscribe' })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Processing failed');
            }

            const result = await response.json();
            alert(result.message);
            GmailCleaner.UI.showSuccessToast('Label processing completed!');

        } catch (error) {
            console.error('Label processing error:', error);
            alert(`Processing failed: ${error.message}`);
        } finally {
            btn.disabled = false;
            btn.innerHTML = `
                <svg viewBox="0 0 24 24" width="18" height="18">
                    <path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zM4 12c0-4.42 3.58-8 8-8 1.85 0 3.55.63 4.9 1.69L5.69 16.9C4.63 15.55 4 13.85 4 12zm8 8c-1.85 0-3.55-.63-4.9-1.69L18.31 7.1C19.37 8.45 20 10.15 20 12c0 4.42-3.58 8-8 8z"/>
                </svg>
                Process 'Unsubscribe' Label
            `;
        }
    }
};

// Global shortcuts for onclick handlers
window.searchThreads = () => GmailCleaner.Export.searchThreads();
window.exportSelected = () => GmailCleaner.Export.exportSelected();
window.toggleExportSelectAll = () => GmailCleaner.Export.toggleSelectAll();
window.processUnsubscribeLabel = () => GmailCleaner.Export.processUnsubscribeLabel();

document.addEventListener('DOMContentLoaded', () => {
    if (window.GmailCleaner && GmailCleaner.Export) {
        GmailCleaner.Export.initEmailAutocomplete();
    }
});
