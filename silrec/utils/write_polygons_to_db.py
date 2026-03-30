from django.contrib.auth import get_user_model
import logging
import json
from datetime import datetime, date
from decimal import Decimal
from django.db import transaction, models, IntegrityError
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
from django.contrib.gis.geos import Polygon as GeosPolygon
from silrec.components.forest_blocks.models import Polygon
from silrec.utils.create_audit_log import RequestMetrics, AuditLogger
from copy import deepcopy
import pandas as pd

logger = logging.getLogger(__name__)

User = get_user_model()

def write_polygons_to_db(gdf_result, request_metrics, iter_seq, revision=None):
    """
    Write GeoDataFrame to polygon table using Django ORM.
    Handles repeated polygon_ids, prioritizes poly_type (CUT > BASE > others),
    and adds 'poly_id_new' column to the returned GeoDataFrame.

    Returns:
        tuple: (operations_summary, gdf_result_with_new_ids)
    """
    # Create a copy to add the new IDs
    gdf_result_with_ids = gdf_result.copy()
    gdf_result_with_ids['poly_id_new'] = None

    # Track operations
    ops_summary = {
        'new_records': 0,
        'updated_records': 0,
        'skipped_records': 0,
        'new_polygon_ids': [],
        'updated_polygon_ids': [],
        'priority_updates': []
    }

    # Sort by poly_type priority (CUT > BASE > others)
    gdf_sorted = _sort_gdf_by_polytype_priority(gdf_result_with_ids)

    # Build a map of polygon_id -> highest priority poly_type in the input
    poly_type_map = _create_poly_type_map(gdf_sorted)

    if 'polygon_id' in gdf_sorted.columns:
        gdf_sorted['polygon_id'] = pd.to_numeric(gdf_sorted['polygon_id'], errors='coerce').fillna(0).astype(int)

    for idx, row in gdf_sorted.iterrows():
        polygon_id = row['polygon_id'] if 'polygon_id' in row else 0
        poly_type = row.get('poly_type', 'OTHER')

        # Skip if polygon_id is invalid
        if pd.isna(polygon_id) or polygon_id == 0:
            ops_summary['skipped_records'] += 1
            logger.warning(f"Skipping record with invalid polygon_id: {polygon_id}")
            continue

        # Check if polygon_id already exists in the database
        existing_polygon = Polygon.objects.filter(polygon_id=polygon_id).first()

        if existing_polygon is None:
            # New polygon_id → insert
            ply = _insert_new_polygon(row, request_metrics, iter_seq)
            if ply:
                # Add to revision if provided
                if revision:
                    revision.add_to_revision(ply)

                ops_summary['new_records'] += 1
                ops_summary['new_polygon_ids'].append(polygon_id)
                gdf_result_with_ids.loc[idx, 'poly_id_new'] = polygon_id
                logger.info(f"Inserted new record with polygon_id: {polygon_id}, poly_type: {poly_type}")

        else:
            # Polygon_id already exists
            if _is_duplicate_in_gdf(gdf_sorted, polygon_id, idx):
                # This polygon_id appears multiple times in the input
                if _should_update_based_on_priority(poly_type_map, polygon_id, poly_type):
                    # Higher priority → update the existing record
                    ply = _update_existing_polygon(row, polygon_id, request_metrics, iter_seq)
                    if ply:
                        # Add to revision if provided
                        if revision:
                            revision.add_to_revision(ply)

                        ops_summary['updated_records'] += 1
                        ops_summary['updated_polygon_ids'].append(polygon_id)
                        ops_summary['priority_updates'].append(polygon_id)
                        gdf_result_with_ids.loc[idx, 'poly_id_new'] = polygon_id
                        logger.info(f"Priority update - Updated existing record with polygon_id: {polygon_id}, new poly_type: {poly_type}")
                else:
                    # Lower priority → create a new record with a new polygon_id
                    new_polygon_id = _get_next_polygon_id()
                    ply = _insert_duplicate_polygon(row, new_polygon_id, request_metrics, iter_seq)
                    if ply:
                        # Add to revision if provided
                        if revision:
                            revision.add_to_revision(ply)

                        ops_summary['new_records'] += 1
                        ops_summary['new_polygon_ids'].append(new_polygon_id)
                        gdf_result_with_ids.loc[idx, 'poly_id_new'] = new_polygon_id
                        logger.info(f"Created duplicate record: {polygon_id} -> {new_polygon_id}, poly_type: {poly_type}")
            else:
                # First occurrence of this polygon_id in the input → update
                ply = _update_existing_polygon(row, polygon_id, request_metrics, iter_seq)
                if ply:
                    # Add to revision if provided
                    if revision:
                        revision.add_to_revision(ply)

                    ops_summary['updated_records'] += 1
                    ops_summary['updated_polygon_ids'].append(polygon_id)
                    gdf_result_with_ids.loc[idx, 'poly_id_new'] = polygon_id
                    logger.info(f"Updated existing record with polygon_id: {polygon_id}, poly_type: {poly_type}")

    logger.info(f"Operation completed: {ops_summary}")
    return ops_summary, gdf_result_with_ids


