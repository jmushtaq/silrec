from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.db.models import F, JSONField, Max, Min, Q
from django.db.models.functions import Cast
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.contrib.auth.models import User
from django.contrib.gis.db.models import MultiPolygonField
from django.contrib.gis.db.models.fields import PolygonField
from django.contrib.gis.db.models.functions import Area

import json
import geopandas as gpd
from rest_framework import serializers
from reversion.models import Version

from dirtyfields import DirtyFieldsMixin

from silrec.components.main.models import (
    Document,
    ApplicationType,
    SecureFileField,
    RevisionedMixin,
)
from silrec.components.forest_blocks.models import (
    Polygon,
)


def update_proposal_doc_filename(instance, filename):
    return f"proposals/{instance.proposal.id}/documents/{filename}"

def update_proposal_comms_log_filename(instance, filename):
    return f"proposals/{instance.log_entry.proposal.id}/{filename}"


class AdditionalDocumentType(RevisionedMixin):
    name = models.CharField(max_length=255, null=True, blank=True)
    help_text = models.CharField(max_length=255, null=True, blank=True)
    enabled = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Additional Document Type"
        app_label = "silrec"
        ordering = ["name"]


class DefaultDocument(Document):
    input_name = models.CharField(max_length=255, null=True, blank=True)
    can_delete = models.BooleanField(
        default=True
    )  # after initial submit prevent document from being deleted
    visible = models.BooleanField(
        default=True
    )  # to prevent deletion on file system, hidden and still be available in history

    class Meta:
        app_label = "silrec"
        abstract = True

    def delete(self):
        if self.can_delete:
            return super().delete()
        logger.info(
            "Cannot delete existing document object after Application has been submitted "
            "(including document submitted before Application pushback to status Draft): {}".format(
                self.name
            )
        )

class ProposalDocument(Document):
    proposal = models.ForeignKey(
        "Proposal", related_name="supporting_documents", on_delete=models.CASCADE
    )
    _file = SecureFileField(upload_to=update_proposal_doc_filename, max_length=512)
    input_name = models.CharField(max_length=255, null=True, blank=True)
    can_delete = models.BooleanField(
        default=True
    )  # after initial submit prevent document from being deleted
    can_hide = models.BooleanField(
        default=False
    )  # after initial submit, document cannot be deleted but can be hidden
    hidden = models.BooleanField(
        default=False
    )  # after initial submit prevent document from being deleted

    class Meta:
        app_label = "silrec"
        verbose_name = "Application Document"


class ShapefileDocumentQueryset(models.QuerySet):
    """Using a custom manager to make sure shapfiles are removed when a bulk .delete is called
    as having multiple files with the shapefile extensions in the same folder causes issues.
    """

    def delete(self):
        for obj in self:
            obj._file.delete()
        super().delete()


class ShapefileDocument(Document):
    objects = ShapefileDocumentQueryset.as_manager()

    proposal = models.ForeignKey(
        "Proposal", related_name="shapefile_documents", on_delete=models.CASCADE
    )
    _file = SecureFileField(upload_to=update_proposal_doc_filename, max_length=500)
    input_name = models.CharField(max_length=255, null=True, blank=True)
    can_delete = models.BooleanField(
        default=True
    )  # after initial submit prevent document from being deleted
    can_hide = models.BooleanField(
        default=False
    )  # after initial submit, document cannot be deleted but can be hidden
    hidden = models.BooleanField(
        default=False
    )  # after initial submit prevent document from being deleted

    def delete(self):
        if self.can_delete:
            self._file.delete()
            return super().delete()
        logger.info(
            "Cannot delete existing document object after Proposal has been submitted "
            "(including document submitted before Proposal pushback to status Draft): {}".format(
                self.name
            )
        )

    class Meta:
        app_label = "silrec"


class ProposalAdditionalDocumentType(models.Model):
    proposal = models.ForeignKey(
        'Proposal', on_delete=models.CASCADE, related_name="additional_document_types"
    )
    additional_document_type = models.ForeignKey(
        AdditionalDocumentType, on_delete=models.CASCADE
    )

    class Meta:
        app_label = "silrec"


class ProposalType(models.Model):
    PROPOSAL_TYPE_NEW = "new"
    PROPOSAL_TYPE_RENEWAL = "renewal"
    PROPOSAL_TYPE_AMENDMENT = "amendment"
    PROPOSAL_TYPE_MIGRATION = "migration"
    PROPOSAL_TYPES = [
        (PROPOSAL_TYPE_NEW, "New Proposal"),
        (PROPOSAL_TYPE_AMENDMENT, "Amendment"),
        (PROPOSAL_TYPE_RENEWAL, "Renewal"),
        (PROPOSAL_TYPE_MIGRATION, "Migration"),
    ]

    # class ProposalType(RevisionedMixin):
    code = models.CharField(max_length=30, blank=True, null=True)
    description = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        # return 'id: {} code: {}'.format(self.id, self.code)
        return self.description

    class Meta:
        app_label = "silrec"


