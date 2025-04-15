#from django.db import models
from django.contrib.gis.db import models
from django.contrib.gis.db.models import MultiPolygonField

from silrec.components.main.models import (
    CohortMetricsLkp,
    MachineLkp,
    ObjectiveLkp,
    OrganisationLkp,
    RegenerationMethodsLkp,
    RescheduleReasonsLkp,
    SpatialPrecisionLkp,
    SpeciesApiLkp,
    TaskLkp,
    TasksAttLkp,
    TreatmentStatusLkp,
)

# Create your models here.

class AssignCategoryToTask(models.Model):
    tsk2cat_id = models.AutoField(primary_key=True)
    task = models.ForeignKey(TaskLkp, on_delete=models.CASCADE, db_column='task', blank=True, null=True)
    tsk_cat = models.ForeignKey('TaskCategory', on_delete=models.CASCADE, blank=True, null=True)
    created_on = models.DateTimeField(blank=True, null=True)
    created_by = models.CharField(max_length=50, blank=True, null=True)
    updated_on = models.DateTimeField(blank=True, null=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = 'assign_category_to_task'


class AssignChtToPly(models.Model):
    cht2ply_id = models.AutoField(primary_key=True)
    polygon = models.ForeignKey('Polygon', on_delete=models.CASCADE)
    cohort = models.OneToOneField('Cohort', on_delete=models.CASCADE)
    op = models.ForeignKey('Operation', on_delete=models.CASCADE, blank=True, null=True, db_comment='New cohort may be created by other than an operation therefore COLUMN IS NULLABLE')
    cohort_closed = models.DateField(blank=True, null=True, db_comment='Cohort is closed when stand is overwritten by new operation or some other disturbance creating a new stand.\n\nPolygon/area MUST always have an open (not closed) or current cohort.')
    created_on = models.DateTimeField(blank=True, null=True)
    created_by = models.CharField(max_length=50, blank=True, null=True)
    updated_on = models.DateTimeField(blank=True, null=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = 'assign_cht_to_ply'
        db_table_comment = "As new operations or events create and subdivide polygons by creating new cohorts, cohorts apply to multiple polygons, as well as vice versa.\nSince a cohort may be closed for one polygon assignment, but open for another polygon assignment, the property of cohorts' closure is necessarily recorded in the assignment to the polygon.\nIt follows that cohort closure is most fully characterised as the date of the successive event and also a description of the nature of the cause of closure (e.g. fire, thin, ...).\nQuerying cohort closure may be part of investigations and analyses of relative frequency of types of closure events, or lifetime/return-time for different event types (e.g. thinning).\nThe property of closure relates primarily to the succeeding cohort, or the event creating the change.  Although this is often a new cohort, making the new cohort identification the closure attribute (e.g. foreign key to cohort) is inappropriate because:\n\n\t1. Complicates relationships with the assignment record already pointing to the preceding/current cohort.\n\t2. If there is a 'global' event (wildfire, polygon closure) wherein there is a universal cohort closure, and no immediate successive cohort for most assignments, it may be difficult to populate a key value.\n\nA date readily facilitates a query that will show a chronological cohort succession, but inter-row attribution and querying is difficult unless using an hierarchical query, but that query type requires a linking item.\nTherefore there are two choices to characterise cohort closure:\n\n\t1. a foreign key relationship to the succeeding cohort;\n\t2. a date and description of the nature of the event precipitating the closure of the cohort.  Likely the description is probably best implemented via a lookup table"


class AssignObjToReport(models.Model):
    obj2rpt_id = models.AutoField(primary_key=True, db_comment='primary key')
    obj_code = models.ForeignKey(ObjectiveLkp, on_delete=models.CASCADE, db_column='obj_code', blank=True, null=True, db_comment='FK to objective table')
    report = models.ForeignKey('ReportCohort', on_delete=models.CASCADE, blank=True, null=True, db_comment='FK to report table')
    report_group_label = models.CharField(max_length=50, blank=True, null=True, db_comment='label to be used for the cohort (or group) report')
    created_on = models.DateTimeField(blank=True, null=True)
    created_by = models.CharField(max_length=50, blank=True, null=True)
    updated_on = models.DateTimeField(blank=True, null=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)
    effective_from = models.DateTimeField(blank=True, null=True)
    effective_to = models.DateTimeField(blank=True, null=True)
    authorised_by = models.CharField(max_length=50, blank=True, null=True)
    revoked_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = 'assign_obj_to_report'
        db_table_comment = 'Table to assign cohorts to report and provide grouping labels\n\nCould create another related table for group labels-\n\nNeed created on/by, updated on/by, effective from/to, authorised/revoked by. Done (DW).Delete comment for PRD.'


class AssignTaskToReport(models.Model):
    tsk2rpt_id = models.AutoField(primary_key=True, db_comment='primary key')
    task = models.ForeignKey(TaskLkp, on_delete=models.CASCADE, db_column='task', blank=True, null=True, db_comment='FK to cohort table')
    tsk_rpt = models.ForeignKey('ReportTreatment', on_delete=models.CASCADE, blank=True, null=True, db_comment='FK to report table')
    report_group_label = models.CharField(max_length=50, blank=True, null=True, db_comment='label to be used for the cohort (or group) report')
    created_on = models.DateTimeField(blank=True, null=True)
    created_by = models.CharField(max_length=50, blank=True, null=True)
    updated_on = models.DateTimeField(blank=True, null=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)
    effective_from = models.DateTimeField(blank=True, null=True)
    effective_to = models.DateTimeField(blank=True, null=True)
    authorised_by = models.CharField(max_length=50, blank=True, null=True)
    revoked_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = 'assign_task_to_report'
        db_table_comment = 'Table to assign task to report and provide grouping labels'


class BaSweep(models.Model):
    ba_transect = models.ForeignKey('BaTransect', on_delete=models.CASCADE, blank=True, null=True)
    basal_area = models.IntegerField(blank=True, null=True)
    easting = models.FloatField(blank=True, null=True)
    northing = models.FloatField(blank=True, null=True)
    projection = models.CharField(max_length=50, blank=True, null=True)
    cell = models.ForeignKey('Cell', on_delete=models.CASCADE, blank=True, null=True)
    tree_count = models.IntegerField(blank=True, null=True)
    baf = models.IntegerField(blank=True, null=True)
    jarrah_count = models.IntegerField(blank=True, null=True)
    karri_count = models.IntegerField(blank=True, null=True)
    marri_count = models.IntegerField(blank=True, null=True)
    top_height = models.FloatField(blank=True, null=True)
    survey_organisation = models.CharField(max_length=10, blank=True, null=True)

    class Meta:
        db_table = 'ba_sweep'


class BaSweepTransfer(models.Model):
    basal_area = models.IntegerField(blank=True, null=True)
    easting = models.FloatField(blank=True, null=True)
    northing = models.FloatField(blank=True, null=True)
    projection = models.CharField(max_length=50, blank=True, null=True)
    operation = models.CharField(max_length=10, blank=True, null=True)
    fpc_survey_id = models.IntegerField(blank=True, null=True)
    cell_no = models.IntegerField(blank=True, null=True)
    tree_count = models.IntegerField(blank=True, null=True)
    baf = models.IntegerField(blank=True, null=True)
    jarrah_count = models.IntegerField(blank=True, null=True)
    karri_count = models.IntegerField(blank=True, null=True)
    marri_count = models.IntegerField(blank=True, null=True)
    top_height = models.FloatField(blank=True, null=True)
    survey_organisation = models.CharField(max_length=10, blank=True, null=True)

    class Meta:
        db_table = 'ba_sweep_transfer'
        db_table_comment = 'This files is for transfer of data from CSV files'


class BaSweepVersion(models.Model):
    ba_version_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, blank=True, null=True)
    deployed_on = models.DateTimeField(blank=True, null=True)
    author = models.CharField(max_length=50, blank=True, null=True)
    description = models.CharField(max_length=250, blank=True, null=True)

    class Meta:
        db_table = 'ba_sweep_version'


class BaTransect(models.Model):
    ba_transect_id = models.AutoField(primary_key=True)
    cell = models.ForeignKey('Cell', on_delete=models.CASCADE, blank=True, null=True)
    fpc_survey_id = models.IntegerField(blank=True, null=True)
    assessment_date = models.DateTimeField(blank=True, null=True)
    transect_no = models.IntegerField(blank=True, null=True)
    top_height = models.DecimalField(max_digits=5, decimal_places=1, blank=True, null=True)
    projection = models.CharField(max_length=50, blank=True, null=True)
    transect_start_east = models.FloatField(blank=True, null=True)
    transect_start_nth = models.FloatField(blank=True, null=True)
    transect_end_east = models.FloatField(blank=True, null=True)
    transect_end_nth = models.FloatField(blank=True, null=True)

    class Meta:
        db_table = 'ba_transect'


class BaTransectTransfer(models.Model):
    cell_no = models.IntegerField(blank=True, null=True)
    fpc_survey_id = models.IntegerField(blank=True, null=True)
    assessment_date = models.DateTimeField(blank=True, null=True)
    operation = models.CharField(max_length=10, blank=True, null=True)
    transect_no = models.IntegerField(blank=True, null=True)
    top_height = models.DecimalField(max_digits=5, decimal_places=1, blank=True, null=True)
    projection = models.CharField(max_length=50, blank=True, null=True)
    transect_start_east = models.FloatField(blank=True, null=True)
    transect_start_nth = models.FloatField(blank=True, null=True)
    transect_end_east = models.FloatField(blank=True, null=True)
    transect_end_nth = models.FloatField(blank=True, null=True)

    class Meta:
        db_table = 'ba_transect_transfer'
        db_table_comment = 'This files is for transfer of data from CSV files'


class Cell(models.Model):
    cell_id = models.AutoField(primary_key=True)
    cell_no = models.IntegerField()
    op = models.ForeignKey('Operation', on_delete=models.CASCADE)

    class Meta:
        db_table = 'cell'


class ClComp2024PolysClearedMga202050Pl(models.Model):
    gid = models.AutoField(primary_key=True)
    bbm_bio_di = models.CharField(db_column='bbm:bio-di', max_length=10, blank=True, null=True)  # Field renamed to remove unsuitable characters.
    bbm_teneme = models.CharField(db_column='bbm:teneme', max_length=10, blank=True, null=True)  # Field renamed to remove unsuitable characters.
    bbm_vegeta = models.CharField(db_column='bbm:vegeta', max_length=12, blank=True, null=True)  # Field renamed to remove unsuitable characters.
    colour = models.FloatField(blank=True, null=True)
    descriptio = models.CharField(max_length=80, blank=True, null=True)
    feature = models.CharField(max_length=10, blank=True, null=True)
    group = models.CharField(max_length=40, blank=True, null=True)
    layer = models.CharField(max_length=40, blank=True, null=True)
    linetype = models.FloatField(blank=True, null=True)
    objname = models.CharField(max_length=40, blank=True, null=True)
    pattern = models.FloatField(blank=True, null=True)
    transforme = models.CharField(max_length=88, blank=True, null=True)
    value = models.FloatField(blank=True, null=True)
    w = models.FloatField(blank=True, null=True)
    z = models.FloatField(blank=True, null=True)
    geom = MultiPolygonField(srid=28350, blank=True, null=True)

    class Meta:
        db_table = 'cl_comp_2024_polys_cleared_mga2020_50_pl'


class Cohort(models.Model):
    cohort_id = models.AutoField(primary_key=True)
    obj_code = models.CharField(max_length=20, db_comment='Silvicultural or management objective for the polygon')
    op_id = models.IntegerField(blank=True, null=True)
    op_date = models.DateTimeField(blank=True, null=True, db_comment='Date of creation of the operation boundary i.e. the date of photography, or other vector data capture method (GPS)')
    pct_area = models.IntegerField(blank=True, null=True, db_comment='Percentage of stand/patch area occupied by the cohort allocated to or represented by this silvicultural objective')
    year_last_cut = models.IntegerField(blank=True, null=True, db_comment='Year of last harvest of the cohort')
    treatments = models.BooleanField(blank=True, null=True, db_comment='yes if treatments have been inserted for this cohort')
    regen_date = models.DateTimeField(blank=True, null=True, db_comment='Date of majority regeneration')
    regen_date2 = models.DateTimeField(blank=True, null=True, db_comment='Date of secondary regeneration = the latest of any minority regeneration (e.g. infill planting)')
    species = models.CharField(max_length=3, blank=True, null=True, db_comment='Dominant overstorey API species of cohort; refer to lookup table\n\n**This is usually calculated by the regen values function following regeneration-creating treatments, and has been manually updated in other cases.  \nConsideration required for systematic update following thinning changing the species composition')
    regen_method = models.ForeignKey(RegenerationMethodsLkp, on_delete=models.CASCADE, db_column='regen_method', db_comment="Method of Regeneration, consistent with FMIS codes; refer to lookup table\nProbably should default to value ' /' for not regenerated  **NEED TO MONITOR FOR ISSUES'")
    regen_done = models.BooleanField(blank=True, null=True, db_comment='Yes if regeneration values  (date, species, method) have been calculated')
    complete_date = models.DateTimeField(blank=True, null=True, db_comment='Date of completion of all activities directly required and intended for the silvic objective in this COHORT.\nExclude from consideration tasks that are long term, aspirational, or have been explicitly written off.')
    resid_ba_m2ha = models.FloatField(blank=True, null=True, db_comment="Residual basal area of stand (average), m2/ha, including all overstorey trees following the implementation of all treatments entailed by the silvicultural objective.\n\nformerly 'ResidBA'")
    target_ba_m2ha = models.FloatField(blank=True, null=True)
    resid_spha = models.FloatField(blank=True, null=True, db_comment='Residual stocking of stand in stems per ha, averaged across stand, for all primary timber species.')
    target_spha = models.IntegerField(blank=True, null=True)
    site_quality = models.CharField(max_length=6, blank=True, null=True, db_comment='Mean cohort/polygon Site Quality class to 2 characters')
    herbicide_app_spec = models.CharField(max_length=50, blank=True, null=True, db_comment='Intended herbicide application specification')
    vrp = models.ForeignKey('VegRetPatch', on_delete=models.CASCADE, blank=True, null=True, db_comment='Number of vegetation retention patch')
    vrp_tot_area = models.FloatField(blank=True, null=True, db_comment='Vegetation retention patch total area (ha)')
    comments = models.CharField(max_length=250, blank=True, null=True, db_comment='Any comments relevant to the setting of the objective for the patch or the residual stand parameters')
    extra_info = models.BooleanField(blank=True, null=True, db_comment='Flag to show if additional attributes recorded or should be recorded in the cohort_xtra table')
    created_on = models.DateTimeField(blank=True, null=True, db_comment='Date the record was created')
    created_by = models.CharField(max_length=50, blank=True, null=True, db_comment='network user ID of person creating the record in the database')
    updated_on = models.DateTimeField(blank=True, null=True, db_comment='date record was last changed')
    updated_by = models.CharField(max_length=50, blank=True, null=True, db_comment='network user ID of person updating the record in the database')
    stand = models.CharField(max_length=10, blank=True, null=True)

    class Meta:
        db_table = 'cohort'
        db_table_comment = "A cohort is characterised primarily by a silvicultural or management objective for a polygon, usually relating to a component of the dominant vegetation on the polygon.  The cohort has attribution related to the vegetation and institution of the silvicultural objective (which is usually some event).\nThis usually entails a suite of follow-up activities to ensure objective is achieved.\nA cohort is 'complete' when all activities prescribed for the institution of the silvicultural objective have been implemented or will not be implemented (no outstanding prescribed activities).\nA cohort is closed when superseded by an event creating a new management regime for the cohort; e.g. a thinning, wildfire or new management paradigm.  Cohort closure is a property of the assignment of the cohort to a polygon since a successive event may not (and typically doesn't) coincide geographically with the preceding event that instituted the cohort. \nIt follows that a cohort has a life that starts with some event, usually some silvicultural operation, or fire or change in the management paradigm; becomes 'complete' when required works are judged to have achieved intentions to an acceptable tolerance; and is closed when superseded by some other event.\nIf the cohort not closed, then it is the current silvicultural objective, and cohort characteristics represent the stand."



class CohortResult(models.Model):
    cr_id = models.AutoField(primary_key=True, db_comment='Primary key for the table')
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, blank=True, null=True, db_comment='Foreign key to cohort table')
    metric = models.ForeignKey(CohortMetricsLkp, on_delete=models.CASCADE, blank=True, null=True, db_comment='Foreign key to the success measures table')
    quantity = models.FloatField(blank=True, null=True, db_comment='Polygon / cohort average quantity (e.g. average BA or average crown density or average LAI)')
    rating = models.CharField(max_length=50, blank=True, null=True, db_comment='Polygon / cohort average rating, e.g. density class, NDVI class')

    class Meta:
        db_table = 'cohort_result'
        db_table_comment = 'Table to record the post harvest/disturbance results or achievement of the operation or disturbance.\n\nArguably could use the cohort-xtra table, but anticipate potentially more than two quantity scores for post thinning assessment of achievement'


