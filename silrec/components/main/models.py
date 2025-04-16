from django.db import models
#from django.contrib.gis.db.models import GeometryField


class ValidateModelMixin(object):
    def clean(self):
        #import ipdb; ipdb.set_trace()
        for field in self._meta.fields:
            field.primary_key
            value = getattr(self, field.name)

            if value and field.primary_key:
                # strip whitespace and restrict to upper case
                try:
                    setattr(self, field.name, value.strip().upper())
                except Exception:
                    pass

    def save(self, *args, **kwargs):
        self.full_clean()
        super(ValidateModelMixin, self).save(*args, **kwargs)


class CohortMetricsLkp(models.Model):
    metric_id = models.AutoField(primary_key=True, db_comment='Primary key')
    name = models.CharField(max_length=50, blank=True, null=True, db_comment='Brief name for the success measure')
    definition = models.CharField(max_length=500, blank=True, null=True, db_comment='Full description and definition of the success measure, including measurement protocols, if required.')
    rating = models.BooleanField(blank=True, null=True, db_comment='Yes if the success measure is a rating or classification or categorical variable\nNo => numeric or quantitative variable')
    value = models.CharField(max_length=50, blank=True, null=True, db_comment='If a rating variable (rating = Yes) then provide a category value. \n\nEnter additional category values as successive rows.\n\nIf NOT a rating (rating = No) then provide the units of the measure or quantity; if a unit-less quantity/variable then leave blank')
    method = models.CharField(max_length=250, blank=True, null=True, db_comment='Key features of the methodology used to calculate or derive the metric')
    reference = models.CharField(max_length=250, blank=True, null=True, db_comment='Any literature or other reference to the metric or method')
    version = models.SmallIntegerField(blank=True, null=True, db_comment='version number to identify versions of the metric')
    created_on = models.DateTimeField(blank=True, null=True)
    created_by = models.CharField(max_length=50, blank=True, null=True)
    updated_on = models.DateTimeField(blank=True, null=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)
    effective_from = models.DateTimeField(blank=True, null=True)
    effective_to = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'cohort_metrics_lkp'
        db_table_comment = 'Table to enable / identify / define metrics associated with cohorts, e.g. calculations of stand density'


class MachineLkp(models.Model):
    machine_id = models.AutoField(primary_key=True)
    manufacturer = models.CharField(max_length=50, blank=True, null=True, db_comment="Manufacturer of the machine, e.g. 'John Deere'.")
    model = models.CharField(max_length=50, blank=True, null=True, db_comment="Designation of machine model by the manufacturer, for example '1270G'.\nModel should INCLUDE length of boom, tracked or wheeled \n??and machine type.")
    machine_type = models.CharField(max_length=50, blank=True, null=True, db_comment='Machine type defined by model but inserted for convenience.\nPredominantly harvester, skidder, forwarder and maybe in forest chipper.')
    felling_head_model = models.CharField(max_length=10, blank=True, null=True, db_comment='Felling head may be different on different models.')
    felling_head_herbicide_spray = models.BooleanField(blank=True, null=True, db_comment='Defines whether herbicide sprayed at time of felling.')

    class Meta:
        db_table = 'machine_lkp'
        db_table_comment = 'List machines and key parameters for machines that may be used for thinning and/or coppice control'

