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

    applyQuickQuery: function(queryText) {
        const input = document.getElementById('search-query');
        if (!input) return;
        input.value = queryText;
        input.focus();
    },

    toggleAdvancedSearch: function() {
        const panel = document.getElementById('advanced-search-fields');
        const btn = document.getElementById('toggle-advanced-search-btn');
        if (!panel || !btn) return;
        panel.classList.toggle('hidden');
        btn.textContent = panel.classList.contains('hidden') ? 'Advanced' : 'Hide advanced';
    },

    clearSearchForm: function() {
        const ids = [
            'search-query',
            'search-subject',
            'search-includes',
            'search-excludes',
            'search-size',
        ];
        ids.forEach((id) => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });

        // Date pickers own their own display text — clear their selection rather
        // than blanking the (readonly) input directly, or stale dates would linger.
        try { this.startPicker?.clearSelection(); } catch (_) { /* ignore */ }
        try { this.endPicker?.clearSelection(); } catch (_) { /* ignore */ }

        const hasAttachment = document.getElementById('search-has-attachment');
        const excludeChats = document.getElementById('search-exclude-chats');
        const includeAnywhere = document.getElementById('search-include-anywhere');
        const scope = document.getElementById('search-scope');
        const customLabel = document.getElementById('search-custom-label');
        if (hasAttachment) hasAttachment.checked = false;
        if (excludeChats) excludeChats.checked = false;
        if (includeAnywhere) includeAnywhere.checked = false;
        if (scope) scope.value = 'all';
        if (customLabel) customLabel.value = '';
        this.handleSearchScopeChange();
        const queryDebug = document.getElementById('search-query-debug');
        if (queryDebug) queryDebug.style.display = 'none';
    },

    syncCustomLabelOptions: function() {
        const source = document.getElementById('filterLabel');
        const target = document.getElementById('search-custom-label');
        if (!target) return;

        const previousValue = target.value;
        target.innerHTML = '<option value="">Select label</option>';

        if (!source) return;

        Array.from(source.options).forEach((opt) => {
            const val = String(opt.value || '').trim();
            const label = String(opt.textContent || '').trim();
            if (!val) return; // skip "All labels"
            const option = document.createElement('option');
            option.value = val;
            option.textContent = label;
            target.appendChild(option);
        });

        if (previousValue && Array.from(target.options).some((o) => o.value === previousValue)) {
            target.value = previousValue;
        }

        // Also populate the Search & Archive "Label & Move" dropdown
        const applySelect = document.getElementById('search-apply-label-select');
        if (applySelect) {
            const prevApply = applySelect.value;
            applySelect.innerHTML = '<option value="">Choose Label...</option><option value="__new__">➕ Create New Label...</option>';
            Array.from(source.options).forEach((opt) => {
                const val = String(opt.value || '').trim();
                const label = String(opt.textContent || '').trim();
                if (!val) return;
                const option = document.createElement('option');
                option.value = val;
                option.textContent = label;
                applySelect.appendChild(option);
            });
            if (prevApply && Array.from(applySelect.options).some((o) => o.value === prevApply)) {
                applySelect.value = prevApply;
            }
        }
    },

    handleSearchLabelSelectChange: function() {
        const select = document.getElementById('search-apply-label-select');
        const input = document.getElementById('search-new-label-input');
        if (!select || !input) return;

        if (select.value === '__new__') {
            input.classList.remove('hidden');
            input.focus();
        } else {
            input.classList.add('hidden');
        }
    },

    handleSearchScopeChange: function() {
        const scope = document.getElementById('search-scope');
        const customLabelGroup = document.getElementById('search-custom-label-group');
        if (!scope || !customLabelGroup) return;

        const isCustom = scope.value === 'custom-label';
        customLabelGroup.classList.toggle('hidden', !isCustom);
        if (isCustom) this.syncCustomLabelOptions();
    },

    /**
     * Set up the Search & Export "From date" / "To date" fields using the same
     * Litepicker calendar (+ relative-date shortcut chips) as the main filter bar,
     * instead of a bare native date input.
     */
    initDateRangePicker: function() {
        const pickers = GmailCleaner.Filters.createDateRangePicker(
            'search-after-date', 'search-before-date', null
        );
        this.startPicker = pickers?.start || null;
        this.endPicker = pickers?.end || null;
        GmailCleaner.Filters.setupDateShortcuts('searchDateShortcuts', this.startPicker, this.endPicker);
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
     * Parse natural language into a Gmail query fragment.
     * Explicit patterns ("from X", "subject X") get operator-wrapped.
     * Everything else is passed through as-is so Gmail's native full-text
     * search does the broadest possible match (including contact matching).
     */
    parseNaturalLanguageQuery: function(rawText) {
        const text = String(rawText || '').trim();
        if (!text) return '';

        // Preserve explicit Gmail operators if user already entered them.
        const hasOperator = /(from:|to:|subject:|after:|before:|older_than:|newer_than:|has:|label:|in:)/i.test(text);
        if (hasOperator) return text;

        // "email from beta" / "from beta" → broaden to from+to+subject
        const fromMatch = text.match(/^(?:emails?\s+)?from\s+(.+)$/i);
        if (fromMatch && fromMatch[1]) {
            const term = fromMatch[1].trim();
            return `(from:(${term}) OR to:(${term}) OR subject:(${term}))`;
        }

        // "subject invoice"
        const subjectMatch = text.match(/^subject\s+(.+)$/i);
        if (subjectMatch && subjectMatch[1]) {
            return `subject:(${subjectMatch[1].trim()})`;
        }

        // Bare keyword or phrase — pass directly.
        // Gmail's API full-text search is broader than wrapping in explicit
        // operators (especially for contact-linked emails).
        return text;
    },

    /**
     * Search for email threads and display previews for selection
     */
    searchThreads: async function() {
        const naturalQueryField = document.getElementById('search-query')?.value.trim();
        const senderField = document.getElementById('filterSender')?.value.trim();
        const subjectField = document.getElementById('search-subject')?.value.trim();
        const includesField = document.getElementById('search-includes')?.value.trim();
        const excludesField = document.getElementById('search-excludes')?.value.trim();
        const sizeField = document.getElementById('search-size')?.value.trim();
        const afterDate = this.startPicker?.getDate()?.dateInstance;
        const beforeDate = this.endPicker?.getDate()?.dateInstance;
        const afterDateField = afterDate ? GmailCleaner.Filters.formatDateForGmail(afterDate) : '';
        const beforeDateField = beforeDate ? GmailCleaner.Filters.formatDateForGmail(beforeDate) : '';
        const hasAttachment = document.getElementById('search-has-attachment')?.checked;
        const excludeChats = document.getElementById('search-exclude-chats')?.checked;
        const includeAnywhere = document.getElementById('search-include-anywhere')?.checked;
        const maxResultsField = document.getElementById('search-max-results')?.value;
        const scopeField = document.getElementById('search-scope')?.value || 'all';
        const customLabelField = document.getElementById('search-custom-label')?.value || '';

        let queryParts = [];
        const parsedNatural = this.parseNaturalLanguageQuery(naturalQueryField);
        if (parsedNatural) queryParts.push(parsedNatural);
        if (subjectField) queryParts.push(`subject:(${subjectField})`);
        if (includesField) queryParts.push(`(${includesField})`);
        if (excludesField) queryParts.push(`-(${excludesField})`);
        if (sizeField) queryParts.push(`larger:${sizeField}M`);
        if (afterDateField) queryParts.push(`after:${afterDateField}`);
        if (beforeDateField) queryParts.push(`before:${beforeDateField}`);
        if (hasAttachment) queryParts.push('has:attachment');
        if (excludeChats) queryParts.push('-in:chats');
        if (includeAnywhere) queryParts.push('in:anywhere');

        if (scopeField === 'inbox') queryParts.push('in:inbox');
        else if (scopeField === 'sent') queryParts.push('in:sent');
        else if (scopeField === 'anywhere') queryParts.push('in:anywhere');
        else if (scopeField === 'trash') queryParts.push('in:trash');
        else if (scopeField === 'spam') queryParts.push('in:spam');
        else if (scopeField === 'custom-label' && customLabelField) queryParts.push(`label:"${customLabelField}"`);

        const btn = document.getElementById('search-threads-btn');
        const resultsContainer = document.getElementById('export-results-container');
        const emptyState = document.getElementById('export-empty-state');

        const finalQuery = queryParts.join(' ');
        if (!finalQuery) {
            alert('Please fill out at least one search field.');
            return;
        }

        btn.disabled = true;
        btn.innerHTML = `
            <svg viewBox="0 0 24 24" width="18" height="18" class="rotating">
                <path fill="currentColor" d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/>
            </svg>
            Searching...
        `;

        // Show the resolved Gmail query so the user can verify it
        const queryDebug = document.getElementById('search-query-debug');
        if (queryDebug) {
            queryDebug.textContent = `Gmail query: ${finalQuery}`;
            queryDebug.style.display = 'block';
        }

        // Hide previous results
        if (resultsContainer) resultsContainer.classList.add('hidden');
        if (emptyState) emptyState.classList.add('hidden');

        try {
            const response = await fetch('/api/search-threads', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: finalQuery,
                    max_results: Number(maxResultsField || 2000),
                })
            });

            if (!response.ok) {
                if (response.status === 401) {
                    // Auth expired or sign-in in progress — refresh UI state.
                    GmailCleaner.Auth.checkStatus();
                    return;
                }
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
     * Helper to get avatar color from sender string
     */
    getAvatarColor: function(str) {
        const colors = [
            '#4f46e5', '#7c3aed', '#db2777', '#dc2626', '#ea580c',
            '#d97706', '#059669', '#0891b2', '#2563eb', '#475569'
        ];
        let hash = 0;
        const s = String(str || 'U');
        for (let i = 0; i < s.length; i++) {
            hash = s.charCodeAt(i) + ((hash << 5) - hash);
        }
        return colors[Math.abs(hash) % colors.length];
    },

    getInitials: function(nameOrEmail) {
        const clean = String(nameOrEmail || 'U').replace(/["'<>]/g, '').trim();
        if (clean.includes('@')) {
            return clean.charAt(0).toUpperCase();
        }
        const parts = clean.split(/\s+/).filter(Boolean);
        if (parts.length >= 2) {
            return (parts[0].charAt(0) + parts[1].charAt(0)).toUpperCase();
        }
        return clean.slice(0, 2).toUpperCase();
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
            item.id = `thread-item-${index}`;

            const safeSnippet = GmailCleaner.UI.escapeHtml(thread.snippet || '');
            const rawSender = thread.sender || 'Unknown';
            const safeSender = GmailCleaner.UI.escapeHtml(rawSender);
            const safeSubject = GmailCleaner.UI.escapeHtml(thread.subject || '(no subject)');
            const safeDate = GmailCleaner.UI.escapeHtml(thread.date || '');
            const avatarBg = GmailCleaner.UI?.getAvatarGradient ? GmailCleaner.UI.getAvatarGradient(rawSender) : this.getAvatarColor(rawSender);
            const initials = this.getInitials(rawSender);

            item.innerHTML = `
                <label class="checkbox-wrapper" onclick="event.stopPropagation()">
                    <input type="checkbox" class="export-thread-cb" data-index="${index}" onchange="GmailCleaner.Export.onCheckboxChange()">
                    <span class="checkmark"></span>
                </label>
                <div class="sender-avatar" style="background: ${avatarBg}; color: white; width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 600; flex-shrink: 0; margin-right: 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.15);">
                    ${initials}
                </div>
                <div class="result-content" style="flex: 1; min-width: 0;">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 2px;">
                        <span class="result-sender" style="font-weight: 600; font-size: 14px;">${safeSender}</span>
                        <span class="result-date-pill" style="font-size: 12px; color: var(--text-muted);">${safeDate}</span>
                    </div>
                    <div class="result-subject" style="font-weight: 500; font-size: 13px; margin-bottom: 3px; color: var(--text-primary);">${safeSubject}</div>
                    <div class="result-snippet" style="font-size: 12px; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${safeSnippet}</div>
                </div>
                <div class="result-meta" style="margin-left: 12px; display: flex; align-items: center;">
                    <span class="thread-count-badge" style="font-size: 11px; background: var(--hover-bg); color: var(--text-secondary); border: 1px solid var(--border-color); padding: 2px 8px; border-radius: 12px; font-weight: 500; white-space: nowrap;">
                        ${msgCount} msg${msgCount > 1 ? 's' : ''}
                    </span>
                </div>
            `;

            item.addEventListener('click', (e) => {
                if (e.target.tagName !== 'INPUT' && !e.target.classList.contains('checkmark')) {
                    const cb = item.querySelector('.export-thread-cb');
                    if (cb) {
                        cb.checked = !cb.checked;
                        this.onCheckboxChange();
                    }
                }
            });

            container.appendChild(item);
        });

        resultsContainer.classList.remove('hidden');

        // Reset select-all checkbox & selection counter
        const selectAll = document.getElementById('export-select-all');
        if (selectAll) selectAll.checked = false;
        this.updateSelectionBadge();
    },

    onCheckboxChange: function() {
        const checkboxes = document.querySelectorAll('.export-thread-cb');
        checkboxes.forEach(cb => {
            const row = cb.closest('.result-item');
            if (row) {
                row.classList.toggle('selected-row', cb.checked);
            }
        });
        this.updateSelectionBadge();
    },

    updateSelectionBadge: function() {
        const selected = document.querySelectorAll('.export-thread-cb:checked').length;
        const total = this.searchResults.length;
        const selectionPill = document.getElementById('export-selection-pill');
        if (selectionPill) {
            if (selected > 0) {
                selectionPill.textContent = `${selected} of ${total} selected`;
                selectionPill.style.display = 'inline-flex';
            } else {
                selectionPill.style.display = 'none';
            }
        }
    },

    /**
     * Toggle all checkboxes in the export results
     */
    toggleSelectAll: function() {
        const selectAll = document.getElementById('export-select-all');
        const checkboxes = document.querySelectorAll('.export-thread-cb');
        checkboxes.forEach(cb => {
            cb.checked = selectAll.checked;
            const row = cb.closest('.result-item');
            if (row) row.classList.toggle('selected-row', selectAll.checked);
        });
        this.updateSelectionBadge();
    },

    getSelectedThreadIds: function() {
        const checkboxes = document.querySelectorAll('.export-thread-cb:checked');
        const selectedIds = [];
        checkboxes.forEach(cb => {
            const idx = parseInt(cb.dataset.index, 10);
            if (this.searchResults[idx]) {
                selectedIds.push(this.searchResults[idx].id);
            }
        });
        return selectedIds;
    },

    /**
     * Export only the selected threads
     */
    exportSelected: async function() {
        const selectedIds = this.getSelectedThreadIds();
        if (selectedIds.length === 0) {
            alert('Please select at least one thread to export.');
            return false;
        }

        const formatSelect = document.getElementById('export-format');
        const format = formatSelect ? formatSelect.value : 'json';

        const btn = document.getElementById('export-selected-btn');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = `
                <svg viewBox="0 0 24 24" width="16" height="16" class="rotating">
                    <path fill="currentColor" d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/>
                </svg>
                Exporting...
            `;
        }

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

            let ext = 'txt';
            if (format === 'json') ext = 'json';
            else if (format === 'html') ext = 'html';
            else if (format === 'eml' || format === 'zip') ext = 'zip';
            else if (format === 'markdown') ext = 'md';
            else if (format === 'pdf') ext = 'pdf';

            const nowStr = new Date().toISOString().slice(0, 10);
            const filename = `gmail_archive_${nowStr}.${ext}`;

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            GmailCleaner.UI.showSuccessToast(`Exported ${selectedIds.length} thread(s) (${ext.toUpperCase()}) successfully!`);
            return true;

        } catch (error) {
            console.error('Export error:', error);
            alert(`Export failed: ${error.message}`);
            return false;
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = `
                    <svg viewBox="0 0 24 24" width="16" height="16">
                        <path fill="currentColor" d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/>
                    </svg>
                    Export Selected
                `;
            }
        }
    },

    /**
     * Archive selected threads in Gmail (removes INBOX label)
     */
    archiveSelected: async function() {
        const selectedIds = this.getSelectedThreadIds();
        if (selectedIds.length === 0) {
            alert('Please select at least one thread to archive.');
            return false;
        }

        const confirmed = confirm(
            `Archive ${selectedIds.length} thread(s) from your Gmail inbox?\n\n` +
            `They will be removed from your Inbox while remaining safely stored and searchable in 'All Mail'.`
        );
        if (!confirmed) return false;

        const btn = document.getElementById('archive-selected-btn');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = `
                <svg viewBox="0 0 24 24" width="16" height="16" class="rotating">
                    <path fill="currentColor" d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/>
                </svg>
                Archiving...
            `;
        }

        try {
            const response = await fetch('/api/archive', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ thread_ids: selectedIds })
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || 'Archive failed');
            }

            await this.pollArchiveProgress();

            // Mark archived threads in UI
            document.querySelectorAll('.export-thread-cb:checked').forEach(cb => {
                const item = cb.closest('.result-item');
                if (item) {
                    item.style.opacity = '0.5';
                    item.style.textDecoration = 'line-through';
                    const pill = item.querySelector('.thread-count-badge');
                    if (pill) pill.textContent = 'Archived';
                }
                cb.checked = false;
            });
            this.updateSelectionBadge();

            GmailCleaner.UI.showSuccessToast(`Archived ${selectedIds.length} thread(s) from Inbox!`);
            return true;

        } catch (error) {
            console.error('Archive error:', error);
            alert(`Archive error: ${error.message}`);
            return false;
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = `
                    <svg viewBox="0 0 24 24" width="16" height="16">
                        <path fill="currentColor" d="M20.54 5.23l-1.39-1.68C18.88 3.21 18.47 3 18 3H6c-.47 0-.88.21-1.16.55L3.46 5.23C3.17 5.57 3 6.02 3 6.5V19c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V6.5c0-.48-.17-.93-.46-1.27zM12 17.5L6.5 12H10v-2h4v2h3.5L12 17.5zM5.12 5l.81-1h12l.94 1H5.12z"/>
                    </svg>
                    Archive Selected
                `;
            }
        }
    },

    /**
     * One-click download retrieval archive AND archive in Gmail
     */
    archiveAndDownloadSelected: async function() {
        const selectedIds = this.getSelectedThreadIds();
        if (selectedIds.length === 0) {
            alert('Please select at least one thread.');
            return;
        }

        const confirmed = confirm(
            `Download local archive and remove ${selectedIds.length} thread(s) from your Gmail inbox in one step?`
        );
        if (!confirmed) return;

        const exported = await this.exportSelected();
        if (exported) {
            await this.archiveSelected();
        }
    },

    /**
     * Bulk archive ALL emails matching the current search query from the inbox
     */
    archiveAllMatching: async function() {
        const naturalQueryField = document.getElementById('search-query')?.value.trim();
        const subjectField = document.getElementById('search-subject')?.value.trim();
        const includesField = document.getElementById('search-includes')?.value.trim();
        const excludesField = document.getElementById('search-excludes')?.value.trim();
        const sizeField = document.getElementById('search-size')?.value.trim();
        const afterDate = this.startPicker?.getDate()?.dateInstance;
        const beforeDate = this.endPicker?.getDate()?.dateInstance;
        const afterDateField = afterDate ? GmailCleaner.Filters.formatDateForGmail(afterDate) : '';
        const beforeDateField = beforeDate ? GmailCleaner.Filters.formatDateForGmail(beforeDate) : '';
        const hasAttachment = document.getElementById('search-has-attachment')?.checked;
        const excludeChats = document.getElementById('search-exclude-chats')?.checked;
        const scopeField = document.getElementById('search-scope')?.value || 'all';
        const customLabelField = document.getElementById('search-custom-label')?.value || '';

        let queryParts = [];
        const parsedNatural = this.parseNaturalLanguageQuery(naturalQueryField);
        if (parsedNatural) queryParts.push(parsedNatural);
        if (subjectField) queryParts.push(`subject:(${subjectField})`);
        if (includesField) queryParts.push(`(${includesField})`);
        if (excludesField) queryParts.push(`-(${excludesField})`);
        if (sizeField) queryParts.push(`larger:${sizeField}M`);
        if (afterDateField) queryParts.push(`after:${afterDateField}`);
        if (beforeDateField) queryParts.push(`before:${beforeDateField}`);
        if (hasAttachment) queryParts.push('has:attachment');
        if (excludeChats) queryParts.push('-in:chats');

        if (scopeField === 'sent') queryParts.push('in:sent');
        else if (scopeField === 'custom-label' && customLabelField) queryParts.push(`label:"${customLabelField}"`);

        const finalQuery = queryParts.join(' ');
        if (!finalQuery) {
            alert('Please specify search terms or filters to archive matching emails.');
            return;
        }

        const confirmed = confirm(
            `Archive ALL emails matching this query from your Inbox?\n\nQuery: "${finalQuery}"\n\n` +
            `This will remove them from your inbox and keep them safely in All Mail.`
        );
        if (!confirmed) return;

        const btn = document.getElementById('archive-all-matching-btn');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = `
                <svg viewBox="0 0 24 24" width="16" height="16" class="rotating">
                    <path fill="currentColor" d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/>
                </svg>
                Archiving all...
            `;
        }

        try {
            const response = await fetch('/api/archive', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: finalQuery })
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || 'Archive matching failed');
            }

            await this.pollArchiveProgress();
            GmailCleaner.UI.showSuccessToast('Bulk archive completed for matching query!');

        } catch (error) {
            console.error('Bulk archive error:', error);
            alert(`Bulk archive error: ${error.message}`);
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = `
                    <svg viewBox="0 0 24 24" width="16" height="16">
                        <path fill="currentColor" d="M20.54 5.23l-1.39-1.68C18.88 3.21 18.47 3 18 3H6c-.47 0-.88.21-1.16.55L3.46 5.23C3.17 5.57 3 6.02 3 6.5V19c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V6.5c0-.48-.17-.93-.46-1.27zM12 17.5L6.5 12H10v-2h4v2h3.5L12 17.5zM5.12 5l.81-1h12l.94 1H5.12z"/>
                    </svg>
                    Archive All Matching
                `;
            }
        }
    },

    pollArchiveProgress: async function() {
        return new Promise((resolve, reject) => {
            const interval = setInterval(async () => {
                try {
                    const res = await fetch('/api/archive-status');
                    const status = await res.json();
                    if (status.done) {
                        clearInterval(interval);
                        if (status.error) {
                            reject(new Error(status.error));
                        } else {
                            resolve(status);
                        }
                    }
                } catch (e) {
                    clearInterval(interval);
                    reject(e);
                }
            }, 500);
        });
    },

    archiveToSelectedLabel: async function() {
        const selectedIds = this.getSelectedThreadIds();
        const select = document.getElementById('search-apply-label-select');
        const newLabelInput = document.getElementById('search-new-label-input');
        
        let labelId = '';
        let labelName = '';
        if (select?.value === '__new__') {
            labelName = newLabelInput?.value.trim() || '';
            if (!labelName) {
                alert('Please enter a new label name.');
                return;
            }
        } else if (select?.value) {
            labelId = select.value;
        } else {
            alert('Please choose or create a label to archive to.');
            return;
        }

        if (selectedIds.length === 0) {
            alert('Please select at least one thread to archive to label.');
            return;
        }

        const labelDesc = labelName || select.options[select.selectedIndex]?.text || 'selected label';
        const confirmed = confirm(`Archive (move) ${selectedIds.length} thread(s) to "${labelDesc}"? This adds the label and removes them from Inbox.`);
        if (!confirmed) return;

        const btn = document.getElementById('archive-to-label-btn');
        if (btn) btn.disabled = true;

        try {
            const body = {
                thread_ids: selectedIds,
                remove_inbox: true,
            };
            if (labelId) body.label_id = labelId;
            if (labelName) body.label_name = labelName;

            const res = await fetch('/api/apply-label-threads', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || 'Failed to archive to label');
            }

            await this.pollLabelProgress();
            GmailCleaner.UI.showSuccessToast(`Archived ${selectedIds.length} thread(s) to "${labelDesc}"!`);
            if (GmailCleaner.Auth?.loadLabelsForFilter) GmailCleaner.Auth.loadLabelsForFilter();
        } catch (e) {
            console.error('Archive to label error:', e);
            alert('Error: ' + e.message);
        } finally {
            if (btn) btn.disabled = false;
        }
    },

    applySelectedLabel: async function() {
        const selectedIds = this.getSelectedThreadIds();
        const select = document.getElementById('search-apply-label-select');
        const newLabelInput = document.getElementById('search-new-label-input');
        
        let labelId = '';
        let labelName = '';
        if (select?.value === '__new__') {
            labelName = newLabelInput?.value.trim() || '';
            if (!labelName) {
                alert('Please enter a new label name.');
                return;
            }
        } else if (select?.value) {
            labelId = select.value;
        } else {
            alert('Please choose or create a label to apply.');
            return;
        }

        if (selectedIds.length === 0) {
            alert('Please select at least one thread to apply label to.');
            return;
        }

        const labelDesc = labelName || select.options[select.selectedIndex]?.text || 'selected label';
        const btn = document.getElementById('apply-selected-label-btn');
        if (btn) btn.disabled = true;

        try {
            const body = {
                thread_ids: selectedIds,
                remove_inbox: false,
            };
            if (labelId) body.label_id = labelId;
            if (labelName) body.label_name = labelName;

            const res = await fetch('/api/apply-label-threads', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || 'Failed to apply label');
            }

            await this.pollLabelProgress();
            GmailCleaner.UI.showSuccessToast(`Applied label "${labelDesc}" to ${selectedIds.length} thread(s)!`);
            if (GmailCleaner.Auth?.loadLabelsForFilter) GmailCleaner.Auth.loadLabelsForFilter();
        } catch (e) {
            console.error('Apply label error:', e);
            alert('Error: ' + e.message);
        } finally {
            if (btn) btn.disabled = false;
        }
    },

    pollLabelProgress: async function() {
        return new Promise((resolve, reject) => {
            const interval = setInterval(async () => {
                try {
                    const res = await fetch('/api/label-operation-status');
                    const status = await res.json();
                    if (status.done) {
                        clearInterval(interval);
                        if (status.error) {
                            reject(new Error(status.error));
                        } else {
                            resolve(status);
                        }
                    }
                } catch (e) {
                    clearInterval(interval);
                    reject(e);
                }
            }, 500);
        });
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
window.archiveSelected = () => GmailCleaner.Export.archiveSelected();
window.archiveAndDownloadSelected = () => GmailCleaner.Export.archiveAndDownloadSelected();
window.archiveAllMatching = () => GmailCleaner.Export.archiveAllMatching();
window.archiveToSelectedLabel = () => GmailCleaner.Export.archiveToSelectedLabel();
window.applySelectedLabel = () => GmailCleaner.Export.applySelectedLabel();
window.toggleExportSelectAll = () => GmailCleaner.Export.toggleSelectAll();
window.processUnsubscribeLabel = () => GmailCleaner.Export.processUnsubscribeLabel();
window.applyQuickQuery = (q) => GmailCleaner.Export.applyQuickQuery(q);
window.toggleAdvancedSearch = () => GmailCleaner.Export.toggleAdvancedSearch();
window.clearSearchForm = () => GmailCleaner.Export.clearSearchForm();
window.handleSearchScopeChange = () => GmailCleaner.Export.handleSearchScopeChange();
window.handleSearchLabelSelectChange = () => GmailCleaner.Export.handleSearchLabelSelectChange();

document.addEventListener('DOMContentLoaded', () => {
    try {
        if (window.GmailCleaner && GmailCleaner.Export) {
            if (typeof GmailCleaner.Export.initEmailAutocomplete === 'function') GmailCleaner.Export.initEmailAutocomplete();
            if (typeof GmailCleaner.Export.initDateRangePicker === 'function') GmailCleaner.Export.initDateRangePicker();
            if (typeof GmailCleaner.Export.syncCustomLabelOptions === 'function') GmailCleaner.Export.syncCustomLabelOptions();
            if (typeof GmailCleaner.Export.handleSearchScopeChange === 'function') GmailCleaner.Export.handleSearchScopeChange();
        }
    } catch (e) {
        console.warn('Export initialization warning:', e);
    }
});

