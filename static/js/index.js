let selectedFile = null;
let statusPollInterval = null;
let currentResultFilename = null;

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

async function pollStatus(jobId) {
    try {
        const response = await fetch(`/status/${jobId}`);
        const status = await response.json();

        if (status.status === 'processing') {
            const progress = (status.current_page / status.total_pages) * 100;
            document.getElementById('progressBar').style.width = `${progress}%`;
            document.getElementById('processingMessage').textContent = status.message;
            document.getElementById('pageStatus').textContent =
                `Page ${status.current_page} of ${status.total_pages}`;
        } else if (status.status === 'complete') {
            clearInterval(statusPollInterval);

            hideStatusMessages();
            currentResultFilename = status.filename;
            document.getElementById('downloadLink').href = `/download/${status.filename}`;
            document.getElementById('statusSuccess').style.display = 'flex';
            document.getElementById('processBtn').disabled = false;
            feather.replace();
        } else if (status.status === 'error') {
            clearInterval(statusPollInterval);

            hideStatusMessages();
            document.getElementById('errorMessage').textContent = status.message;
            document.getElementById('statusError').style.display = 'flex';
            document.getElementById('processBtn').disabled = false;
            feather.replace();
        }
    } catch (error) {
        console.error('Status poll error:', error);
    }
}

async function processFile() {
    if (!selectedFile) return;

    hideStatusMessages();
    document.getElementById('statusProcessing').style.display = 'flex';
    document.getElementById('processBtn').disabled = true;
    document.getElementById('progressBar').style.width = '0%';
    document.getElementById('processingMessage').textContent = 'Starting processing...';
    document.getElementById('pageStatus').textContent = 'Page 0 of 0';

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
        const response = await fetch('/process', {
            method: 'POST',
            body: formData,
        });

        const result = await response.json();

        if (result.success && result.job_id) {
            // Start polling for status
            statusPollInterval = setInterval(() => pollStatus(result.job_id), 500);
        } else {
            hideStatusMessages();
            document.getElementById('errorMessage').textContent =
                result.error || 'Processing failed';
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

async function previewResult(event) {
    event.preventDefault();

    if (!currentResultFilename) return;

    try {
        const response = await fetch(`/download/${currentResultFilename}`);
        const markdown = await response.text();

        document.getElementById('previewContent').innerHTML = marked.parse(markdown);
        document.getElementById('previewModal').style.display = 'flex';
    } catch (error) {
        alert('Preview error: ' + error.message);
    }
}

function closePreview() {
    document.getElementById('previewModal').style.display = 'none';
}