class CohortXtra(models.Model):
    cohort_extra_id = models.AutoField(primary_key=True)
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE)
    sub_type = models.CharField(max_length=25, blank=True, null=True)
    timeframe = models.IntegerField(blank=True, null=True)
    category1 = models.ForeignKey('ObjectiveCategory', on_delete=models.CASCADE, db_column='category1', blank=True, null=True, db_comment='Category 1 value as per category lookup table. Must be a value where target_column is "obj_cat.category1".')
    category2 = models.ForeignKey('ObjectiveCategory', on_delete=models.CASCADE, db_column='category2', related_name='cohortxtra_category2_set', blank=True, null=True, db_comment='Category 2 value as per category lookup table. Must be a value where target_column is "obj_cat.category2".')
    quantity1 = models.FloatField(blank=True, null=True, db_comment='quantity1 value as per objective lookup table')
    quantity2 = models.FloatField(blank=True, null=True, db_comment='quantity2 value as per objective lookup table')
    reference1 = models.CharField(max_length=50, blank=True, null=True, db_comment='reference1 value as per objective lookup table (free text entry)')
    reference2 = models.CharField(max_length=50, blank=True, null=True, db_comment='reference2 value as per objective lookup table (free text entry)')
    memo = models.TextField(blank=True, null=True, db_comment='Any detailed notes applicable')
    stream = models.BooleanField(blank=True, null=True, db_comment='If patch also qualifies as stream buffer')
    travel = models.BooleanField(blank=True, null=True, db_comment='If patch also qualifies as travel route buffer')
    silvic = models.CharField(max_length=20, blank=True, null=True)
    zpatch_id = models.CharField(max_length=10, blank=True, null=True, db_comment='Identifier for spatial patch\n\nrelegated in v3 structure')

    class Meta:
        db_table = 'cohort_xtra'
        db_table_comment = "cohort_xtra is for additional information to be recorded against individual cohorts, but the information isn't required for the majority of cohorts.\nThe structure provides an efficient means of a sparse population / attribution of items, rather than having a large 'flat table' with many rows having null values for columns.\n\nDelete comments below for PRD.\nDW>> Just for me, I need an explanation of the difference between cohorts and corhorts Xtra. (DW)\nDS> Cohorts extra table for additional information for specific objectives, but not required for all cohorts/objectives"


