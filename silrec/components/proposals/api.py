from rest_framework import viewsets
from rest_framework.decorators import action
from django.db.models import Q
from .models import Proposal
from .serializers import ProposalDatatableSerializer

from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Q


class _ProposalDatatableAPIView(APIView):
    def get(self, request):
        # Extract DataTables parameters
        draw = request.GET.get('draw', 1)
        start = int(request.GET.get('start', 0))
        length = int(request.GET.get('length', 10))
        search_value = request.GET.get('search', '')
        print(f'search value: {search_value}' )

        queryset = Proposal.objects.select_related('proposal_type').all()
        total_records = queryset.count()
        if search_value:
            queryset = queryset.filter(
                Q(lodgement_number__icontains=search_value) |
                Q(title__icontains=search_value) |
                Q(proposal_type__description__icontains=search_value) |
                Q(processing_status__icontains=search_value)
            )

        filtered_records = queryset.count()
        queryset = queryset[start:start + length]
        serializer = ProposalDatatableSerializer(queryset, many=True)

        # Return DataTables-compatible response
        return Response({
            'draw': int(draw),
            'recordsTotal': total_records,
            'recordsFiltered': filtered_records,
            'data': serializer.data
        })

from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Q
from datetime import datetime

class ProposalDatatableAPIView(APIView):
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