#class ProposalManager(models.Manager):
#    def get_queryset(self):
#        return (
#            super()
#            .get_queryset()
#            .select_related(
#                "proposal_type", "org_applicant", "application_type", "approval"
#            )
#        )


class ProposalAssessorGroup(models.Model):
    name = models.CharField(max_length=255)
    members = models.ManyToManyField(User)
    default = models.BooleanField(default=False)

    class Meta:
        app_label = 'silrec'

    def __str__(self):
        return self.name

    def clean(self):
        try:
            default = ProposalAssessorGroup.objects.get(default=True)
        except ProposalAssessorGroup.DoesNotExist:
            default = None

        if default and self.default:
            raise ValidationError('There can only be one default proposal assessor group')

    def member_is_assigned(self, member):
        for p in self.current_proposals:
            if p.assigned_officer == member:
                return True
        return False

    @property
    def current_proposals(self):
        assessable_states = ['with_assessor','with_assessor_tre','with_assessor_requirements']
        return Proposal.objects.filter(processing_status__in=assessable_states)

    @property
    def members_email(self):
        return [i.email for i in self.members.all()]


class Proposal(RevisionedMixin, DirtyFieldsMixin):
    #objects = ProposalManager()

    MODEL_PREFIX = "P"

    PROCESSING_STATUS_DRAFT = "draft"
    PROCESSING_STATUS_AMENDMENT_REQUIRED = "amendment_required"
    PROCESSING_STATUS_WITH_ASSESSOR = "with_assessor"
    PROCESSING_STATUS_WITH_ASSESSOR_TREATMENTS = "with_assessor_treatments"
    PROCESSING_STATUS_WITH_ASSESSOR_TASKS = "with_assessor_tasks"
    PROCESSING_STATUS_WITH_REVIEWER = "with_reviewer"
    PROCESSING_STATUS_REVIEW_COMPLETED = "review_Completed"
    PROCESSING_STATUS_DECLINED = "declined"
    PROCESSING_STATUS_DISCARDED = "discarded"
    PROCESSING_STATUS_CHOICES = (
        (PROCESSING_STATUS_DRAFT, "Draft"),
        (PROCESSING_STATUS_AMENDMENT_REQUIRED, "Amendment Required"),
        (PROCESSING_STATUS_WITH_ASSESSOR, "With Assessor"),
        (PROCESSING_STATUS_WITH_ASSESSOR_TREATMENTS, "With Assessor (Treatments)"),
        (PROCESSING_STATUS_WITH_ASSESSOR_TASKS, "With Assessor (Tasks)"),
        (PROCESSING_STATUS_WITH_REVIEWER, "With Reviewer"),
        (PROCESSING_STATUS_REVIEW_COMPLETED, "Review Completed"),
        (PROCESSING_STATUS_DECLINED, "Declined"),
        (PROCESSING_STATUS_DISCARDED, "Discarded"),
    )

    ASSESSABLE_STATES = [
        PROCESSING_STATUS_WITH_ASSESSOR,
        PROCESSING_STATUS_WITH_ASSESSOR_TREATMENTS,
        PROCESSING_STATUS_WITH_ASSESSOR_TREATMENTS
    ]

    REVIEWABLE_STATES = [PROCESSING_STATUS_WITH_REVIEWER]

    proposal_type = models.ForeignKey(
        ProposalType, blank=True, null=True, on_delete=models.SET_NULL
    )
    proposed_issuance_approval = JSONField(blank=True, null=True)
    lodgement_number = models.CharField(max_length=9, blank=True, default='')
    lodgement_date = models.DateTimeField(blank=True, null=True)
    submitter = models.IntegerField(null=True)  # EmailUserRO
    processing_status = models.CharField(
        "Processing Status",
        max_length=35,
        choices=PROCESSING_STATUS_CHOICES,
        default=PROCESSING_STATUS_CHOICES[0][0],
    )
    prev_processing_status = models.CharField(max_length=30, blank=True, null=True)
    previous_application = models.ForeignKey(
        "self", blank=True, null=True, on_delete=models.SET_NULL
    )
    # Special Fields
    title = models.CharField(max_length=255, null=True, blank=True)
    application_type = models.ForeignKey(ApplicationType, on_delete=models.PROTECT)

    shapefile_json               = JSONField('Source/Submitter (multi) polygon geometry', blank=True, null=True)
    geojson_data_processed       = JSONField('Source Polygon intersected with hist and split (multi) polygon geometry final result', blank=True, null=True)
    geojson_data_processed_iters = JSONField('Source Polygon Intersected with hist and split (multi) polygon geometry - all iterations', blank=True, null=True)
    migrated = models.BooleanField(default=False)

    class Meta:
        app_label = "silrec"
        verbose_name = "Proposal"

    def save(self, *args, **kwargs):
        # django reversion before they are overwritten by super() below
        original_processing_status = self._original_state['processing_status']

        # Handle shapefile JSON data if passed in kwargs
        shapefile_json = kwargs.pop('shapefile_json', None)
        if shapefile_json:
            self.shapefile_json = shapefile_json
        super().save(*args, **kwargs)

        if self.lodgement_number == '':
            self.lodgement_number = 'P{0:06d}'.format(self.pk)
            self.save()

        # If the processing_status has changed then add a reversion comment
        # so we have a way of filtering based on the status changing
        if self.processing_status != original_processing_status:
            self.save(version_comment=f'processing_status: {self.processing_status}')

    @property
    def submitter_obj(self):
        return User.objects.get(id=self.submitter)

    def __assessor_group(self):
            return ProposalAssessorGroup.objects.get(default=True)

    def __approver_group(self):
        return ProposalApproverGroup.objects.get(default=True)

    @property
    def can_user_view(self):
        return True

    @property
    def can_user_edit(self):
        """ :return: True if the application is in one of the editable status.
        """
        return self.customer_status in self.CUSTOMER_EDITABLE_STATE

    @property
    def can_user_view(self):
        """ :return: True if the application is in one of the approved status.
        """
        return self.customer_status in self.CUSTOMER_VIEWABLE_STATE

    def can_assess(self,user):
        if self.processing_status in self.ASSESSABLE_STATES:
            return self.__assessor_group() in user.proposalassessorgroup_set.all()
        elif self.processing_status in self.REVIEWABLE_STATES:
            return self.__reviewer_group() in user.proposalreviewergroup_set.all()
        return False

    @property
    def shp_to_gdf(self):
        return gpd.read_file(json.dumps(self.shapefile_json))


class ProposalGeometryManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .annotate(area=Area(Cast("polygon", PolygonField(geography=True))))
        )


class ProposalGeometry(models.Model):
    SOURCE_CHOICE_APPLICANT = "proponent"
    SOURCE_CHOICE_ASSESSOR = "assessor"
    SOURCE_CHOICES = (
        (SOURCE_CHOICE_APPLICANT, "Proponent"),
        (SOURCE_CHOICE_ASSESSOR, "Assessor"),
    )

    objects = ProposalGeometryManager()

    proposal = models.ForeignKey(
        Proposal, on_delete=models.CASCADE, related_name="proposalgeometry"
    )
    polygon = PolygonField(srid=4326, blank=True, null=True)
    intersects = models.BooleanField(default=False)
    copied_from = models.ForeignKey(
        "self", on_delete=models.SET_NULL, blank=True, null=True
    )
    drawn_by = models.IntegerField(blank=True, null=True)  # EmailUserRO
    source_type = models.CharField(
        max_length=255, blank=True, choices=SOURCE_CHOICES, default=SOURCE_CHOICES[0][0],
    )
    source_name = models.CharField(max_length=255, blank=True)
    locked = models.BooleanField(default=False)

    class Meta:
        app_label = "silrec"

    @property
    def area_sqm(self):
        if not hasattr(self, "area") or not self.area:
            logger.warning(f"ProposalGeometry: {self.id} has no area")
            return None
        return self.area.sq_m

    @property
    def area_sqhm(self):
        if not hasattr(self, "area") or not self.area:
            logger.warning(f"ProposalGeometry: {self.id} has no area")
            return None
        return self.area.sq_m / 10000


class PolygonHistory(models.Model):
    ''' Iteratively stores the Intersecting Historical Polygons (from forest_blocks.Polygon) at each base polygon split.
        Updates the version_id at each NEW base polygon split.
    '''
    #polygon_id = models.AutoField(primary_key=True, db_comment='Primary key')
    version_id = models.IntegerField()
    geom = MultiPolygonField(srid=28350)
    proposal = models.ForeignKey(
        Proposal, on_delete=models.CASCADE, related_name="polygonhistory"
    )
    polygon_src = models.OneToOneField(Polygon, on_delete=models.DO_NOTHING, related_name='polygon', blank=True, null=True)
    name = models.CharField(max_length=10, blank=True, null=True)
    area_ha = models.FloatField(blank=True, null=True, db_comment='Area in ha of the polygon')
    created_on = models.DateTimeField(auto_now_add=True, null=False, blank=False)
    created_by = models.CharField(max_length=50, blank=True, null=True, db_comment='user ID')
    updated_on = models.DateTimeField(auto_now_add=True, null=False, blank=False)
    updated_by = models.CharField(max_length=50, blank=True, null=True, db_comment='user ID')
    closed = models.DateField(blank=True, null=True)
    reason_closed = models.CharField(max_length=250, blank=True, null=True)
    info = JSONField(blank=True, null=True)