class CombinedSilrec2023(models.Model):
    gid = models.AutoField(primary_key=True)
    poly_id = models.CharField(max_length=254, blank=True, null=True)
    area = models.DecimalField(max_digits=100, decimal_places=16, blank=True, null=True)
    hectares = models.DecimalField(max_digits=100, decimal_places=16, blank=True, null=True)
    perimeter = models.DecimalField(max_digits=100, decimal_places=16, blank=True, null=True)
    x = models.DecimalField(max_digits=100, decimal_places=16, blank=True, null=True)
    y = models.DecimalField(max_digits=100, decimal_places=16, blank=True, null=True)
    uid = models.DecimalField(max_digits=100, decimal_places=16, blank=True, null=True)
    geom = MultiPolygonField(srid=28350, blank=True, null=True)

    class Meta:
        db_table = 'combined_silrec_2023'


class CombinedSilrec20232(models.Model):
    gid = models.AutoField(primary_key=True)
    poly_id = models.CharField(max_length=254, blank=True, null=True)
    area = models.DecimalField(max_digits=100, decimal_places=16, blank=True, null=True)
    hectares = models.DecimalField(max_digits=100, decimal_places=16, blank=True, null=True)
    perimeter = models.DecimalField(max_digits=100, decimal_places=16, blank=True, null=True)
    x = models.DecimalField(max_digits=100, decimal_places=16, blank=True, null=True)
    y = models.DecimalField(max_digits=100, decimal_places=16, blank=True, null=True)
    uid = models.DecimalField(max_digits=100, decimal_places=16, blank=True, null=True)
    geom = MultiPolygonField(srid=28350, blank=True, null=True)

    class Meta:
        db_table = 'combined_silrec_2023_2'


class Compartments(models.Model):
    compartment = models.CharField(primary_key=True, max_length=5)
    block = models.CharField(max_length=20, blank=True, null=True)
    district = models.CharField(max_length=10, blank=True, null=True)
    supply = models.CharField(max_length=15, blank=True, null=True)
    region = models.CharField(max_length=10, blank=True, null=True)
    geom = MultiPolygonField(srid=28350, blank=True, null=True)
    zmapinfo_id = models.IntegerField(db_column='zMapInfo_ID', blank=True, null=True, db_comment='Does this column need to be in compartment table?')  # Field name made lowercase.

    class Meta:
        db_table = 'compartments'
        db_table_comment = 'Use of supply area ???\n\nAttach geo-object for each compartment to\n\n\t1. Enable matching of compartment to operational polygon in cases where compartment misspelt or other typo\n\t2. Presentation of operational polygons in spatial context of compartment. Done (DW).'


class Duplicates(models.Model):
    name = models.CharField(max_length=10, blank=True, null=True)
    pcount = models.BigIntegerField(blank=True, null=True)

    class Meta:
        db_table = 'duplicates'


class FeaActiveFmp25Region(models.Model):
    gid = models.AutoField(primary_key=True)
    feaid = models.CharField(max_length=10, blank=True, null=True)
    area = models.FloatField(blank=True, null=True)
    nett_area = models.FloatField(blank=True, null=True)
    coyear_ori = models.CharField(max_length=4, blank=True, null=True)
    coyear_las = models.CharField(max_length=4, blank=True, null=True)
    costatus = models.CharField(max_length=20, blank=True, null=True)
    co_field = models.DecimalField(db_column='co_', max_digits=100, decimal_places=16, blank=True, null=True)  # Field renamed because it ended with '_'.
    region = models.CharField(max_length=20, blank=True, null=True)
    block = models.CharField(max_length=254, blank=True, null=True)
    compno = models.CharField(max_length=2, blank=True, null=True)
    block_cpt = models.CharField(max_length=50, blank=True, null=True)
    targetsilv = models.CharField(max_length=50, blank=True, null=True)
    cawsarea = models.BooleanField(blank=True, null=True)
    dra = models.BooleanField(blank=True, null=True)
    swalcarea = models.CharField(max_length=50, blank=True, null=True)
    feayear = models.FloatField(blank=True, null=True)
    id = models.FloatField(blank=True, null=True)
    geom = MultiPolygonField(srid=28350, blank=True, null=True)

    class Meta:
        db_table = 'fea_active_fmp25_region'



class ObjectiveCategory(models.Model):
    obj_cat_id = models.AutoField(primary_key=True)
    objective = models.CharField(max_length=50, blank=True, null=True)
    target_column = models.CharField(max_length=9, blank=True, null=True)
    category_value = models.CharField(max_length=25, blank=True, null=True)
    description = models.CharField(max_length=200, blank=True, null=True)
    fmis_code = models.CharField(max_length=2, blank=True, null=True)
    effective_from = models.DateField(blank=True, null=True)
    effective_to = models.DateField(blank=True, null=True)
    authorised_by = models.CharField(max_length=50, blank=True, null=True)
    authorised_on = models.DateField(blank=True, null=True)
    revoked_by = models.CharField(max_length=50, blank=True, null=True)
    revoked_on = models.DateField(blank=True, null=True)

    class Meta:
        db_table = 'objective_category'
        unique_together = (('objective', 'target_column', 'category_value'),)
        db_table_comment = 'Relates to former code1, code2 in cohort extra table of SILREC v2\n\nProvides the categorisation values (e.g. dropdown) to be used for category1, category2'


