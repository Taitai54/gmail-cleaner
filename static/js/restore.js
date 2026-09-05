/**
 * Gmail Cleaner - Restore from Archive Module
 */

window.GmailCleaner = window.GmailCleaner || {};

GmailCleaner.Restore = {
    selectedFile: null,
    previewData: null,
    pollingInterval: null,

    init() {
        this.populateLabelsDropdown();
    },

    handleDragOver(e) {
        e.preventDefault();
        e.stopPropagation();
        const dropzone = document.getElementById('restoreDropzone');
        if (dropzone) dropzone.classList.add('drag-over');
    },

    handleDragLeave(e) {
        e.preventDefault();
        e.stopPropagation();
        const dropzone = document.getElementById('restoreDropzone');
        if (dropzone) dropzone.classList.remove('drag-over');
    },

    handleDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        const dropzone = document.getElementById('restoreDropzone');
        if (dropzone) dropzone.classList.remove('drag-over');

        const files = e.dataTransfer?.files;
        if (files && files.length > 0) {
            this.processFile(files[0]);
        }
    },

    handleFileSelect(e) {
        const files = e.target?.files;
        if (files && files.length > 0) {
            this.processFile(files[0]);
        }
    },

    fileToBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = () => {
                const result = reader.result || '';
                const base64 = result.includes(',') ? result.split(',')[1] : result;
                resolve(base64);
            };
            reader.onerror = error => reject(error);
        });
    },

    async processFile(file) {
        if (!file) return;
        this.selectedFile = file;

        const uploadCard = document.getElementById('restoreUploadCard');
        const previewCard = document.getElementById('restorePreviewCard');
        const progressCard = document.getElementById('restoreProgressCard');
        
        if (progressCard) progressCard.classList.add('hidden');

        // Show loading state in dropzone
        const dropzone = document.getElementById('restoreDropzone');
        if (dropzone) {
            dropzone.innerHTML = `
                <div class="spinner-container" style="padding: 24px; text-align: center;">
                    <div class="account-switch-spinner" style="margin: 0 auto 12px;"></div>
                    <p style="font-weight: 500;">Reading archive <strong>${GmailCleaner.UI.escapeHtml(file.name)}</strong>...</p>
                </div>
            `;
        }

        try {
            const b64 = await this.fileToBase64(file);
            const response = await fetch('/api/restore/preview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    filename: file.name,
                    content_base64: b64,
                }),
            });

            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.detail || data.error || 'Failed to inspect archive');
            }

            this.previewData = data;
            this.renderPreview(data);
        } catch (err) {
            alert('Error inspecting archive: ' + err.message);
            this.resetDropzone();
        }
    },

    resetDropzone() {
        const dropzone = document.getElementById('restoreDropzone');
        if (dropzone) {
            dropzone.innerHTML = `
                <div class="dropzone-icon">
                    <svg viewBox="0 0 24 24" width="48" height="48">
                        <path fill="currentColor" d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z"/>
                    </svg>
                </div>
                <h3 style="margin-top: 10px; margin-bottom: 6px;">Drag &amp; drop your archive file here</h3>
                <p style="color: var(--text-secondary); margin-bottom: 12px;">or click to browse your computer</p>
                <div class="format-badges" style="display: flex; gap: 8px; justify-content: center; flex-wrap: wrap;">
                    <span class="badge" style="background: rgba(30, 142, 62, 0.1); color: #1e8e3e; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 500;">⚡ JSON (.json)</span>
                    <span class="badge" style="background: rgba(26, 115, 232, 0.1); color: var(--primary); padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 500;">✉️ Email Archive (.zip)</span>
                    <span class="badge" style="background: rgba(128, 134, 139, 0.1); color: var(--text-secondary); padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: 500;">📄 Single EML (.eml)</span>
                </div>
            `;
        }
        const fileInput = document.getElementById('restoreFileInput');
        if (fileInput) fileInput.value = '';
        this.selectedFile = null;
        this.previewData = null;
    },

    renderPreview(data) {
        const previewCard = document.getElementById('restorePreviewCard');
        const badge = document.getElementById('restoreFileInfoBadge');
        const list = document.getElementById('restoreMessagesList');

        if (badge) {
            const fmtName = data.format === 'json' ? '⚡ JSON' : (data.format === 'zip' ? '✉️ ZIP/EML' : '📄 EML');
            badge.textContent = `${data.total_messages} message(s) • ${fmtName}`;
            badge.style.display = 'inline-block';
        }

        this.populateLabelsDropdown();

        if (list) {
            const msgs = data.messages || [];
            if (msgs.length === 0) {
                list.innerHTML = '<div style="padding: 16px; color: var(--text-secondary); text-align: center;">No messages found in archive.</div>';
            } else {
                list.innerHTML = msgs.slice(0, 100).map((m, idx) => {
                    const initials = (m.from || 'U').charAt(0).toUpperCase();
                    const color = GmailCleaner.UI?.getAvatarGradient ? GmailCleaner.UI.getAvatarGradient(m.from) : '#1a73e8';
                    const safeFrom = GmailCleaner.UI.escapeHtml(m.from);
                    const safeSubj = GmailCleaner.UI.escapeHtml(m.subject || '(No Subject)');
                    const safeDate = GmailCleaner.UI.escapeHtml(m.date || '');
                    const safeSnippet = GmailCleaner.UI.escapeHtml(m.snippet || '');

                    return `
                        <div class="restore-msg-item" style="display: flex; align-items: center; gap: 12px; padding: 8px 12px; border-bottom: 1px solid var(--border-color, #eee); font-size: 13px;">
                            <div class="sender-avatar" style="background: ${color}; width: 28px; height: 28px; font-size: 11px; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 600; box-shadow: 0 1px 4px rgba(0,0,0,0.15);">${initials}</div>
                            <div style="flex: 1; min-width: 0;">
                                <div style="display: flex; justify-content: space-between; align-items: baseline;">
                                    <strong style="color: var(--text-primary); max-width: 60%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${safeFrom}</strong>
                                    <span style="font-size: 11px; color: var(--text-secondary);">${safeDate}</span>
                                </div>
                                <div style="color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                    <span style="color: var(--text-primary); font-weight: 500;">${safeSubj}</span> — ${safeSnippet}
                                </div>
                            </div>
                        </div>
                    `;
                }).join('');

                if (msgs.length > 100) {
                    list.innerHTML += `<div style="padding: 8px; text-align: center; color: var(--text-secondary); font-size: 12px;">+ ${msgs.length - 100} more messages</div>`;
                }
            }
        }

        if (previewCard) previewCard.classList.remove('hidden');
    },

    populateLabelsDropdown() {
        const select = document.getElementById('restoreLabelSelect');
        if (!select) return;

        const currentVal = select.value;
        select.innerHTML = `
            <option value="">None (All Mail only)</option>
            <option value="__new__">➕ Create New Label...</option>
        `;

        const userLabels = GmailCleaner.Labels?.labels?.user || [];
        userLabels.forEach((lbl) => {
            const opt = document.createElement('option');
            opt.value = lbl.id;
            opt.textContent = lbl.name;
            select.appendChild(opt);
        });

        if (currentVal && Array.from(select.options).some(o => o.value === currentVal)) {
            select.value = currentVal;
        }
    },

    handleLabelSelectChange() {
        const select = document.getElementById('restoreLabelSelect');
        const input = document.getElementById('restoreNewLabelInput');
        if (!select || !input) return;

        if (select.value === '__new__') {
            input.classList.remove('hidden');
            input.focus();
        } else {
            input.classList.add('hidden');
        }
    },

    async startRestore() {
        if (!this.selectedFile) {
            alert('Please select an archive file first.');
            return;
        }

        const labelSelect = document.getElementById('restoreLabelSelect');
        const newLabelInput = document.getElementById('restoreNewLabelInput');
        const addToInbox = document.getElementById('restoreAddToInbox')?.checked || false;
        const markUnread = document.getElementById('restoreMarkUnread')?.checked || false;
        const executeBtn = document.getElementById('restoreExecuteBtn');
        const progressCard = document.getElementById('restoreProgressCard');
        const progressBar = document.getElementById('restoreProgressBar');
        const progressText = document.getElementById('restoreProgressText');

        let targetLabelId = '';
        let targetLabelName = '';

        if (labelSelect?.value === '__new__') {
            targetLabelName = newLabelInput?.value.trim() || 'Restored Archive';
        } else if (labelSelect?.value) {
            targetLabelId = labelSelect.value;
        }

        try {
            const b64 = await this.fileToBase64(this.selectedFile);
            const payload = {
                filename: this.selectedFile.name,
                content_base64: b64,
                target_label_id: targetLabelId || null,
                target_label_name: targetLabelName || null,
                add_to_inbox: addToInbox,
                mark_unread: markUnread,
            };

            const response = await fetch('/api/restore/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            const data = await response.json();
            if (!response.ok || data.status !== 'started') {
                throw new Error(data.detail || 'Failed to begin restoration');
            }

            this.pollProgress();
        } catch (err) {
            alert('Error starting restoration: ' + err.message);
            if (executeBtn) {
                executeBtn.disabled = false;
                executeBtn.textContent = 'Start Restore to Gmail';
            }
        }
    },

    pollProgress() {
        if (this.pollingInterval) clearInterval(this.pollingInterval);

        this.pollingInterval = setInterval(async () => {
            try {
                const response = await fetch('/api/restore-status');
                const status = await response.json();

                const progressBar = document.getElementById('restoreProgressBar');
                const progressText = document.getElementById('restoreProgressText');
                const executeBtn = document.getElementById('restoreExecuteBtn');

                if (progressBar) {
                    progressBar.style.width = `${Math.max(5, status.progress || 0)}%`;
                }
                if (progressText) {
                    progressText.textContent = status.message || 'Restoring messages...';
                }

                if (status.done) {
                    clearInterval(this.pollingInterval);
                    this.pollingInterval = null;

                    if (executeBtn) {
                        executeBtn.disabled = false;
                        executeBtn.textContent = 'Restore Complete';
                    }

                    if (status.error) {
                        alert('Restoration error: ' + status.error);
                    } else {
                        if (GmailCleaner.UI?.showToast) {
                            GmailCleaner.UI.showToast(`Restoration complete! ${status.restored_count || 0} messages restored to Gmail.`);
                        } else {
                            alert(`Restoration complete! ${status.restored_count || 0} messages restored to Gmail.`);
                        }
                    }
                }
            } catch (err) {
                console.error('Error polling restore progress:', err);
            }
        }, 1000);
    },

    clear() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
        this.resetDropzone();
        const previewCard = document.getElementById('restorePreviewCard');
        if (previewCard) previewCard.classList.add('hidden');
        const progressCard = document.getElementById('restoreProgressCard');
        if (progressCard) progressCard.classList.add('hidden');
    }
};

// Global shortcuts
window.startRestore = () => GmailCleaner.Restore.startRestore();
window.clearRestoreFile = () => GmailCleaner.Restore.clear();
