import datetime
import logging

from django.conf import settings
from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext as _
from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from silrec.components.main.serializers import (
    UserSerializerSimple,
    ApplicationTypeSerializer,
    #CommunicationLogEntrySerializer,
    #EmailUserSerializer,
)
from silrec.components.proposals.models import (
    AmendmentRequest,
    Proposal,
    #ProposalGeometry,
    ProposalType,
    #ProposalUserAction,
    #Referral,
    #SectionChecklist,
)

from silrec.helpers import (
    is_internal,
)


class ProposalTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProposalType
        fields = (
            "id",
            "code",
            "description",
        )

    def get_activities(self, obj):
        return obj.activities.names()


class BaseProposalSerializer(serializers.ModelSerializer):
    model_name = serializers.CharField(read_only=True)
    proposal_type = ProposalTypeSerializer()
    application_type = ApplicationTypeSerializer()
    #accessing_user_roles = serializers.SerializerMethodField()
    #proposalgeometry = ProposalGeometrySerializer(many=True, read_only=True)
    #applicant = serializers.SerializerMethodField()
    lodgement_date_display = serializers.SerializerMethodField()
    #applicant = serializers.SerializerMethodField()
    submitter_obj = UserSerializerSimple()
    #groups = serializers.SerializerMethodField(read_only=True)
    #allowed_assessors = EmailUserSerializer(many=True)
    #details_url = serializers.SerializerMethodField(read_only=True)
    details_url = serializers.SerializerMethodField(read_only=True)
    readonly = serializers.SerializerMethodField(read_only=True)
    #approval = serializers.SerializerMethodField(read_only=True, allow_null=True)
    # Gis data fields
#    identifiers = serializers.SerializerMethodField()
#    names = serializers.SerializerMethodField()
#    acts = serializers.SerializerMethodField()
#    tenures = serializers.SerializerMethodField()
#    categories = serializers.SerializerMethodField()
#    regions = serializers.SerializerMethodField()
#    districts = serializers.SerializerMethodField()
#    lgas = serializers.SerializerMethodField()

    class Meta:
        model = Proposal
        fields = (
            "id",
            "model_name",
            #"allowed_assessors",
            "application_type",
            "proposal_type",
            "title",
            "processing_status",
            "processing_status_id",
            #"submitter_obj",
            #"assigned_officer",
            "previous_application",
            #"get_history",
            "lodgement_date",
            "lodgement_number",
            "details_url",
            #"supporting_documents",
            #"requirements",
            "readonly",
            #"approval",
#            "can_user_edit",
#            "can_user_view",
#            "documents_url",
#            "reference",
#            "can_officer_process",
#            "accessing_user_roles",
#            "added_internally",
#            "details_text",
#            "proposalgeometry",
#            "groups",
#            "details_url",
        )
        #read_only_fields = ("supporting_documents",)

#    def get_groups(self, obj):
#        group_ids = obj.groups.values_list("group__id", flat=True)
#        group_qs = Group.objects.filter(id__in=group_ids).values("id", "name")
#        return GroupSerializer(group_qs, many=True).data

    def get_lodgement_date_display(self, obj):
        if obj.lodgement_date:
            return (
                obj.lodgement_date.strftime("%d/%m/%Y")
                + " at "
                + obj.lodgement_date.strftime("%-I:%M %p")
            )

    def get_details_url(self, obj):
        request = self.context["request"]
        if request.user.is_authenticated:
            if is_internal(request):
                return reverse("internal-proposal-detail", kwargs={"pk": obj.id})
            else:
                return reverse(
                    "external-proposal-detail", kwargs={"proposal_pk": obj.id}
                )

#    def get_applicant(self, obj):
#        if isinstance(obj.applicant, Organisation):
#            return obj.applicant.ledger_organisation_name
#        elif isinstance(obj.applicant, ProposalApplicant):
#            return obj.applicant.full_name
#        elif isinstance(obj.applicant, EmailUser):
#            return f"{obj.applicant.first_name} {obj.applicant.last_name}"
#        else:
#            return "Applicant not yet assigned"

#    def get_applicant(self, obj):
#        return UserSerializerSimple(obj.applicant).data

#    def get_documents_url(self, obj):
#        return "/media/{}/proposals/{}/documents/".format(
#            settings.MEDIA_APP_DIR, obj.id
#        )

    def get_readonly(self, obj):
        return False

    def get_submitter_obj(self, obj):
        if obj.submitter:
            return obj.submitter_obj
        else:
            return None

    def get_processing_status(self, obj):
        #return obj.get_processing_status_display()
        return obj.get_processing_status_display()

#    def get_accessing_user_roles(self, proposal):
#        request = self.context.get("request")
#        accessing_user = request.user
#        roles = []
#
#        for choice in GROUP_NAME_CHOICES:
#            group = SystemGroup.objects.get(name=choice[0])
#            ids = group.get_system_group_member_ids()
#            if accessing_user.id in ids:
#                roles.append(group.name)
#
#        referral_ids = list(proposal.referrals.values_list("referral", flat=True))
#        if accessing_user.id in referral_ids:
#            roles.append("referral")
#
#        return roles

