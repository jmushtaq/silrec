$(document).ready(function() {
    function initializeUniversalDataTable() {
        $('#debugTable').DataTable({
            processing: true,
            serverSide: true,
            ajax: {
                url: '/api/proposal-datatable/',
                type: 'GET',
                data: function(d) {
                    return {
                        draw: d.draw,
                        start: d.start,
                        length: d.length,
                        search: d.search.value
                    };
                },
                dataSrc: function(json) {
                    console.log('Raw JSON response:', json);

                    // Handle multiple possible response structures
                    if (json.data !== undefined) {
                        console.log('Using "data" array');
                        return json.data;
                    } else if (json.results !== undefined) {
                        console.log('Using "results" array');
                        return json.results;
                    } else if (Array.isArray(json)) {
                        console.log('Response is direct array');
                        return json;
                    } else {
                        console.error('Unknown response structure. Available keys:', Object.keys(json));
                        return [];
                    }
                }
            },
            columns: [
                { data: 'lodgement_number' },
                { data: 'title' },
                { data: 'proposal_type_name' },
                { data: 'lodgement_date_formatted' },
                { data: 'processing_status_display' }
            ]
        });
    }

    // Test API first, then initialize
    $.get('/api/proposal-datatable/', function(response) {
        console.log('API Response Structure Analysis:');
        console.log('- Type:', typeof response);
        console.log('- Keys:', Object.keys(response));
        console.log('- Has "data":', response.data !== undefined);
        console.log('- Has "results":', response.results !== undefined);
        console.log('- Is array:', Array.isArray(response));
        console.log('- Full response:', response);

        initializeUniversalDataTable();
    });
});
