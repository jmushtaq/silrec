from django.db.models import Q
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt

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

from datetime import datetime
import pandas as pd
import geopandas as gpd
import openpyxl

import os
import tempfile
import zipfile
import fiona
import json

class ProposalViewSet(mixins.ListModelMixin,
                     mixins.RetrieveModelMixin,
                     mixins.UpdateModelMixin,
                     viewsets.GenericViewSet):
    queryset = Proposal.objects.all()
    serializer_class = ProposalSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.select_related('proposal_type', 'previous_application', 'application_type')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

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


class ProposalUploadShapefileViewSet(viewsets.ModelViewSet):
    queryset = Proposal.objects.all()
    serializer_class = ProposalSerializer

    @action(detail=False, methods=['post'], url_path='upload_shapefile')
    def upload_shapefile(self, request):
        print("Upload shapefile endpoint called")
        print("User:", request.user)
        print("User authenticated:", request.user.is_authenticated)

        try:
            if 'shapefile' not in request.FILES:
                print("No shapefile in request.FILES")
                return Response({
                    'success': False,
                    'error': 'No shapefile provided'
                }, status=status.HTTP_400_BAD_REQUEST)

            shapefile_zip = request.FILES['shapefile']
            print(f"Received file: {shapefile_zip.name}, size: {shapefile_zip.size}")

            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract zip file
                zip_path = os.path.join(temp_dir, 'shapefile.zip')
                with open(zip_path, 'wb') as f:
                    for chunk in shapefile_zip.chunks():
                        f.write(chunk)

                # Extract contents
                extract_dir = os.path.join(temp_dir, 'extracted')
                os.makedirs(extract_dir)

                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)

                # Find .shp file
                shp_file = None
                for file in os.listdir(extract_dir):
                    if file.endswith('.shp'):
                        shp_file = os.path.join(extract_dir, file)
                        break

                if not shp_file:
                    return Response({
                        'success': False,
                        'error': 'No .shp file found in zip archive'
                    }, status=status.HTTP_400_BAD_REQUEST)

                print(f"Found shapefile: {shp_file}")

                # Convert to GeoJSON using GeoPandas
                import ipdb; ipdb.set_trace()
                geojson_data = self.shapefile_to_geojson(shp_file)
                print("GeoJSON conversion successful")

                return Response({
                    'success': True,
                    'message': 'Shapefile processed successfully',
                    'geojson_data': geojson_data
                })

        except Exception as e:
            print(f"Error in upload_shapefile: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return Response({
                'success': False,
                'error': f'Error processing shapefile: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def shapefile_to_geojson(self, shp_file_path):
        """Convert shapefile to GeoJSON in EPSG:4326 using GeoPandas"""
        try:
            # Read shapefile using GeoPandas
            gdf = gpd.read_file(shp_file_path)
            print(f"Original CRS: {gdf.crs}")
            print(f"Number of features: {len(gdf)}")
            print(f"Columns: {list(gdf.columns)}")

            # Reproject to EPSG:4326 if needed
            if gdf.crs and gdf.crs != 'EPSG:4326':
                print("Reprojecting to EPSG:4326")
                gdf = gdf.to_crs('EPSG:4326')

            # Convert to GeoJSON
            geojson_data = gdf.to_json()

            # Parse the JSON string to a Python dict for the response
            import json
            geojson_dict = json.loads(geojson_data)

            print(f"Successfully converted {len(gdf)} features to GeoJSON")
            return geojson_dict

        except Exception as e:
            print(f"Error in shapefile_to_geojson: {str(e)}")
            import traceback
            print(traceback.format_exc())
            raise Exception(f"Error converting shapefile to GeoJSON: {str(e)}")


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