#class ProposalSerializer(serializers.ModelSerializer):
#
#    class Meta:
#        model = Proposal
#        #fields = "__all__"
#        fields = (
#            "id",
#            "model_name",
#        )

#
class ProposalSerializer(BaseProposalSerializer):
    #submitter_obj = serializers.SerializerMethodField(read_only=True)
    model_name = serializers.SerializerMethodField(read_only=True)
    submitter_obj = UserSerializerSimple()
    processing_status = serializers.SerializerMethodField(read_only=True)
    processing_status_id = serializers.SerializerMethodField(read_only=True)
    # Had to add assessor mode and lodgement versions for this serializer to work for
    # external user that is a referral
    assessor_mode = serializers.SerializerMethodField(read_only=True)
    details_url = serializers.SerializerMethodField(read_only=True)
    #lodgement_versions = serializers.SerializerMethodField(read_only=True)
    #referrals = ProposalReferralSerializer(many=True)
    #additional_document_types = ProposalAdditionalDocumentTypeSerializer(
    #    many=True, read_only=True
    #)
    #assessor_assessment = serializers.SerializerMethodField(read_only=True)
    proposalgeometry = serializers.SerializerMethodField(read_only=True)
    proposalgeometry_sep = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Proposal
        #fields = "__all__"
        fields = (
            "id",
            "model_name",
            #"allowed_assessors",
            "application_type",
            "proposal_type",
            "title",
            "processing_status",
            "processing_status_id",
            "submitter_obj",
            "previous_application",
            "lodgement_date",
            "lodgement_number",
            "details_url",
            "readonly",
            "assessor_mode",
            "processing_status_id",
            "proposalgeometry",
            "proposalgeometry_sep",
        )

    def get_proposalgeometry(self, obj):
        return obj.shapefile_json

    def get_proposalgeometry_sep(self, obj):
        return obj.shapefile_json

    def get_model_name(self, obj):
        return obj._meta.model_name

    def get_processing_status_id(self, obj):
        return obj.get_processing_status_display()

    def get_assessor_mode(self, obj):
        return True

    def get_readonly(self, obj):
        return obj.can_user_view

    def get_submitter_obj(self, obj):
        if obj.submitter:
            return obj.submitter_obj
        else:
            return None

    def get_details_url(self, obj):
        request = self.context["request"]
        if request.user.is_authenticated:
            if is_internal(request):
                return reverse("internal-proposal-detail", kwargs={"pk": obj.id})
            else:
                return reverse(
                    "external-proposal-detail", kwargs={"proposal_pk": obj.id}
                )


#    def get_proposalgeometry(self, obj):
#        # TODO - JM
#        return {}

class ListProposalMinimalSerializer(serializers.ModelSerializer):
    #proposalgeometry = ProposalGeometrySerializer(many=True, read_only=True)
#    application_type_name_display = serializers.CharField(
#        read_only=True, source="application_type.name"
#    )
    processing_status_display = serializers.CharField(
        read_only=True, source="get_processing_status"
    )
    lodgement_date_display = serializers.DateTimeField(
        read_only=True, format="%d/%m/%Y", source="lodgement_date"
    )

    class Meta:
        model = Proposal
        fields = (
            "id",
            "processing_status",
            "processing_status_display",
            #"proposalgeometry",
            #"application_type_name_display",
            "application_type_id",
            "lodgement_number",
            "lodgement_date",
            "lodgement_date_display",
        )

class ListProposalSerializer(BaseProposalSerializer):
    #submitter = serializers.SerializerMethodField(read_only=True)
    processing_status_id = serializers.SerializerMethodField(read_only=True)
    proposalgeometry = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Proposal
        fields = (
            "id",
            "application_type",
            "proposal_type",
            "title",
            "processing_status",
            "processing_status_id",
            #"review_status",
            "submitter_obj",
            "previous_application",
            #"get_history",
            "lodgement_date",
            "lodgement_number",
            "readonly",
            #"can_user_edit",
            #"can_user_view",
            #"can_officer_process",
            #"allowed_assessors",
            "proposal_type",
            #"accessing_user_can_process",
            #"groups",
            "proposalgeometry",
        )
        # the serverSide functionality of datatables is such that only columns that have
        # field 'data' defined are requested from the serializer. We
        # also require the following additional fields for some of the mRender functions
        datatables_always_serialize = (
            "id",
            "application_type",
            "proposal_type",
            "title",
            "processing_status",
            "processing_status_id",
            "submitter_obj",
            "previous_application",
            "lodgement_date",
            "lodgement_number",
            #"can_user_edit",
            #"can_user_view",
            #"can_officer_process",
            #"accessing_user_can_process",
            #"groups",
        )

    def get_submitter(self, obj):
        if obj.submitter:
            email_user = retrieve_email_user(obj.submitter)
            return EmailUserSerializer(email_user).data
        else:
            return ""

    def get_processing_status_id(self, obj):
        return obj.processing_status

    def get_proposalgeometry(self, obj):
        # TODO - JM
        return {}


