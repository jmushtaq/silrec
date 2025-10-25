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

    async init() {
        try {
            await this.loadStatusOptions();
            this.initializeTable();
            this.bindEvents();
            console.log('DataTable dashboard initialized successfully');
        } catch (error) {
            console.error('Error initializing DataTable:', error);
        }
    }

    async loadStatusOptions() {
        try {
            // Use the new status_choices endpoint
            const response = await fetch('/api/proposals/status_choices/');
            if (!response.ok) {
                throw new Error('Failed to load status options');
            }

            const statusOptions = await response.json();
            const statusFilter = this.element.querySelector('#statusFilter');

            if (statusFilter && statusOptions.length > 0) {
                // Clear existing options
                statusFilter.innerHTML = '';

                // Add new options
                statusOptions.forEach(option => {
                    const optionElement = document.createElement('option');
                    optionElement.value = option.value;
                    optionElement.textContent = option.text;
                    statusFilter.appendChild(optionElement);
                });

                console.log('Loaded status options from API:', statusOptions);
            } else {
                console.warn('No status options found or status filter not found');
                this.loadDefaultStatusOptions();
            }
        } catch (error) {
            console.error('Error loading status options:', error);
            // Fallback to default options if API fails
            this.loadDefaultStatusOptions();
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

        // In initializeTable or bindEvents:
        $('#statusFilter').select2({
            placeholder: "Select statuses...",
            width: '100%'
        });

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

        // Reset UI elements - Select2 requires special handling
        const statusFilter = $('#statusFilter');
        if (statusFilter.length && $.fn.select2) {
            statusFilter.val(null).trigger('change.select2');
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
        try {
            // Construct the base URL for export
            let baseUrl = this.apiUrl.replace('/datatable/', '/export_excel/');

            // Build parameters object
            const params = {
                search: this.filters.search || '',
                from_date: this.filters.fromDate || '',
                to_date: this.filters.toDate || '',
            };

            // Add status as comma-separated string (alternative approach)
            if (this.filters.status && this.filters.status.length > 0) {
                params.status = this.filters.status.join(',');
            }

            // Build URL with parameters
            const queryString = Object.keys(params)
                .filter(key => params[key] !== '') // Remove empty params
                .map(key => `${encodeURIComponent(key)}=${encodeURIComponent(params[key])}`)
                .join('&');

            const exportUrl = queryString ? `${baseUrl}?${queryString}` : baseUrl;

            console.log('Exporting to:', exportUrl);

            // Direct download
            window.location.href = exportUrl;

        } catch (error) {
            console.error('Export error:', error);
            alert('Error generating Excel export: ' + error.message);
        }
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