class ObjectiveSubtype(models.Model):
    type_id = models.AutoField(primary_key=True)
    silvic = models.CharField(max_length=20, blank=True, null=True, db_comment='Silvicultural Objective the sub-type applies to')
    subtype = models.CharField(unique=True, max_length=50, blank=True, null=True, db_comment='Name of the Sub type for the silvicultural objective')
    description = models.CharField(max_length=50, blank=True, null=True, db_comment='Brief description of the sub type')
    fmiscode = models.CharField(db_column='FMIScode', max_length=50, blank=True, null=True, db_comment='FMIS code for export to FMIS')  # Field name made lowercase.

    class Meta:
        db_table = 'objective_subtype'
        db_table_comment = "Lookup table for values and definitions for relevant silvicultural objectives\n\nThis table deprecated and contents incorporated to the cohort_xtra table because subtypes can be represented as categories applied to groups/subgroups of an objective.\n\nPlease explain why this detail  is not in the silvic_lkp table. (DW) Delete comment for PRD.\n\nDS> This table is for types of silvic objective especially those that may not be entered in some situations, e.g. different types of utility, different types of veg complex, etc.  Somewhat distinct from 'category 1/2' in that these have an official status related to the objective itself; nevertheless, could be subsumed into the category table structure."


class Operation(models.Model):
    op_id = models.AutoField(primary_key=True, db_comment='Unique identifier for each operation')
    das_id = models.IntegerField(blank=True, null=True, db_comment='Disturbance Approval System (DAS) identifier')
    fea_id = models.CharField(max_length=20, blank=True, null=True, db_comment='Unique identifier for the FEA / OPERATION as determined by the planner (Peter Murray).\n\nWith historical v2 data FEA ID will be Stands.OpCode')
    plan_release = models.CharField(max_length=50, blank=True, null=True, db_comment='identifier for the release package including the FEA')
    silvic_plan_map = models.BinaryField(blank=True, null=True, db_comment='Document (PDF) of a map of the silvics plan (FINAL VERSION)\n\nCorrect data type?\nStore simply as URL to SharePoint location')
    silvic_plan_doc = models.BinaryField(blank=True, null=True, db_comment='Silvic plan document (FINAL VERSION) providing the detailed silvicultural tactics to be applied in the operation, may be .DOCX or PDF file.\n\nStore simply as URL to SharePoint location')

    class Meta:
        db_table = 'operation'
        db_table_comment = "List of operations / coupes / FEA's.  Provides a link back to planning units for analysis and reporting.\nOne row per FEA, with a unique FEA ID; aspatial table (no geographic object/boundary); spatial location only acquire via direct/indirect link to polygon table.  \nPurpose of the table is to bundle/group polygons/cohorts from a single operation (FEA) with a single DAS proposal/approval.\n\nUndecided whether this relates to polygon table or cohort table (or treatment table).\nRelated to Silviculturist's comment and Cohort. Treatment and Task can be accessed via relationship to Cohort so that silviculturist can record a comment on Operation, Cohort, Treatment or Task.\nForm can be created so that it has drop downs for all the above attributes. i.e. drilling down to finest detail for comment. (DW) \n\nDelete comments below for PRD.\nPolygon table\n- Pros: Helps provide direct and explicit spatial boundary for the coupe for capturing all polygons within the FEA, helping ensure FEA fully mapped.\n- Cons: Polygons aren't stable over time, they may be subdivided in future operations; PLUS a polygon can be multiple coupes/FEA over time.\n\nCohort table\n- Pros: Provides direct and explicit link to cohorts created by the operation; cohort will be completed and closed as per the effects of the operation.\n- Cons: Less direct spatial boundary may create difficulties ensuring all areas within operation boundary fully described.\n\nPossibly should be independent spatial table?  But then may need to update records if operation boundary changed ...\n\nMy thought leans towards Cohort. A simply spatial overlay between polygon and the FEA annual plan after each annual upload of the plan will ensure all areas within the plan are covered. This assumes the upload is by each individual FEA.\nUNRESOLVED as to linking treatments to operations, but preferences leaning to no linkage.\nAs for areas within each operation/FEA boundary, I presume if they are not in a cohort then they are considered extrinsic. (DW)"



class Polygon(models.Model):
    polygon_id = models.AutoField(primary_key=True, db_comment='Primary key')
    name = models.CharField(max_length=10, blank=True, null=True, db_comment="Formerly 'PolyID'\nName of the polygon, usually descriptive of the administrative unit containing the polygon, e.g. code for forest block and compartment")
    compartment = models.ForeignKey(Compartments, on_delete=models.CASCADE, db_column='compartment', db_comment='foreign key to compartment and blocks table')
    area_ha = models.FloatField(blank=True, null=True, db_comment='Area in ha of the polygon, as measured on flat/2D plane\nTrigger to calculate & populate ON UPDATE, ON CREATE')
    sp_code = models.ForeignKey(SpatialPrecisionLkp, on_delete=models.CASCADE, db_column='sp_code', blank=True, null=True, db_comment='Code for spatial precision of mapping or capture method\nforeign key to lookup table')
    created_on = models.DateTimeField(blank=True, null=True, db_comment='Date/time of creation of the polygon in the SILREC database')
    created_by = models.CharField(max_length=50, blank=True, null=True, db_comment='user ID of person creating the polygon in the database')
    updated_on = models.DateTimeField(blank=True, null=True, db_comment='date patch area was last changed')
    updated_by = models.CharField(max_length=50, blank=True, null=True, db_comment='user ID of person updating the patch area in the database')
    closed = models.DateField(blank=True, null=True, db_comment='Date when polygon is closed for activity; further work assigned to new, overlaying polygon\n\nALL open polygons (i.e. NOT CLOSED) should not overlap, i.e. planar enforcement')
    reason_closed = models.CharField(max_length=250, blank=True, null=True, db_comment='Reason for closure of polygon, usually system related (data restructure), major perturbation resulting in destruction of multiple stands (e.g. wildfire), or new management regime (e.g. FMP24)')
    zcoupeid = models.CharField(db_column='zCoupeID', max_length=5, blank=True, null=True)  # Field name made lowercase.
    zstandno = models.CharField(db_column='zStandNo', max_length=5, blank=True, null=True)  # Field name made lowercase.
    zmslink = models.FloatField(db_column='zMSLink', blank=True, null=True)  # Field name made lowercase.
    zfea_id = models.CharField(max_length=7, blank=True, null=True, db_comment='Operation Code defining or causing creation of the patch.\nWas Opcode. Now referred to as FEA ID on plan (DW)')
    geom = MultiPolygonField(srid=28350, blank=True, null=True)

    class Meta:
        db_table = 'polygon'
        db_table_comment = "Geo-spatial object of non-zero area enclosing a portion of DBCA (or successor) estate.\n\nColumns in this table do and should only relate to the spatial occurrence of the polygon (DW).\nDelete comments below for PRD.\nArea column options\n1. Trigger to calculate and populate area of object when polygon created or updated.\n2. Drop the area column and recalculate area 'on the fly'\n\npreference for #1\n\nEasting and Northing have been dropped. (DW)\nPolygon_id was of type Long.  Changed to Integer. (DW)\nInteger is -32,768 to 32,768\nLong is -2,147,483,648 to 2,147,483,648\nQuestion if more than 32,768 polygons is likely?  (DW)"


class PolygonDa(models.Model):
    gid = models.AutoField(primary_key=True)
    polygon_id = models.FloatField(blank=True, null=True)
    name = models.CharField(max_length=10, blank=True, null=True)
    compartmen = models.CharField(max_length=5, blank=True, null=True)
    area_ha = models.DecimalField(max_digits=100, decimal_places=16, blank=True, null=True)
    sp_code = models.CharField(max_length=10, blank=True, null=True)
    created_on = models.CharField(max_length=29, blank=True, null=True)
    created_by = models.CharField(max_length=50, blank=True, null=True)
    updated_on = models.CharField(max_length=29, blank=True, null=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)
    closed = models.DateField(blank=True, null=True)
    reason_clo = models.CharField(max_length=250, blank=True, null=True)
    zcoupeid = models.CharField(max_length=5, blank=True, null=True)
    zstandno = models.CharField(max_length=5, blank=True, null=True)
    zmslink = models.DecimalField(max_digits=100, decimal_places=16, blank=True, null=True)
    zfea_id = models.CharField(max_length=7, blank=True, null=True)
    geom = MultiPolygonField(srid=28350, blank=True, null=True)

    class Meta:
        db_table = 'polygon_da'


