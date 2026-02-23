// --- UI Elements ---
const strokeWidthSlider = document.getElementById('stroke-width');
const maxBlobsSlider = document.getElementById('max-blobs');
const minSizeSlider = document.getElementById('min-size');
const labelTypeSelect = document.getElementById('label-type');
const customTextWrapper = document.getElementById('custom-text-wrapper');

// --- Real-Time Slider Number Updates ---
const updateVal = (e, suffix = '') => {
    e.target.previousElementSibling.querySelector('.val').innerText = e.target.value + suffix;
};
strokeWidthSlider.addEventListener('input', (e) => updateVal(e, 'px'));
maxBlobsSlider.addEventListener('input', (e) => updateVal(e));
minSizeSlider.addEventListener('input', (e) => updateVal(e, 'px'));

// --- Toggle Custom Text Input ---
labelTypeSelect.addEventListener('change', (e) => {
    if (e.target.value === 'custom') {
        customTextWrapper.style.display = 'block';
    } else {
        customTextWrapper.style.display = 'none';
    }
});

// --- Upload & Rendering Logic ---
const uploadZone = document.getElementById('upload-zone');
const previewZone = document.getElementById('preview-zone');
const resultPlayer = document.getElementById('result-player');
const renderBtn = document.getElementById('render-btn');
const downloadBtn = document.getElementById('download-btn');
const uploadTitle = document.getElementById('upload-title');
const uploadIcon = document.querySelector('.upload-icon');

let uploadedFile = null;

// Handle file selection
uploadZone.addEventListener('click', () => {
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = 'video/mp4, video/avi, video/quicktime';
    
    fileInput.onchange = e => {
        uploadedFile = e.target.files[0];
        uploadTitle.innerText = "READY: " + uploadedFile.name;
        uploadIcon.innerText = '✓';
        uploadIcon.style.color = 'var(--accent-success)';
        
        // Reset preview if uploading a new file
        previewZone.style.display = 'none';
        uploadZone.style.display = 'flex';
        downloadBtn.style.display = 'none';
    };
    fileInput.click();
});

// Render Button Action
renderBtn.addEventListener('click', async () => {
    if (!uploadedFile) {
        alert("Please select a video file first.");
        return;
    }

    // UI Loading State
    renderBtn.innerText = "RENDERING IN PROGRESS...";
    renderBtn.disabled = true;
    downloadBtn.style.display = 'none';
    
    // Gather all settings
    const formData = new FormData();
    formData.append('video', uploadedFile);
    formData.append('shape', document.getElementById('shape-select').value);
    formData.append('box_color', document.getElementById('box-color').value);
    formData.append('stroke_width', strokeWidthSlider.value);
    formData.append('connection', document.getElementById('conn-select').value);
    formData.append('conn_color', document.getElementById('conn-color').value);
    formData.append('label_type', labelTypeSelect.value);
    formData.append('custom_text', document.getElementById('custom-text-input').value);
    formData.append('text_color', document.getElementById('text-color').value);
    formData.append('max_blobs', maxBlobsSlider.value);
    formData.append('min_size', minSizeSlider.value);

    try {
        // Send to Python server
        const response = await fetch('http://localhost:5000/process', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            // Retrieve video as a blob
            const blob = await response.blob();
            const videoUrl = window.URL.createObjectURL(blob);
            
            // Swap out the upload UI for the Video Player
            uploadZone.style.display = 'none';
            previewZone.style.display = 'flex';
            
            // Load and play the rendered video
            resultPlayer.src = videoUrl;
            
            // Setup the Download Button
            downloadBtn.href = videoUrl;
            downloadBtn.style.display = 'block';

        } else {
            alert("Error processing video. Check your Python terminal.");
        }
    } catch (error) {
        console.error("Fetch error:", error);
        alert("Could not connect to the Python server. Is it running?");
    } finally {
        // Reset Render Button
        renderBtn.innerText = "INITIATE RENDER SEQUENCE";
        renderBtn.disabled = false;
    }
});