class OrganisationLkp(models.Model):
    organisation = models.CharField(primary_key=True, max_length=10, db_comment='Code or acronym for the organisation')
    description = models.CharField(max_length=100, blank=True, null=True, db_comment='Organisation description or name in full')
    created_on = models.DateTimeField(blank=True, null=True)
    created_by = models.CharField(max_length=50, blank=True, null=True)
    updated_on = models.DateTimeField(blank=True, null=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = 'organisation_lkp'


class RegenerationMethodsLkp(models.Model):
    regen_method = models.CharField(primary_key=True, max_length=2, db_comment='code (primary key) for the regeneration method, corresponds to FMIS code to match FMIS theme.')
    description = models.CharField(max_length=50, blank=True, null=True, db_comment='Description or definition of regeneration method')

    class Meta:
        db_table = 'regeneration_methods_lkp'
        db_table_comment = "Code lookup table for methods of regeneration \nRegen methods as per FMIS theme\n\t- Plant/infill Karri or any sp NOT Jarrah\n\t- Karri seed tree >= 1967\n\t- Karri direct seed\n\t- natural or 'untreated' regeneration\n\t- Karri seed tree < 1967\n\t- Jarrah, Wandoo lignotuber\n\t- Plant/infill Jarrah\n\t- Coppice Karri or Jarrah\n\n\nIs regeneration method the objective residual BA.  If so then residual BA is in cohort.  Or are we recording the method of cut. I.e. machine, machine type and hand fallen.  This, along with forwarder movement,  may reflect the potential for soil damage and hence regeneration (DW) \nDS> regen methods as listed above; not related to residual BA"


class RescheduleReasonsLkp(models.Model):
    rescheduled_reason = models.CharField(primary_key=True, max_length=15)
    description = models.CharField(max_length=50, blank=True, null=True)
    created_on = models.DateTimeField(blank=True, null=True)
    created_by = models.CharField(max_length=50, blank=True, null=True)
    updated_on = models.DateTimeField(blank=True, null=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = 'reschedule_reasons_lkp'
        db_table_comment = 'Standard/accepted reasons for rescheduling a prescribed task/treatment'


class SpatialPrecisionLkp(models.Model):
    precision_code = models.CharField(primary_key=True, max_length=10, db_comment='Code for spatial precision of mapping or capture method')
    resolution = models.CharField(max_length=50, blank=True, null=True, db_comment='resolution of the mapping in metres')
    description = models.CharField(max_length=50, blank=True, null=True, db_comment='description / example of the mapping methods')
    created_on = models.DateTimeField(blank=True, null=True)
    created_by = models.CharField(max_length=50, blank=True, null=True)
    updated_on = models.DateTimeField(blank=True, null=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = 'spatial_precision_lkp'
        db_table_comment = 'Lookup values and definitions for spatial mapping precision'


class SpeciesApiLkp(models.Model):
    species = models.CharField(primary_key=True, max_length=5, db_comment='Silrec species code')
    short_description = models.CharField(max_length=15, blank=True, null=True, db_comment='Ready reference guide for code selection')
    full_description = models.CharField(max_length=150, blank=True, null=True, db_comment='Formal definition of species code')
    fmiscode_species = models.CharField(db_column='FMIScode_species', max_length=2, blank=True, null=True, db_comment='FMIS code for FMIS species theme')  # Field name made lowercase.
    fmisdescription_type = models.CharField(db_column='FMISdescription_type', max_length=255, blank=True, null=True, db_comment='Description for code for FMIS forest type theme')  # Field name made lowercase.
    fmiscode_type = models.CharField(db_column='FMIScode_type', max_length=2, blank=True, null=True, db_comment='FMIS code for FMIS forest type theme')  # Field name made lowercase.
    created_on = models.DateTimeField(blank=True, null=True)
    created_by = models.CharField(max_length=50, blank=True, null=True)
    updated_on = models.DateTimeField(blank=True, null=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = 'species_api_lkp'
        db_table_comment = 'Lookup code values and definitions for API species types.\nDelete comments below for PRD.\nDW>> Suggest table renamed dominant species.  I.e. Jarrah or Karri etc. Then a relationship created to cohort (DW).\n\nShould the species codes be a replication of the Oracle table sfm_common.species. (DW) \nDS>> No, these are API type codes, as per the FMIS API types; i.e. a stand-based descriptor c.f. a tree-based descriptor.'


class TaskLkp(ValidateModelMixin, models.Model):
    task = models.CharField(primary_key=True, unique=True, max_length=20, db_comment='Code for the task\n\nAPPLY check constraint to restrict to upper case')
    task_name = models.CharField(max_length=50, blank=True, null=True, db_comment='Short meaningful name for the task')
    definition = models.TextField(blank=True, null=True, db_comment='Detailed definition of task')
    category1_label = models.CharField(max_length=50, blank=True, null=True)
    category2_label = models.CharField(max_length=50, blank=True, null=True)
    category3_label = models.CharField(max_length=50, blank=True, null=True)
    category4_label = models.CharField(max_length=50, blank=True, null=True)
    qty1_label = models.CharField(max_length=20, blank=True, null=True)
    qty2_label = models.CharField(max_length=20, blank=True, null=True)
    qty3_label = models.CharField(max_length=20, blank=True, null=True)
    qty4_label = models.CharField(max_length=20, blank=True, null=True)
    record_standard = models.TextField(blank=True, null=True, db_comment='Specifications, standards and parameters for recording the task.')
    only_1silvic = models.CharField(max_length=50, blank=True, null=True, db_comment="Silvicultural objective if this task is linked to only one objective\nI think this was required for some complex reporting and analyses; not sure if still relevant, but likely still required for legacy purposes.\nformerly 'SilvicObjective'\nSee comment on silvicultural objective in comment on prescription table and also comment on stand in treatments table (DW).\nIs silvicultural objective from legacy stand? (DW)\n**Retain for legacy purposes, but review - it may not be needed**")
    financial_activity = models.CharField(max_length=3, blank=True, null=True, db_comment='Activity code to match to financial system for expenditure; $ for activities usually resulting in commercial yields')
    forest_type = models.CharField(max_length=10, blank=True, null=True, db_comment='Silvic guidelines relevant to this task, e.g. silviculture in Jarrah/Karri/Wandoo forests relevant to the task; helps filter/sort drop down lists\n**Lookup table??**\n**To Review**')
    default_organisation = models.CharField(max_length=10, blank=True, null=True, db_comment="Default organisation or role having responsibility for task implementation\nForeign key to organisation table\nformerly 'Def_Rspnsblty'\nNote that the responsible organisation for any specific implementation may change for special circumstances, hence organisation is a lookup table to both task-lkp and treatment")
    addition_attribs = models.ForeignKey('TasksAttLkp', on_delete=models.CASCADE, db_column='addition_attribs', blank=True, null=True, db_comment='Yes if additional attributes are recordable and have been configured in Treatments Extra table for the task/treatment')
    regen_init = models.BooleanField(blank=True, null=True, db_comment='Yes if task initiates regeneration of overstorey, as used in RegenValues() function')
    created_on = models.DateTimeField(blank=True, null=True)
    created_by = models.CharField(max_length=30, blank=True, null=True)
    updated_on = models.DateTimeField(blank=True, null=True)
    updated_by = models.CharField(max_length=30, blank=True, null=True)
    auth_on = models.DateField(blank=True, null=True, db_comment='Date the task was defined or authorised for use')
    auth_by = models.CharField(max_length=50, blank=True, null=True, db_comment='Name of person or body authorising the task for use')
    revoked_on = models.DateTimeField(blank=True, null=True)
    revoked_by = models.CharField(max_length=30, blank=True, null=True)
    z2report = models.BooleanField(db_column='z2Report', blank=True, null=True)  # Field name made lowercase.
    zothr_rpt_category = models.CharField(max_length=50, blank=True, null=True, db_comment='Category to be used in user & ad hoc reporting')
    zann_rpt_category = models.CharField(max_length=50, blank=True, null=True, db_comment='Category to be used in annual reports.  Probably requires lookup table')
    zmapinfo_id = models.IntegerField(db_column='zMapInfo_ID', blank=True, null=True, db_comment='DW>> Why MapInfo ID in this table.  Is the only spatial data at the polygon level? (DW)\nDS>> MapInfo creates this key whenever table is opened')  # Field name made lowercase.
    zustncolour = models.CharField(db_column='zUstnColour', max_length=10, blank=True, null=True, db_comment='Hachure Specification for MicroStation / Mappa for display on thematic mapping\nDW>> Is UstnColour a legacy column.  Prefix with "z"? (DW)')  # Field name made lowercase.
    zavailable = models.BooleanField(db_column='zAvailable', blank=True, null=True, db_comment='Yes if task is available for current use, No if task has been revoked and is unavailable.\n\nBetter to use effective from/to')  # Field name made lowercase.
    zcoupetask = models.BooleanField(db_column='zCoupeTask', blank=True, null=True, db_comment='Yes if task can be or is only applied to coupe works program\nDS>> Likely this is better managed by DAS??\nDW>> Use of the word "coupe" has been deliberately avoided by PM.  Should this be renamed FEA. (DW)')  # Field name made lowercase.
    zpatchtask = models.BooleanField(db_column='zPatchTask', blank=True, null=True, db_comment="Yes if task can be applied to patch level treatments / works program\nPartners 'CoupeTask'\n\nAlso likely not relevant")  # Field name made lowercase.
    ztiming = models.IntegerField(blank=True, null=True, db_comment='Default timing for task, in years from start of harvest\n\nLikely this is better managed with prescription; unsure of any use in SILREC v2')
    ztreatmentid = models.BigIntegerField(db_column='ztreatmentID', blank=True, null=True)  # Field name made lowercase.
    effective_from = models.DateTimeField(blank=True, null=True)
    effective_to = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.task

    class Meta:
        db_table = 'task_lkp'
        db_table_comment = 'Any task or activity undertaken or planned for a cohort\n\n**Drop report category columns and create separate tables to define reports and assign tasks to individual reports, similar to that established for cohort reporting. Done (DW). Delete comment for PRD.\n\nInsert / update privilege restricted to information custodian & delegates\nConsider advantage of lookup table for Forest Type and also use for silvic-lkp'


class TasksAttLkp(models.Model):
    addition_attrib = models.CharField(primary_key=True, max_length=1)
    description = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = 'tasks_att_lkp'


class TreatmentStatusLkp(models.Model):
    status = models.CharField(primary_key=True, max_length=1, db_comment='Treatment status code')
    name = models.CharField(max_length=50, blank=True, null=True, db_comment='Ready reference description/guide for code selection (e.g. for drop down lists)')
    definition = models.CharField(max_length=1000, blank=True, null=True, db_comment='Full definition of treatment status')
    created_on = models.DateTimeField(blank=True, null=True)
    created_by = models.CharField(max_length=50, blank=True, null=True)
    updated_on = models.DateTimeField(blank=True, null=True)
    updated_by = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = 'treatment_status_lkp'
        db_table_comment = "Lookup values and definitions for treatment status\n\nNo longer require 'UstnHachureCode' = 'Hachure code for colouring patterns in MicroStation/Mappa'"


class ObjectiveLkp(models.Model):
    obj_code = models.CharField(primary_key=True, max_length=20, db_comment='Name/code of silvicultural or management objective\n\napply check constraint for upper case only')
    description = models.CharField(max_length=150, blank=True, null=True, db_comment='Definition or description of the silvicultural / management objective')
    definition = models.TextField(blank=True, null=True, db_comment='Full definition of silvicultural objective')
    cut = models.CharField(max_length=5, blank=True, null=True, db_comment='Flag CUT to indicate the objective should involve harvest of trees\nFlag UNCUT to indicate the objective does NOT involve harvest of trees\nFlag BOTH if the objective may nor may not involve tree removal')
    forest_type = models.CharField(max_length=10, blank=True, null=True, db_comment='Forest type the objective is applicable to;\nThree types\n\n\t1. Any (all)\n\t2. Jarrah - stand dominated by jarrah or marri\n\t3. Karri - stand dominated by karri (or has karri > 20 percent)\n\t4. Wandoo - stand dominated by wandoo')
    fmis_code = models.CharField(max_length=2, blank=True, null=True, db_comment='FMIS code for the silvic type')
    resid_ba_ge15 = models.BooleanField(blank=True, null=True, db_comment='Yes if the residual Basal Area can be presumed to be greater than or equal to 15 m2/ha\n\n**QUERY RELEVANCE**')
    prescription = models.BooleanField(blank=True, null=True, db_comment='Yes if the silvicultural objective has/will have a prescription attached.')
    issues = models.TextField(blank=True, null=True, db_comment='Any issues in definition or database maintenance')
    untreated_outcome = models.CharField(max_length=20, blank=True, null=True, db_comment='Silvic to apply if stand not successfully treated with required treatment\n\nAlthough not required for FMP24 silvics, this needs to be retained for clarity & interpretation of historic data')
    auth_source = models.CharField(max_length=50, blank=True, null=True, db_comment="Source document authorising the patch objective\nFormerly 'Source'")
    record_stds = models.TextField(blank=True, null=True, db_comment="Standards and specifications for recording attributes and mapping patches\nFormerly 'Recording Stds'")
    addition_attribs = models.BooleanField(blank=True, null=True, db_comment="Yes if additional attributes are record-able for the silvicultural objective.  In other words if entries for silvics_xtra are defined\nFormerly 'AdditionAttribs'")
    type = models.CharField(max_length=50, blank=True, null=True, db_comment='Name of any subtype to be recorded for the objective as additional information/attibute.\n\nThis is an informational item for the user, providing a meaningful label for the group of subtypes in the silvic_subtypes table.')
    reference1_label = models.CharField(max_length=50, blank=True, null=True, db_comment="Name of the first text attribute to be recorded for the objective as additional information/attibute\n\nThis item provides a form label to be used for cohort_Xtra.reference1 item.  For example, a value of 'Heritage Register' (for U-CULTBUF SILVIC) means that cohort_xtra.reference1 is labelled as 'Heritage Register'  for this silvic in the cohort_xtra table, and in the cohort_xtra table 'reference1' is populated with a heritage register name or ID.")
    reference2_label = models.CharField(max_length=50, blank=True, null=True, db_comment="Name of the second text attribute to be recorded for the objective as additional information/attibute\n\n(refer to 'reference1' for more info)")
    category1_label = models.CharField(max_length=50, blank=True, null=True, db_comment="Name of the first category attribute to be recorded for the objective as additional information/attibute\n\nThis is distinct from 'reference1'; in this case a list or drop-own set of values are provided in silvic_code1 table")
    category2_label = models.CharField(max_length=50, blank=True, null=True, db_comment='Name of the second category attribute to be recorded for the objective as additional information/attibute\n\nsee [code2] for more detail/information')
    qty1_label = models.CharField(max_length=50, blank=True, null=True, db_comment='Name of the first numeric attribute to be recorded for the objective as additional information/attibute')
    qty2_label = models.CharField(max_length=50, blank=True, null=True, db_comment='Name of the second numeric attribute to be recorded for the objective as additional information/attibute')
    created_on = models.DateTimeField(blank=True, null=True, db_comment='Date when objective (row) first created')
    created_by = models.CharField(max_length=50, blank=True, null=True, db_comment='Username of person creating the silvicultural objective')
    updated_on = models.DateTimeField(blank=True, null=True, db_comment="formerly 'Modified'\n\nDate when objective was last updated")
    updated_by = models.CharField(max_length=50, blank=True, null=True, db_comment="formerly 'Modified By'\n\nUsername of person modifying the silvicultural objective")
    effective_from = models.DateTimeField(blank=True, null=True, db_comment='Date from when the silvicultural objective became allowable for use.')
    effective_to = models.DateTimeField(blank=True, null=True, db_comment='Date the Silvicultural objective was revoked from use.')
    authorised_by = models.CharField(max_length=50, blank=True, null=True, db_comment="Name or authority authorising the use of the silvicultural objective from the 'effective from' date")
    revoked_by = models.CharField(max_length=50, blank=True, null=True, db_comment="Name of person revoking the objective, i.e. providing the 'effective to' date")
    zann_rpt_category = models.CharField(db_column='zann_rpt category', max_length=50, blank=True, null=True, db_comment="Category to use in annual and related reports\nformerly 'Report Category'\n\nProbably should use a lookup table")  # Field renamed to remove unsuitable characters.
    zothr_report_category = models.CharField(max_length=50, blank=True, null=True, db_comment="Category to use in ad hoc and other reports\nFormerly 'Report Category2'\n\nProbably should use a lookup table, although a free text entry might allow flexibility for ad hoc reporting.")
    zustncolour = models.CharField(db_column='zUstnColour', max_length=10, blank=True, null=True, db_comment='MicroStation pen colour for hatching/colour fill')  # Field name made lowercase.
    zmapinfo_id = models.IntegerField(db_column='zMapInfo_ID', blank=True, null=True, db_comment='primary key for MapInfo')  # Field name made lowercase.
    z2report = models.BooleanField(db_column='z2Report', blank=True, null=True, db_comment='Tick if objective required for this query\n\nProvides facility for users to individually select silvics for query/report, in a given session.\n\n**Probably not relevant in v3 context/environment')  # Field name made lowercase.
    zavailable = models.BooleanField(db_column='zAvailable', blank=True, null=True, db_comment="Yes if objective is available for current use, No if objective has been revoked and is unavailable.\n\nThis is replaced by 'effective from' & 'effective to' which provide a more flexible means of managing the status of silvic objectives.")  # Field name made lowercase.
    zobjective = models.CharField(db_column='zObjective', max_length=150, blank=True, null=True, db_comment="Precise statement of objective for patch / vegetation\n\n**This should be properly articulated in the definition; I don't think it is used in any query/report")  # Field name made lowercase.
    ztimeframe = models.CharField(max_length=50, blank=True, null=True, db_comment='Definition or description of any timeframe attribute to be recorded for the objective.\n\nUnless this is referenced in a query/report (or may be), then possibly this column could be relegated.')

    class Meta:
        db_table = 'objective_lkp'
        db_table_comment = "Lookup table for silvic codes, i.e. silvicultural / management objectives\nMaybe this should be renamed to 'objective_lkp' (and alias = obj)\n\n**Remove reporting categories to separate reporting table(s)\n\n**To create single lookup table for category values; columns:\n\n\t1. category_id = pk (seq)\n\t2. obj_code = FK  to cohort_extra table\n\t3. target_column = {category1, category2}\n\t4. catgry_value = value(s) for the objective and category (e.g. full, partial)\n\t5. description = full definition of the category value;\ne.g. FULL => thinning to full crop tree density, no culls used to achieve residual ba\n\t6. fmis_code = code for use in exports to FMIS\n\n\nCOLUMNS #2, #3, #4 have a uniqueness constraint\n\nThis table replaces both of silvic_code1 and silvic_code2"


'''
'''