# ------------------------------------------------------------------------------
# Priority sorting helpers (pandas logic, unchanged)
# ------------------------------------------------------------------------------

def _sort_gdf_by_polytype_priority(gdf):
    """Sort GeoDataFrame by poly_type priority: CUT > BASE > others."""
    if 'poly_type' not in gdf.columns:
        return gdf

    priority_order = {'CUT': 1, 'BASE': 2}
    gdf_sorted = gdf.copy()
    gdf_sorted['_priority'] = gdf_sorted['poly_type'].map(priority_order).fillna(3)
    gdf_sorted = gdf_sorted.sort_values(['_priority', 'polygon_id'])
    gdf_sorted = gdf_sorted.drop('_priority', axis=1)
    return gdf_sorted

def _create_poly_type_map(gdf):
    """Map each polygon_id to its highest priority poly_type in the input."""
    if 'poly_type' not in gdf.columns:
        return {}

    poly_type_map = {}
    priority_order = {'CUT': 1, 'BASE': 2}

    for _, row in gdf.iterrows():
        pid = row['polygon_id']
        ptype = row['poly_type']
        current_prio = priority_order.get(ptype, 3)

        if pid not in poly_type_map:
            poly_type_map[pid] = ptype
        else:
            existing_prio = priority_order.get(poly_type_map[pid], 3)
            if current_prio < existing_prio:
                poly_type_map[pid] = ptype

    return poly_type_map

def _should_update_based_on_priority(poly_type_map, polygon_id, new_poly_type):
    """Return True if new_poly_type has higher priority than what's already processed."""
    if polygon_id not in poly_type_map:
        return True

    priority_order = {'CUT': 1, 'BASE': 2}
    existing_priority = priority_order.get(poly_type_map[polygon_id], 3)
    new_priority = priority_order.get(new_poly_type, 3)
    return new_priority < existing_priority

def _is_duplicate_in_gdf(gdf, polygon_id, current_index):
    """Check if this polygon_id appears multiple times in the GeoDataFrame."""
    if 'polygon_id' not in gdf.columns:
        return False

    total_count = (gdf['polygon_id'] == polygon_id).sum()
    if total_count <= 1:
        return False

    first_idx = gdf[gdf['polygon_id'] == polygon_id].index[0]
    return current_index != first_idx

# ------------------------------------------------------------------------------
# Django ORM database helpers
# ------------------------------------------------------------------------------

def _insert_new_polygon(row, request_metrics, iter_seq):
    """Insert a new polygon record. Returns the created object."""
    if not hasattr(row['geometry'], 'wkt'):
        logger.error("Row has no WKT geometry")
        return None

    geom = GEOSGeometry(row['geometry'].wkt)
    proposal_id_row = row.get('proposal_id') if row.get('poly_type') == 'BASE' else None
    user_id = request_metrics.user.id if request_metrics.user else None

    # Prepare field values
    polygon_id = int(row['polygon_id']) if 'polygon_id' in row else None
    name = row['name'] if 'name' in row else None
    compartment_id = row['compartment'] if 'compartment' in row else None
    area_ha = row['area_ha'] if 'area_ha' in row else None
    sp_code = row['sp_code'] if 'sp_code' in row else None

    try:
        # Convert to MultiPolygon if it's a Polygon
        if isinstance(geom, GeosPolygon):
            geom = MultiPolygon(geom)

        ply = Polygon.objects.create(
            polygon_id=polygon_id,
            name=name,
            compartment_id=compartment_id,
            area_ha=area_ha,
            sp_code_id=sp_code,
            proposal_id=proposal_id_row,
            geom=geom,
            created_by=user_id,
            updated_by=user_id,
        )

        al = AuditLogger(Polygon, ply, 'INSERT', request_metrics, iter_seq, new_vals=ply).create()
        return ply

    except IntegrityError as e:
        logger.error(f"Database integrity error creating polygon record: {e}")
        return None
    except Exception as e2:
        logger.error(f"Error inserting polygon: {e2}")
        return None


