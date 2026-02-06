/**
 * Gmail Cleaner - Export & Label Processing Module
 * Handles email thread search, selective export, and unsubscribe label processing
 */

window.GmailCleaner = window.GmailCleaner || {};

GmailCleaner.Export = {
    // Stores the current search results (thread previews)
    searchResults: [],

    /**
     * Search for email threads and display previews for selection
     */
    searchThreads: async function() {
        const query = document.getElementById('search-query').value.trim();
        const btn = document.getElementById('search-threads-btn');
        const resultsContainer = document.getElementById('export-results-container');
        const emptyState = document.getElementById('export-empty-state');

        if (!query) {
            alert('Please enter a search query');
            return;
        }

        btn.disabled = true;
        btn.innerHTML = `
            <svg viewBox="0 0 24 24" width="18" height="18" class="rotating">
                <path fill="currentColor" d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/>
            </svg>
            Searching...
        `;

        // Hide previous results
        if (resultsContainer) resultsContainer.classList.add('hidden');
        if (emptyState) emptyState.classList.add('hidden');

        try {
            const response = await fetch('/api/search-threads', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query, max_results: 100 })
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
                body: JSON.stringify({ thread_ids: selectedIds })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Export failed');
            }

            const textContent = await response.text();
            const blob = new Blob([textContent], { type: 'text/plain' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'email_export.txt';
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