class PolygonMiningUnion(models.Model):
    gid = models.AutoField(primary_key=True)
    cpt = models.CharField(max_length=10, blank=True, null=True)
    bbm_teneme = models.CharField(max_length=10, blank=True, null=True)
    bbm_vegeta = models.CharField(max_length=12, blank=True, null=True)
    colour = models.FloatField(blank=True, null=True)
    descriptio = models.CharField(max_length=80, blank=True, null=True)
    feature = models.CharField(max_length=10, blank=True, null=True)
    group = models.CharField(max_length=40, blank=True, null=True)
    layer = models.CharField(max_length=40, blank=True, null=True)
    linetype = models.FloatField(blank=True, null=True)
    objname = models.CharField(max_length=40, blank=True, null=True)
    pattern = models.FloatField(blank=True, null=True)
    transforme = models.CharField(max_length=88, blank=True, null=True)
    value = models.FloatField(blank=True, null=True)
    w = models.FloatField(blank=True, null=True)
    z = models.FloatField(blank=True, null=True)
    polygon_id = models.FloatField(blank=True, null=True)
    name = models.CharField(max_length=10, blank=True, null=True)
    compartmen = models.CharField(max_length=5, blank=True, null=True)
    area_ha = models.DecimalField(max_digits=100, decimal_places=16, blank=True, null=True)
    sp_code = models.CharField(max_length=10, blank=True, null=True)
    created_on = models.CharField(max_length=29, blank=True, null=True)
    created_by = models.CharField(max_length=50, blank=True, null=True)
    updated_on = models.CharField(max_length=29, blank=True, null=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)
    closed = models.DateField(blank=True, null=True)
    reason_clo = models.CharField(max_length=250, blank=True, null=True)
    zcoupeid = models.CharField(max_length=5, blank=True, null=True)
    zstandno = models.CharField(max_length=5, blank=True, null=True)
    zmslink = models.DecimalField(max_digits=100, decimal_places=16, blank=True, null=True)
    zfea_id = models.CharField(max_length=7, blank=True, null=True)
    geom = MultiPolygonField(srid=28350, blank=True, null=True)

    class Meta:
        db_table = 'polygon_mining_union'


class PolygonPriorToAreaFix(models.Model):
    polygon_id = models.IntegerField(blank=True, null=True)
    name = models.CharField(max_length=10, blank=True, null=True)
    compartment = models.CharField(max_length=5, blank=True, null=True)
    area_ha = models.FloatField(blank=True, null=True)
    sp_code = models.CharField(max_length=10, blank=True, null=True)
    created_on = models.DateTimeField(blank=True, null=True)
    created_by = models.CharField(max_length=50, blank=True, null=True)
    updated_on = models.DateTimeField(blank=True, null=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)
    closed = models.DateField(blank=True, null=True)
    reason_closed = models.CharField(max_length=250, blank=True, null=True)
    zcoupeid = models.CharField(db_column='zCoupeID', max_length=5, blank=True, null=True)  # Field name made lowercase.
    zstandno = models.CharField(db_column='zStandNo', max_length=5, blank=True, null=True)  # Field name made lowercase.
    zmslink = models.FloatField(db_column='zMSLink', blank=True, null=True)  # Field name made lowercase.
    zfea_id = models.CharField(max_length=7, blank=True, null=True)
    geom = MultiPolygonField(srid=28350, blank=True, null=True)

    class Meta:
        db_table = 'polygon_prior_to_area_fix'
        db_table_comment = 'Polygon data was created from Microstation files which have the area in square metres.  The column area_ha is obviously hectares.\nThis version of the polygon table is before the SQL below was run. \nUPDATE public.polygon\nSET area_ha = area_ha/10000;'


class Prescription(models.Model):
    prescription_id = models.AutoField(primary_key=True, db_comment='Primary key')
    obj_code = models.ForeignKey(ObjectiveLkp, on_delete=models.CASCADE, related_name='prescriptions', db_column='obj_code', blank=True, null=True, db_comment='silvicultural objective task entry applies to\nForeign key to silvic_lkp  (OBJECTIVE-LKP??)\n**Change column name to match lookup table PK')
    sequence = models.IntegerField(blank=True, null=True, db_comment='Sequence of this task in the prescription for the silvicultural objective')
    task = models.ForeignKey(TaskLkp, on_delete=models.CASCADE, db_column='task', blank=True, null=True, db_comment='Foreign key to tasks table')
    year = models.IntegerField(blank=True, null=True, db_comment='Years from operation date/year that task is required to be implemented')
    responsibility = models.ForeignKey(OrganisationLkp, on_delete=models.CASCADE, db_column='responsibility', blank=True, null=True, db_comment='Organisation or role having responsibility for implementing the task\nLookup table to organisation-lkp\nShould we have this - working arrangements can be dynamic in curent context')
    area_pct = models.IntegerField(blank=True, null=True, db_comment='Nominal percent area of polygon/cohort to be treated\nAPPLY check constraint to limit to 1 to 100 ')
    can_reschedule = models.BooleanField(blank=True, null=True, db_comment='Yes/TRUE if task can be rescheduled from the default')
    mandatory = models.BooleanField(blank=True, null=True, db_comment='Yes/TRUE if the task is required or mandatory for achievement of the silvicultural objective')
    done = models.BooleanField(blank=True, null=True, db_comment='Yes / TRUE if the task is usually completed/implemented when the prescription is loaded (e.g. harvesting or planning/preparation)')
    comment = models.CharField(max_length=250, blank=True, null=True, db_comment='Comments as to inclusion of the task in the prescription for the silvicultural objective')
    effective_from = models.DateTimeField(blank=True, null=True, db_comment='Date from which this entry in the prescription is valid')
    effective_to = models.DateTimeField(blank=True, null=True, db_comment='date this task is revoked from the prescription and no longer to be used as a default prescribed task')
    authorised_by = models.CharField(max_length=50, blank=True, null=True, db_comment='Person / document / authority authorising the task for inclusion in the prescription.\nNormally this will be the Senior Silviculturalist via silvicultural guidelines')
    revoked_by = models.CharField(max_length=50, blank=True, null=True, db_comment='Person / document / authority revoking the task from inclusion in the prescription.\nNormally this will be the Senior Silviculturalist via silvicultural guidelines')

    class Meta:
        db_table = 'prescription'
        db_table_comment = 'Prescribed tasks for each silvicultural objective, with default timing.\nEntity is a task prescribed for consideration to a particular silvicultural objective\n\nDS>> A prescription (set of tasks for a silvic objective) does relate to a silvic objective, and is flagged in the silvic_lkp table.\nSo in an FEA we might have several stands with silvic objective of K-ETHIN1 (to different intensities), with some specified to have coppice control.  The prescriptions will then be:\nNo coppice control\nE-THIN-K1 (the thinning task)\n(Uncertain if other tasks might be prescribed)\nCoppice Control\nE-THIN-K1 (the thinning task)\nCULL-COPC (Year harvest)\nASST-COPC (year harvest +1) to assess effectiveness of coppice control)'


class ReportCohort(models.Model):
    report_id = models.AutoField(primary_key=True, db_comment='primary key')
    report_name = models.CharField(max_length=50, blank=True, null=True, db_comment='Name of report')
    description = models.CharField(max_length=50, blank=True, null=True, db_comment='description of report, with additional clarifying information as to target audience, filtering, etc.')

    class Meta:
        db_table = 'report_cohort'
        db_table_comment = 'Names of reports to be run for cohorts - by silvic objective'


class ReportTreatment(models.Model):
    tsk_rpt_id = models.AutoField(primary_key=True, db_comment='primary key')
    report_name = models.CharField(max_length=50, blank=True, null=True, db_comment='Name of report')
    description = models.CharField(max_length=50, blank=True, null=True, db_comment='description of report, with additional clarifying information as to target audience, filtering, etc.')

    class Meta:
        db_table = 'report_treatment'
        db_table_comment = 'Names of reports to be run for treatments - by task.'


