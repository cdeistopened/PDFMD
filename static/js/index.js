let selectedFile = null;
let currentDocument = null;
let pollIntervals = {};

// Initialize Feather icons
document.addEventListener('DOMContentLoaded', () => {
    feather.replace();
});

function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file && file.type === 'application/pdf') {
        selectedFile = file;
        showSelectedFile(file.name);
        document.getElementById('processBtn').disabled = false;
    }
}

function handleDragOver(event) {
    event.preventDefault();
    event.currentTarget.classList.add('drag-over');
}

function handleDragLeave(event) {
    event.currentTarget.classList.remove('drag-over');
}

function handleDrop(event) {
    event.preventDefault();
    event.currentTarget.classList.remove('drag-over');

    const files = event.dataTransfer.files;
    if (files.length > 0 && files[0].type === 'application/pdf') {
        selectedFile = files[0];
        showSelectedFile(files[0].name);
        document.getElementById('processBtn').disabled = false;
    }
}

function showSelectedFile(fileName) {
    document.getElementById('fileName').textContent = fileName;
    document.getElementById('fileSelected').style.display = 'flex';
    feather.replace();
}

function hideStatusMessages() {
    document.getElementById('statusProcessing').style.display = 'none';
    document.getElementById('statusSuccess').style.display = 'none';
    document.getElementById('statusError').style.display = 'none';
}

async function processFile() {
    if (!selectedFile) return;

    hideStatusMessages();
    document.getElementById('batchProgress').style.display = 'none';
    document.getElementById('processBtn').disabled = true;

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('batch_size', document.getElementById('batchSize').value);
    formData.append('model', document.getElementById('modelSelect').value);

    try {
        const response = await fetch('/workbench/upload', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            // Backend returns doc_id, filename, total_pages, batches directly
            currentDocument = {
                doc_id: result.doc_id,
                filename: result.filename,
                total_pages: result.total_pages,
                batches: result.batches
            };
            renderBatchProgress();

            // Auto-process all batches
            processAllBatches();
        } else {
            hideStatusMessages();
            document.getElementById('errorMessage').textContent = result.error || 'Upload failed';
            document.getElementById('statusError').style.display = 'flex';
            document.getElementById('processBtn').disabled = false;
            feather.replace();
        }
    } catch (error) {
        hideStatusMessages();
        document.getElementById('errorMessage').textContent = 'Network error occurred';
        document.getElementById('statusError').style.display = 'flex';
        document.getElementById('processBtn').disabled = false;
        feather.replace();
    }
}

function renderBatchProgress() {
    if (!currentDocument) return;

    document.getElementById('batchProgress').style.display = 'block';
    document.getElementById('batchDocTitle').textContent = currentDocument.filename;
    document.getElementById('batchDocMeta').textContent =
        `${currentDocument.total_pages} pages • ${currentDocument.batches.length} batches`;

    const batchList = document.getElementById('batchList');
    batchList.innerHTML = currentDocument.batches.map((batch, index) =>
        renderBatch(currentDocument.doc_id, batch, index)
    ).join('');

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
    if (batch.status === 'completed') {
        actions = `
            <button class="btn-sm" onclick="previewBatch(${index})">Preview</button>
            <button class="btn-sm btn-secondary" onclick="downloadBatch('${batch.result_file}')">Download</button>
        `;
    } else if (batch.status === 'processing') {
        actions = `<span style="font-size: 13px; color: var(--stone-500);">Processing...</span>`;
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
        </div>
    `;
}

async function processAllBatches() {
    if (!currentDocument) return;

    for (let i = 0; i < currentDocument.batches.length; i++) {
        const batch = currentDocument.batches[i];
        if (batch.status === 'pending') {
            await processBatch(currentDocument.doc_id, i);
        }
    }
}

async function processBatch(docId, batchIndex) {
    try {
        const model = document.getElementById('modelSelect').value;
        const response = await fetch(`/workbench/process-batch/${docId}/${batchIndex}?model=${model}`, {
            method: 'POST'
        });

        const result = await response.json();

        if (result.success) {
            // Update batch status
            currentDocument.batches[batchIndex].status = 'processing';
            renderBatchProgress();

            // Start polling for status
            pollBatchStatus(docId, batchIndex, result.job_id);
        } else {
            currentDocument.batches[batchIndex].status = 'error';
            renderBatchProgress();
        }
    } catch (error) {
        currentDocument.batches[batchIndex].status = 'error';
        renderBatchProgress();
    }
}

async function pollBatchStatus(docId, batchIndex, jobId) {
    const pollId = `${docId}_${batchIndex}`;

    pollIntervals[pollId] = setInterval(async () => {
        try {
            const response = await fetch(`/status/${jobId}`);
            const status = await response.json();

            if (status.status === 'complete') {
                clearInterval(pollIntervals[pollId]);

                // Fetch updated document info
                const docResponse = await fetch('/workbench/documents');
                const data = await docResponse.json();
                const updatedDoc = data.documents.find(d => d.doc_id === docId);

                if (updatedDoc) {
                    currentDocument = updatedDoc;
                    renderBatchProgress();

                    // Check if all done
                    const allComplete = currentDocument.batches.every(b => b.status === 'completed');
                    if (allComplete) {
                        document.getElementById('processBtn').disabled = false;
                        showCompletionMessage();
                    }
                }
            } else if (status.status === 'error') {
                clearInterval(pollIntervals[pollId]);
                currentDocument.batches[batchIndex].status = 'error';
                renderBatchProgress();
            }
        } catch (error) {
            console.error('Status poll error:', error);
        }
    }, 500);
}

function showCompletionMessage() {
    document.getElementById('statusSuccess').style.display = 'flex';
    document.getElementById('statusSuccess').querySelector('span').innerHTML =
        `All batches complete! <a href="#" onclick="downloadAll(event)">Download All</a>`;
    feather.replace();
}

async function downloadAll(event) {
    if (event) event.preventDefault();
    if (!currentDocument) return;

    window.location.href = `/workbench/download-all/${currentDocument.doc_id}`;
}

async function previewBatch(batchIndex) {
    if (!currentDocument) return;

    const batch = currentDocument.batches[batchIndex];
    if (!batch.result_file) return;

    try {
        const response = await fetch(`/download/${batch.result_file}`);
        const markdown = await response.text();

        document.getElementById('previewContent').innerHTML = marked.parse(markdown);
        document.getElementById('previewModal').style.display = 'flex';
    } catch (error) {
        alert('Preview error: ' + error.message);
    }
}

function downloadBatch(filename) {
    window.location.href = `/download/${filename}`;
}

function closePreview() {
    document.getElementById('previewModal').style.display = 'none';
}