#    compartment = models.ForeignKey(Compartments, on_delete=models.CASCADE, db_column='compartment', db_comment='foreign key to compartment and blocks table')
#    sp_code = models.ForeignKey(SpatialPrecisionLkp, on_delete=models.CASCADE, db_column='sp_code', blank=True, null=True, db_comment='Code for spatial precision of mapping or capture method\nforeign key to lookup table')
#    zcoupeid = models.CharField(db_column='zCoupeID', max_length=5, blank=True, null=True)  # Field name made lowercase.
#    zstandno = models.CharField(db_column='zStandNo', max_length=5, blank=True, null=True)  # Field name made lowercase.
#    zmslink = models.FloatField(db_column='zMSLink', blank=True, null=True)  # Field name made lowercase.
#    zfea_id = models.CharField(max_length=7, blank=True, null=True, db_comment='Operation Code defining or causing creation of the patch.\nWas Opcode. Now referred to as FEA ID on plan (DW)')

    class Meta:
        app_label = "silrec"

#    def save(self, *args, **kwargs):
#        poly_history_qs = PolygonHistory.objects.filter(proposal_id=self.proposal.id)
#        self.version_id = poly_history_qs.aggregate(models.Max('version_id'))['version_id__max'] + 1 if not poly_history_qs.empty else 0
#        if self.geom:
#            self.area_ha = self.geom.area/10000
#
#        super().save(*args, **kwargs)


class AmendmentReason(models.Model):
    reason = models.CharField("Reason", max_length=125)

    class Meta:
        app_label = "silrec"
        verbose_name = "Proposal Amendment Reason"  # display name in Admin
        verbose_name_plural = "Proposal Amendment Reasons"

    def __str__(self):
        return self.reason

class ProposalRequest(models.Model):
    proposal = models.ForeignKey(
        Proposal, related_name="proposalrequest_set", on_delete=models.CASCADE
    )
    subject = models.CharField(max_length=200, blank=True)
    text = models.TextField(blank=True)
    # fficer = models.ForeignKey(EmailUser, null=True, on_delete=models.SET_NULL)
    officer = models.IntegerField(null=True)  # EmailUserRO

    def __str__(self):
        return f"{self.subject} - {self.text}"

    class Meta:
        app_label = "silrec"


class AmendmentRequest(ProposalRequest):
    STATUS_CHOICE_REQUESTED = "requested"
    STATUS_CHOICE_AMENDED = "amended"
    STATUS_CHOICES = (
        (STATUS_CHOICE_REQUESTED, "Requested"),
        (STATUS_CHOICE_AMENDED, "Amended"),
    )

    status = models.CharField(
        "Status", max_length=30, choices=STATUS_CHOICES, default=STATUS_CHOICES[0][0]
    )
    reason = models.ForeignKey(
        AmendmentReason, blank=True, null=True, on_delete=models.SET_NULL
    )

    class Meta:
        app_label = "silrec"

#    @transaction.atomic
#    def generate_amendment(self, request):
#        if not self.proposal.can_assess(request.user):
#            raise exceptions.ProposalNotAuthorized()
#
#        if self.status == AmendmentRequest.STATUS_CHOICE_REQUESTED:
#            proposal = self.proposal
#            if proposal.processing_status != Proposal.PROCESSING_STATUS_DRAFT:
#                proposal.processing_status = Proposal.PROCESSING_STATUS_DRAFT
#                proposal.save(
#                    version_comment=f"Proposal amendment requested {request.data.get('reason', '')}"
#                )
#
#                # Mark any related documents that the assessor may have attached to the proposal as not delete-able
#                self.proposal.mark_documents_not_deleteable()
#
#            # Create a log entry for the proposal
#            proposal.log_user_action(
#                ProposalUserAction.ACTION_ID_REQUEST_AMENDMENTS, request
#            )
#
#            # Create a log entry for the applicant
#            proposal.applicant.log_user_action(
#                ProposalUserAction.ACTION_REQUESTED_AMENDMENT.format(proposal.id),
#                request,
#            )
#
#            # send email
#            send_amendment_email_notification(self, request, self.proposal)
#
#        self.save()
#
#    def user_has_object_permission(self, user_id):
#        return self.proposal.user_has_object_permission(user_id)


