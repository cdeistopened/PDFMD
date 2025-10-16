let documents = [];
let pollIntervals = {};

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    feather.replace();
    loadDocuments();
    // Auto-refresh documents every 5 seconds
    setInterval(loadDocuments, 5000);
});

async function loadDocuments() {
    try {
        const response = await fetch('/workbench/documents');
        const data = await response.json();
        documents = data.documents;
        renderDocuments();
    } catch (error) {
        console.error('Failed to load documents:', error);
    }
}

function renderDocuments() {
    const container = document.getElementById('documentsList');

    if (documents.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i data-feather="inbox" style="width: 64px; height: 64px;"></i>
                <p>No documents yet. Upload a PDF to get started.</p>
            </div>
        `;
        feather.replace();
        return;
    }

    container.innerHTML = documents.map(doc => `
        <div class="document-card">
            <div class="document-header">
                <div class="document-info">
                    <div class="document-icon">
                        <i data-feather="file-text" style="width: 20px; height: 20px;"></i>
                    </div>
                    <div>
                        <div class="document-title">${doc.filename}</div>
                        <div class="document-meta">${doc.total_pages} pages • ${doc.batches.length} batches (${doc.batch_size} pages each)</div>
                    </div>
                </div>
                <button class="btn btn-success btn-sm" onclick="downloadAll('${doc.doc_id}')">
                    <i data-feather="download" style="width: 14px; height: 14px;"></i>
                    Download All
                </button>
            </div>
            <div class="batch-list">
                ${doc.batches.map((batch, index) => renderBatch(doc.doc_id, batch, index)).join('')}
            </div>
        </div>
    `).join('');

    feather.replace();
}

function renderBatch(docId, batch, index) {
    const statusIcons = {
        pending: '⏳',
        processing: '🔄',
        completed: '✓',
        error: '✕'
    };

    let actions = '';
    if (batch.status === 'pending') {
        actions = `<button class="btn btn-primary btn-sm" onclick="processBatch('${docId}', ${index})">Process</button>`;
    } else if (batch.status === 'completed') {
        actions = `
            <button class="btn btn-secondary btn-sm" onclick="previewBatch('${docId}', ${index})">
                <i data-feather="eye" style="width: 14px; height: 14px;"></i>
                Preview
            </button>
            <button class="btn btn-secondary btn-sm" onclick="downloadBatch('${batch.result_file}')">
                <i data-feather="download" style="width: 14px; height: 14px;"></i>
                Download
            </button>
        `;
    } else if (batch.status === 'processing') {
        actions = `<span class="progress-text">Processing...</span>`;
    }

    return `
        <div class="batch-item" id="batch_${docId}_${index}">
            <div class="batch-info">
                <div class="batch-status ${batch.status}">${statusIcons[batch.status]}</div>
                <div class="batch-pages">Pages ${batch.start}-${batch.end}</div>
            </div>
            <div class="batch-actions">
                ${actions}
            </div>
            ${batch.status === 'processing' ? `
                <div class="progress-container" id="progress_${docId}_${index}">
                    <div class="progress-bar-wrapper">
                        <div class="progress-bar-fill" style="width: 0%"></div>
                    </div>
                    <div class="progress-text">Page ${batch.start} of ${batch.end}</div>
                </div>
            ` : ''}
        </div>
    `;
}

async function uploadDocument(event) {
    event.preventDefault();

    const fileInput = document.getElementById('pdfFile');
    const batchSize = document.getElementById('batchSize').value;

    if (!fileInput.files[0]) return;

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('batch_size', batchSize);

    try {
        const response = await fetch('/workbench/upload', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            // Reset form
            document.getElementById('uploadForm').reset();

            // Reload documents
            await loadDocuments();
        } else {
            alert('Upload failed: ' + result.error);
        }
    } catch (error) {
        alert('Upload error: ' + error.message);
    }
}

async function processBatch(docId, batchIndex) {
    try {
        const response = await fetch(`/workbench/process-batch/${docId}/${batchIndex}`, {
            method: 'POST'
        });

        const result = await response.json();

        if (result.success) {
            // Start polling for status
            pollBatchStatus(docId, batchIndex, result.job_id);
        } else {
            alert('Processing failed: ' + result.error);
        }
    } catch (error) {
        alert('Processing error: ' + error.message);
    }
}

async function pollBatchStatus(docId, batchIndex, jobId) {
    const pollId = `${docId}_${batchIndex}`;

    pollIntervals[pollId] = setInterval(async () => {
        try {
            const response = await fetch(`/status/${jobId}`);
            const status = await response.json();

            if (status.status === 'processing') {
                // Update progress
                const doc = documents.find(d => d.doc_id === docId);
                if (doc) {
                    const batch = doc.batches[batchIndex];
                    const progress = ((status.current_page - batch.start) / (batch.end - batch.start + 1)) * 100;

                    const progressContainer = document.getElementById(`progress_${docId}_${batchIndex}`);
                    if (progressContainer) {
                        progressContainer.querySelector('.progress-bar-fill').style.width = `${progress}%`;
                        progressContainer.querySelector('.progress-text').textContent = `Page ${status.current_page} of ${batch.end}`;
                    }
                }
            } else if (status.status === 'complete' || status.status === 'error') {
                // Stop polling
                clearInterval(pollIntervals[pollId]);

                // Reload documents
                await loadDocuments();
            }
        } catch (error) {
            console.error('Status poll error:', error);
        }
    }, 500);
}

async function previewBatch(docId, batchIndex) {
    const doc = documents.find(d => d.doc_id === docId);
    if (!doc) return;

    const batch = doc.batches[batchIndex];
    if (!batch.result_file) return;

    try {
        const response = await fetch(`/download/${batch.result_file}`);
        const markdown = await response.text();

        document.getElementById('previewTitle').textContent = `Pages ${batch.start}-${batch.end}`;
        document.getElementById('previewContent').innerHTML = marked.parse(markdown);
        document.getElementById('previewModal').classList.add('active');
    } catch (error) {
        alert('Preview error: ' + error.message);
    }
}

function closePreview() {
    document.getElementById('previewModal').classList.remove('active');
}

function downloadBatch(filename) {
    window.location.href = `/download/${filename}`;
}

function downloadAll(docId) {
    window.location.href = `/workbench/download-all/${docId}`;
}
