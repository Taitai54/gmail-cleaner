/**
 * Gmail Unsubscribe - Filters Module
 */

window.GmailCleaner = window.GmailCleaner || {};

GmailCleaner.Filters = {
    startPicker: null,
    endPicker: null,

    setup() {
        const clearBtn = document.getElementById('filterClearBtn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clear());
        }

        this.setupDateRangePicker();

        const olderThanSelect = document.getElementById('filterOlderThan');
        if (olderThanSelect) {
            olderThanSelect.addEventListener('change', (e) => this.handleOlderThanChange(e));
        }
    },

    setupDateRangePicker() {
        const startInput = document.getElementById('dateRangeStart');
        const endInput = document.getElementById('dateRangeEnd');
        if (!startInput || !endInput || !window.Litepicker) return;

        // Tear down existing pickers if re-running (e.g. after clear/show toggle).
        for (const key of ['startPicker', 'endPicker']) {
            if (this[key]) {
                try { this[key].destroy(); } catch (_) { /* ignore */ }
                this[key] = null;
            }
        }

        try {
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            const sevenDaysAgo = new Date(today);
            sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);

            const commonOpts = {
                singleMode: true,
                format: 'DD/MM/YYYY',
                autoApply: true,
                position: 'bottom left',
                lang: 'en-GB',
                firstDay: 1, // Monday
                minDate: new Date(2000, 0, 1),
                maxDate: today,
                dropdowns: { months: true, years: true, minYear: 2000, maxYear: today.getFullYear() },
            };

            this.startPicker = new Litepicker({
                ...commonOpts,
                element: startInput,
                startDate: sevenDaysAgo,
            });
            this.endPicker = new Litepicker({
                ...commonOpts,
                element: endInput,
                startDate: today,
            });

            // When start changes, end can't be before it.
            this.startPicker.on('selected', (date) => {
                const d = date && date.dateInstance ? date.dateInstance : null;
                if (!d) return;
                this.endPicker.setOptions({ minDate: d });
                const endD = this.endPicker.getDate();
                if (endD && endD < d) {
                    this.endPicker.setDate(d);
                }
            });

            // When end changes, start can't be after it.
            this.endPicker.on('selected', (date) => {
                const d = date && date.dateInstance ? date.dateInstance : null;
                if (!d) return;
                this.startPicker.setOptions({ maxDate: d });
                const startD = this.startPicker.getDate();
                if (startD && startD > d) {
                    this.startPicker.setDate(d);
                }
            });
        } catch (error) {
            console.error('Error initializing Litepicker:', error);
        }
    },

    handleOlderThanChange(event) {
        const value = event.target.value;
        const dateRangeGroup = document.getElementById('dateRangeGroup');

        if (value === 'custom') {
            dateRangeGroup?.classList.remove('hidden');
            if (!this.startPicker || !this.endPicker) {
                this.setupDateRangePicker();
            }
        } else {
            // Keep the picker state so dates persist if the user toggles back.
            dateRangeGroup?.classList.add('hidden');
        }
    },

    get() {
        const olderThanSelect = document.getElementById('filterOlderThan');
        const olderThanValue = olderThanSelect?.value || '';
        let olderThan = '';
        let afterDate = '';
        let beforeDate = '';

        // If custom date range is selected, read the picker Date objects directly.
        if (olderThanValue === 'custom') {
            const startD = this.startPicker?.getDate();
            const endD = this.endPicker?.getDate();
            if (startD && endD) {
                const fmt = (d) => {
                    const y = d.getFullYear();
                    const m = String(d.getMonth() + 1).padStart(2, '0');
                    const day = String(d.getDate()).padStart(2, '0');
                    return `${y}/${m}/${day}`;
                };
                afterDate = fmt(startD);
                // Add 1 day for Gmail's exclusive upper bound (before:).
                const endPlus = new Date(endD);
                endPlus.setDate(endPlus.getDate() + 1);
                beforeDate = fmt(endPlus);
            }
        } else {
            olderThan = olderThanValue;
        }

        const largerThan = document.getElementById('filterLargerThan')?.value || '';
        const category = document.getElementById('filterCategory')?.value || '';
        const sender = document.getElementById('filterSender')?.value?.trim() || '';
        const label = document.getElementById('filterLabel')?.value || '';

        const filters = {
            older_than: olderThan,
            after_date: afterDate,
            before_date: beforeDate,
            larger_than: largerThan,
            category: category,
            sender: sender,
            label: label
        };
        
        // Update filter badge
        this.updateFilterBadge(filters);
        
        return filters;
    },
    
    updateFilterBadge(filters) {
        const badge = document.getElementById('filterBadge');
        if (!badge) return;
        
        let count = 0;
        if (filters.older_than) count++;
        if (filters.after_date && filters.before_date) count++;
        if (filters.larger_than) count++;
        if (filters.category) count++;
        if (filters.sender) count++;
        if (filters.label) count++;
        
        if (count > 0) {
            badge.textContent = count;
            badge.style.display = 'inline-flex';
        } else {
            badge.style.display = 'none';
        }
    },

    clear() {
        const olderThan = document.getElementById('filterOlderThan');
        const largerThan = document.getElementById('filterLargerThan');
        const category = document.getElementById('filterCategory');
        const sender = document.getElementById('filterSender');
        const label = document.getElementById('filterLabel');
        const dateRangeGroup = document.getElementById('dateRangeGroup');

        if (olderThan) olderThan.value = '';
        if (largerThan) largerThan.value = '';
        if (category) category.value = '';
        if (sender) sender.value = '';
        if (label) label.value = '';

        // Reset both date pickers back to the default 7-day window.
        if (this.startPicker && this.endPicker) {
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            const sevenDaysAgo = new Date(today);
            sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
            try {
                this.startPicker.setOptions({ minDate: new Date(2000, 0, 1), maxDate: today });
                this.endPicker.setOptions({ minDate: new Date(2000, 0, 1), maxDate: today });
                this.startPicker.setDate(sevenDaysAgo);
                this.endPicker.setDate(today);
            } catch (_) { /* ignore */ }
        }

        if (dateRangeGroup) {
            dateRangeGroup.classList.add('hidden');
        }
        
        // Update badge
        this.updateFilterBadge({});
    },

    populateLabelDropdown(labels) {
        const select = document.getElementById('filterLabel');
        if (!select) return;

        // Keep the default option
        select.innerHTML = '<option value="">All labels</option>';

        // Add user labels
        if (labels && labels.length > 0) {
            labels.forEach(label => {
                const option = document.createElement('option');
                option.value = label.name;
                option.textContent = label.name;
                select.appendChild(option);
            });
        }
    },

    showBar(show) {
        const filterBar = document.getElementById('filterBar');
        const mainContent = document.querySelector('.main-content');

        if (filterBar) {
            if (show) {
                filterBar.classList.remove('hidden');
            } else {
                filterBar.classList.add('hidden');
            }
        }
        if (mainContent) {
            if (show) {
                mainContent.classList.add('with-filters');
            } else {
                mainContent.classList.remove('with-filters');
            }
        }
    }
};

// Global shortcut
function clearFilters() { GmailCleaner.Filters.clear(); }