class SilrecPly2023(models.Model):
    poly_id = models.CharField(max_length=20, blank=True, null=True)
    area = models.DecimalField(max_digits=100, decimal_places=16, blank=True, null=True)
    hectares = models.DecimalField(max_digits=100, decimal_places=16, blank=True, null=True)
    perimeter = models.DecimalField(max_digits=100, decimal_places=16, blank=True, null=True)
    x = models.DecimalField(max_digits=100, decimal_places=16, blank=True, null=True)
    y = models.DecimalField(max_digits=100, decimal_places=16, blank=True, null=True)
    uid = models.DecimalField(max_digits=100, decimal_places=16, blank=True, null=True)
    geom = MultiPolygonField(srid=28350, blank=True, null=True)

    class Meta:
        db_table = 'silrec_ply_2023'


class SilrecVersion(models.Model):
    version_id = models.AutoField(primary_key=True, db_comment="Primary key\nCorresponds to 'Build Number'")
    name = models.CharField(max_length=50, blank=True, null=True, db_comment='Name or numeric code for version / release (User supplied)')
    deployed_on = models.DateTimeField(blank=True, null=True, db_comment='Date of final submission of version for Change Request')
    author = models.CharField(max_length=50, blank=True, null=True, db_comment='Author or person releasing the update/version')
    description = models.CharField(max_length=250, blank=True, null=True, db_comment='Description of the update ')

    class Meta:
        db_table = 'silrec_version'
        db_table_comment = 'Table to document and manage enhancements in versions and releases'


class SilrecVersionTracking(models.Model):
    tracking_id = models.AutoField(primary_key=True, db_comment='Primary key')
    version = models.ForeignKey(SilrecVersion, on_delete=models.CASCADE, blank=True, null=True, db_comment='Foreign key to versions table, identifies what version/release the changes refer to')
    object = models.CharField(max_length=50, blank=True, null=True, db_comment='Object that has been changed or created')
    description = models.CharField(max_length=250, blank=True, null=True, db_comment='Description of the changes')

    class Meta:
        db_table = 'silrec_version_tracking'
        db_table_comment = 'Document changes to SILREC versions'


class SilvicPlanInput(models.Model):
    silvplan_id = models.AutoField(primary_key=True, db_comment='Unique identifier for rows/items in the table\n(not part of input shape file)')
    plan_release = models.CharField(max_length=50, blank=True, null=True, db_comment='Date stamp or identifier for the release of one or more silvic plans.\n(not part of input shape file)')
    id = models.IntegerField(blank=True, null=True, db_comment='integer field allegedly an identifier (but most rows have same value)')
    fea_id = models.CharField(max_length=10, blank=True, null=True, db_comment='Identifier for the FEA or operation incorporating the polygon.\nFollows the convention (using former LOIS coding)\nDBBCCYY\nwhere\nD = District code\nBB = Forest Block code\nCC = compartment (can be 3 digits)\nYY = last two digits of calendar year of operational plan.\n\ne.g. PWR0623, DOGO010023, DOSU071524')
    block_cpt = models.CharField(max_length=50, blank=True, null=True, db_comment='Forest block name concatenated with compartment number(s), with no separator character, unless there are multiple compartments.\n\t- Case can be mixed\n\t- May have suffix for locality\n\ne.g. WARREN06, Sutton11, Gordon01 Jarrah Nth, SUTTON07-15')
    thin_inten = models.CharField(max_length=10, blank=True, null=True, db_comment='Target residual density; may be a single figure (18, 22) or a range (10-14), or a textual description of silvic intent.\nUnits (m2/ha) are implied.\ne.g. 18, 10 -14, Restore, Harvested')
    veg_complex = models.CharField(max_length=20, blank=True, null=True, db_comment="Shape file has 'veg_comple'\nComma separated list of vegetation complexes included in the polygon (in order of dominance?)\n\ne.g. \n\t- Crowea, Warren\n\t- Pemberton, PM1\n\t- Yanmah, YN,Crowea")
    lmu = models.CharField(max_length=20, blank=True, null=True, db_comment='Land Management Unit the polygon/FEA falls into\ne.g. Central Karri, Strachan CJ')
    area_ha = models.FloatField(blank=True, null=True, db_comment='Area of the polygon in hectares')
    herb_app = models.CharField(max_length=15, blank=True, null=True, db_comment="Specification for herbicide application for coppice control; usually expressed as 'Y' & concentration to be applied (e.g. 1;10, 1:15)\ne.g. Yes, Y 1:15, Y 1:10")
    zone = models.CharField(max_length=5, blank=True, null=True, db_comment='silvic planning zone, as per the text document accompanying the silvic plan-map; each different thinning intensity/residual intended will be assigned a different zone\ne.g. A, B, C...')
    comment = models.CharField(max_length=50, blank=True, null=True, db_comment='pertinent comments to the silvic intent')
    created_on = models.DateTimeField(blank=True, null=True)
    created_by = models.CharField(max_length=50, blank=True, null=True)
    updated_on = models.DateTimeField(blank=True, null=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)
    geom = MultiPolygonField(srid=28350, blank=True, null=True)

    class Meta:
        db_table = 'silvic_plan_input'
        db_table_comment = "Table to receive the shape file(s) specifying the silvicultural plan for each FEA/operation\nUncertain of publication frequency or standard\n\nMy thoughts are that annually, the Active FEA plan (Active is PM's terminology) is imported.  Overwriting this table.  Then some overlay process so that new polygons are added where they do not already exist and old polygons/cohorts possibly updated.  This is simply a rough idea of how I envisage it working. (DW) Delete comment for PRD.\nDS: Use of the table as follows:\n\n\t1. Data structure matches the structure of the silvic planning outputs (shape file).\n\t2. Aim is to provide a permanent repository of the source data for backtracking, cross referencing and validating.\n\t3. Since the silvic plan is a detailed tactical plan, it is unlikely to be revised and changed once released/published.  Not like an annual harvest plan.\n\t4. While it is possible that an FEA is carried over a year or three, the structure of the ET program makes that unlikely.\n\t5. No formal relationships to be established, but ad hoc query can link FEA_ID to OPERATION.OP_ID; as well as use of spatial operators (within, overlaps, etc.)\n\t6. Retention of successive silvic plans means that at some stage there will be overlapping spatial objects (polygons); i.e. NO planar enforcement."


class SilviculturistComment(models.Model):
    s_comment_id = models.AutoField(primary_key=True)
    comment = models.CharField(max_length=1000, blank=True, null=True)
    scope = models.CharField(max_length=50, blank=True, null=True, db_comment='scope of comment:\n\t- polygon\n\t- cohort\n\t- treatment\n\t- operation\n\t- proposed operation\n\nIn a forms environment this is populated with help of a dropdown')
    required_action = models.CharField(max_length=100, blank=True, null=True, db_comment='Specification of any follow up action in relation to this note')
    action_complete = models.DateField(blank=True, null=True, db_comment='Date at which any required action is deemed to be completed or finalised')
    op = models.ForeignKey(Operation, on_delete=models.CASCADE, blank=True, null=True, db_comment='FK to operation table\nNullable because operation may not be known at time of making comment')
    polygon = models.ForeignKey(Polygon, on_delete=models.CASCADE, blank=True, null=True, db_comment='FK to polygon table\nNullable because operation may not be known at time of making comment')
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, blank=True, null=True, db_comment='FK to cohort table\nNullable because operation may not be known at time of making comment')
    treatment = models.ForeignKey('Treatment', on_delete=models.CASCADE, blank=True, null=True, db_comment='FK to treatment table\nNullable because operation may not be known at time of making comment')
    easting_note_taken = models.IntegerField(blank=True, null=True, db_comment='Easting of location where note/observation/comment recorded.\n\nassumed to be captured by field PDA')
    northing_note_taken = models.IntegerField(blank=True, null=True, db_comment='Northing of location where note/observation/comment recorded.\n\nassumed to be captured by field PDA')
    created_on = models.DateTimeField(blank=True, null=True, db_comment='populated by trigger')
    created_by = models.CharField(max_length=50, blank=True, null=True)
    updated_on = models.DateTimeField(blank=True, null=True, db_comment='populated by trigger')
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = 'silviculturist_comment'
        db_table_comment = "Repository for Senior Silviculturist's comments.\n\nSuch comments may be in relation to either:\n1. The Operation\n2.  The cohort within an operation\n3. The treatments on a cohort/s \n\nIn Arc GIS Pro you can create relationship down one level I believe.  I do not know how this would work if the user entered a comment at the polygon level.  It would be stored in this table, but how then would the operation, cohort and treatment id be retrieved? Delete comment for PRD.\n\nShould this table be restricted to simply link to Operation table to maximise flexibility? Delete comment for PRD.\n\nAdd columns for easting, northing, i.e. point at which notes taken should be geo-coded. Done(DW) Delete comment for PRD."