def _insert_duplicate_polygon(row, new_polygon_id, request_metrics, iter_seq):
    """Insert a duplicate polygon with a new polygon_id. Returns the created object."""
    if not hasattr(row['geometry'], 'wkt'):
        logger.error("Row has no WKT geometry")
        return None

    geom = GEOSGeometry(row['geometry'].wkt)
    proposal_id_row = row.get('proposal_id') if row.get('poly_type') == 'BASE' else None
    user_id = request_metrics.user.id if request_metrics.user else None

    # Prepare field values
    name = row['name'] if 'name' in row else None
    compartment_id = row['compartment'] if 'compartment' in row else None
    area_ha = row['area_ha'] if 'area_ha' in row else None
    sp_code = row['sp_code'] if 'sp_code' in row else None

    try:
        # Convert to MultiPolygon if it's a Polygon
        if isinstance(geom, GeosPolygon):
            geom = MultiPolygon(geom)

        ply = Polygon.objects.create(
            polygon_id=int(new_polygon_id),
            name=name,
            compartment_id=compartment_id,
            area_ha=area_ha,
            sp_code_id=sp_code,
            proposal_id=proposal_id_row,
            geom=geom,
            created_by=user_id,
            updated_by=user_id,
        )

        al = AuditLogger(Polygon, ply, 'INSERT', request_metrics, iter_seq, new_vals=ply).create()
        return ply

    except IntegrityError as e:
        logger.error(f"Database integrity error creating duplicate polygon: {e}")
        return None
    except Exception as e2:
        logger.error(f"Error inserting duplicate polygon: {e2}")
        return None


def _update_existing_polygon(row, polygon_id, request_metrics, iter_seq):
    """
    Update an existing polygon record. Returns the updated object.
    """
    try:
        poly = Polygon.objects.get(polygon_id=int(polygon_id))
        poly_orig = deepcopy(poly)

        # Update fields if they exist in the row
        if 'name' in row:
            poly.name = row['name']
        if 'compartment' in row:
            poly.compartment_id = row['compartment']
        if 'area_ha' in row:
            poly.area_ha = row['area_ha']
        if 'sp_code' in row:
            poly.sp_code_id = row['sp_code']

        if hasattr(row['geometry'], 'wkt'):
            geom = GEOSGeometry(row['geometry'].wkt)
            # Convert to MultiPolygon if it's a Polygon
            if isinstance(geom, GeosPolygon):
                geom = MultiPolygon(geom)
            poly.geom = geom

        if request_metrics.user:
            poly.updated_by = request_metrics.user.id

        # Only set proposal_id if it's None and poly_type is BASE
        if poly.proposal_id is None and row.get('poly_type') == 'BASE' and request_metrics.proposal:
            poly.proposal_id = request_metrics.proposal.id

        poly.save()

        al = AuditLogger(Polygon, poly, 'UPDATE', request_metrics, iter_seq,
                        old_vals=poly_orig, new_vals=poly).create()

        return poly

    except IntegrityError as e:
        logger.error(f"Database integrity error updating polygon {polygon_id}: {e}")
        return None
    except Polygon.DoesNotExist:
        logger.error(f"Polygon with ID {polygon_id} not found")
        return None
    except Exception as e2:
        logger.error(f"Error updating polygon {polygon_id}: {e2}")
        return None

def _get_next_polygon_id():
    """Return the next available polygon_id (max existing + 1)."""
    max_id = Polygon.objects.aggregate(models.Max('polygon_id'))['polygon_id__max']
    return (int(max_id) or 0) + 1


def _prepare_for_json(obj):
    """Convert datetime/date/Decimal to JSON‑serializable types."""
    if isinstance(obj, dict):
        return {k: _prepare_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    else:
        return obj
