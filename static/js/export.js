/**
 * Gmail Cleaner - Export & Label Processing Module
 * Handles email thread export and unsubscribe label processing
 */

window.GmailCleaner = window.GmailCleaner || {};

GmailCleaner.Export = {
    /**
     * Export email threads by search query
     */
    exportThreads: async function() {
        const query = document.getElementById('search-query').value.trim();
        const btn = document.getElementById('export-threads-btn');

        if (!query) {
            alert('Please enter a search query');
            return;
        }

        // Disable button during export
        btn.disabled = true;
        btn.innerHTML = `
            <svg viewBox="0 0 24 24" width="18" height="18" class="rotating">
                <path fill="currentColor" d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/>
            </svg>
            Exporting...
        `;

        try {
            const response = await fetch('/api/export-threads', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: query,
                    max_threads: 50
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Export failed');
            }

            // Get the text content
            const textContent = await response.text();

            // Create a blob and trigger download
            const blob = new Blob([textContent], { type: 'text/plain' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'email_export.txt';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            // Show success message
            GmailCleaner.UI.showNotification('Export completed successfully!', 'success');

        } catch (error) {
            console.error('Export error:', error);
            alert(`Export failed: ${error.message}`);
        } finally {
            // Re-enable button
            btn.disabled = false;
            btn.innerHTML = `
                <svg viewBox="0 0 24 24" width="18" height="18">
                    <path fill="currentColor" d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/>
                </svg>
                Export to Text File
            `;
        }
    },

    /**
     * Process emails with 'Unsubscribe' label
     */
    processUnsubscribeLabel: async function() {
        const btn = document.getElementById('process-unsubscribe-btn');

        // Confirm before processing
        const confirmed = confirm(
            "This will process all emails labeled 'Unsubscribe' and visit their unsubscribe links. " +
            "The label will be removed after processing. Continue?"
        );

        if (!confirmed) {
            return;
        }

        // Disable button during processing
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
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    label_name: 'Unsubscribe'
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Processing failed');
            }

            const result = await response.json();

            // Show success message with details
            alert(result.message);
            GmailCleaner.UI.showNotification('Label processing completed!', 'success');

        } catch (error) {
            console.error('Label processing error:', error);
            alert(`Processing failed: ${error.message}`);
        } finally {
            // Re-enable button
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

// Make functions globally accessible for onclick handlers
window.exportThreads = () => GmailCleaner.Export.exportThreads();
window.processUnsubscribeLabel = () => GmailCleaner.Export.processUnsubscribeLabel();
