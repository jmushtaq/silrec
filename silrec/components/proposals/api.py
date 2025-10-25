from django.db.models import Q
from django.http import HttpResponse
from datetime import datetime

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Proposal
from .serializers import ProposalSerializer #, ProposalDatatableSerializer


from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from datetime import datetime

import pandas as pd
import openpyxl


class ProposalViewSet(mixins.ListModelMixin,
                     mixins.RetrieveModelMixin,
                     mixins.UpdateModelMixin,
                     viewsets.GenericViewSet):
    queryset = Proposal.objects.all()
    serializer_class = ProposalSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.select_related('proposal_type', 'previous_application', 'application_type')

    @action(detail=False, methods=['get'])
    def status_choices(self, request):
        """Get unique processing status values for filter dropdown"""
        try:
            # Get unique processing status values from the database
            status_choices = Proposal.objects.values_list('processing_status', flat=True).distinct()

            # Filter out empty/null values and create choices list
            choices = [
                {'value': status, 'text': self.get_status_display(status)}
                for status in status_choices
                if status  # Filter out None/empty values
            ]

            # Sort alphabetically by text
            choices.sort(key=lambda x: x['text'])

            return Response(choices)

        except Exception as e:
            print(f"Status choices API error: {str(e)}")
            return Response([], status=500)

    def get_status_display(self, status_value):
        """Convert status value to display text"""
        # Use the model's get_processing_status_display method if available
        try:
            # Create a temporary instance to use the get_FOO_display method
            temp_instance = Proposal(processing_status=status_value)
            return temp_instance.get_processing_status_display()
        except:
            # Fallback: convert snake_case to Title Case
            return status_value.replace('_', ' ').title()

    @action(detail=False, methods=['get'])
    def datatable(self, request):
        """Special endpoint for DataTables with server-side processing"""
        try:
            # Extract DataTables parameters
            draw = int(request.GET.get('draw', 1))
            start = int(request.GET.get('start', 0))
            length = int(request.GET.get('length', 10))
            search_value = request.GET.get('search', '')

            # Extract custom filters
            status_filter = request.GET.getlist('status[]') or request.GET.get('status', '').split(',')
            from_date = request.GET.get('from_date', '')
            to_date = request.GET.get('to_date', '')

            print(f"Filters - Status: {status_filter}, From: {from_date}, To: {to_date}")

            # Get base queryset
            queryset = self.get_queryset().order_by('id')

            # Total records count
            total_records = queryset.count()

            # Apply search filter
            if search_value:
                queryset = queryset.filter(
                    Q(lodgement_number__icontains=search_value) |
                    Q(title__icontains=search_value) |
                    Q(proposal_type__description__icontains=search_value) |
                    Q(processing_status__icontains=search_value)
                )

            # Apply status filter
            if status_filter and status_filter != ['']:
                queryset = queryset.filter(processing_status__in=status_filter)

            # Apply date filters
            if from_date:
                from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
                queryset = queryset.filter(lodgement_date__gte=from_date_obj)

            if to_date:
                to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
                queryset = queryset.filter(lodgement_date__lte=to_date_obj)

            # Count after filtering
            filtered_records = queryset.count()

            # Apply pagination
            queryset = queryset[start:start + length]

            # Serialize data using the datatable serializer
            from .serializers import ProposalDatatableSerializer
            serializer = ProposalDatatableSerializer(queryset, many=True)
            data = serializer.data

            print(f"Returning {len(data)} records after filtering")

            # Return DataTables-compatible response
            response_data = {
                'draw': draw,
                'recordsTotal': total_records,
                'recordsFiltered': filtered_records,
                'data': data
            }

            return Response(response_data)

        except Exception as e:
            print(f"DataTable API Error: {str(e)}")
            return Response({
                'draw': 1,
                'recordsTotal': 0,
                'recordsFiltered': 0,
                'data': [],
                'error': str(e)
            }, status=500)

    @action(detail=False, methods=['get'])
    def export_excel(self, request):
        """Export proposals to Excel with filtering"""
        try:
            # Extract filter parameters - handle both formats
            search_value = request.GET.get('search', '')

            # Handle status filter - could be status[] array or comma-separated string
            status_filter = request.GET.getlist('status[]')
            if not status_filter:
                status_str = request.GET.get('status', '')
                status_filter = [s for s in status_str.split(',') if s]  # Split and remove empty

            from_date = request.GET.get('from_date', '')
            to_date = request.GET.get('to_date', '')

            print(f"Export filters - Search: '{search_value}', Status: {status_filter}, From: {from_date}, To: {to_date}")

            # Apply the same filters as the datatable
            queryset = self.get_queryset()

            if search_value:
                queryset = queryset.filter(
                    Q(lodgement_number__icontains=search_value) |
                    Q(title__icontains=search_value) |
                    Q(proposal_type__description__icontains=search_value) |
                    Q(processing_status__icontains=search_value)
                )

            if status_filter and status_filter != ['']:
                queryset = queryset.filter(processing_status__in=status_filter)

            if from_date:
                try:
                    from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
                    queryset = queryset.filter(lodgement_date__gte=from_date_obj)
                except ValueError:
                    print(f"Invalid from_date format: {from_date}")

            if to_date:
                try:
                    to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
                    queryset = queryset.filter(lodgement_date__lte=to_date_obj)
                except ValueError:
                    print(f"Invalid to_date format: {to_date}")

            print(f"Export query will return {queryset.count()} records")

            # Use pandas for Excel export
            try:
                import pandas as pd

                # Serialize data
                from .serializers import ProposalDatatableSerializer
                serializer = ProposalDatatableSerializer(queryset, many=True)
                data = serializer.data

                if not data:
                    return Response({'error': 'No data to export'}, status=404)

                # Convert to DataFrame
                df = pd.DataFrame(data)

                # Rename columns for better Excel headers
                column_mapping = {
                    'lodgement_number': 'Lodgement Number',
                    'title': 'Title',
                    'proposal_type_name': 'Proposal Type',
                    'lodgement_date_formatted': 'Lodgement Date',
                    'processing_status_display': 'Status'
                }
                df = df.rename(columns=column_mapping)

                # Create Excel response
                response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                response['Content-Disposition'] = 'attachment; filename="proposals_export.xlsx"'

                with pd.ExcelWriter(response, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Proposals', index=False)

                    # Auto-adjust column widths
                    worksheet = writer.sheets['Proposals']
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min((max_length + 2), 50)  # Cap at 50 characters
                        worksheet.column_dimensions[column_letter].width = adjusted_width

                return response

            except ImportError:
                # Fallback to CSV if pandas is not available
                return self.export_csv_fallback(queryset)

        except Exception as e:
            print(f"Excel export error: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({'error': f'Failed to generate Excel export: {str(e)}'}, status=500)

    def export_csv_fallback(self, queryset):
        """Fallback CSV export if pandas is not available"""
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="proposals_export.csv"'

        writer = csv.writer(response)
        # Write headers
        writer.writerow(['Lodgement Number', 'Title', 'Proposal Type', 'Lodgement Date', 'Status'])

        # Write data
        for proposal in queryset:
            writer.writerow([
                proposal.lodgement_number or '',
                proposal.title or '',
                proposal.proposal_type.name if proposal.proposal_type else '',
                proposal.lodgement_date.strftime('%Y-%m-%d %H:%M') if proposal.lodgement_date else '',
                proposal.get_processing_status_display()
            ])

        return response


class _ProposalDatatableAPIView(APIView):
    def get(self, request):
        try:
            # Extract DataTables parameters
            draw = int(request.GET.get('draw', 1))
            start = int(request.GET.get('start', 0))
            length = int(request.GET.get('length', 10))
            search_value = request.GET.get('search', '')

            # Extract custom filters
            status_filter = request.GET.getlist('status[]') or request.GET.get('status', '').split(',')
            from_date = request.GET.get('from_date', '')
            to_date = request.GET.get('to_date', '')

            print(f"Filters - Status: {status_filter}, From: {from_date}, To: {to_date}")

            # Get base queryset
            queryset = Proposal.objects.select_related('proposal_type').all().order_by('id')

            # Total records count
            total_records = queryset.count()

            # Apply search filter
            if search_value:
                queryset = queryset.filter(
                    Q(lodgement_number__icontains=search_value) |
                    Q(title__icontains=search_value) |
                    Q(proposal_type__description__icontains=search_value) |
                    Q(processing_status__icontains=search_value)
                )

            # Apply status filter
            if status_filter and status_filter != ['']:
                queryset = queryset.filter(processing_status__in=status_filter)

            # Apply date filters
            if from_date:
                from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
                queryset = queryset.filter(lodgement_date__gte=from_date_obj)

            if to_date:
                to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
                queryset = queryset.filter(lodgement_date__lte=to_date_obj)

            # Count after filtering
            filtered_records = queryset.count()

            # Apply pagination
            queryset = queryset[start:start + length]

            # Serialize data
            from .serializers import ProposalDatatableSerializer
            serializer = ProposalDatatableSerializer(queryset, many=True)
            data = serializer.data

            print(f"Returning {len(data)} records after filtering")

            # Return DataTables-compatible response
            response_data = {
                'draw': draw,
                'recordsTotal': total_records,
                'recordsFiltered': filtered_records,
                'data': data
            }

            return Response(response_data)

        except Exception as e:
            print(f"API Error: {str(e)}")
            return Response({
                'draw': 1,
                'recordsTotal': 0,
                'recordsFiltered': 0,
                'data': [],
                'error': str(e)
            }, status=500)