class SplitUnchangedPolygons(models.Model):
    polygon_id = models.FloatField(blank=True, null=True)
    old_area = models.DecimalField(max_digits=100, decimal_places=16, blank=True, null=True)
    new_area = models.DecimalField(max_digits=100, decimal_places=16, blank=True, null=True)

    class Meta:
        db_table = 'split_unchanged_polygons'


class TaskCategory(models.Model):
    tsk_cat_id = models.AutoField(primary_key=True)
    task = models.CharField(max_length=20, blank=True, null=True)
    target_column = models.CharField(max_length=9, blank=True, null=True)
    category_value = models.CharField(max_length=30, blank=True, null=True)
    description = models.CharField(max_length=250, blank=True, null=True)
    comment = models.CharField(max_length=250, blank=True, null=True)
    alt_code = models.CharField(max_length=10, blank=True, null=True)
    created_on = models.DateTimeField(blank=True, null=True)
    created_by = models.CharField(max_length=50, blank=True, null=True)
    updated_on = models.DateTimeField(blank=True, null=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = 'task_category'
        unique_together = (('task', 'target_column'),)



class Treatment(models.Model):
    treatment_id = models.AutoField(primary_key=True, db_comment='Primary key identifying treatment\n(task implemented on polygon/cohort)')
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, blank=True, null=True, db_comment='If/when a new prescription is created for a silvic objective, there is a linkage back to the prescription item that created the treatment (where it exists … sometimes there are ‘unprescribed’ treatments)')
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, blank=True, null=True, db_comment='Foreign key to cohort table\nidentifies the cohort the task was applied to')
    task = models.ForeignKey(TaskLkp, on_delete=models.CASCADE, db_column='task', blank=True, null=True, db_comment='Foreign key to task_lkp to identify task applied')
    plan_mth = models.IntegerField(blank=True, null=True, db_comment="Formerly 'PlannedMo'\n\nIdentifies the month in which the task is intended/scheduled for implementation or completion")
    plan_yr = models.IntegerField(blank=True, null=True, db_comment="Formerly 'PlannedYr'\n\nCalendar year task is planned for completion")
    pct_area = models.IntegerField(blank=True, null=True, db_comment='Percent of the cohort the treatment has been applied to or to be applied; e.g. if THIN is 50 pct of cohort, and only half of that has been treated, then PCT_AREA=50 pct')
    complete_date = models.DateTimeField(blank=True, null=True, db_comment="Date of completion of the task or treatment, or when the treatment status changes from 'planned'.")
    results = models.CharField(max_length=250, blank=True, null=True, db_comment='Textual description of treatment implementation or results')
    status = models.CharField(max_length=1, blank=True, null=True, db_comment='Code / Foreign key to treatment_status_lkp table\n\nProvides status of completion of treatment\nC=Treatment Cancelled\nD=Treatment Completed\nF=Treatment Failed\nP=Treatment Planned\nW=Treatment Written Off\nX=Treatment Not Required')
    changed_by = models.CharField(max_length=50, blank=True, null=True, db_comment='Person authorising any change, either:\n\t- rescheduling the treatment to a new planned year/month\n\t- treatment status other than completed, i.e. person authorising cancellation of a treatment.')
    reference = models.CharField(max_length=250, blank=True, null=True, db_comment='Reference to further information on the treatment implementation (or not); can be URL e.g. to SharePoint, or Report title, etc.')
    organisation = models.CharField(max_length=10, blank=True, null=True, db_comment='Organisation or role responsible for implementing treatment')
    initial_plan_yr = models.IntegerField(blank=True, null=True, db_comment="Year task initially planned/scheduled to implement\nEnables computation of treatment delay when treatments rescheduled (BUT treatment rescheduling never been managed in SILREC to date)\n\nformerly 'InitialPlanYear'")
    can_reschedule = models.BooleanField(blank=True, null=True, db_comment="flag to show planned/scheduled timing of treatment is review-able\nFormerly 'ToReview'")
    created_on = models.DateTimeField(blank=True, null=True, db_comment='Date of creation of treatment record in database')
    created_by = models.CharField(max_length=50, blank=True, null=True, db_comment='network user ID of person creating the treatmentin the database')
    updated_on = models.DateTimeField(blank=True, null=True, db_comment='date treatment record was last changed')
    updated_by = models.CharField(max_length=50, blank=True, null=True, db_comment='network user ID of person updating the treatment record in the database')
    ztreatment_method = models.IntegerField(blank=True, null=True, db_comment='[Legacy - no longer used] Method of undertaking treatment; e.g. CLMH => culling by hand (c.f. machine) by Dept staff/crew (c.f. contractors)\n\nPossibly re-instate for coppice control\n\t- Foliar spray\n\t- stump\n**LOOKUP TABLE NEEDED**')
    zoperation = models.CharField(max_length=10, blank=True, null=True, db_comment='Operation or coupe or FEA ID as entered to planning system\n**Likely not needed\n\nDW>> Is this still called LOIS Op code.  PM plan now refers to FEA ID (DW).')
    zstand = models.CharField(db_column='zStand', max_length=10, blank=True, null=True, db_comment='Patch Id (or polygon ID) formerly part of compound primary key\n\nDW>> Is this the legacy stand the treatment falls within.  If so should the legacy stand table be remain with a relationship to this table and this column be a FK to that table.\n\nFurther: does this relate to the cohort rather than the treatment.  If so this column should be in the cohort table. There is a stand column in cohort already (duplication).')  # Field name made lowercase.
    zsilvic = models.CharField(db_column='zSilvic', max_length=20, blank=True, null=True, db_comment='Current silvicultural objective for the stand (formerly part of compound primary key)\nDW>> See Stand column comment!\nIf the legacy stand table relationship is retained  to the Stand column then legacy SILVICS relationship to that table retained.  If so Silvic should be removed.')  # Field name made lowercase.
    ztreatno = models.FloatField(db_column='zTreatNo', blank=True, null=True, db_comment='Number for application of treatment (formerly part of compound primary key)\nRequired to provide unique identifier for each treatment, especially in circumstances where multiple instances of the same treatment applied to a stand/cohort, e.g. infill planting.\nThe new single-element primary key obviates the need for this construct, which was very difficult and complex to manage.\nDW>> What is this column for.  Is it a link to a lookup table of treatment types?  I.e. a FK to a table yet to be placed in this ERD.')  # Field name made lowercase.
    zcomplmo = models.IntegerField(db_column='zComplMo', blank=True, null=True, db_comment='month of completion of treatment')  # Field name made lowercase.
    zcompl_yr = models.IntegerField(db_column='zCompl_Yr', blank=True, null=True, db_comment='Year of completion of treatment')  # Field name made lowercase.
    zscheduleconfirmed = models.BooleanField(db_column='zScheduleConfirmed', blank=True, null=True, db_comment='flag to show plannedyr assessed & confirmed at least once (but may be re-assessable)\n\n**Never used, not helpful')  # Field name made lowercase.
    zextra_info = models.BooleanField(blank=True, null=True, db_comment='Flag to show if additional attributes recorded or should be recorded\n(populated when task inserted to treatment table)')

    class Meta:
        db_table = 'treatment'
        db_table_comment = "A treatment is a task or activity applied/implemented to a cohort within a polygon; every attempt to implement a given task is a new treatment.\nThe treatment may be a task that directly establishes a cohort, such as a thinning/harvest, or a mandated follow up silvicultural treatment, such as coppice control; it may also be part of routine stand management, such as prescribed burn or some assessment of status/condition.\nTreatments are directly related to polygons because often treatments, although having an inherent spatial boundary, are best defined as clipped to a polygon boundary; it also better facilitates presentation of stand history of treatments 'with a simple click'.  A treatment may be independently defined, such as a fire burn envelope, from which overlapping polygons get treatment records inserted against the current cohort.\nBurn envelopes may necessitate polygons being split.\nDECIDE to retain planned month, year in preference to planned date because planned date implies too much precision\nDelete comments below for PRD.\nADD FK to prescription table\n**Need lookup table for METHOD** Done. (DW)"



