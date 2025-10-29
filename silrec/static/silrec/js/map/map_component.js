document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing map...');

    // Initialize the map - Centered on Western Australia
    const map = new ol.Map({
        target: 'map',
        view: new ol.View({
            center: [122, -25.5], // Centered on Western Australia
            zoom: 6.5, // Higher zoom level for better WA focus
            projection: 'EPSG:4326'
        }),
        layers: [
            new ol.layer.Tile({
                source: new ol.source.OSM()
            })
        ]
    });

    // Store map instance globally for access from other scripts
    window.mapInstance = map;
    console.log('Map instance set globally:', window.mapInstance);

    // Custom fullscreen functionality
    const fullscreenBtn = document.getElementById('fullscreen-btn');
    const mapContainer = document.querySelector('.map-container');

    if (fullscreenBtn && mapContainer) {
        fullscreenBtn.addEventListener('click', function() {
            if (!document.fullscreenElement) {
                if (mapContainer.requestFullscreen) {
                    mapContainer.requestFullscreen();
                } else if (mapContainer.webkitRequestFullscreen) {
                    mapContainer.webkitRequestFullscreen();
                } else if (mapContainer.msRequestFullscreen) {
                    mapContainer.msRequestFullscreen();
                }
            } else {
                if (document.exitFullscreen) {
                    document.exitFullscreen();
                } else if (document.webkitExitFullscreen) {
                    document.webkitExitFullscreen();
                } else if (document.msExitFullscreen) {
                    document.msExitFullscreen();
                }
            }
        });

        // Update fullscreen button icon when fullscreen changes
        document.addEventListener('fullscreenchange', updateFullscreenButton);
        document.addEventListener('webkitfullscreenchange', updateFullscreenButton);
        document.addEventListener('msfullscreenchange', updateFullscreenButton);

        function updateFullscreenButton() {
            const isFullscreen = document.fullscreenElement ||
                                document.webkitFullscreenElement ||
                                document.msFullscreenElement;

            const icon = fullscreenBtn.querySelector('svg path');
            if (icon) {
                if (isFullscreen) {
                    icon.setAttribute('d', 'M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3');
                } else {
                    icon.setAttribute('d', 'M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3');
                }
            }

            // Update map size when fullscreen changes
            map.updateSize();
        }
    }

    // Handle window resize
    window.addEventListener('resize', function() {
        map.updateSize();
    });

    // Dispatch a custom event when map is ready
    const mapReadyEvent = new CustomEvent('mapReady', { detail: { map: map } });
    window.dispatchEvent(mapReadyEvent);
    console.log('Map ready event dispatched');
});
