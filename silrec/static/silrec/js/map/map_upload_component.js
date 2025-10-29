class ShapefileUploader {
    constructor(mapInstance, options = {}) {
        console.log('ShapefileUploader constructor called');
        this.map = mapInstance;
        //this.uploadUrl = options.uploadUrl || '/api/proposals/upload_shapefile/';
        this.uploadUrl = options.uploadUrl || '/api/proposal-uploads/upload_shapefile/';
        this.vectorLayer = null;
        this.initializeElements();
        this.bindEvents();
    }

    initializeElements() {
        console.log('Initializing elements...');
        this.uploadBtn = document.getElementById('upload-shapefile-btn');
        this.fileInput = document.getElementById('shapefile-upload');
        this.filenameSpan = document.getElementById('selected-filename');
        this.progressContainer = document.getElementById('upload-progress');
        this.progressFill = this.progressContainer?.querySelector('.progress-fill');
        this.progressText = this.progressContainer?.querySelector('.progress-text');

        console.log('Elements found:', {
            uploadBtn: this.uploadBtn,
            fileInput: this.fileInput,
            filenameSpan: this.filenameSpan,
            progressContainer: this.progressContainer
        });
    }

    bindEvents() {
        console.log('Binding events...');
        if (this.uploadBtn && this.fileInput) {
            this.uploadBtn.addEventListener('click', () => {
                console.log('Upload button clicked');
                this.fileInput.click();
            });
            this.fileInput.addEventListener('change', (e) => {
                console.log('File selected:', e.target.files[0]);
                this.handleFileSelect(e);
            });
        } else {
            console.error('Required elements not found!');
        }
    }

    handleFileSelect(event) {
        console.log('handleFileSelect called');
        const file = event.target.files[0];
        if (!file) {
            console.log('No file selected');
            return;
        }

        console.log('File selected:', file.name, file.type, file.size);

        if (!file.name.toLowerCase().endsWith('.zip')) {
            alert('Please select a valid ZIP file containing shapefile components.');
            return;
        }

        this.filenameSpan.textContent = `Selected: ${file.name}`;
        this.uploadShapefile(file);
    }

    async uploadShapefile(file) {
        console.log('uploadShapefile called with file:', file.name);
        if (!file) return;

        this.setUploadState(true, 'Uploading...');

        const formData = new FormData();
        formData.append('shapefile', file);

        try {
            console.log('Sending request to:', this.uploadUrl);

            // Get CSRF token using the more reliable method
            const csrfToken = this.getCsrfToken();
            console.log('CSRF Token:', csrfToken ? 'Found' : 'Not found');

            const response = await fetch(this.uploadUrl, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': csrfToken,
                    // Don't set Content-Type for FormData - let browser set it with boundary
                },
                credentials: 'include' // Important for session/cookie authentication
            });

            console.log('Response status:', response.status);
            console.log('Response ok:', response.ok);

            if (response.status === 403) {
                // Check if it's a CSRF failure
                const responseText = await response.text();
                console.log('403 Response:', responseText);

                if (responseText.includes('CSRF') || responseText.includes('csrf')) {
                    throw new Error('CSRF verification failed. Please refresh the page and try again.');
                } else {
                    throw new Error('Authentication required. Please log in.');
                }
            }

            if (!response.ok) {
                throw new Error(`Upload failed: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            console.log('Response data:', data);

            if (data.success) {
                this.setUploadState(false, 'Upload successful!');
                this.filenameSpan.textContent = 'Upload successful!';
                this.filenameSpan.style.color = '#28a745';

                // Display the uploaded shapefile on map
                await this.displayShapefileOnMap(data.geojson_data);

                // Clear file input
                this.fileInput.value = '';

                // Reset filename after delay
                setTimeout(() => {
                    this.filenameSpan.textContent = '';
                    this.filenameSpan.style.color = '';
                }, 3000);
            } else {
                throw new Error(data.error || 'Upload failed');
            }
        } catch (error) {
            console.error('Shapefile upload error:', error);
            this.setUploadState(false, '');
            this.filenameSpan.textContent = `Error: ${error.message}`;
            this.filenameSpan.style.color = '#dc3545';

            setTimeout(() => {
                this.filenameSpan.textContent = '';
                this.filenameSpan.style.color = '';
            }, 5000);
        }
    }

    displayShapefileOnMap(geojsonData) {
        console.log('Displaying shapefile on map:', geojsonData);

        // Remove existing vector layer
        if (this.vectorLayer) {
            this.map.removeLayer(this.vectorLayer);
        }

        if (!geojsonData) {
            console.warn('No GeoJSON data to display');
            return;
        }

        try {
            // Create vector source from GeoJSON
            //        featureProjection: 'EPSG:3857',
            const vectorSource = new ol.source.Vector({
                features: new ol.format.GeoJSON().readFeatures(geojsonData, {
                    featureProjection: 'EPSG:4326',
                    dataProjection: 'EPSG:4326'
                })
            });

            // Create vector layer
            this.vectorLayer = new ol.layer.Vector({
                source: vectorSource,
                style: new ol.style.Style({
                    stroke: new ol.style.Stroke({
                        color: 'blue',
                        width: 2
                    }),
                    fill: new ol.style.Fill({
                        color: 'rgba(0, 0, 255, 0.1)'
                    })
                })
            });

            // Add layer to map
            this.map.addLayer(this.vectorLayer);
            console.log('Vector layer added to map');

            // Zoom to the extent of the features
            const extent = vectorSource.getExtent();
            console.log('Features extent:', extent);

            if (extent && extent[0] !== Infinity && extent[1] !== Infinity) {
                this.map.getView().fit(extent, {
                    padding: [50, 50, 50, 50],
                    duration: 1000
                });
                console.log('Map zoomed to feature extent');
            } else {
                console.warn('Invalid extent, cannot zoom to features');
            }
        } catch (error) {
            console.error('Error displaying shapefile on map:', error);
        }
    }

    setUploadState(uploading, text) {
        if (this.uploadBtn) {
            this.uploadBtn.disabled = uploading;
        }

        if (this.progressContainer) {
            this.progressContainer.style.display = uploading ? 'block' : 'none';
        }

        if (this.progressFill) {
            this.progressFill.style.width = uploading ? '50%' : '100%';
        }

        if (this.progressText) {
            this.progressText.textContent = text;
        }
    }

    getCsrfToken() {
        // Method 1: Check for CSRF token in cookie
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }

        // Method 2: Check for CSRF token in meta tag (common in Django)
        if (!cookieValue) {
            const csrfMeta = document.querySelector('meta[name="csrf-token"]');
            if (csrfMeta) {
                cookieValue = csrfMeta.getAttribute('content');
            }
        }

        // Method 3: Check for input field with CSRF token
        if (!cookieValue) {
            const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
            if (csrfInput) {
                cookieValue = csrfInput.value;
            }
        }

        console.log('CSRF Token found:', cookieValue ? 'Yes' : 'No');
        return cookieValue;
    }

    // Method to clear the displayed shapefile
    clearShapefile() {
        if (this.vectorLayer) {
            this.map.removeLayer(this.vectorLayer);
            this.vectorLayer = null;
        }
        this.filenameSpan.textContent = '';
        this.fileInput.value = '';
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing ShapefileUploader...');

    // Try multiple ways to get the map instance
    function initializeUploader() {
        // Method 1: Check if map instance is available globally
        if (window.mapInstance) {
            console.log('Map instance found via window.mapInstance');
            window.shapefileUploader = new ShapefileUploader(window.mapInstance);
            return true;
        }

        // Method 2: Try to find map by ID
        const mapElement = document.getElementById('map');
        if (mapElement && mapElement._ol_map) {
            console.log('Map instance found via element reference');
            window.shapefileUploader = new ShapefileUploader(mapElement._ol_map);
            return true;
        }

        return false;
    }

    // Try to initialize immediately
    if (!initializeUploader()) {
        // If not ready, wait for map ready event or check periodically
        console.log('Map instance not ready, waiting...');

        // Listen for custom map ready event
        window.addEventListener('mapReady', function(event) {
            console.log('Map ready event received', event.detail);
            window.mapInstance = event.detail.map;
            window.shapefileUploader = new ShapefileUploader(window.mapInstance);
        });

        // Fallback: check periodically (with timeout)
        let attempts = 0;
        const maxAttempts = 50; // 5 seconds max
        const checkInterval = setInterval(() => {
            attempts++;
            if (initializeUploader()) {
                console.log('Map instance found after', attempts, 'attempts');
                clearInterval(checkInterval);
            } else if (attempts >= maxAttempts) {
                console.error('Failed to find map instance after', maxAttempts, 'attempts');
                clearInterval(checkInterval);
            }
        }, 100);
    }
});
