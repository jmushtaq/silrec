from django.conf import settings
from django.db import models, transaction, IntegrityError
from django.contrib.auth import get_user_model
from django.utils import timezone

import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from shapely.ops import unary_union, polygonize

import json
import os
from confy import database
from copy import deepcopy

import reversion

from silrec.utils.plot_utils import plot_gdf as plot
from silrec.utils.plot_utils import plot_overlay, plot_multi
from silrec.utils.plot_canvas import create_tabbed_charts
from silrec.utils.sliver_merge import find_and_merge
from silrec.utils.sliver_test1 import identify_slivers

from silrec.utils.write_polygons_to_db import write_polygons_to_db
from silrec.utils.write_cohort_to_db import write_cohort_to_db, save_cht_new_to_db

from silrec.components.forest_blocks.models import Polygon, Cohort, AssignChtToPly
from silrec.components.proposals.models import Proposal
from silrec.utils.create_audit_log import RequestMetrics, AuditLogger

import logging
logger = logging.getLogger(__name__)

User = get_user_model()

class ShapefileSliversMerger():
    '''
    '''
    def __init__(self, proposal_id, gdf_shpfile=None, threshold=None, user_id=None):
        self.proposal_id = proposal_id
        self.gdf_shpfile = self.get_shapefile(gdf_shpfile)
        self.threshold = threshold
        self.user_id = user_id
        # Removed SQLAlchemy engine

    def get_shapefile(self, gdf_shpfile):
        if gdf_shpfile is None:
            try:
                p = Proposal.objects.get(id=self.proposal_id)
                if p.geojson_shpfile_to_gdf is not None:
                    return p.geojson_shpfile_to_gdf.to_crs(settings.CRS_GDA94)
                raise Exception(f'There is no Shapefile associated with this Proposal {self.proposal_id}')
            except Proposal.DoesNotExist as pe:
                raise Proposal.DoesNotExist(f'{pe}. Proposal ID {self.proposal_id}')
            except Exception as e:
                raise Exception(f'{e}')

        return gdf_shpfile

    @staticmethod
    def get_polygons_gdf(gdf, table_name, proposal_id, sql=None):
        ''' Get intersecting polygons from forest_blocks.polygon - intersecting with the given base polygon
            Using Django ORM instead of SQLAlchemy

            Returns --> SQL query result as gdf
        '''

        # Build the base polygon WKT for spatial query
        srid = 'SRID=' + settings.CRS_GDA94.split(':')[1] + '; '  # SRID=28350;
        combined_geometry = unary_union(gdf['geometry'])
        base_polygon_wkt = srid + combined_geometry.wkt

        # Use Django ORM with raw SQL for spatial operations
        from django.db import connection

        # Fix column names - use actual database column names
        sql = f'''SELECT
                ph.polygon_id,
                ph.name,
                ph.area_ha,
                ph.compartment as compartment,
                ph.sp_code as sp_code,
                ST_AsText(ph.geom) as geom_wkt
            FROM polygon AS ph
            WHERE ph.zclosed IS NULL
            AND (
                ST_Overlaps(ph.geom, ST_GeomFromEWKT('{base_polygon_wkt}'))
                OR ST_Contains(ph.geom, ST_GeomFromEWKT('{base_polygon_wkt}'))
                OR ST_Within(ph.geom, ST_GeomFromEWKT('{base_polygon_wkt}'))
                OR ST_Crosses(ph.geom, ST_GeomFromEWKT('{base_polygon_wkt}'))
            );'''

        with connection.cursor() as cursor:
            cursor.execute(sql)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()

        # Convert to DataFrame
        df = pd.DataFrame(rows, columns=columns)

        if df.empty:
            return gpd.GeoDataFrame()

        # Convert WKT to Shapely geometries
        from shapely import wkt
        df['geometry'] = df['geom_wkt'].apply(wkt.loads)
        df.drop('geom_wkt', axis=1, inplace=True)

        gdf_result = gpd.GeoDataFrame(df, geometry='geometry')
        gdf_result['polygon_id'] = pd.to_numeric(gdf_result['polygon_id'], errors='coerce').astype(int)

        gdf_result['poly_type'] = 'HIST'
        gdf_result['iter_seq'] = 1
        gdf_result['proposal_id'] = proposal_id
        gdf_result.set_crs(settings.CRS_GDA94, inplace=True)

        return gdf_result.explode()

    def get_base_polygon_gdf(self, gdf_base, gdf_common_boundary):
        ''' returns the equiv. of gdf_single, but the one after
            historical polygon intersection and subsequent splitting
            to form new polygons

            --> Returns the 'new split' base polygon
        '''
        centroids_gdf1 = gdf_base.geometry.representative_point()
        centroids_df = gpd.GeoDataFrame(geometry=centroids_gdf1)

        if 'index_right' in gdf_common_boundary.columns:
            gdf_common_boundary.drop(['index_right'], axis=1, inplace=True)

        gdf = gpd.sjoin(gdf_common_boundary, centroids_df, how="inner", predicate="intersects")
        gdf['poly_type'] = 'BASE'
        gdf['polygon_id'] = gdf['polygon_id'] if 'polygon_id' in gdf.columns else 0
        gdf['proposal_id'] = self.proposal_id

        return gdf.iloc[[0]]

    def merge_touching(self, gdf, buffer_distance=0.0001):
        '''
        Use small buffer to ensure boundaries connect properly,
        then merge and remove buffer

        merged_gdf = merge_touching(gdf)
        '''
        # Apply small buffer to ensure connections
        buffered = gdf.geometry.buffer(buffer_distance)

        # Merge buffered geometries
        merged_buffered = unary_union(buffered)

        # Remove the buffer
        merged_clean = merged_buffered.buffer(-buffer_distance)

        return gpd.GeoDataFrame([1], geometry=[merged_clean], crs=gdf.crs)

    def create_gdf(self, savepoint_callback=None):
        '''
        Main processing method that creates the merged GeoDataFrames
        '''
        idx_count = 0
        gdf_shpfile = self.gdf_shpfile.copy()
        list_state = []

        # SET Init history and Shapefile to list_state
        gdf_hist = self.get_polygons_gdf(self.gdf_shpfile, 'polygon', self.proposal_id)
        polygon_ids_hist = gdf_hist.polygon_id.to_list() if not gdf_hist.empty else []

        if polygon_ids_hist:
            assignments = AssignChtToPly.objects.filter(polygon_id__in=polygon_ids_hist).values('cohort_id', 'cht2ply_id')
            cohort_ids_hist = [a['cohort_id'] for a in assignments]
            cht2ply_ids_hist = [a['cht2ply_id'] for a in assignments]

        # initialise store
        list_state.append({
            "gdf_hist".upper(): gdf_hist.copy(),
            "gdf_shp".upper(): self.gdf_shpfile.copy(),
        })

        proposal = Proposal.objects.get(id=self.proposal_id)
        user = User.objects.get(id=self.user_id)
        self.request_metrics = RequestMetrics.objects.create(proposal=proposal, user=user)

        # Process each polygon in the shapefile
        for index, row in self.gdf_shpfile.iterrows():
            idx_count += 1
            print('****************************************************************************************')
            print(f'                                 Polygon {idx_count}')
            print('****************************************************************************************')

            try:
                # Start a transaction with reversion
                with transaction.atomic():
                    with reversion.create_revision() as revision:
                        # Create a single polygon GeoDataFrame
                        self.gdf_single = gpd.GeoDataFrame([row], geometry=[row.geometry], crs=settings.CRS_GDA94)
                        self.gdf_single = self.set_data(self.gdf_single, poly_type='BASE')

                        target_ba = float(self.gdf_single.iloc[0].target_ba_) if 'target_ba_' in self.gdf_single.columns else 0
                        obj_code = self.gdf_single.iloc[0].obj_code if 'obj_code' in self.gdf_single.columns else ''
                        op_id = 1
                        year = 2024
                        regen_method = ' %'  # non-null FK req'd

                        # Create cohort and pass revision
                        cohort_id = write_cohort_to_db(
                            obj_code, op_id, year, target_ba, regen_method,
                            self.request_metrics, idx_count, revision
                        )

                        # Get intersecting historical polygons
                        gdf_hist = self.get_polygons_gdf(self.gdf_single, 'polygon', self.proposal_id)

                        # Rename columns for consistency
                        if not gdf_hist.empty:
                            gdf_hist.set_geometry('geometry', inplace=True)
                            gdf_hist.set_crs(settings.CRS_GDA94, inplace=True)

                            # Process cookie cut
                            gdf_result = self.process_cookie_cut(gdf_hist)

                            # Assemble result with cohort data
                            gdf_result = self.assemble_gdf_result(gdf_result, gdf_hist, cohort_id, op_id, idx_count, revision)
                            gdf_result['poly_id_new'] = pd.to_numeric(gdf_result['poly_id_new'], errors='coerce').fillna(0).astype(int)

                            # Get initial cohort data
                            import ipdb; ipdb.set_trace()
                            gdf_cht_init, cohort_gdf_init = self.merge_cohort_data_init(gdf_result, gdf_hist)
                            if not gdf_cht_init.empty:
                                gdf_cht_init['polygon_id'] = pd.to_numeric(gdf_cht_init['polygon_id'], errors='coerce').fillna(0).astype(int)

                            # Get new cohort data
                            gdf_cht_new = self.merge_cohort_data_new(gdf_result, gdf_hist, cohort_gdf_init, cohort_id, op_id)

                            # Save new cohort assignments with revision
                            if not gdf_cht_new.empty:
                                save_cht_new_to_db(gdf_cht_new, self.request_metrics, idx_count, revision)

                            # Store state
                            list_state = self.set_gdf_store(idx_count, list_state, gdf_hist, gdf_result, gdf_cht_init, gdf_cht_new)
                        else:
                            logger.warning(f"No intersecting historical polygons found for polygon {idx_count}")

                        # Set reversion comment
                        reversion.set_comment(f'Shapefile processing iteration {idx_count} for proposal {self.proposal_id}')

            except Exception as e:
                # Something went wrong in this iteration
                logger.error(f"Error in iteration {idx_count}: {str(e)}")
                # Re-raise the exception to stop processing
                raise

        # Add combined gdf_result's to list_state
        if len(list_state) > 1:
            gdf_result_combined = self.get_gdf_result_combined(list_state)
            list_state[0].update({'GDF_RESULT_COMBINED': gdf_result_combined})

        return list_state

    def set_gdf_store(self, idx_count, list_state, gdf_hist, gdf_result, gdf_cht_init, gdf_cht_new):
        gdf_cht_init = gdf_cht_init.copy() if not gdf_cht_init.empty else gpd.GeoDataFrame()

        self.gdf_single['iter_seq'] = idx_count
        gdf_result['iter_seq'] = idx_count
        if not gdf_cht_init.empty:
            gdf_cht_init['iter_seq'] = idx_count
        if not gdf_cht_new.empty:
            gdf_cht_new['iter_seq'] = idx_count

        # add column identifying store type
        gdf_hist['state'] = "gdf_hist".upper()
        self.gdf_single['state'] = "gdf_single".upper()
        gdf_result['state'] = "gdf_result".upper()
        if not gdf_cht_init.empty:
            gdf_cht_init['state'] = "gdf_cht_init".upper()
        if not gdf_cht_new.empty:
            gdf_cht_new['state'] = "gdf_cht_new".upper()

        list_state.append({
            "gdf_hist".upper(): gdf_hist.copy(),
            "gdf_single".upper(): self.gdf_single.copy(),
            "gdf_result".upper(): gdf_result.copy(),
            "gdf_cht_init".upper(): gdf_cht_init.copy() if not gdf_cht_init.empty else gpd.GeoDataFrame(),
            "gdf_cht_new".upper(): gdf_cht_new.copy() if not gdf_cht_new.empty else gpd.GeoDataFrame(),
        })

        return list_state

    def process_cookie_cut(self, gdf_hist):
        '''
        Performs the (shapefile) polygon overlay onto historical (current) polygons and
        cookie-cut's the intersections. Then absorbs/merges the slivers for the
        given area/length threshold
        '''
        # Determine which geometries in polygons geodataframe (hist) intersect with any geometry in gdf_single
        # polygons_intersecting are a subset of geometries for gdf polygons that intersect/overlay the base gdf (gdf_single)
        intersects_mask_single = gdf_hist.geometry.intersects(self.gdf_shpfile.unary_union)
        gdf_polygons_intersecting_single = gdf_hist[intersects_mask_single]

        # non overlapping overlayed geometries (creates independent partitioned geometries)
        self.gdf_polygons_partitioned = gpd.overlay(self.gdf_single[['geometry']], gdf_polygons_intersecting_single, how='union', keep_geom_type=True)
        self.gdf_polygons_partitioned = self.gdf_polygons_partitioned[self.gdf_polygons_partitioned.area>1] # drop tiny areas (> 1 sqm)
        self.gdf_polygons_partitioned = self.gdf_polygons_partitioned.explode() # explode multipolys to indep polys
        self.gdf_polygons_partitioned = self.gdf_polygons_partitioned.explode() # explode multipolys to indep polys
        self.gdf_polygons_partitioned.reset_index(inplace=True)

        base_polygon = self.get_base_polygon_gdf(self.gdf_single, self.gdf_polygons_partitioned)[['geometry']]
        base_polygon['poly_type'] = 'BASE'

        # extract the land slivers
        self.threshold = self.threshold if self.threshold else settings.SLIVER_AREALENGTH_THRESHOLD
        gdf_slivers = identify_slivers(self.gdf_polygons_partitioned.explode(), base_polygon, sliver_threshold=self.threshold)
        gdf_slivers['poly_type'] = 'SLVR'
        mask = self.gdf_polygons_partitioned.explode().geometry.area/self.gdf_polygons_partitioned.explode().geometry.length < self.threshold
        gdf_excl_slivers = self.gdf_polygons_partitioned.explode()[~(mask)]
        gdf_slivers_plus_base = gpd.GeoDataFrame(pd.concat([gdf_slivers, base_polygon], ignore_index=True))

        # re-merge land slivers to base_polygon and create poly_type column
        gdf_excl_slivers_plus_base = gpd.overlay(self.gdf_polygons_partitioned, gdf_slivers_plus_base, how='difference', keep_geom_type=True)
        gdf_excl_slivers_plus_base['poly_type'] = 'HIST'
        gdf_slivers_merged = gdf_slivers_plus_base.dissolve()
        gdf_slivers_merged['poly_type'] = 'BASE'
        gdf_slivers_merged['polygon_id'] = 0
        gdf_slivers_merged['proposal_id'] = self.proposal_id

        # re-merge merged base_polygon with remaining cookie-cut and hist polygons
        gdf_result = gpd.GeoDataFrame(pd.concat([gdf_excl_slivers_plus_base, gdf_slivers_merged], ignore_index=True))
        gdf_result = gdf_result[gdf_result.area>1] # drop tiny areas  (> 1 sqm)

        return gdf_result

    def get_gdf_result_combined(self, list_state):
        # Concatenate the two GeoDataFrames
        gdf_list = [d['GDF_RESULT'] for d in list_state[1:] if 'GDF_RESULT' in d and not d['GDF_RESULT'].empty]
        if not gdf_list:
            return gpd.GeoDataFrame()

        gdf_result_combined = pd.concat(gdf_list, ignore_index=True)

        # Sort by iter_seq descending so that the highest value comes first for each poly_id_new
        gdf_result_combined_sorted = gdf_result_combined.sort_values('iter_seq', ascending=False)

        # Drop duplicates based on poly_id_new, keeping the first (which has the max iter_seq)
        gdf_result_combined_deduplicated = gdf_result_combined_sorted.drop_duplicates(subset='poly_id_new', keep='first')

        return gdf_result_combined_deduplicated

    def set_proposal_data(self, list_state):
        '''
            Creates Data Structure for input to model Proposal
        '''
        geom_data = {}
        for i in range(1, len(list_state)): # ignore index 0 - base data
            gdf_hist = list_state[i]['GDF_HIST']
            gdf_single = list_state[i]['GDF_SINGLE']
            gdf_result = list_state[i]['GDF_RESULT']
            gdf_cht_init = list_state[i]['GDF_CHT_INIT']
            gdf_cht_new = list_state[i]['GDF_CHT_NEW']

            geojson = json.loads(gdf_result.to_crs(settings.CRS).to_json())
            geojson['cht_init'] = gdf_cht_init.to_json() if not gdf_cht_init.empty else None
            geojson['cht_new'] = gdf_cht_new.to_json() if not gdf_cht_new.empty else None

            geom_data.update({f'geometry_{i}': geojson})

        return geom_data

    def set_data(self, gdf, polygon_id=0, poly_type=None):
        gdf['proposal_id'] = self.proposal_id
        gdf['polygon_id'] = polygon_id if 'polygon_id' not in gdf else gdf['polygon_id'].fillna(polygon_id)
        if poly_type == 'SLVR':
            try:
                gdf['poly_type'] = gdf['poly_type'].fillna('SLVR')
            except:
                gdf['poly_type'] = 'SLVR'

        elif poly_type == 'BASE':
            gdf['poly_type'] = 'HIST'
            base_polygon = self.get_base_polygon_gdf(self.gdf_single, self.gdf_shpfile)
            if not base_polygon.empty:
                gdf.at[base_polygon.iloc[0].name, 'poly_type'] = 'BASE' # 'BASE'

        else:
            logger.error(f'poly_type {poly_type} not recognised')

        return gdf

    @property
    def gdf_result_filtered(self):
        iters = [int(item) for item in self.gdf_merge_store.iter_seq.unique() if not (isinstance(item, float) and np.isnan(item))]
        return self.gdf_merge_store[(self.gdf_merge_store.state=='GDF_RESULT_FILTERED') & (self.gdf_merge_store.iter_seq==max(iters))]

    def plot_canvas(self):
        '''
        import geopandas as gpd
        from silrec.utils.shapefile_silvers_merger3 import ShapefileSliversMerger

        gdf_shp = gpd.read_file('silrec/utils/Shapefiles/demarcation_16_polygons/Demarcation_Boundary_16_polygons.shp')
        gdf_shp.to_crs('EPSG:28350', inplace=True)
        ssm = ShapefileSliversMerger(gdf_shp, proposal_id=1)

        gdf_merge_store = ssm.create_gdf()
        ssm.plot_canvas()

        '''
        iters = [int(item) for item in self.gdf_merge_store.iter_seq.unique() if not (isinstance(item, float) and np.isnan(item))]
        iters.insert(0, 0)
        states = [item for item in self.gdf_merge_store.state.unique() if not (isinstance(item, float) and np.isnan(item))]

        gdf_iter_list = []
        chart_titles_list = []
        for it in iters[:3]:
            gdf_state_list = []
            chart_titles = []
            if it == 0:
                # Plot Summary on first Tab
                gdf_state_list.append(self.gdf_shpfile)
                gdf_state_list.append(self.gdf_hist_polygons_total)
                gdf_state_list.append(self.gdf_result_filtered)
                chart_titles.append(f'Shpfile: Polys {len(self.gdf_shpfile)}, Area_HA {round(self.gdf_shpfile.area.sum()/10000, 2)}')
                chart_titles.append(f'Hist: Polys {len(self.gdf_hist_polygons_total)}, Area_HA {round(self.gdf_hist_polygons_total.area.sum()/10000, 2)}')
                chart_titles.append(f'Result: Polys {len(self.gdf_result_filtered)}, Area_HA {round(self.gdf_result_filtered.area.sum()/10000, 2)}')

            else:
                for state in states:
                    gdf = self.gdf_merge_store[(self.gdf_merge_store.state==state) & (self.gdf_merge_store.iter_seq==it)]
                    gdf['colour'] = gdf['poly_type'].apply(lambda x: 'grey' if x=='BASE' else ('green' if x=='CUT' else ('yellow' if x=='SLVR' else 'BLUE')))
                    gdf_state_list.append(gdf)
                    chart_titles.append(f'{state} - Polygons {len(gdf)}, Area_HA {round(gdf.area.sum()/10000, 2)}')

            gdf_iter_list.append(gdf_state_list)
            chart_titles_list.append(chart_titles)

        create_tabbed_charts(*gdf_iter_list, chart_titles=chart_titles_list)

    def classify_polygons(self, gdf_result, gdf_single, tolerance=0.95):
        """
        Classify polygons in gdf_result based on their spatial relationship with gdf_single
        with area-based tolerance.
        i.e. set gdf_result.poly_type = 'BASE' or 'CUT', with area tolerance

        Parameters:
        gdf_result: GeoDataFrame with polygons to classify
        gdf_single: GeoDataFrame with reference polygon(s)
        tolerance: float (0-1), minimum proportion of area that must be inside gdf_single
                to be classified as 'BASE'. Default 0.95 (95%)

        Returns:
        GeoDataFrame with added 'poly_type' column
        """

        # Create a unified geometry from gdf_single for efficient spatial operations
        if len(gdf_single) > 0:
            hist_union = gdf_single.unary_union
        else:
            # If gdf_single is empty, all polygons are 'CUT'
            gdf_result = gdf_result.copy()
            gdf_result['poly_type'] = 'CUT'
            return gdf_result

        # Initialize the result column
        gdf_result = gdf_result.copy()
        poly_types = []

        for geom in gdf_result.geometry:
            if geom is None or geom.is_empty:
                poly_types.append('CUT')
                continue

            # Calculate the intersection area
            try:
                intersection = geom.intersection(hist_union)
                if intersection.is_empty:
                    # No intersection at all
                    area_ratio = 0.0
                else:
                    # Calculate ratio of intersection area to original area
                    area_ratio = intersection.area / geom.area

                # Classify based on area ratio
                if area_ratio >= tolerance:
                    poly_types.append('BASE')
                else:
                    poly_types.append('CUT')

            except Exception as e:
                # Handle any geometric operation errors
                print(f"Error processing geometry: {e}")
                poly_types.append('CUT')

        gdf_result['poly_type'] = poly_types
        gdf_result['area_ratio'] = [intersection.area / geom.area if geom and not geom.is_empty else 0.0
        for geom, intersection in zip(gdf_result.geometry,
            [g.intersection(hist_union) for g in gdf_result.geometry])]

        return gdf_result

    def add_cht_id_to_gdf_sql(self, gdf_result):
        ''' Query the DB table assign_cht_to_ply for ply_id's, cht_id's
        '''
        # Get polygon_ids
        polygon_ids = gdf_result['polygon_id'].tolist()

        # Query using Django ORM with proper error handling
        try:
            # Check if we're in a transaction and it's valid
            from django.db import connection
            if connection.in_atomic_block and not connection.needs_rollback:
                queryset = AssignChtToPly.objects.filter(
                    polygon_id__in=polygon_ids,
                    status_current=True
                ).values('polygon_id', 'cohort_id')

                # Create mapping dictionary
                cohort_mapping = {item['polygon_id']: item['cohort_id'] for item in queryset}

                # Apply to GeoDataFrame
                gdf_result['cht_id_cur'] = gdf_result['polygon_id'].map(cohort_mapping).fillna(1).astype(int)

        except Exception as e:
            logger.error(f"Unexpected error creating cohort record: {e}")
            gdf_result['cht_id_cur'] = 1

        return gdf_result

    def merge_cohort_data_init(self, gdf_result, gdf_hist):
        """
        Query DB for cohort data.
        Namely, from 'polygon - assign_cht_to_ply - cohort' triple and merge with gdf
        """

        cols = ['polygon_id', 'area_ha_orig', 'poly_type', 'cht_type', 'cht_id_cur', 'iter_seq', 'proposal_id']

        # Filter rows where polygon_id equals poly_id_new
        if 'poly_id_new' not in gdf_result.columns:
            return gpd.GeoDataFrame(), None

        mask = gdf_result['polygon_id'] == gdf_result['poly_id_new']
        gdf_cht_init = gdf_result[mask][cols].copy()

        if gdf_cht_init.empty:
            return gdf_result, None

        polygon_ids = gdf_hist.polygon_id.to_list() if not gdf_hist.empty else []
        polygon_ids = list(set(polygon_ids)) if polygon_ids else [0]

        cohort_ids = gdf_result.cht_id_cur.to_list() if 'cht_id_cur' in gdf_result.columns else []
        cohort_ids = list(set(cohort_ids)) if cohort_ids else [0]
        if len(cohort_ids) == 0:
            return gdf_cht_init, None

        # Use Django ORM to get cohort data
        try:
            # Get assignments with related cohort data
            assignments = AssignChtToPly.objects.filter(
                cohort_id__in=cohort_ids,
                status_current=True
            ).select_related('cohort').values(
                'polygon_id',
                'cht2ply_id',
                'cohort__cohort_id',
                'cohort__obj_code',
                'cohort__op_id',
                'cohort__complete_date',
                'cohort__target_ba_m2ha',
                'status_current'
            )

            # Also get polygon data
            polygons = Polygon.objects.filter(
                polygon_id__in=polygon_ids
            ).values(
                'polygon_id',
                'name',
                'area_ha',
                'compartment',
                'sp_code'
            )

            # Convert to DataFrames
            assignment_list = list(assignments)
            polygon_list = list(polygons)

            cohort_df = pd.DataFrame(assignment_list) if assignment_list else pd.DataFrame()
            polygon_df = pd.DataFrame(polygon_list) if polygon_list else pd.DataFrame()

            if not cohort_df.empty and not polygon_df.empty:
                # Rename columns for consistency
                cohort_df = cohort_df.rename(columns={
                    'cohort__cohort_id': 'cohort_id',
                    'cohort__obj_code': 'obj_code',
                    'cohort__op_id': 'op_id',
                    'cohort__complete_date': 'complete_date',
                    'cohort__target_ba_m2ha': 'target_ba_m2ha'
                })

                # Merge polygon data with cohort data
                cohort_gdf_init = polygon_df.merge(
                    cohort_df,
                    left_on='polygon_id',
                    right_on='polygon_id',
                    how='left'
                )

                # Merge with original GeoDataFrame
                gdf_cht_init = gdf_cht_init.merge(
                    cohort_gdf_init,
                    left_on='cht_id_cur',
                    right_on='cohort_id',
                    how='left'
                )
            else:
                cohort_gdf_init = pd.DataFrame()

        except Exception as e:
            logger.error(f'Error in merge_cohort_data_init: {e}')
            cohort_gdf_init = pd.DataFrame()

        # Clean up columns
        if not gdf_cht_init.empty:
            # Drop spurious columns created by merge
            for col in ['obj_code_x', 'obj_code_y', 'polygon_id_x', 'polygon_id_y']:
                if col in gdf_cht_init.columns:
                    gdf_cht_init = gdf_cht_init.drop(col, axis=1)

            if 'obj_code_y' in gdf_cht_init.columns and 'obj_code_x' in gdf_cht_init.columns:
                gdf_cht_init = gdf_cht_init.rename(columns={'obj_code_y': 'obj_code'})

            if 'polygon_id_y' in gdf_cht_init.columns and 'polygon_id_x' in gdf_cht_init.columns:
                gdf_cht_init = gdf_cht_init.rename(columns={'polygon_id_y': 'polygon_id'})

            # Strip blank spaces from obj_code
            if 'obj_code' in gdf_cht_init.columns:
                gdf_cht_init['obj_code'] = gdf_cht_init['obj_code'].astype(str).str.strip()

            cols_reqd = ['cohort_id', 'polygon_id', 'cht2ply_id', 'name', 'area_ha_orig', 'obj_code', 'complete_date', 'target_ba_m2ha', 'op_id', 'status_current']
            available_cols = [col for col in cols_reqd if col in gdf_cht_init.columns]

            if available_cols:
                gdf_cht_init = gdf_cht_init[available_cols]

                for col in ['cohort_id', 'polygon_id', 'cht2ply_id', 'op_id']:
                    if col in gdf_cht_init.columns:
                        gdf_cht_init[col] = pd.to_numeric(gdf_cht_init[col], errors='coerce').fillna(0).astype(int)

            import ipdb; ipdb.set_trace()
        return gdf_cht_init, cohort_gdf_init

    def merge_cohort_data_new(self, gdf_result, gdf_hist, cohort_gdf_init, cohort_ids, op_id):
        """
        Set the gdf.status_current = True/False and merge with gdf_cht_new
        """

        def merge_gdfs(gdf1, gdf2, cols):
            """
            Update NaN values in gdf1 (gdf_cht_combined) with values from gdf2 (cohort_gdf_init) based on cohort_id
            """
            if gdf1.empty or gdf2.empty:
                return gdf1

            # Create copies to avoid modifying originals
            gdf_result_local = gdf1.copy()
            gdf2_subset = gdf2[cols].copy()

            # Set cohort_id as index for both DataFrames
            if 'cohort_id' not in gdf_result_local.columns or 'cohort_id' not in gdf2_subset.columns:
                return gdf_result_local

            gdf_result_indexed = gdf_result_local.set_index('cohort_id')
            gdf2_indexed = gdf2_subset.set_index('cohort_id')

            # Drop duplicate indexes, keep last
            gdf2_indexed = gdf2_indexed[~gdf2_indexed.index.duplicated(keep='last')]

            # Update only NaN values (overwrite=False means only replace NaN/None values)
            gdf_result_indexed.update(gdf2_indexed, overwrite=False)

            # Reset index and return
            return gdf_result_indexed.reset_index()

        if not isinstance(cohort_ids, list):
            cohort_ids = [cohort_ids]

        cols1 = ['polygon_id', 'poly_id_new', 'area_ha', 'cht_id_new']
        cols2 = ['polygon_id', 'poly_id_new', 'area_ha', 'cht_id_cur']

        # Initialize gdf_cht_combined as empty DataFrame
        gdf_cht_combined = pd.DataFrame()

        # For assigning ASSIGN_CHT_TO_PLY - for the orig polygons assigned to ORIG cohort_id(s)
        if 'poly_type' in gdf_result.columns and 'cht_type' in gdf_result.columns:
            mask1 = (gdf_result.poly_type == 'CUT') & (gdf_result.cht_type == 'ORIG')
            if mask1.any() and all(col in gdf_result.columns for col in cols1):
                gdf_cht_orig_Y = gdf_result[mask1][cols1].copy()
                gdf_cht_orig_Y['status_current'] = True
                gdf_cht_orig_Y['desc'] = 'ORIG-CUT_Y'
                gdf_cht_orig_Y = gdf_cht_orig_Y.rename(columns={'cht_id_new': 'cohort_id'})
                gdf_cht_combined = pd.concat([gdf_cht_combined, gdf_cht_orig_Y], ignore_index=True)

            # For assigning ASSIGN_CHT_TO_PLY - for the new polygons assigned to NEW cohort_id(s)
            mask2 = (gdf_result.poly_type == 'BASE') & (gdf_result.cht_type == 'NEW')
            if mask2.any() and all(col in gdf_result.columns for col in cols1):
                gdf_cht_new_Y = gdf_result[mask2][cols1].copy()
                gdf_cht_new_Y['status_current'] = True
                gdf_cht_new_Y['desc'] = 'NEW-BASE_Y'
                gdf_cht_new_Y = gdf_cht_new_Y.rename(columns={'cht_id_new': 'cohort_id'})
                gdf_cht_combined = pd.concat([gdf_cht_combined, gdf_cht_new_Y], ignore_index=True)

            # For assigning ASSIGN_CHT_TO_PLY - for the new polygon id's assigned to OLD cohort_id(s)
            mask3 = (gdf_result.poly_type == 'BASE') & (gdf_result.cht_type == 'NEW')
            if mask3.any() and all(col in gdf_result.columns for col in cols2):
                gdf_cht_new_N = gdf_result[mask3][cols2].copy()
                gdf_cht_new_N['status_current'] = False
                gdf_cht_new_N['desc'] = 'NEW-BASE_N'
                gdf_cht_new_N = gdf_cht_new_N.rename(columns={'cht_id_cur': 'cohort_id'})
                gdf_cht_combined = pd.concat([gdf_cht_combined, gdf_cht_new_N], ignore_index=True)

            # For assigning ASSIGN_CHT_TO_PLY - for the new polygon id's assigned to OLD cohort_id(s), that are new 'CUT' (not 'BASE')
            mask4 = (gdf_result.poly_type == 'CUT') & (gdf_result.cht_type == 'NEW')
            if mask4.any() and all(col in gdf_result.columns for col in cols2):
                gdf_cht_new_Y_newcut = gdf_result[mask4][cols2].copy()
                gdf_cht_new_Y_newcut['status_current'] = True
                gdf_cht_new_Y_newcut['desc'] = 'NEW-CUT_Y'
                gdf_cht_new_Y_newcut = gdf_cht_new_Y_newcut.rename(columns={'cht_id_cur': 'cohort_id'})
                gdf_cht_combined = pd.concat([gdf_cht_combined, gdf_cht_new_Y_newcut], ignore_index=True)

        # update with data from cohort_get_init
        if not gdf_cht_combined.empty and cohort_gdf_init is not None and not cohort_gdf_init.empty:
            gdf_cht_combined = merge_gdfs(
                gdf_cht_combined,
                cohort_gdf_init,
                ['cohort_id']
            )

        return gdf_cht_combined

    def assemble_gdf_result(self, gdf_result, gdf_hist, cohort_id, op_id, iter_seq, revision=None):
        '''
            Assembles the final result with polygon and cohort data
        '''
        def get_base_polygon_field(row, col_name, gdf_hist):
            ''' for given cookie-cut polygon, returns the polygon_id of the parent (historical polygons gdf) polygon
                usage: gdf_tmp['polygon_id'] = gdf_tmp.apply(get_base_polygon_field, axis=1, args=('col_name',))
                --> Returns the parent polygon_id (intersected by the centroid - representative_point() falls inside the polygon)
            '''
            # Convert Centroid POINT to GDF
            centroid_point = row.geometry.representative_point()
            data = {'geometry': [centroid_point]}
            centroid_gdf = gpd.GeoDataFrame(data, geometry='geometry', crs=settings.CRS_GDA94)

            if 'index_right' in gdf_hist.columns:
                gdf_hist.drop(['index_right'], axis=1, inplace=True)

            gdf = gpd.sjoin(gdf_hist, centroid_gdf, how="inner", predicate="intersects")
            return None if gdf.empty else gdf[col_name].iloc[0]

        # identify and assign the src polygon from active hist polygon (silrec_v3)
        gdf_result['polygon_id'] = gdf_result.apply(get_base_polygon_field, axis=1, args=('polygon_id', gdf_hist))
        gdf_result['name'] = gdf_result.apply(get_base_polygon_field, axis=1, args=('name', gdf_hist))
        gdf_result['compartment'] = gdf_result.apply(get_base_polygon_field, axis=1, args=('compartment', gdf_hist))
        gdf_result['sp_code'] = gdf_result.apply(get_base_polygon_field, axis=1, args=('sp_code', gdf_hist))
        gdf_result['polygon_id'] = gdf_result['polygon_id'].fillna(0).astype(int)
        gdf_result['area_ha'] = gdf_result.area/10000
        gdf_result['proposal_id'] = self.proposal_id

        cols_to_drop = ['index', 'is_sliver', 'sliver_ratio', 'area', 'length', 'intersect_area', 'overlap_perc']
        for col in cols_to_drop:
            if col in gdf_result.columns:
                gdf_result.drop(columns=[col], inplace=True, errors='ignore')

        gdf_result = find_and_merge(gdf_result, self.threshold) # merge 'small' polygons with longest neighbour

        gdf_result = self.add_cht_id_to_gdf_sql(gdf_result)
        gdf_result = self.classify_polygons(gdf_result, self.gdf_single, tolerance=0.95)  # set poly_type 'CUT' or 'BASE'

        if 'index_right' in gdf_result.columns:
            gdf_result.drop('index_right', axis=1, inplace=True)

        gdf_result = gdf_result.explode()
        gdf_result.reset_index(inplace=True)

        # Write polygons to DB with revision
        operations_summary, gdf_result = write_polygons_to_db(
            gdf_result, self.request_metrics, iter_seq, revision
        )

        logger.info(f'\nCohort_id:  {cohort_id}')

        # Add new column cht_id_new
        gdf_result['cht_id_new'] = gdf_result['cht_id_cur'] if 'cht_id_cur' in gdf_result.columns else cohort_id
        if 'cht_id_cur' in gdf_result.columns:
            gdf_result.loc[gdf_result['poly_type'] == 'BASE', 'cht_id_new'] = cohort_id  # assign to new cohort

            # assign cohort id to new value for the additional duplicated/multiple polygon 'CUT's
            if 'polygon_id' in gdf_result.columns and 'poly_id_new' in gdf_result.columns:
                gdf_result.loc[
                    (gdf_result['poly_type'] == 'CUT') & (gdf_result['polygon_id'] != gdf_result['poly_id_new']),
                    'cht_id_new'
                ] = cohort_id

        # Add area_ha_orig column (from gdf_hist)
        if not gdf_hist.empty and 'polygon_id' in gdf_hist.columns and 'area_ha' in gdf_hist.columns:
            hist_areas = gdf_hist[['polygon_id', 'area_ha']].rename(columns={'area_ha': 'area_ha_orig', 'polygon_id': 'poly_id_new'})
            gdf_result = gdf_result.merge(
                hist_areas,
                on='poly_id_new',
                how='left',
            )

        # Add new column cht_type
        gdf_result['cht_type'] = 'NEW'  # initialize column
        if 'cht_id_cur' in gdf_result.columns and 'cht_id_new' in gdf_result.columns:
            gdf_result.loc[gdf_result['cht_id_cur'] == gdf_result['cht_id_new'], 'cht_type'] = 'ORIG'  # assign to new cohort

        return gdf_result

