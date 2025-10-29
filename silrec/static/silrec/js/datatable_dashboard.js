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
        console.log('JM5: ' + JSON.stringify(this.getColumns()))

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
            const dataField = header.getAttribute('data-data');

            if (dataField === 'actions') {
                // Special handling for actions column
                columns.push({
                    data: dataField,
                    orderable: false,
                    searchable: false,
                    render: function(data, type, row) {
                        if (type === 'display') {
                            return DatatableDashboard.renderActionsColumn(row);
                        }
                        return data;
                    }
                });
            } else {
                columns.push({
                    data: dataField,
                    orderable: true,
                    searchable: true,
                    defaultContent: ''
                });
            }
        });

        return columns;
    }

    static renderActionsColumn(row) {
        // Check if user can process this proposal
        //console.log('JM3: ' + JSON.stringify(row))
        console.log('JM4: ' + JSON.stringify(row))
        const canProcess = row.can_assess || row.can_review;
        const isReadOnly = row.is_read_only;

        if (canProcess && !isReadOnly) {
            return `<div class="action-buttons">
                <a href="/proposals/view/${row.id}/" class="btn btn-warning btn-sm" title="Process Proposal">
                    <i class="fas fa-cog"></i> Process
                </a>
            </div>`;
        } else {
            // Show View button for all other cases
            return `<div class="action-buttons">
                <a href="/proposals/view/${row.id}/" class="btn btn-info btn-sm" title="View Proposal">
                    <i class="fas fa-eye"></i> View
                </a>
            </div>`;
        }
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

        // Export Excel form submission - sync hidden fields
        const exportForm = this.element.querySelector('#exportExcelForm');
        if (exportForm) {
            exportForm.addEventListener('submit', (e) => {
                this.syncExportForm();
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

        const clearFiltersBtn = this.element.querySelector('#clearFilters');
        console.log('Clear Filters button found:', clearFiltersBtn);

        if (clearFiltersBtn) {
            clearFiltersBtn.addEventListener('click', (e) => {
                console.log('Clear Filters button CLICKED!');
                e.preventDefault();
                this.clearFilters();
            });
        } else {
            console.error('Clear Filters button not found!');
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
        console.log('clearFilters called - current filters:', this.filters);

        // Reset filter values
        this.filters = {
            status: [],
            fromDate: '',
            toDate: '',
            search: ''
        };

        console.log('clearFilters - reset filters to:', this.filters);

        // Reset UI elements - Select2 requires special handling
        const statusFilter = $('#statusFilter');
        if (statusFilter.length && $.fn.select2) {
            console.log('Clearing Select2 status filter');
            statusFilter.val(null).trigger('change.select2');
        }

        // Reset form inputs
        const fromDateFilter = this.element.querySelector('#fromDateFilter');
        if (fromDateFilter) {
            console.log('Clearing fromDateFilter, current value:', fromDateFilter.value);
            fromDateFilter.value = '';
        }

        const toDateFilter = this.element.querySelector('#toDateFilter');
        if (toDateFilter) {
            console.log('Clearing toDateFilter, current value:', toDateFilter.value);
            toDateFilter.value = '';
        }

        const searchInput = this.element.querySelector('#searchInput');
        if (searchInput) {
            console.log('Clearing searchInput, current value:', searchInput.value);
            searchInput.value = '';
        }

        // Also clear the export form hidden fields
        this.syncExportForm();

        console.log('clearFilters - reloading table with filters:', this.filters);

        // Reload table
        this.table.ajax.reload();
    }

    syncExportForm() {
        // Sync current filter values to the export form hidden fields
        const exportSearch = this.element.querySelector('#exportSearch');
        const exportStatus = this.element.querySelector('#exportStatus');
        const exportFromDate = this.element.querySelector('#exportFromDate');
        const exportToDate = this.element.querySelector('#exportToDate');

        if (exportSearch) exportSearch.value = this.filters.search || '';
        if (exportStatus) exportStatus.value = this.filters.status.join(',');
        if (exportFromDate) exportFromDate.value = this.filters.fromDate || '';
        if (exportToDate) exportToDate.value = this.filters.toDate || '';

        console.log('Syncing export form with filters:', this.filters);
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
