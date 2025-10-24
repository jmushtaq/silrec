from rest_framework import viewsets
from rest_framework.decorators import action
from django.db.models import Q
from .models import Proposal
from .serializers import ProposalDatatableSerializer

from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Q


class ProposalDatatableAPIView(APIView):
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

