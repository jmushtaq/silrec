class DatatableDashboard {
    constructor(element) {
        this.element = element;
        this.apiUrl = this.element.dataset.apiUrl;
        this.table = null;
        this.filters = {
            status: [],
            fromDate: '',
            toDate: '',
            search: ''
        };
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

        // Destroy existing DataTable if it exists
        if ($.fn.DataTable.isDataTable(table)) {
            $(table).DataTable().destroy();
        }

        this.table = $(table).DataTable({
            processing: true,
            serverSide: true,
            ajax: {
                url: this.apiUrl,
                type: 'GET',
                data: (d) => {
                    // Add custom filters to the request
                    return {
                        draw: d.draw,
                        start: d.start,
                        length: d.length,
                        search: d.search.value,
                        status: this.filters.status,
                        from_date: this.filters.fromDate,
                        to_date: this.filters.toDate
                    };
                }
            },
            columns: this.getColumns(),
            order: [[0, 'asc']],
            pageLength: 10,
            lengthMenu: [10, 25, 50, 100],
            dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>rt<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
            responsive: true,
            language: {
                processing: '<div class="spinner-border spinner-border-sm" role="status"></div> Processing...',
                emptyTable: 'No proposals found',
                zeroRecords: 'No matching proposals found',
                info: 'Showing _START_ to _END_ of _TOTAL_ proposals',
                infoEmpty: 'Showing 0 to 0 of 0 proposals',
                infoFiltered: '(filtered from _MAX_ total proposals)',
                search: '',
                searchPlaceholder: 'Search...',
                paginate: {
                    first: 'First',
                    last: 'Last',
                    next: 'Next',
                    previous: 'Previous'
                }
            }
        });
    }

    getColumns() {
        const columns = [];
        const headers = this.element.querySelectorAll('thead th');

        headers.forEach(header => {
            columns.push({
                data: header.getAttribute('data-data'),
                orderable: true,
                searchable: true,
                defaultContent: ''
            });
        });

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

        // Export Excel button
        const exportBtn = this.element.querySelector('#exportExcel');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => {
                this.exportToExcel();
            });
        }

        // Clear Filters button
        const clearFiltersBtn = this.element.querySelector('#clearFilters');
        if (clearFiltersBtn) {
            clearFiltersBtn.addEventListener('click', () => {
                this.clearFilters();
            });
        }

        // Status filter
        const statusFilter = this.element.querySelector('#statusFilter');
        if (statusFilter) {
            statusFilter.addEventListener('change', (e) => {
                this.filters.status = Array.from(e.target.selectedOptions).map(option => option.value);
                this.applyFilters();
            });
        }

        // From date filter
        const fromDateFilter = this.element.querySelector('#fromDateFilter');
        if (fromDateFilter) {
            fromDateFilter.addEventListener('change', (e) => {
                this.filters.fromDate = e.target.value;
                this.applyFilters();
            });
        }

        // To date filter
        const toDateFilter = this.element.querySelector('#toDateFilter');
        if (toDateFilter) {
            toDateFilter.addEventListener('change', (e) => {
                this.filters.toDate = e.target.value;
                this.applyFilters();
            });
        }

        // Search input
        const searchInput = this.element.querySelector('#searchInput');
        if (searchInput) {
            searchInput.addEventListener('keyup', (e) => {
                // Use debounce to avoid too many requests
                clearTimeout(this.searchTimeout);
                this.searchTimeout = setTimeout(() => {
                    this.filters.search = e.target.value;
                    this.applyFilters();
                }, 500);
            });
        }

        // Page length select
        const pageLengthSelect = this.element.querySelector('#pageLengthSelect');
        if (pageLengthSelect) {
            pageLengthSelect.addEventListener('change', (e) => {
                this.table.page.len(e.target.value).draw();
            });
        }
    }

    applyFilters() {
        console.log('Applying filters:', this.filters);
        this.table.ajax.reload();
    }

    clearFilters() {
        // Reset filter values
        this.filters = {
            status: [],
            fromDate: '',
            toDate: '',
            search: ''
        };

        // Reset UI elements
        const statusFilter = this.element.querySelector('#statusFilter');
        if (statusFilter) {
            statusFilter.selectedIndex = -1;
        }

        const fromDateFilter = this.element.querySelector('#fromDateFilter');
        if (fromDateFilter) {
            fromDateFilter.value = '';
        }

        const toDateFilter = this.element.querySelector('#toDateFilter');
        if (toDateFilter) {
            toDateFilter.value = '';
        }

        const searchInput = this.element.querySelector('#searchInput');
        if (searchInput) {
            searchInput.value = '';
        }

        // Reload table
        this.table.ajax.reload();
    }

    exportToExcel() {
        const params = new URLSearchParams({
            format: 'xlsx',
            search: this.filters.search,
            status: this.filters.status.join(','),
            from_date: this.filters.fromDate,
            to_date: this.filters.toDate
        });

        const exportUrl = `${this.apiUrl}?${params.toString()}`;
        window.open(exportUrl, '_blank');
    }

    destroy() {
        if (this.table) {
            this.table.destroy();
        }
    }
}

// Initialize all datatable dashboards
document.addEventListener('DOMContentLoaded', function() {
    if (typeof $ === 'undefined' || typeof $.fn.DataTable === 'undefined') {
        console.error('Required libraries not loaded');
        return;
    }

    document.querySelectorAll('.datatable-dashboard').forEach(dashboard => {
        new DatatableDashboard(dashboard);
    });
});
