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
)

from django.utils import timezone
from datetime import datetime, timedelta


@admin.register(OrganisationLkp)
class OrganisationLkpAdmin(admin.ModelAdmin):
    list_display = ["organisation", "description"]
    #list_filter = ["system"]
    search_fields = ["organisation"]

@admin.register(TaskLkp)
class  TaskLkpAdmin(admin.ModelAdmin):
    list_display = ["task", "task_name", "category1_label", "category2_label", "category3_label", "category4_label"]
    search_fields = ["task", "task_name"]


@admin.register(TasksAttLkp)
class  TasksAttLkpAdmin(admin.ModelAdmin):
    list_display = ["addition_attrib", "description"]
    search_fields = ["addition_attrib"]


@admin.register(ObjectiveLkp)
class ObjectiveLkpAdmin(admin.ModelAdmin):
    list_display = ["obj_code", "definition", "cut", "forest_type", "fmis_code"]
    search_fields = ["obj_code", "fmis_code"]


@admin.register(SpeciesApiLkp)
class SpeciesApiLkpAdmin(admin.ModelAdmin):
    list_display = ["species", "short_description"] #, "FMIScode_species", "FMIScode_type"]
    search_fields = ["species"] #, "FMIScode_species", "FMIScode_type"]


@admin.register(RegenerationMethodsLkp)
class RegenerationMethodsLkpAdmin(admin.ModelAdmin):
    list_display = ["regen_method", "description"]
    search_fields = ["regen_method"]


@admin.register(SpatialPrecisionLkp)
class SpatialPrecisionLkpAdmin(admin.ModelAdmin):
    list_display = ["precision_code", "resolution", "description"]
    search_fields = ["precision_code", "resolution"]


@admin.register(TreatmentStatusLkp)
class TreatmentStatusLkpAdmin(admin.ModelAdmin):
    list_display = ["status", "name"]
    search_fields = ["status", "name"]


@admin.register(RescheduleReasonsLkp)
class RescheduleReasonsLkpAdmin(admin.ModelAdmin):
    list_display = ["rescheduled_reason", "description"]
    search_fields = ["rescheduled_reason"]

'''
tasklkp
tasksattlkp
objectivelkp
speciesapilkp
organisationlkp
regenerationmethodslkp
spatialprecisionlkp
treatmentstatuslkp
reschedulereasonslkp
'''
