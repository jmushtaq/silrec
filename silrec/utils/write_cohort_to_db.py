from django.db import IntegrityError, transaction
from silrec.components.forest_blocks.models import Cohort, AssignChtToPly
from silrec.utils.create_audit_log import AuditLogger

import pandas as pd
from datetime import datetime
from django.utils import timezone
from copy import deepcopy
import logging

logger = logging.getLogger(__name__)

def write_cohort_to_db(obj_code, op_id, year, target_ba, regen_method, request_metrics, iter_seq, revision=None):
    """
    Create a record in the cohort table for the USER PROVIDED SHAPEFILE polygons.

    Returns the cohort_id if the record exists or is created successfully,
    otherwise returns None.
    """
    try:
        op_date = datetime(year, 1, 1)
        target_ba_float = float(target_ba) if target_ba else 0.0

        # Use get_or_create to either fetch the existing record or create a new one.
        cohort_obj, created = Cohort.objects.get_or_create(
            obj_code=obj_code,
            op_id=op_id,
            op_date=op_date,
            target_ba_m2ha=target_ba_float,
            regen_method_id=regen_method,
            defaults={
                'created_by': request_metrics.user.username if request_metrics.user else None,
                'updated_by': request_metrics.user.username if request_metrics.user else None,
            }
        )

        # Add to revision if provided
        if revision and created:
            revision.add_to_revision(cohort_obj)

        if created:
            al = AuditLogger(Cohort, cohort_obj, 'INSERT', request_metrics, iter_seq, new_vals=cohort_obj).create()
            logger.info(f"Successful INSERT cohort record with ID: {cohort_obj.cohort_id}")
        else:
            logger.info(f"Successful RETRIEVE of cohort record with ID: {cohort_obj.cohort_id}")

        return cohort_obj.cohort_id

    except IntegrityError as e:
        # Handle any database integrity errors (e.g., duplicate key despite check)
        logger.error(f"Database integrity error creating cohort record: {e}")
        return None
    except Exception as e2:
        logger.error(f"Unexpected error creating cohort record: {e2}")
        return None


def save_cht_new_to_db(gdf_cht_new, request_metrics, iter_seq, revision=None):
    """
    Saves the gdf_cht_new to AssignChtToPly (assign_cht_to_ply) table with NA value handling
    """

    from silrec.components.forest_blocks.models import AssignChtToPly

    user_id = request_metrics.user.id if request_metrics.user else None
    if gdf_cht_new.empty:
        logger.info("No records found. Nothing to update (model AssignChtToPly).")
        return []

    # Prepare data for database
    if 'poly_id_new' not in gdf_cht_new.columns:
        logger.error("poly_id_new column not found in gdf_cht_new")
        return []

    db_data = gdf_cht_new[['poly_id_new','cohort_id','status_current']].copy()
    db_data = db_data.rename(columns={'poly_id_new': 'polygon_id'})

    # Ensure correct data types
    db_data['polygon_id'] = pd.to_numeric(db_data['polygon_id'], errors='coerce').fillna(0).astype(int)
    db_data['cohort_id'] = pd.to_numeric(db_data['cohort_id'], errors='coerce').fillna(0).astype(int)

    # Handle status_current
    db_data['status_current'] = db_data['status_current'].fillna(False)
    db_data['status_current'] = db_data['status_current'].astype(bool)

    cht2ply_ids = []
    current_time = timezone.now()
    success_count = 0
    error_count = 0

    try:
        with transaction.atomic():
            for index, row in db_data.iterrows():
                try:
                    # Convert all values to native Python types
                    polygon_id = int(row['polygon_id'])
                    cohort_id = int(row['cohort_id'])
                    status_current = bool(row['status_current'])

                    logger.info(f"Processing cohort_id {cohort_id}: polygon_id={polygon_id}, status_current={status_current}")

                    # Use update_or_create to handle both insert and update
                    obj, created = AssignChtToPly.objects.update_or_create(
                        cohort_id=cohort_id,
                        polygon_id=polygon_id,
                        defaults={
                            'status_current': status_current,
                            'updated_by': user_id
                        }
                    )

                    # Add to revision if provided
                    if revision:
                        revision.add_to_revision(obj)

                    if created:
                        obj.created_on = current_time
                        obj.created_by = user_id
                        obj_orig = None
                        action = "INSERT"
                    else:
                        action = "UPDATE"
                        obj_orig = obj

                    obj.updated_on = current_time
                    obj.updated_by = user_id
                    obj.save()

                    al = AuditLogger(
                        AssignChtToPly, obj, action, request_metrics, iter_seq,
                        old_vals=obj_orig, new_vals=obj
                    ).create()

                    cht2ply_ids.append([obj.cht2ply_id, obj.polygon_id, obj.cohort_id])
                    success_count += 1
                    logger.info(f"Successful {action} record for cohort_id {cohort_id} (cht2ply_id: {obj.cht2ply_id})")

                except Exception as e:
                    error_count += 1
                    logger.error(f"Error processing cohort_id {row['cohort_id']}: {str(e)}")
                    logger.error(f"Problematic row data: polygon_id={row['polygon_id']}, cohort_id={row['cohort_id']}, status_current={row['status_current']}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    continue

        logger.info(f"Successfully processed {success_count} records, {error_count} errors")
        return cht2ply_ids

    except IntegrityError as e:
        logger.error(f"Database integrity error creating cohort record: {e}")
        return None
    except Exception as e2:
        logger.error(f"Error saving data to PostgreSQL: {str(e2)}")
        raise

