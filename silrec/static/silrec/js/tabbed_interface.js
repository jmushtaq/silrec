document.addEventListener('DOMContentLoaded', function() {
    // Store map reference globally when it's created
    window.mapInstance = null;

    // Function to update map size safely
    function updateMapSize() {
        if (window.mapInstance && typeof window.mapInstance.updateSize === 'function') {
            window.mapInstance.updateSize();
        }
    }

    // Initialize collapse components for the active tab
    function initializeCollapseComponents() {
        // Get the active tab content
        const activeTab = document.querySelector('.tab-pane.active');
        if (!activeTab) return;

        // Find all collapse elements in the active tab and initialize them
        const collapseElements = activeTab.querySelectorAll('.collapse');
        collapseElements.forEach(function(collapseEl) {
            // Check if already initialized
            if (!collapseEl._collapse) {
                const collapse = new bootstrap.Collapse(collapseEl, {
                    toggle: false
                });
                collapseEl._collapse = collapse;
            }
        });

        // Initialize collapse triggers
        const collapseTriggers = activeTab.querySelectorAll('[data-bs-toggle="collapse"]');
        collapseTriggers.forEach(function(trigger) {
            trigger.addEventListener('click', function() {
                const targetSelector = this.getAttribute('data-bs-target') || this.getAttribute('href');
                const target = document.querySelector(targetSelector);
                if (target && target._collapse) {
                    target._collapse.toggle();
                }
            });
        });
    }

    // Initialize collapses when page loads
    initializeCollapseComponents();

    // Re-initialize collapses when tab changes
    const tabTriggers = document.querySelectorAll('[data-bs-toggle="pill"]');
    tabTriggers.forEach(function(tab) {
        tab.addEventListener('shown.bs.tab', function() {
            setTimeout(initializeCollapseComponents, 50);

            // Update map size if we're switching to map tab
            if (this.id === 'pills-map-tab') {
                setTimeout(updateMapSize, 100);
            }
        });
    });

    // Update map size when map section is expanded/collapsed
    const mapContent = document.getElementById('mapContent');
    if (mapContent) {
        mapContent.addEventListener('shown.bs.collapse', function() {
            setTimeout(updateMapSize, 100);
        });

        mapContent.addEventListener('hidden.bs.collapse', function() {
            setTimeout(updateMapSize, 100);
        });
    }
});
