from django.contrib import admin
from django.conf import settings
from silrec.components.main.models import (
    OrganisationLkp,
    TaskLkp,
    TasksAttLkp,
    ObjectiveLkp,
    SpeciesApiLkp,
    RegenerationMethodsLkp,
    TreatmentStatusLkp,
    RescheduleReasonsLkp,
    SpatialPrecisionLkp,
    CohortMetricsLkp,
    MachineLkp,
)

from django.utils import timezone
from datetime import datetime, timedelta

admin.autodiscover()

@admin.register(OrganisationLkp)
class OrganisationLkpAdmin(admin.ModelAdmin):
    list_display = ["organisation", "description"]
    #list_filter = ["system"]
    search_fields = ["organisation", "description"]

@admin.register(TaskLkp)
class  TaskLkpAdmin(admin.ModelAdmin):
    list_display = ["task", "task_name", "category1_label", "category2_label", "category3_label", "category4_label"]
    search_fields = ["task", "task_name"]


@admin.register(TasksAttLkp)
class  TasksAttLkpAdmin(admin.ModelAdmin):
    list_display = ["addition_attrib", "description"]
    search_fields = ["addition_attrib", "description"]


@admin.register(ObjectiveLkp)
class ObjectiveLkpAdmin(admin.ModelAdmin):
    list_display = ["obj_code", "definition", "cut", "forest_type", "fmis_code"]
    search_fields = ["obj_code", "fmis_code", "cut", "forest_type", "fmis_code"]


@admin.register(SpeciesApiLkp)
class SpeciesApiLkpAdmin(admin.ModelAdmin):
    list_display = ["species", "short_description", "fmiscode_species", "fmiscode_type"]
    search_fields = ["species", "short_description", "fmiscode_species", "fmiscode_type"]


@admin.register(RegenerationMethodsLkp)
class RegenerationMethodsLkpAdmin(admin.ModelAdmin):
    list_display = ["regen_method", "description"]
    search_fields = ["regen_method", "description"]


@admin.register(SpatialPrecisionLkp)
class SpatialPrecisionLkpAdmin(admin.ModelAdmin):
    list_display = ["precision_code", "resolution", "description"]
    search_fields = ["precision_code", "resolution", "description"]


@admin.register(TreatmentStatusLkp)
class TreatmentStatusLkpAdmin(admin.ModelAdmin):
    list_display = ["status", "name"]
    search_fields = ["status", "name"]


@admin.register(RescheduleReasonsLkp)
class RescheduleReasonsLkpAdmin(admin.ModelAdmin):
    list_display = ["rescheduled_reason", "description"]
    search_fields = ["rescheduled_reason", "description"]


@admin.register(CohortMetricsLkp)
class CohortMetricsLkpAdmin(admin.ModelAdmin):
    list_display = ["name", "definition", "rating", "value", "method"]
    search_fields = ["name", "definition", "rating", "value", "method"]


@admin.register(MachineLkp)
class MachineLkpAdmin(admin.ModelAdmin):
    list_display = ["machine_id", "manufacturer", "model", "machine_type"]
    search_fields = ["machine_id", "manufacturer", "model", "machine_type"]

'''
 public | cohort_metrics_lkp       | table | postgres
 public | machine_lkp              | table | postgres
 public | objective_lkp            | table | postgres
 public | organisation_lkp         | table | postgres
 public | regeneration_methods_lkp | table | postgres
 public | reschedule_reasons_lkp   | table | postgres
 public | spatial_precision_lkp    | table | postgres
 public | species_api_lkp          | table | postgres
 public | task_lkp                 | table | postgres
 public | tasks_att_lkp            | table | postgres
 public | treatment_status_lkp     | table | postgres
'''
