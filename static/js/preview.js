/**
 * Gmail Cleaner - Email Preview Module
 */

window.GmailCleaner = window.GmailCleaner || {};

GmailCleaner.Preview = {
    async showPreview(sender, emailCount) {
        // Create modal
        const modal = document.createElement('div');
        modal.className = 'preview-modal';
        modal.id = 'emailPreviewModal';
        
        modal.innerHTML = `
            <div class="preview-modal-content">
                <div class="preview-modal-header">
                    <h3>Email Preview</h3>
                    <button class="preview-modal-close" onclick="GmailCleaner.Preview.closePreview()">
                        <svg viewBox="0 0 24 24" width="24" height="24">
                            <path fill="currentColor" d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                        </svg>
                    </button>
                </div>
                <div class="preview-modal-body">
                    <div class="preview-sender-info">
                        <div class="preview-sender-email">${GmailCleaner.UI.escapeHtml(sender)}</div>
                        <div class="preview-stats">
                            <div class="preview-stat">
                                <svg viewBox="0 0 24 24">
                                    <path fill="currentColor" d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z"/>
                                </svg>
                                <span>${emailCount} emails</span>
                            </div>
                        </div>
                    </div>
                    <div class="preview-loading">
                        <svg class="spinner" viewBox="0 0 24 24">
                            <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2" stroke-dasharray="60" stroke-linecap="round"/>
                        </svg>
                        <div>Loading preview...</div>
                    </div>
                </div>
                <div class="preview-modal-footer">
                    <button class="btn btn-secondary" onclick="GmailCleaner.Preview.closePreview()">Close</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Close on background click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.closePreview();
            }
        });
        
        // Load preview data
        try {
            const response = await fetch('/api/preview-emails', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sender, limit: 10 })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.displayPreviewEmails(data.emails);
            } else {
                this.showPreviewError(data.error || 'Failed to load preview');
            }
        } catch (error) {
            this.showPreviewError('Failed to load preview: ' + error.message);
        }
    },
    
    displayPreviewEmails(emails) {
        const modal = document.getElementById('emailPreviewModal');
        if (!modal) return;
        
        const body = modal.querySelector('.preview-modal-body');
        
        if (emails.length === 0) {
            body.innerHTML = `
                <div class="preview-sender-info">
                    <div class="preview-sender-email">No emails found</div>
                </div>
            `;
            return;
        }
        
        const senderInfo = body.querySelector('.preview-sender-info');
        const emailsList = document.createElement('div');
        emailsList.className = 'preview-emails-list';
        
        emails.forEach(email => {
            const item = document.createElement('div');
            item.className = 'preview-email-item';
            
            const date = email.date ? new Date(email.date).toLocaleDateString() : 'Unknown date';
            
            item.innerHTML = `
                <div class="preview-email-subject">${GmailCleaner.UI.escapeHtml(email.subject || '(No subject)')}</div>
                <div class="preview-email-date">${date}</div>
                ${email.snippet ? `<div class="preview-email-snippet">${GmailCleaner.UI.escapeHtml(email.snippet)}</div>` : ''}
            `;
            
            emailsList.appendChild(item);
        });
        
        body.innerHTML = '';
        body.appendChild(senderInfo);
        body.appendChild(emailsList);
    },
    
    showPreviewError(message) {
        const modal = document.getElementById('emailPreviewModal');
        if (!modal) return;
        
        const body = modal.querySelector('.preview-modal-body');
        body.innerHTML = `
            <div class="preview-loading">
                <svg viewBox="0 0 24 24" width="40" height="40">
                    <path fill="#ea4335" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
                </svg>
                <div>${GmailCleaner.UI.escapeHtml(message)}</div>
            </div>
        `;
    },
    
    closePreview() {
        const modal = document.getElementById('emailPreviewModal');
        if (modal) {
            modal.remove();
        }
    }
};