class TreatmentXtra(models.Model):
    treatment_xtra_id = models.AutoField(primary_key=True)
    treatment = models.ForeignKey(Treatment, on_delete=models.CASCADE)
    rescheduled_reason = models.CharField(max_length=30, blank=True, null=True, db_comment='Reason for rescheduling treatment')
    success_rate_pct = models.IntegerField(blank=True, null=True, db_comment='Number of sample points / plots meeting the specified stocking rate, as a percent of total sample points / plots\n\nis a real number between 0 and 100\nApply check constraint')
    stocking_rate_spha = models.FloatField(blank=True, null=True, db_comment='Assessed Mean stocking rate in stems per ha; i.e. average from all survey points assessed.')
    api_species_assessed = models.CharField(max_length=3, blank=True, null=True, db_comment='Species mix (API) as determined by the assessment\nSHOULD LINK TO API SPECIES LOOKUP TABLE Done. (DW)')
    category1 = models.OneToOneField(TaskCategory, on_delete=models.CASCADE, db_column='category1', blank=True, null=True)
    category2 = models.OneToOneField(TaskCategory, on_delete=models.CASCADE, db_column='category2', related_name='treatmentxtra_category2_set', blank=True, null=True)
    category3 = models.ForeignKey(TaskCategory, on_delete=models.CASCADE, db_column='category3', related_name='treatmentxtra_category3_set', blank=True, null=True)
    category4 = models.OneToOneField(TaskCategory, on_delete=models.CASCADE, db_column='category4', related_name='treatmentxtra_category4_set', blank=True, null=True)
    qty1 = models.FloatField(blank=True, null=True)
    qty2 = models.FloatField(blank=True, null=True)
    qty3 = models.FloatField(blank=True, null=True)
    qty4 = models.FloatField(blank=True, null=True)
    zmachine_id = models.IntegerField(blank=True, null=True)
    zseed_source = models.CharField(max_length=50, blank=True, null=True, db_comment='Description of seed source: Zone or Forest Block')
    zassessment_type = models.CharField(max_length=50, blank=True, null=True, db_comment='Type of plant / tree / regeneration included in the assessment\n\nCreate lookup table from table assessment-types (MS Access SILREC v2) to be named assessment_type_lkp')
    zspecies1_planted = models.IntegerField(blank=True, null=True, db_comment='Species1 planted / sown to have lookup to tree species code\nDone. (DW)')
    zplanting_rate1_spha = models.IntegerField(blank=True, null=True, db_comment='Nominal rate of planting first (most dominant) species in stems per ha')
    zspecies2_planted = models.IntegerField(blank=True, null=True, db_comment='Species2 planted / sown to have lookup to tree species code\nDone. (DW)')
    zplanting_rate2_spha = models.IntegerField(blank=True, null=True, db_comment='Nominal rate of planting second(least dominant) species in stems per ha')
    zresult_standard = models.CharField(max_length=20, blank=True, null=True, db_comment='Assessed standard achieved, as per the formal survey; e.g. adequate / optimal\nhave lookup')
    zpatch = models.CharField(max_length=10, blank=True, null=True)
    zsilvic = models.CharField(max_length=20, blank=True, null=True)
    ztaskid = models.CharField(db_column='zTaskID', max_length=20, blank=True, null=True)  # Field name made lowercase.
    ztreatno = models.FloatField(db_column='zTreatNo', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        db_table = 'treatment_xtra'
        db_table_comment = "Treatments-Xtra is for additional information to be recorded against individual treatments, but the information isn't required for the majority of treatments.\nThe structure provides an efficient means of a sparse population / attribution of items, rather than having a large 'flat table' with many rows having null values for columns.\nDelete comments below for PRD.\nNeed to remove relationships to species-api and create new lookup table species-tree-lkp\ncreate lookup from api-species-assessed to species-api-lkp"


class VegRetPatch(models.Model):
    vrp_id = models.AutoField(primary_key=True, db_comment='Primary key')
    habitat_log = models.IntegerField(blank=True, null=True, db_comment='Number of habitat logs included when demarcated in the field')
    habitat_tree = models.IntegerField(blank=True, null=True, db_comment='Number of habitat trees included when demarcated in the field')
    midstorey = models.IntegerField(blank=True, null=True, db_comment='Number of midstorey items included when demarcated in the field')
    score = models.IntegerField(blank=True, null=True, db_comment='Rating score for retention elements\nNotional item, depends on how vegetation retention patches are specified in field procedures')
    width_m = models.IntegerField(blank=True, null=True, db_comment='Approximate width or diameter of the vegetation retention patch')
    area_ha = models.FloatField(blank=True, null=True, db_comment='Area in ha of the vegetation retention patch')
    comments = models.CharField(max_length=250, blank=True, null=True, db_comment='Comments as to the demarcation and retention elements of the vegetation retention patch')
    created_on = models.DateTimeField(blank=True, null=True)
    created_by = models.CharField(max_length=50, blank=True, null=True)
    updated_on = models.DateTimeField(blank=True, null=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)
    geom = MultiPolygonField(srid=28350, blank=True, null=True)

    class Meta:
        db_table = 'veg_ret_patch'
        db_table_comment = 'Table of vegetation retention patches.\n\t- Stored as points\n\t- Initially imported from silvic plan as points/centroids of nominal location & size of vegetation retention patches\n\t- Updated by moving point to approximate centre of actual location and  providing information on retention elements included; possibly from post-operation imagery, or field demarcation.'


class FpcHarvestTracker(models.Model):
    objectid = models.IntegerField(primary_key=True)
    lois = models.CharField(max_length=20, blank=True, null=True)
    fallers_block = models.CharField(unique=True, max_length=10, blank=True, null=True)
    operation_start = models.DateField(blank=True, null=True)
    authorised_officer = models.CharField(max_length=50, blank=True, null=True)
    cutover_progress = models.SmallIntegerField(blank=True, null=True)
    custodian_name = models.CharField(max_length=50, blank=True, null=True)
    approval_date = models.DateField(blank=True, null=True)
    cell_certified = models.DateField(blank=True, null=True)
    comments = models.CharField(max_length=250, blank=True, null=True)
    shape_area = models.FloatField(blank=True, null=True)
    shape_length = models.FloatField(blank=True, null=True)
    globalid = models.UUIDField(blank=True, null=True)
    karri_mature_harvest_cf = models.BooleanField(blank=True, null=True)
    karri_1st_thinning = models.BooleanField(blank=True, null=True)
    karri_2nd_thinning = models.BooleanField(blank=True, null=True)
    jarrah_integrated_harvest = models.BooleanField(blank=True, null=True)
    jarrah_salvage_operation = models.BooleanField(blank=True, null=True)
    jarrah_mine_site_clearing = models.BooleanField(blank=True, null=True)
    karrai_salvage_operation = models.BooleanField(blank=True, null=True)
    contractor = models.CharField(max_length=50, blank=True, null=True)
    creation_date = models.DateField(blank=True, null=True)
    creator = models.CharField(max_length=50, blank=True, null=True)
    editdate = models.DateField(blank=True, null=True)
    editor = models.CharField(max_length=50, blank=True, null=True)
    season = models.CharField(max_length=50, blank=True, null=True)
    geom = MultiPolygonField(srid=28350, blank=True, null=True)

    class Meta:
        db_table = 'fpc_harvest_tracker'
        db_table_comment = 'placeholder for FPC Harvest Tracking tool, to facilitate tracking progress of the operation\n\nIntend for this table/dataset to be displayed as a reference layer, and the database is not intended to hold these data objects'


