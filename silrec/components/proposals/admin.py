from typing import Any

from django.contrib import admin
from django.db.models import TextField
from django.forms import Textarea
from django.http import HttpResponseRedirect
from django.http.request import HttpRequest
from django.urls import re_path

from silrec import helpers
from silrec.components.main.models import ApplicationType, SystemMaintenance
from silrec.components.proposals import forms, models
#from silrec.components.proposals.forms import SectionChecklistForm
#from silrec.components.proposals.models import ChecklistQuestion
#from silrec.utils import create_helppage_object


@admin.register(models.ProposalType)
class ProposalTypeAdmin(admin.ModelAdmin):
    list_display = ["code", "description"]
    ordering = ("code",)
    list_filter = ("code",)


class ProposalDocumentInline(admin.TabularInline):
    model = models.ProposalDocument
    extra = 0


@admin.register(models.AmendmentReason)
class AmendmentReasonAdmin(admin.ModelAdmin):
    list_display = ["reason"]


#@admin.register(models.Proposal)
#class ProposalAdmin(admin.ModelAdmin):
#    list_display = [
#        "lodgement_number",
#        "application_type",
#        "proposal_type",
#        "processing_status",
#        "submitter",
#        #"assigned_officer",
#        #"applicant",
#    ]
#    inlines = [
#        ProposalDocumentInline,
#    ]


@admin.register(SystemMaintenance)
class SystemMaintenanceAdmin(admin.ModelAdmin):
    list_display = ["name", "description", "start_date", "end_date", "duration"]
    ordering = ("start_date",)
    readonly_fields = ("duration",)
    form = forms.SystemMaintenanceAdminForm


@admin.register(ApplicationType)
class ApplicationTypeAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "order",
        "visible",
    ]
    ordering = ("order",)
    readonly_fields = ["name"]


@admin.register(models.ProposalOfficerGroup)
class ProposalOfficerGroupAdmin(admin.ModelAdmin):
    list_display = ['name']
    filter_horizontal = ('members',)
    form = forms.ProposalAssessorGroupAdminForm
    #readonly_fields = ['default']

    def has_delete_permission(self, request, obj=None):
        if obj and obj.default:
            return False
        return super(ProposalOfficerGroupAdmin, self).has_delete_permission(request, obj)

    def has_add_permission(self, request):
        # Check if any records already exist
        if models.ProposalOfficerGroup.objects.exists():
            return False
        return True


@admin.register(models.ProposalAssessorGroup)
class ProposalAssessorGroupAdmin(admin.ModelAdmin):
    list_display = ['name']
    filter_horizontal = ('members',)
    form = forms.ProposalAssessorGroupAdminForm
    #readonly_fields = ['default']

    def has_delete_permission(self, request, obj=None):
        if obj and obj.default:
            return False
        return super(ProposalAssessorGroupAdmin, self).has_delete_permission(request, obj)

    def has_add_permission(self, request):
        # Check if any records already exist
        if models.ProposalAssessorGroup.objects.exists():
            return False
        return True


@admin.register(models.ProposalReviewerGroup)
class ProposalReviewerGroupAdmin(admin.ModelAdmin):
    list_display = ['name']
    filter_horizontal = ('members',)
    form = forms.ProposalReviewerGroupAdminForm
    #readonly_fields = ['default']

    def has_delete_permission(self, request, obj=None):
        if obj and obj.default:
            return False
        return super(ProposalReviewerGroupAdmin, self).has_delete_permission(request, obj)

    def has_add_permission(self, request):
        # Check if any records already exist
        if models.ProposalReviewerGroup.objects.exists():
            return False
        return True


@admin.register(models.ProposalAdminGroup)
class ProposalAdminGroupAdmin(admin.ModelAdmin):
    list_display = ['name']
    filter_horizontal = ('members',)
    form = forms.ProposalAdminGroupAdminForm
    #readonly_fields = ['default']

    def has_delete_permission(self, request, obj=None):
        if obj and obj.default:
            return False
        return super(ProposalAdminGroupAdmin, self).has_delete_permission(request, obj)

    def has_add_permission(self, request):
        # Check if any records already exist
        if models.ProposalAdminGroup.objects.exists():
            return False
        return True