class DatatableDashboard {
    constructor(element) {
        this.element = element;
        this.apiUrl = this.element.dataset.apiUrl;
        this.table = null;
        this.init();
    }

    init() {
        try {
            this.initializeTable();
            this.bindEvents();
            console.log('DataTable dashboard initialized successfully');
        } catch (error) {
            console.error('Error initializing DataTable:', error);
        }
    }

    initializeTable() {
        const table = this.element.querySelector('table');

        // Ensure table has an ID
        if (!table.id) {
            table.id = 'datatable-' + Math.random().toString(36).substr(2, 9);
        }

        // Destroy existing DataTable if it exists
        if ($.fn.DataTable.isDataTable(table)) {
            $(table).DataTable().destroy();
            $(table).empty();
        }

        this.table = $(table).DataTable({
            processing: true,
            serverSide: true,
            ajax: {
                url: this.apiUrl,
                type: 'GET',
                data: function(d) {
                    return {
                        draw: d.draw,
                        start: d.start,
                        length: d.length,
                        search: d.search.value
                    };
                },
                error: function(xhr, error, thrown) {
                    console.error('DataTables AJAX error:', error, thrown);
                }
            },
            columns: this.getColumns(),
            order: [[0, 'asc']],
            pageLength: 10,
            responsive: true,
            language: {
                processing: 'Processing...',
                emptyTable: 'No data available',
                zeroRecords: 'No matching records found'
            }
        });
    }

    getColumns() {
        const columns = [];
        const headers = this.element.querySelectorAll('thead th');

        headers.forEach(header => {
            const field = header.getAttribute('data-data');
            if (!field) {
                console.warn('Table header missing data-data attribute:', header);
            }
            columns.push({
                data: field,
                orderable: true,
                searchable: true,
                defaultContent: '' // Handle null values
            });
        });

        console.log('Configured columns:', columns);
        return columns;
    }

    bindEvents() {
        // Refresh button
        const refreshBtn = this.element.querySelector('#refreshTable');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.table.ajax.reload();
            });
        }

        // Export button
        const exportBtn = this.element.querySelector('#exportExcel');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => {
                this.exportToExcel();
            });
        }
    }

    exportToExcel() {
        const searchTerm = this.table.search();
        const exportUrl = `${this.apiUrl}?format=xlsx&search=${encodeURIComponent(searchTerm)}`;
        window.open(exportUrl, '_blank');
    }
}

// Initialize with safety checks
document.addEventListener('DOMContentLoaded', function() {
    if (typeof $ === 'undefined') {
        console.error('jQuery not loaded');
        return;
    }
    if (typeof $.fn.DataTable === 'undefined') {
        console.error('DataTables not loaded');
        return;
    }

    document.querySelectorAll('.datatable-dashboard').forEach(dashboard => {
        new DatatableDashboard(dashboard);
    });
});
