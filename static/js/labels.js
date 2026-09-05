/**
 * Gmail Cleaner - Label Management Module
 */

window.GmailCleaner = window.GmailCleaner || {};

GmailCleaner.Labels = {
    labels: {
        system: [],
        user: []
    },

    async loadLabels() {
        try {
            const response = await fetch('/api/labels');
            const data = await response.json();

            if (data.success) {
                this.labels.system = data.system_labels || [];
                this.labels.user = data.user_labels || [];
                return this.labels;
            } else {
                console.error('Failed to load labels:', data.error);
                return null;
            }
        } catch (error) {
            console.error('Error loading labels:', error);
            return null;
        }
    },

    async createLabel(name) {
        try {
            const response = await fetch('/api/labels', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name })
            });
            const result = await response.json();

            if (result.success) {
                // Add to local cache
                this.labels.user.push(result.label);
                this.labels.user.sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()));
            }

            return result;
        } catch (error) {
            return { success: false, error: error.message };
        }
    },

    async deleteLabel(labelId) {
        try {
            const response = await fetch(`/api/labels/${encodeURIComponent(labelId)}`, {
                method: 'DELETE'
            });
            const result = await response.json();

            if (result.success) {
                // Remove from local cache
                this.labels.user = this.labels.user.filter(l => l.id !== labelId);
            }

            return result;
        } catch (error) {
            return { success: false, error: error.message };
        }
    },

    async applyLabelToSenders(labelId, senders) {
        try {
            const response = await fetch('/api/apply-label', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ label_id: labelId, senders })
            });
            return await response.json();
        } catch (error) {
            return { success: false, error: error.message };
        }
    },

    async removeLabelFromSenders(labelId, senders) {
        try {
            const response = await fetch('/api/remove-label', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ label_id: labelId, senders })
            });
            return await response.json();
        } catch (error) {
            return { success: false, error: error.message };
        }
    },

    async pollLabelOperation(onComplete) {
        try {
            const response = await fetch('/api/label-operation-status');
            const status = await response.json();

            if (status.done) {
                onComplete(status);
            } else {
                setTimeout(() => this.pollLabelOperation(onComplete), 300);
            }

            return status;
        } catch (error) {
            setTimeout(() => this.pollLabelOperation(onComplete), 500);
        }
    },

    // Show label dropdown for selecting/creating labels
    showLabelDropdown(buttonElement, onSelect) {
        // Remove any existing dropdown
        this.hideLabelDropdown();

        const dropdown = document.createElement('div');
        dropdown.id = 'labelDropdown';
        dropdown.className = 'label-dropdown';

        // Build dropdown content
        let html = '<div class="label-dropdown-content">';
        html += '<div class="label-dropdown-header">Select or Create Label</div>';

        // Create new label input
        html += `
            <div class="label-create-section">
                <input type="text" id="newLabelInput" placeholder="New label name..." class="label-input">
                <button id="createLabelBtn" class="label-create-btn">Create</button>
            </div>
        `;

        // Existing labels
        if (this.labels.user.length > 0) {
            html += '<div class="label-list-header">Your Labels</div>';
            html += '<div class="label-list">';
            this.labels.user.forEach(label => {
                html += `
                    <div class="label-item" data-id="${GmailCleaner.UI.escapeHtml(label.id)}" data-name="${GmailCleaner.UI.escapeHtml(label.name)}">
                        <span class="label-icon">🏷️</span>
                        <span class="label-name">${GmailCleaner.UI.escapeHtml(label.name)}</span>
                    </div>
                `;
            });
            html += '</div>';
        } else {
            html += '<div class="label-empty">No custom labels yet</div>';
        }

        html += '</div>';
        dropdown.innerHTML = html;

        // Position dropdown
        const rect = buttonElement.getBoundingClientRect();
        dropdown.style.position = 'fixed';
        dropdown.style.top = (rect.bottom + 5) + 'px';
        dropdown.style.left = rect.left + 'px';
        dropdown.style.zIndex = '10000';

        document.body.appendChild(dropdown);

        // Event handlers
        dropdown.querySelectorAll('.label-item').forEach(item => {
            item.addEventListener('click', () => {
                const labelId = item.dataset.id;
                const labelName = item.dataset.name;
                this.hideLabelDropdown();
                onSelect({ id: labelId, name: labelName });
            });
        });

        const createBtn = dropdown.querySelector('#createLabelBtn');
        const newLabelInput = dropdown.querySelector('#newLabelInput');

        createBtn.addEventListener('click', async () => {
            const name = newLabelInput.value.trim();
            if (!name) return;

            createBtn.disabled = true;
            createBtn.textContent = '...';

            const result = await this.createLabel(name);

            if (result.success) {
                this.hideLabelDropdown();
                onSelect(result.label);
            } else {
                alert('Error: ' + result.error);
                createBtn.disabled = false;
                createBtn.textContent = 'Create';
            }
        });

        newLabelInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                createBtn.click();
            }
        });

        // Close on click outside
        setTimeout(() => {
            document.addEventListener('click', this._dropdownClickHandler = (e) => {
                if (!dropdown.contains(e.target) && e.target !== buttonElement) {
                    this.hideLabelDropdown();
                }
            });
        }, 10);
    },

    hideLabelDropdown() {
        const dropdown = document.getElementById('labelDropdown');
        if (dropdown) {
            dropdown.remove();
        }
        if (this._dropdownClickHandler) {
            document.removeEventListener('click', this._dropdownClickHandler);
            this._dropdownClickHandler = null;
        }
    },

    // Show label operation overlay
    showLabelOverlay(action, labelName, emailCount) {
        this.hideLabelOverlay();

        const actionText = action === 'apply' ? 'Applying' : 'Removing';
        const overlay = document.createElement('div');
        overlay.id = 'labelOverlay';
        overlay.className = 'label-overlay';
        overlay.innerHTML = `
            <div class="label-overlay-content">
                <svg class="label-overlay-spinner spinner" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="10" fill="none" stroke="#8b5cf6" stroke-width="2" stroke-dasharray="60" stroke-linecap="round"/>
                </svg>
                <h3>${actionText} Label "${GmailCleaner.UI.escapeHtml(labelName)}"...</h3>
                <div class="label-progress-container">
                    <div class="label-progress-bar" id="labelProgressBar"></div>
                </div>
                <p id="labelProgressText">Starting...</p>
            </div>
        `;
        document.body.appendChild(overlay);
    },

    updateLabelOverlay(status) {
        const progressBar = document.getElementById('labelProgressBar');
        const progressText = document.getElementById('labelProgressText');

        if (progressBar) {
            progressBar.style.width = status.progress + '%';
        }
        if (progressText) {
            progressText.textContent = status.message;
        }
    },

    hideLabelOverlay() {
        const overlay = document.getElementById('labelOverlay');
        if (overlay) {
            overlay.remove();
        }
    },

    // Show apply label dropdown
    async showApplyLabelDropdown(event) {
        event.stopPropagation();

        // Check if senders are selected
        const checkboxes = document.querySelectorAll('.delete-cb:checked');
        if (checkboxes.length === 0) {
            alert('Please select at least one sender first.');
            return;
        }

        // Load labels if not loaded
        if (this.labels.user.length === 0 && this.labels.system.length === 0) {
            await this.loadLabels();
        }

        this.showLabelDropdown(event.target.closest('button'), async (label) => {
            await this.applyLabelToSelected(label);
        });
    },

    // Show remove label dropdown
    async showRemoveLabelDropdown(event) {
        event.stopPropagation();

        // Check if senders are selected
        const checkboxes = document.querySelectorAll('.delete-cb:checked');
        if (checkboxes.length === 0) {
            alert('Please select at least one sender first.');
            return;
        }

        // Load labels if not loaded
        if (this.labels.user.length === 0 && this.labels.system.length === 0) {
            await this.loadLabels();
        }

        this.showLabelDropdown(event.target.closest('button'), async (label) => {
            await this.removeLabelFromSelected(label);
        });
    },

    // Apply label to selected senders
    async applyLabelToSelected(label) {
        const checkboxes = document.querySelectorAll('.delete-cb:checked');
        const senders = [];

        checkboxes.forEach(cb => {
            senders.push(cb.dataset.email);
        });

        this.showLabelOverlay('apply', label.name, senders.length);

        try {
            const result = await this.applyLabelToSenders(label.id, senders);

            if (result.status === 'started') {
                // Poll for progress
                this.pollLabelOperation((status) => {
                    this.updateLabelOverlay(status);
                    if (status.done) {
                        this.hideLabelOverlay();
                        if (status.error) {
                            alert('Error: ' + status.error);
                        } else {
                            alert(`Label "${label.name}" applied to emails from ${senders.length} sender(s)`);
                        }
                    }
                });
            } else if (result.error) {
                this.hideLabelOverlay();
                alert('Error: ' + result.error);
            }
        } catch (error) {
            this.hideLabelOverlay();
            alert('Error: ' + error.message);
        }
    },

    // Remove label from selected senders
    async removeLabelFromSelected(label) {
        const checkboxes = document.querySelectorAll('.delete-cb:checked');
        const senders = [];

        checkboxes.forEach(cb => {
            senders.push(cb.dataset.email);
        });

        this.showLabelOverlay('remove', label.name, senders.length);

        try {
            const result = await this.removeLabelFromSenders(label.id, senders);

            if (result.status === 'started') {
                // Poll for progress
                this.pollLabelOperation((status) => {
                    this.updateLabelOverlay(status);
                    if (status.done) {
                        this.hideLabelOverlay();
                        if (status.error) {
                            alert('Error: ' + status.error);
                        } else {
                            alert(`Label "${label.name}" removed from emails from ${senders.length} sender(s)`);
                        }
                    }
                });
            } else if (result.error) {
                this.hideLabelOverlay();
                alert('Error: ' + result.error);
            }
        } catch (error) {
            this.hideLabelOverlay();
            alert('Error: ' + error.message);
        }
    },

    // Archive selected senders' emails
    async archiveSelected() {
        const checkboxes = document.querySelectorAll('.delete-cb:checked');
        if (checkboxes.length === 0) {
            alert('Please select at least one sender first.');
            return;
        }

        const senders = [];
        let totalEmails = 0;
        checkboxes.forEach(cb => {
            senders.push(cb.dataset.email);
            const index = parseInt(cb.dataset.index);
            totalEmails += GmailCleaner.deleteResults[index]?.count || 0;
        });

        if (!confirm(`Archive emails from ${senders.length} sender(s)?\n\nThis will remove ${totalEmails} emails from your inbox but keep them in "All Mail".`)) {
            return;
        }

        this.showArchiveOverlay(senders.length);

        try {
            const response = await fetch('/api/archive', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ senders })
            });

            const result = await response.json();

            if (result.status === 'started') {
                this.pollArchiveStatus();
            } else if (result.error) {
                this.hideArchiveOverlay();
                alert('Error: ' + result.error);
            }
        } catch (error) {
            this.hideArchiveOverlay();
            alert('Error: ' + error.message);
        }
    },

    // Archive every inbox email matching the current filter bar, independent of any
    // sender selection (e.g. "everything in Promotions older than 90 days").
    async archiveByFilters() {
        const filters = GmailCleaner.Filters?.get() || {};
        const hasActiveFilter = Object.values(filters).some((v) => !!v);
        if (!hasActiveFilter) {
            alert('Set at least one filter above first, then Archive Matching.');
            return;
        }

        if (!confirm('Archive every inbox email matching the current filters?\n\nThey\'ll be removed from your inbox but kept in "All Mail".')) {
            return;
        }

        this.showArchiveOverlay(0);

        try {
            const response = await fetch('/api/archive', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ senders: [], filters })
            });

            const result = await response.json();

            if (result.status === 'started') {
                this.pollArchiveStatus();
            } else if (result.error) {
                this.hideArchiveOverlay();
                alert('Error: ' + result.error);
            }
        } catch (error) {
            this.hideArchiveOverlay();
            alert('Error: ' + error.message);
        }
    },

    async pollArchiveStatus() {
        try {
            const response = await fetch('/api/archive-status');
            const status = await response.json();

            this.updateArchiveOverlay(status);

            if (status.done) {
                this.hideArchiveOverlay();
                // The backend's own status message already distinguishes
                // "from N senders" vs. "matching filters" phrasing — reuse it.
                alert(status.error ? 'Error: ' + status.error : status.message);
            } else {
                setTimeout(() => this.pollArchiveStatus(), 300);
            }
        } catch (error) {
            setTimeout(() => this.pollArchiveStatus(), 500);
        }
    },

    showArchiveOverlay(senderCount) {
        this.hideLabelOverlay();
        this.hideArchiveOverlay();

        const overlay = document.createElement('div');
        overlay.id = 'archiveOverlay';
        overlay.className = 'label-overlay';
        overlay.innerHTML = `
            <div class="label-overlay-content">
                <svg class="label-overlay-spinner spinner" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="10" fill="none" stroke="#f59e0b" stroke-width="2" stroke-dasharray="60" stroke-linecap="round"/>
                </svg>
                <h3>Archiving Emails...</h3>
                <div class="label-progress-container">
                    <div class="label-progress-bar" id="archiveProgressBar" style="background: #f59e0b;"></div>
                </div>
                <p id="archiveProgressText">Starting...</p>
                <p class="label-stats">0/${senderCount} senders processed</p>
            </div>
        `;
        document.body.appendChild(overlay);
    },

    updateArchiveOverlay(status) {
        const progressBar = document.getElementById('archiveProgressBar');
        const progressText = document.getElementById('archiveProgressText');

        if (progressBar) {
            progressBar.style.width = status.progress + '%';
        }
        if (progressText) {
            progressText.textContent = status.message;
        }
    },

    hideArchiveOverlay() {
        const overlay = document.getElementById('archiveOverlay');
        if (overlay) {
            overlay.remove();
        }
    },

    // Mark or unmark selected senders' emails as important
    async markImportantSelected(important = true) {
        const checkboxes = document.querySelectorAll('.delete-cb:checked');
        if (checkboxes.length === 0) {
            alert('Please select at least one sender first.');
            return;
        }

        const senders = [];
        let totalEmails = 0;
        checkboxes.forEach(cb => {
            senders.push(cb.dataset.email);
            const index = parseInt(cb.dataset.index);
            totalEmails += GmailCleaner.deleteResults[index]?.count || 0;
        });

        const actionVerb = important ? 'Mark' : 'Unmark';
        if (!confirm(`${actionVerb} ${totalEmails} emails from ${senders.length} sender(s) as important?`)) {
            return;
        }

        this.showImportantOverlay(senders.length, important);

        try {
            const response = await fetch('/api/mark-important', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ senders, important })
            });

            const result = await response.json();

            if (result.status === 'started') {
                this.pollImportantStatus();
            } else if (result.error) {
                this.hideImportantOverlay();
                alert('Error: ' + result.error);
            }
        } catch (error) {
            this.hideImportantOverlay();
            alert('Error: ' + error.message);
        }
    },

    async pollImportantStatus() {
        try {
            const response = await fetch('/api/important-status');
            const status = await response.json();

            this.updateImportantOverlay(status);

            if (status.done) {
                this.hideImportantOverlay();
                if (status.error) {
                    alert('Error: ' + status.error);
                } else {
                    alert(`Marked ${status.affected_count} emails as important`);
                }
            } else {
                setTimeout(() => this.pollImportantStatus(), 300);
            }
        } catch (error) {
            setTimeout(() => this.pollImportantStatus(), 500);
        }
    },

    showImportantOverlay(senderCount, important = true) {
        this.hideLabelOverlay();
        this.hideArchiveOverlay();
        this.hideImportantOverlay();

        const overlay = document.createElement('div');
        overlay.id = 'importantOverlay';
        overlay.className = 'label-overlay';
        const heading = important ? 'Marking as Important...' : 'Removing Important flag...';
        overlay.innerHTML = `
            <div class="label-overlay-content">
                <svg class="label-overlay-spinner spinner" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="10" fill="none" stroke="#eab308" stroke-width="2" stroke-dasharray="60" stroke-linecap="round"/>
                </svg>
                <h3>${heading}</h3>
                <div class="label-progress-container">
                    <div class="label-progress-bar" id="importantProgressBar" style="background: #eab308;"></div>
                </div>
                <p id="importantProgressText">Starting...</p>
                <p class="label-stats">0/${senderCount} senders processed</p>
            </div>
        `;
        document.body.appendChild(overlay);
    },

    updateImportantOverlay(status) {
        const progressBar = document.getElementById('importantProgressBar');
        const progressText = document.getElementById('importantProgressText');

        if (progressBar) {
            progressBar.style.width = status.progress + '%';
        }
        if (progressText) {
            progressText.textContent = status.message;
        }
    },

    hideImportantOverlay() {
        const overlay = document.getElementById('importantOverlay');
        if (overlay) {
            overlay.remove();
        }
    },

    // ----- Label Tree (Manage Labels view) -----
    // Gmail nests labels via "/" in the name (e.g. "Work/Projects"). There's no
    // separate parent/child API — a "parent" may be a real label or just an
    // implied grouping that exists only because a child label's name starts with it.

    treeExpanded: null, // Set of expanded paths; null until first render (defaults to all-expanded)

    /** Turn the flat user_labels list into a nested tree keyed by path segment. */
    buildLabelTree(labels) {
        const root = { path: '', children: {} };
        labels.forEach((label) => {
            const parts = label.name.split('/');
            let node = root;
            let path = '';
            parts.forEach((part) => {
                path = path ? `${path}/${part}` : part;
                if (!node.children[part]) {
                    node.children[part] = { name: part, path, id: null, children: {} };
                }
                node = node.children[part];
            });
            node.id = label.id; // real Gmail label at this exact path
        });
        return root;
    },

    async loadAndRenderTree() {
        await this.loadLabels();
        this.renderLabelTree();
    },

    // Jump to Search & Export, pre-filtered to this label, and run the search
    // immediately — the quickest way to see what's actually in a label.
    viewLabelContents(labelName) {
        GmailCleaner.UI.showView('search');

        const scope = document.getElementById('search-scope');
        const customLabel = document.getElementById('search-custom-label');
        if (!scope || !customLabel) return;

        GmailCleaner.Export.clearSearchForm();

        scope.value = 'custom-label';
        GmailCleaner.Export.handleSearchScopeChange(); // reveals the group, repopulates options

        customLabel.value = labelName;
        if (customLabel.value !== labelName) {
            // Defensive: label wasn't in the dropdown's source list yet — add it directly.
            const opt = document.createElement('option');
            opt.value = labelName;
            opt.textContent = labelName;
            customLabel.appendChild(opt);
            customLabel.value = labelName;
        }

        GmailCleaner.Export.searchThreads();
    },

    renderLabelTree() {
        const container = document.getElementById('labelTreeContainer');
        if (!container) return;

        const tree = this.buildLabelTree(this.labels.user);
        if (this.treeExpanded === null) {
            // Default to fully expanded on first render.
            this.treeExpanded = new Set();
            const collectPaths = (node) => {
                Object.values(node.children).forEach((child) => {
                    this.treeExpanded.add(child.path);
                    collectPaths(child);
                });
            };
            collectPaths(tree);
        }

        const rootChildren = Object.values(tree.children).sort((a, b) =>
            a.name.toLowerCase().localeCompare(b.name.toLowerCase())
        );

        if (rootChildren.length === 0) {
            container.innerHTML = '<div class="label-empty">No custom labels yet</div>';
            return;
        }

        container.innerHTML = rootChildren.map((node) => this.renderTreeNode(node, 0)).join('');
    },

    renderTreeNode(node, depth) {
        const children = Object.values(node.children).sort((a, b) =>
            a.name.toLowerCase().localeCompare(b.name.toLowerCase())
        );
        const hasChildren = children.length > 0;
        const expanded = this.treeExpanded.has(node.path);
        const escapedPath = GmailCleaner.UI.escapeHtml(node.path);
        const escapedName = GmailCleaner.UI.escapeHtml(node.name);

        const toggle = hasChildren
            ? `<button class="label-tree-toggle${expanded ? ' expanded' : ''}" onclick="GmailCleaner.Labels.toggleTreeNode('${escapedPath}')" title="${expanded ? 'Collapse' : 'Expand'}">
                   <svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6z"/></svg>
               </button>`
            : `<span class="label-tree-toggle-spacer"></span>`;

        // A row may be a real label (has an id) or just an implied grouping folder
        // (e.g. "Work" shown because "Work/Projects" exists, with no "Work" label itself).
        const actions = node.id
            ? `<div class="label-tree-actions">
                   <button class="label-tree-icon-btn" title="View emails in this label" onclick="GmailCleaner.Labels.viewLabelContents('${escapedPath}')">
                       <svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/></svg>
                   </button>
                   <button class="label-tree-icon-btn" title="Rename" onclick="GmailCleaner.Labels.startRenameInTree('${node.id}', '${escapedPath}', '${escapedName}')">
                       <svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34a.9959.9959 0 00-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>
                   </button>
                   <button class="label-tree-icon-btn" title="Move to a different parent" onclick="GmailCleaner.Labels.startMoveInTree('${node.id}', '${escapedPath}')">
                       <svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M10 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/></svg>
                   </button>
                   <button class="label-tree-icon-btn danger" title="Delete" onclick="GmailCleaner.Labels.deleteFromTree('${node.id}', '${escapedPath}')">
                       <svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
                   </button>
               </div>`
            : '';

        const row = `
            <div class="label-tree-row" data-path="${escapedPath}" style="padding-left: ${16 + depth * 20}px">
                ${toggle}
                <span class="label-icon">${node.id ? '🏷️' : '📁'}</span>
                <span class="label-tree-name" id="label-tree-name-${escapedPath.replace(/[^a-zA-Z0-9]/g, '_')}">${escapedName}</span>
                ${actions}
            </div>
        `;

        const childrenHtml = hasChildren && expanded
            ? children.map((child) => this.renderTreeNode(child, depth + 1)).join('')
            : '';

        return row + childrenHtml;
    },

    toggleTreeNode(path) {
        if (this.treeExpanded.has(path)) {
            this.treeExpanded.delete(path);
        } else {
            this.treeExpanded.add(path);
        }
        this.renderLabelTree();
    },

    async createFromTreePanel() {
        const input = document.getElementById('labelTreeNewName');
        const name = input?.value.trim();
        if (!name) return;

        const btn = document.getElementById('labelTreeCreateBtn');
        if (btn) { btn.disabled = true; btn.textContent = '...'; }

        const result = await this.createLabel(name);

        if (btn) { btn.disabled = false; btn.textContent = 'Create'; }

        if (result.success) {
            input.value = '';
            this.renderLabelTree();
        } else {
            alert('Error: ' + result.error);
        }
    },

    startRenameInTree(labelId, path, currentName) {
        const nameEl = document.getElementById(`label-tree-name-${path.replace(/[^a-zA-Z0-9]/g, '_')}`);
        if (!nameEl) return;

        const parentPath = path.includes('/') ? path.slice(0, path.lastIndexOf('/')) : '';

        nameEl.outerHTML = `
            <input type="text" class="label-tree-rename-input"
                   id="label-tree-name-${path.replace(/[^a-zA-Z0-9]/g, '_')}"
                   value="${GmailCleaner.UI.escapeHtml(currentName)}">
        `;
        const input = document.getElementById(`label-tree-name-${path.replace(/[^a-zA-Z0-9]/g, '_')}`);
        input.focus();
        input.select();

        const save = async () => {
            const newLeaf = input.value.trim();
            if (!newLeaf || newLeaf === currentName) {
                this.renderLabelTree();
                return;
            }
            const newName = parentPath ? `${parentPath}/${newLeaf}` : newLeaf;
            const result = await this.renameLabel(labelId, newName);
            if (!result.success) alert('Error: ' + result.error);
            await this.loadAndRenderTree();
        };

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') save();
            if (e.key === 'Escape') this.renderLabelTree();
        });
        input.addEventListener('blur', save, { once: true });
    },

    async renameLabel(labelId, newName) {
        try {
            const response = await fetch('/api/labels/rename', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ label_id: labelId, new_name: newName })
            });
            return await response.json();
        } catch (error) {
            return { success: false, error: error.message };
        }
    },

    startMoveInTree(labelId, path) {
        const row = document.querySelector(`.label-tree-row[data-path="${CSS.escape(path)}"]`);
        if (!row) return;

        // Candidate parents: every other label's full path, plus root.
        const options = this.labels.user
            .map((l) => l.name)
            .filter((name) => name !== path && !name.startsWith(path + '/'));

        const select = document.createElement('select');
        select.className = 'label-tree-move-select';
        select.innerHTML = '<option value="">— Root —</option>' +
            options.map((o) => `<option value="${GmailCleaner.UI.escapeHtml(o)}">${GmailCleaner.UI.escapeHtml(o)}</option>`).join('');

        select.addEventListener('change', async () => {
            const result = await this.moveLabel(labelId, select.value);
            if (!result.success) alert('Error: ' + result.error);
            await this.loadAndRenderTree();
        });
        select.addEventListener('click', (e) => e.stopPropagation());

        const actions = row.querySelector('.label-tree-actions');
        if (actions) actions.replaceWith(select);
    },

    async moveLabel(labelId, newParent) {
        try {
            const response = await fetch('/api/labels/move', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ label_id: labelId, new_parent: newParent })
            });
            return await response.json();
        } catch (error) {
            return { success: false, error: error.message };
        }
    },

    async deleteFromTree(labelId, path) {
        if (!confirm(`Delete label "${path}"?`)) return;

        const result = await this.deleteLabelWithCascade(labelId, false);

        if (result.success) {
            await this.loadAndRenderTree();
            return;
        }

        if (result.children && result.children.length > 0) {
            // Has nested sub-labels — nothing was deleted yet. Ask for the bigger
            // commitment explicitly before cascading.
            this.showCascadeConfirmModal(labelId, path, result.children);
            return;
        }

        alert('Error: ' + result.error);
    },

    async deleteLabelWithCascade(labelId, cascade) {
        try {
            const response = await fetch(`/api/labels/${encodeURIComponent(labelId)}?cascade=${cascade}`, {
                method: 'DELETE'
            });
            return await response.json();
        } catch (error) {
            return { success: false, error: error.message };
        }
    },

    showCascadeConfirmModal(labelId, path, childNames) {
        this.closeCascadeConfirmModal();

        const modal = document.createElement('div');
        modal.className = 'preview-modal';
        modal.id = 'labelCascadeModal';
        modal.innerHTML = `
            <div class="preview-modal-content">
                <div class="preview-modal-header">
                    <h3>Delete "${GmailCleaner.UI.escapeHtml(path)}"?</h3>
                    <button class="preview-modal-close" onclick="GmailCleaner.Labels.closeCascadeConfirmModal()">
                        <svg viewBox="0 0 24 24" width="24" height="24">
                            <path fill="currentColor" d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                        </svg>
                    </button>
                </div>
                <div class="preview-modal-body">
                    <p>This label has ${childNames.length} nested sub-label(s). Deleting it will also delete:</p>
                    <ul class="label-cascade-list">
                        ${childNames.map((n) => `<li>${GmailCleaner.UI.escapeHtml(n)}</li>`).join('')}
                    </ul>
                </div>
                <div class="preview-modal-footer">
                    <button class="btn btn-secondary" onclick="GmailCleaner.Labels.closeCascadeConfirmModal()">Cancel</button>
                    <button class="btn btn-danger" onclick="GmailCleaner.Labels.confirmCascadeDelete('${labelId}')">Delete label + sub-labels</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        modal.addEventListener('click', (e) => { if (e.target === modal) this.closeCascadeConfirmModal(); });
    },

    closeCascadeConfirmModal() {
        document.getElementById('labelCascadeModal')?.remove();
    },

    async confirmCascadeDelete(labelId) {
        const result = await this.deleteLabelWithCascade(labelId, true);
        this.closeCascadeConfirmModal();
        if (!result.success) alert('Error: ' + result.error);
        await this.loadAndRenderTree();
    }
};

// Initialize labels when auth is confirmed
document.addEventListener('DOMContentLoaded', async () => {
    // Load labels after a short delay to ensure auth check completes
    setTimeout(async () => {
        const authResponse = await fetch('/api/auth-status');
        const authStatus = await authResponse.json();
        if (authStatus.logged_in) {
            await GmailCleaner.Labels.loadLabels();
        }
    }, 500);
});
