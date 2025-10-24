import logging
from collections import OrderedDict
from datetime import datetime

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import CharField, F, Func, Q, Value
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.cache import cache_page
from rest_framework import serializers, status, views, viewsets
from rest_framework.decorators import action as detail_route
from rest_framework.decorators import action as list_route
from rest_framework.decorators import renderer_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework_datatables.pagination import DatatablesPageNumberPagination
from rest_framework_datatables.renderers import DatatablesRenderer
from rest_framework_datatables.filters import DatatablesFilterBackend
from reversion.models import Version

from silrec.components.proposals.models import (
    Proposal,
    ProposalType,
)

from silrec.components.main.models import (
    ApplicationType,
)

from silrec.components.main.process_document import (
    process_generic_document,
)

from silrec.components.main.utils import (
    validate_map_files,
    populate_gis_data,
)
from silrec.components.proposals.serializers import (
    ProposalSerializer,
    ListProposalMinimalSerializer,
    ListProposalSerializer,
    ProposalTypeSerializer,
)
from silrec.components.main.api import (
    UserActionLoggingViewset,
)
from silrec.components.main.decorators import basic_exception_handler

logger = logging.getLogger(__name__)


class GetApplicationTypeDict(views.APIView):
    renderer_classes = [JSONRenderer,]

    def get(self, request):
        types = ApplicationType.objects.filter(enabled=True)
        if types:
            serializers = ApplicationTypeSerializer(types, many=True)
            return Response(serializers.data)
        else:
            return Response({})


class GetApplicationStatusesDict(views.APIView):
    ''' http://localhost:8001/api/application_statuses_dict?for_filter=true
    '''
    renderer_classes = [
        JSONRenderer,
    ]

    def get(self, request, format=None):
        data = {}

        for_filter = request.query_params.get("for_filter", "")
        for_filter = True if for_filter == "true" else False

        if for_filter:
            application_statuses = [
                {"id": i[0], "text": i[1]} for i in Proposal.PROCESSING_STATUS_CHOICES
            ]

            return Response(application_statuses)
        else:
            internal_application_statuses = [
                {"code": i[0], "description": i[1]}
                for i in Proposal.PROCESSING_STATUS_CHOICES
            ]
            data["internal_statuses"] = internal_application_statuses

#            external_application_statuses = [
#                {"code": i[0], "description": i[1]}
#                for i in Proposal.PROCESSING_STATUS_CHOICES
#            ]
#            data["external_statuses"] = external_application_statuses

            return Response(data)


class GetProposalType(views.APIView):
    renderer_classes = [JSONRenderer,]

    def get(self, request):
        _type = ProposalType.objects.first()
        if _type:
            serializers = ProposalTypeSerializer(_type)
            return Response(serializers.data)
        else:
            return Response(
                {"error": "There is currently no proposal type."},
                status=status.HTTP_404_NOT_FOUND,
            )



#class ProposalFilterBackend(LedgerDatatablesFilterBackend):
class ProposalFilterBackend(DatatablesFilterBackend):
    """
    Custom filters
    """

    def filter_queryset(self, request, queryset, view):
        total_count = queryset.count()

        filter_lodged_from = request.GET.get("filter_lodged_from")
        filter_lodged_to = request.GET.get("filter_lodged_to")
        filter_application_type = (
            request.GET.get("filter_application_type")
            if request.GET.get("filter_application_type") != "all"
            else ""
        )
        filter_application_status = (
            request.GET.get("filter_application_status")
            if request.GET.get("filter_application_status") != "all"
            else ""
        )

        if queryset.model is Proposal:
            if filter_lodged_from:
                filter_lodged_from = datetime.strptime(filter_lodged_from, "%Y-%m-%d")
                queryset = queryset.filter(lodgement_date__gte=filter_lodged_from)
            if filter_lodged_to:
                filter_lodged_to = datetime.strptime(filter_lodged_to, "%Y-%m-%d")
                queryset = queryset.filter(lodgement_date__lte=filter_lodged_to)
            if filter_application_type:
                queryset = queryset.filter(application_type_id=filter_application_type)
            if filter_application_status:
                queryset = queryset.filter(processing_status=filter_application_status)

        ledger_lookup_fields = [
            "submitter",
        ]
        # Prevent the external user from searching for officers
#        if is_internal(request):
#            ledger_lookup_fields += ["assigned_officer", "assigned_approver"]

#        queryset = self.apply_request(
#            request,
#            queryset,
#            view,
#            ledger_lookup_fields=ledger_lookup_fields,
#        )

        setattr(view, "_datatables_filtered_count", queryset.count())
        setattr(view, "_datatables_total_count", total_count)

        return queryset


class ProposalRenderer(DatatablesRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        if "view" in renderer_context and hasattr(
            renderer_context["view"], "_datatables_total_count"
        ):
            data["recordsTotal"] = renderer_context["view"]._datatables_total_count
        return super().render(data, accepted_media_type, renderer_context)


class ProposalPaginatedViewSet(viewsets.ReadOnlyModelViewSet):
    filter_backends = (ProposalFilterBackend,)
    pagination_class = DatatablesPageNumberPagination
    renderer_classes = (ProposalRenderer,)
    queryset = Proposal.objects.none()
    serializer_class = ListProposalSerializer
    page_size = 10

    def get_queryset(self):
        user = self.request.user
#        if not is_internal(self.request) and not is_customer(self.request):
#            return Proposal.objects.none()

        qs = Proposal.objects.all()
#        if is_assessor(self.request) or is_approver(self.request):
#            target_email_user_id = self.request.query_params.get(
#                "target_email_user_id", None
#            )
#            if (
#                target_email_user_id
#                and target_email_user_id.isnumeric()
#                and int(target_email_user_id) > 0
#            ):
#                qs = qs.filter(submitter=target_email_user_id)
#        elif is_finance_officer(self.request):
#            qs = qs.filter(
#                processing_status=Proposal.PROCESSING_STATUS_APPROVED_EDITING_INVOICING
#            )
#        else:
#            qs = Proposal.objects.none()

        return qs

    def get_serializer_class(self):
#        email_user_id_assigned = self.request.query_params.get(
#            "email_user_id_assigned", None
#        )
#        if self.action == "list" and email_user_id_assigned:
#            return ListProposalReferralSerializer
        return super().get_serializer_class()

    def list(self, request, *args, **kwargs):
        ''' http://localhost:8001/api/proposal_paginated/?draw=1&length=10
        '''
        qs = self.get_queryset()

#        email_user_id_assigned = int(
#            request.query_params.get("email_user_id_assigned", "0")
#        )
#
#        if email_user_id_assigned:
#            qs = Proposal.objects.filter(
#                Q(
#                    referrals__in=Referral.objects.exclude(
#                        processing_status=Referral.PROCESSING_STATUS_RECALLED
#                    ).filter(referral=email_user_id_assigned)
#                ),
#                referrals__referral=email_user_id_assigned,
#            ).annotate(referral_processing_status=F("referrals__processing_status"))

        qs = self.filter_queryset(qs)

        self.paginator.page_size = qs.count()
        result_page = self.paginator.paginate_queryset(qs, request)
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(
            result_page, context={"request": request}, many=True
        )

        return self.paginator.get_paginated_response(serializer.data)


class ProposalViewSet(UserActionLoggingViewset):
    ''' http://localhost:8001/api/proposal/1/  <-- calls retrieve()
    '''
    queryset = Proposal.objects.none()
    serializer_class = ProposalSerializer
    lookup_field = "id"

    def retrieve(self, request, *args, **kwargs):
        #import ipdb; ipdb.set_trace()
        instance = self.get_object()
        serializer = self.get_serializer(instance, context={"request": request})
        return Response(serializer.data)


#    def retrieve(self, request, *args, **kwargs):
#        instance = self.get_object()
#        return super().retrieve(request, *args, **kwargs)


    def get_queryset(self):
        #import ipdb; ipdb.set_trace()
        user = self.request.user
        return Proposal.objects.all()

    def get_serializer_class(self):
#        if is_internal(self.request):
#            return InternalProposalSerializer
        return ProposalSerializer

    @list_route(methods=["GET"], detail=False)
    def filter_list(self, request, *args, **kwargs):
        """Used by the internal/external dashboard filters"""
        #import ipdb; ipdb.set_trace()
        submitter_qs = (
            self.get_queryset()
            .filter(submitter__isnull=False)
            .distinct("submitter__email")
            .values_list(
                "submitter__first_name", "submitter__last_name", "submitter__email"
            )
        )
        submitters = [
            dict(email=i[2], search_term=f"{i[0]} {i[1]} ({i[2]})")
            for i in submitter_qs
        ]
        application_types = ApplicationType.objects.filter(visible=True).values_list(
            "name", flat=True
        )
        data = dict(
            submitters=submitters,
            application_types=application_types,
            approval_status_choices=[i[1] for i in Approval.STATUS_CHOICES],
        )
        return Response(data)

#    @detail_route(methods=["GET"], detail=True)
#    def compare_list(self, request, *args, **kwargs):
#        """Returns the reversion-compare urls --> list"""
#        current_revision_id = (
#            Version.objects.get_for_object(self.get_object()).first().revision_id
#        )
#        versions = (
#            Version.objects.get_for_object(self.get_object())
#            .select_related("revision__user")
#            .filter(
#                Q(revision__comment__icontains="status")
#                | Q(revision_id=current_revision_id)
#            )
#        )
#        version_ids = [i.id for i in versions]
#        urls = [
#            f"?version_id2={version_ids[0]}&version_id1={version_ids[i + 1]}"
#            for i in range(len(version_ids) - 1)
#        ]
#        return Response(urls)

#    @detail_route(methods=["POST"], detail=True)
#    @renderer_classes((JSONRenderer,))
#    @basic_exception_handler
#    def process_shapefile_document(self, request, *args, **kwargs):
#        instance = self.get_object()
#        returned_data = process_generic_document(
#            request, instance, document_type="shapefile_document"
#        )
#        if returned_data:
#            return Response(returned_data)
#        else:
#            return Response()

    def list(self, request, *args, **kwargs):
        ''' http://localhost:8001/api/proposal/
        '''
        proposals = self.get_queryset()

        statuses = list(map(lambda x: x[0], Proposal.PROCESSING_STATUS_CHOICES))
        types = list(map(lambda x: x[0], ApplicationType.APPLICATION_TYPES))
        type = request.query_params.get("type", "")
        status = request.query_params.get("status", "")
        if status in statuses and type in types:
            # both status and type exists
            proposals = proposals.filter(
                Q(processing_status=status) & Q(application_type__name=type)
            )
        #serializer = ListProposalMinimalSerializer(
        serializer = ListProposalSerializer(
            proposals, context={"request": request}, many=True
        )
        return Response(serializer.data)

    @list_route(methods=["GET"], detail=False)
    def list_for_map(self, request, *args, **kwargs):
        """Returns the proposals for the map"""
        #import ipdb; ipdb.set_trace()
        proposal_ids = [
            int(id)
            for id in request.query_params.get("proposal_ids", "").split(",")
            if id.lstrip("-").isnumeric()
        ]
        application_type = request.query_params.get("application_type", None)
        processing_status = request.query_params.get("processing_status", None)

        cache_key = settings.CACHE_KEY_MAP_PROPOSALS
        qs = cache.get(cache_key)
        if qs is None:
            qs = (
                self.get_queryset()
                .exclude(proposalgeometry__isnull=True)
                .prefetch_related("proposalgeometry")
            )
            cache.set(cache_key, qs, settings.CACHE_TIMEOUT_2_HOURS)

        if len(proposal_ids) > 0:
            qs = qs.filter(id__in=proposal_ids)

        if (
            application_type
            and application_type.isnumeric()
            and int(application_type) > 0
        ):
            qs = qs.filter(application_type_id=application_type)

        if processing_status:
            qs = qs.filter(processing_status=processing_status)

        serializer = ListProposalMinimalSerializer(
            qs, context={"request": request}, many=True
        )
        return Response(serializer.data)

    @detail_route(methods=["post"], detail=True)
    @renderer_classes((JSONRenderer,))
    @basic_exception_handler
    def validate_map_files(self, request, *args, **kwargs):
        instance = self.get_object()
        valid_geometry_saved = validate_map_files(request, instance)
        #import ipdb;ipdb.set_trace()
        instance.save()
        if valid_geometry_saved:
            populate_gis_data(instance, "proposalgeometry")
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @detail_route(methods=["POST"], detail=True)
    @renderer_classes((JSONRenderer,))
    @basic_exception_handler
    def process_shapefile_document(self, request, *args, **kwargs):
        #import ipdb; ipdb.set_trace()
        instance = self.get_object()
        returned_data = process_generic_document(
            request, instance, document_type="shapefile_document"
        )
        if returned_data:
            return Response(returned_data)
        else:
            return Response()



#    @detail_route(methods=["GET"], detail=True)
#    @basic_exception_handler
#    def action_log(self, request, *args, **kwargs):
#        #import ipdb; ipdb.set_trace()
#        instance = self.get_object()
#        qs = instance.action_logs.all()
#        serializer = ProposalUserActionSerializer(qs, many=True)
#        return Response(serializer.data)
#
#    @detail_route(methods=["GET"], detail=True)
#    @basic_exception_handler
#    def comms_log(self, request, *args, **kwargs):
#        instance = self.get_object()
#        qs = instance.comms_logs.all()
#        serializer = ProposalLogEntrySerializer(qs, many=True)
#        return Response(serializer.data)
#
#    @detail_route(methods=["POST"], detail=True)
#    @renderer_classes((JSONRenderer,))
#    @basic_exception_handler
#    def add_comms_log(self, request, *args, **kwargs):
#        with transaction.atomic():
#            instance = self.get_object()
#            mutable = request.data._mutable
#            request.data._mutable = True
#            request.data["proposal"] = f"{instance.id}"
#            request.data["staff"] = f"{request.user.id}"
#            request.data._mutable = mutable
#            serializer = ProposalLogEntrySerializer(data=request.data)
#            serializer.is_valid(raise_exception=True)
#            comms = serializer.save()
#
#            # Save the files
#            for f in request.FILES.getlist("files"):
#                document = comms.documents.create()
#                document.name = str(f)
#                document._file = f
#                document.save()
#
#            return Response(serializer.data)
#
#    @detail_route(methods=["GET"], detail=True)
#    @basic_exception_handler
#    def revision_version(self, request, *args, **kwargs):
#        """
#        Returns the version of this model at `revision_id`
#        """
#
#        # The django reversion revision id to return the model for
#        revision_id = request.query_params.get("revision_id", None)
#        # The model instance
#        instance = self.get_object()
#        # This model's class
#        model_class = instance.__class__
#        # The serializer to apply
#        serializer_class = self.get_serializer_class()
#        if not revision_id:
#            logger.warning(
#                f"Request does not contain revision_id. Returning {model_class.__name__}"
#            )
#            serializer = serializer_class(instance, context={"request": request})
#            return Response(serializer.data)
#
#        try:
#            # This model's version for `revision_id`
#            version = self.get_object().revision_version(revision_id)
#        except IndexError:
#            raise serializers.ValidationError(f"Revision {revision_id} does not exist")
#
#        version.revision.version_set.all()
#
#        # An instance of the model version
#        instance = model_class(**version.field_dict)
#        # Serialize the instance
#        serializer = serializer_class(instance, context={"request": request})
#
#        # Feature collection to return as proposal's proposalgeometry property
#        geometry_data = {"type": "FeatureCollection", "features": []}
#        # Build geometry data structure containing only the geometry versions at `revision_id`
#        proposalgeometries = instance.proposalgeometry.all()
#        for geometry in proposalgeometries:
#            # Get associated proposal geometry at the time of `revision_id`
#            pg_versions = (
#                Version.objects.get_for_object(geometry)
#                .filter(Q(revision_id__lte=revision_id))
#                .order_by("-revision__date_created")
#            )
#            pg_version = pg_versions.first()
#            if not pg_version:
#                # Geometry might not have existed back then
#                continue
#            # Build a proposal geometry instance from the version
#            proposalgeometry = ProposalGeometry(**pg_version.field_dict)
#            pg_serializer = ProposalGeometrySerializer(
#                proposalgeometry, context={"request": request}
#            )
#            # Append the geometry to the feature collection
#            geometry_data["features"].append(pg_serializer.data)
#
#        revision_data = serializer.data.copy()
#        revision_data["proposalgeometry"] = OrderedDict(geometry_data)
#
#        return Response(revision_data)
#
#    @list_route(methods=["GET"], detail=False)
#    def user_list(self, request, *args, **kwargs):
#        qs = self.get_queryset().exclude(processing_status="discarded")
#        serializer = ListProposalSerializer(qs, context={"request": request}, many=True)
#        return Response(serializer.data)
#
#    @list_route(methods=["GET"], detail=False)
#    def user_list_paginated(self, request, *args, **kwargs):
#        """
#        Placing Paginator class here (instead of settings.py) allows specific method for desired behaviour),
#        otherwise all serializers will use the default pagination class
#
#        https://stackoverflow.com/questions/29128225/django-rest-framework-3-1-breaks-pagination-paginationserializer
#        """
#        proposals = self.get_queryset().exclude(processing_status="discarded")
#        paginator = DatatablesPageNumberPagination()
#        paginator.page_size = proposals.count()
#        result_page = paginator.paginate_queryset(proposals, request)
#        serializer = ListProposalSerializer(
#            result_page, context={"request": request}, many=True
#        )
#        return paginator.get_paginated_response(serializer.data)
#
#    @list_route(methods=["GET"], detail=False)
#    def list_paginated(self, request, *args, **kwargs):
#        """
#        Placing Paginator class here (instead of settings.py) allows specific method for desired behaviour),
#        otherwise all serializers will use the default pagination class
#
#        https://stackoverflow.com/questions/29128225/django-rest-framework-3-1-breaks-pagination-paginationserializer
#        """
#        proposals = self.get_queryset()
#        paginator = DatatablesPageNumberPagination()
#        paginator.page_size = proposals.count()
#        result_page = paginator.paginate_queryset(proposals, request)
#        serializer = ListProposalSerializer(
#            result_page, context={"request": request}, many=True
#        )
#        return paginator.get_paginated_response(serializer.data)
#
#    @detail_route(methods=["GET", "POST"], detail=True)
#    def internal_proposal(self, request, *args, **kwargs):
#        instance = self.get_object()
#        serializer = InternalProposalSerializer(instance, context={"request": request})
#        #import ipdb; ipdb.set_trace()
#        return Response(serializer.data)
#
#    @detail_route(methods=["post"], detail=True)
#    @renderer_classes((JSONRenderer,))
#    @basic_exception_handler
#    def submit(self, request, *args, **kwargs):
#        instance = self.get_object()
#        save_proponent_data(instance, request, self)
#        instance = proposal_submit(instance, request)
#        serializer = self.get_serializer(instance)
#        return Response(serializer.data)
#
#    @detail_route(methods=["POST"], detail=True)
#    @renderer_classes((JSONRenderer,))
#    @basic_exception_handler
#    def validate_map_files(self, request, *args, **kwargs):
#        instance = self.get_object()
#        valid_geometry_saved = validate_map_files(request, instance)
#        instance.save()
#        if valid_geometry_saved:
#            populate_gis_data(instance, "proposalgeometry")
#        serializer = self.get_serializer(instance)
#        return Response(serializer.data)
#
#    @detail_route(methods=["GET"], detail=True)
#    @basic_exception_handler
#    def assign_request_user(self, request, *args, **kwargs):
#        instance = self.get_object()
#        instance.assign_officer(request, request.user)
#        serializer_class = self.get_serializer_class()
#        serializer = serializer_class(instance, context={"request": request})
#        return Response(serializer.data)
#
#    @detail_route(methods=["POST"], detail=True)
#    @basic_exception_handler
#    def assign_to(self, request, *args, **kwargs):
#        instance = self.get_object()
#        user_id = request.data.get("assessor_id", None)
#        user = None
#        if not user_id:
#            raise serializers.ValidationError("An assessor id is required")
#        try:
#            user = EmailUser.objects.get(id=user_id)
#        except EmailUser.DoesNotExist:
#            raise serializers.ValidationError(
#                "A user with the id passed in does not exist"
#            )
#        instance.assign_officer(request, user)
#        # serializer = InternalProposalSerializer(instance,context={'request':request})
#        serializer_class = self.get_serializer_class()
#        serializer = serializer_class(instance, context={"request": request})
#        return Response(serializer.data)
#
#    @detail_route(methods=["GET"], detail=True)
#    @basic_exception_handler
#    def unassign(self, request, *args, **kwargs):
#        instance = self.get_object()
#        instance.unassign(request)
#        # serializer = InternalProposalSerializer(instance,context={'request':request})
#        serializer_class = self.get_serializer_class()
#        serializer = serializer_class(instance, context={"request": request})
#        return Response(serializer.data)
#
#    @detail_route(methods=["PATCH"], detail=True)
#    @basic_exception_handler
#    def back_to_assessor(self, request, *args, **kwargs):
#        instance = self.get_object()
#        instance.processing_status = Proposal.PROCESSING_STATUS_WITH_ASSESSOR
#        # Reset fields related to the propose approve / decline so that the assessor must
#        # make a new proposal to approve or deline (since the last one was rejected)
#        instance.proposed_decline_status = False
#        instance.proposed_issuance_approval = None
#        instance.save()
#        serializer_class = self.get_serializer_class()
#        serializer = serializer_class(instance, context={"request": request})
#        return Response(serializer.data)
#
#    @detail_route(methods=["POST"], detail=True)
#    @basic_exception_handler
#    def switch_status(self, request, *args, **kwargs):
#        instance = self.get_object()
#        status = request.data.get("status")
#        approver_comment = request.data.get("approver_comment")
#        if not status:
#            raise serializers.ValidationError("Status is required")
#        else:
#            if status not in [
#                Proposal.PROCESSING_STATUS_WITH_ASSESSOR,
#                Proposal.PROCESSING_STATUS_WITH_ASSESSOR_CONDITIONS,
#                Proposal.PROCESSING_STATUS_WITH_APPROVER,
#                Proposal.PROCESSING_STATUS_WITH_REFERRAL,
#            ]:
#                raise serializers.ValidationError("The status provided is not allowed")
#        instance.move_to_status(request, status, approver_comment)
#        serializer_class = self.get_serializer_class()
#        serializer = serializer_class(instance, context={"request": request})
#        return Response(serializer.data)
#
#    @detail_route(methods=["POST"], detail=True)
#    @basic_exception_handler
#    def reissue_approval(self, request, *args, **kwargs):
#        instance = self.get_object()
#        if not is_assessor(request):
#            raise PermissionDenied(
#                "Assessor permissions are required to reissue approval"
#            )
#
#        instance.reissue_approval()
#        instance.log_user_action(
#            ProposalUserAction.ACTION_REISSUE_APPROVAL.format(instance.id), request
#        )
#        serializer = InternalProposalSerializer(instance, context={"request": request})
#        return Response(serializer.data)
#
#    @detail_route(methods=["POST"], detail=True)
#    @basic_exception_handler
#    def renew_approval(self, request, *args, **kwargs):
#        instance = self.get_object()
#        instance = instance.renew_approval(request)
#        serializer = SaveProposalSerializer(instance, context={"request": request})
#        return Response(serializer.data)
#
#    @detail_route(methods=["GET"], detail=True)
#    @basic_exception_handler
#    def amend_approval(self, request, *args, **kwargs):
#        instance = self.get_object()
#        error_msg = _("Not allowed to amend this approval.")
#
#        if not is_customer(request):
#            raise serializers.ValidationError(error_msg, code="invalid")
#
#        proposals = Proposal.get_proposals_for_emailuser(request.user.id)
#        if not proposals.filter(id=instance.id).exists():
#            raise serializers.ValidationError(error_msg, code="invalid")
#
#        instance = instance.amend_approval(request)
#        serializer = SaveProposalSerializer(instance, context={"request": request})
#        return Response(serializer.data)
#
#    @basic_exception_handler
#    @detail_route(methods=["POST"], detail=True)
#    # store comments, deficiencies, etc
#    def internal_save(self, request, *args, **kwargs):
#        instance = self.get_object()
#        # Was previously InternalSaveProposalSerializer however no such serializer exists
#        serializer = SaveProposalSerializer(instance, data=request.data)
#        serializer.is_valid(raise_exception=True)
#        save_site_name(instance, request.data["site_name"])
#        serializer.save()
#
#        save_assessor_data(instance, request, self)
#
#        # serializer_class = self.get_serializer_class()
#        # serializer = serializer_class(instance, context={"request": request})
#        # return Response(serializer.data)
#        return Response()
#
#    @basic_exception_handler
#    @detail_route(methods=["POST"], detail=True)
#    def proposed_approval(self, request, *args, **kwargs):
#        instance = self.get_object()
#        approval_type = request.data.get("approval_type", None)
#        if not approval_type:
#            serializer = ProposedApprovalROISerializer(data=request.data)
#        else:
#            serializer = ProposedApprovalSerializer(data=request.data)
#        serializer.is_valid(raise_exception=True)
#        instance.proposed_approval(request, request.data)
#        serializer_class = self.get_serializer_class()
#        serializer = serializer_class(instance, context={"request": request})
#        return Response(serializer.data)
#
#    @basic_exception_handler
#    @detail_route(methods=["POST"], detail=True)
#    def final_approval(self, request, *args, **kwargs):
#        instance = self.get_object()
#        approval_type = request.data.get("approval_type", None)
#        if not approval_type:
#            serializer = ProposedApprovalROISerializer(data=request.data)
#        else:
#            serializer = ProposedApprovalSerializer(data=request.data)
#        serializer.is_valid(raise_exception=True)
#        instance.final_approval(request, request.data)
#        serializer_class = self.get_serializer_class()
#        serializer = serializer_class(instance, context={"request": request})
#        return Response(serializer.data)
#
#    @detail_route(methods=["POST"], detail=True)
#    @basic_exception_handler
#    def proposed_decline(self, request, *args, **kwargs):
#        instance = self.get_object()
#        instance.proposed_decline(request, request.data)
#        serializer_class = self.get_serializer_class()
#        serializer = serializer_class(instance, context={"request": request})
#        return Response(serializer.data)
#
#    @detail_route(methods=["PATCH"], detail=True)
#    @basic_exception_handler
#    def final_decline(self, request, *args, **kwargs):
#        instance = self.get_object()
#        serializer = ProposalDeclineSerializer(instance.proposaldeclineddetails)
#        instance.final_decline(request, serializer.data)
#        serializer_class = self.get_serializer_class()
#        serializer = serializer_class(instance, context={"request": request})
#        return Response(serializer.data)
#
#    @detail_route(methods=["POST"], detail=True)
#    @renderer_classes((JSONRenderer,))
#    @basic_exception_handler
#    def draft(self, request, *args, **kwargs):
#        instance = self.get_object()
#        save_proponent_data(instance, request, self)
#        # return redirect(reverse('external'))
#        serializer = self.get_serializer(instance)
#        return Response(serializer.data)
#
#    @detail_route(methods=["POST"], detail=True)
#    @renderer_classes((JSONRenderer,))
#    @basic_exception_handler
#    def complete_referral(self, request, *args, **kwargs):
#        instance = self.get_object()
#        referee_id = request.data.get("referee_id", None)
#        if not referee_id:
#            raise serializers.ValidationError(
#                _("referee_id is required"), code="required"
#            )
#
#        if not instance.referrals.filter(referral=referee_id).exists():
#            msg = _(
#                f"There is no referral for application: {instance.lodgement_number} "
#                f"and referee (email user): {referee_id}"
#            )
#            raise serializers.ValidationError(msg, code="invalid")
#
#        save_referral_data(instance, request)
#
#        referral = instance.referrals.get(referral=referee_id)
#        referral.complete(request)
#
#        serializer = self.get_serializer(instance)
#        return Response(serializer.data)
#
#    @detail_route(methods=["POST"], detail=True)
#    @renderer_classes((JSONRenderer,))
#    @basic_exception_handler
#    def referral_save(self, request, *args, **kwargs):
#        instance = self.get_object()
#        save_referral_data(instance, request)
#
#        serializer_class = self.get_serializer_class()
#        serializer = serializer_class(instance, context={"request": request})
#        return Response(serializer.data)
#
#    @detail_route(methods=["POST"], detail=True)
#    @renderer_classes((JSONRenderer,))
#    @basic_exception_handler
#    def assessor_save(self, request, *args, **kwargs):
#        instance = self.get_object()
#        save_assessor_data(instance, request, self)
#
#        serializer_class = self.get_serializer_class()
#        serializer = serializer_class(instance, context={"request": request})
#        return Response(serializer.data)
#
#    @basic_exception_handler
#    @transaction.atomic
#    def create(self, request, *args, **kwargs):
#        application_type_str = request.data.get("application_type", {}).get("code")
#        application_type = ApplicationType.objects.get(name=application_type_str)
#        proposal_type = ProposalType.objects.get(code=ProposalType.PROPOSAL_TYPE_NEW)
#
#        data = {
#            "applicant": (request.user.id),
#            "application_type_id": application_type.id,
#            "proposal_type_id": proposal_type.id,
#        }
#
#        serializer = CreateProposalSerializer(data=data)
#        serializer.is_valid(raise_exception=True)
#        instance = serializer.save()
#
#        make_proposal_applicant_ready(instance, request.user)
#
#        serializer = SaveProposalSerializer(instance)
#        return Response(serializer.data)
#
#    @basic_exception_handler
#    def update(self, request, *args, **kwargs):
#        instance = self.get_object()
#        serializer = SaveProposalSerializer(instance, data=request.data)
#        serializer.is_valid(raise_exception=True)
#        self.perform_update(serializer)
#        return Response(serializer.data)
#
#    @detail_route(methods=["patch"], detail=True)
#    @basic_exception_handler
#    def discard(self, request, *args, **kwargs):
#        instance = self.get_object()
#        if not instance.can_discard(request):
#            raise serializers.ValidationError("Not allowed to discard this proposal.")
#
#        serializer = SaveProposalSerializer(
#            instance,
#            {
#                "processing_status": Proposal.PROCESSING_STATUS_DISCARDED,
#                "previous_application": None,
#            },
#            partial=True,
#        )
#        serializer.is_valid(raise_exception=True)
#        self.perform_update(serializer)
#
#        return Response(
#            ProposalSerializer(instance, context={"request": request}).data,
#            status=status.HTTP_200_OK,
#        )
#
#    @detail_route(methods=["GET"], detail=True)
#    @basic_exception_handler
#    def get_related_items(self, request, *args, **kwargs):
#        instance = self.get_object()
#        related_items = instance.get_related_items()
#        serializer = RelatedItemsSerializer(related_items, many=True)
#        return Response(serializer.data)
#
#    @detail_route(
#        methods=["GET"],
#        detail=True,
#        renderer_classes=[DatatablesRenderer],
#        pagination_class=DatatablesPageNumberPagination,
#    )
#    def related_items(self, request, *args, **kwargs):
#        """Uses union to combine a queryset of multiple different model types
#        and uses a generic related item serializer to return the data"""
#        instance = self.get_object()
#        proposals_queryset = (
#            Proposal.objects.filter(
#                Q(generated_proposal=instance) | Q(originating_proposal=instance)
#            )
#            .annotate(
#                description=F("processing_status"),
#                type=Value("proposal", output_field=CharField()),
#            )
#            .values("id", "lodgement_number", "description", "type")
#        )
#        competitive_process_queryset = (
#            CompetitiveProcess.objects.filter(
#                id__in=[
#                    instance.generated_competitive_process_id,
#                    instance.originating_competitive_process_id,
#                ]
#            )
#            .annotate(
#                description=F("status"),
#                type=Value("competitiveprocess", output_field=CharField()),
#            )
#            .values("id", "lodgement_number", "description", "type")
#        )
#        approval_queryset = (
#            Approval.objects.filter(id=instance.approval_id)
#            .annotate(
#                description=Func(
#                    F("expiry_date"),
#                    Value("DD/MM/YYYY"),
#                    function="to_char",
#                    output_field=CharField(),
#                ),
#                type=Value("approval", output_field=CharField()),
#            )
#            .values("id", "lodgement_number", "description", "type")
#        )
#        queryset = proposals_queryset.union(
#            competitive_process_queryset, approval_queryset
#        ).order_by("lodgement_number")
#        serializer = RelatedItemSerializer(queryset, many=True)
#        data = {}
#        # Add the fields that the datatables renderer expects
#        data["data"] = serializer.data
#        data["recordsFiltered"] = queryset.count()
#        data["recordsTotal"] = queryset.count()
#        return Response(data=data)
#
#    @detail_route(methods=["POST"], detail=True)
#    def preview_document(self, request, *args, **kwargs):
#        instance = self.get_object()
#        try:
#            document = instance.preview_document(request, request.data)
#        except NotImplementedError as e:
#            e.args[0]
#            raise serializers.ValidationError(e.args[0])
#
#        return Response({document})


#class SearchReferenceView(views.APIView):
#    renderer_classes = [
#        JSONRenderer,
#    ]
#
#    def get(self, request, format=None):
#        search_term = request.GET.get("term", "")
#        proposals = Proposal.objects.filter(
#            Q(lodgement_number__icontains=search_term)
#            | Q(original_leaselicence_number__icontains=search_term)
#        )[:4]
#        proposal_results = [
#            {
#                "id": proposal.id,
#                "text": f"{ proposal.lodgement_number }"
#                + f" - { proposal.application_type.name_display }"
#                + f" - { proposal.proposal_type.description } [Proposal]",
#                "redirect_url": reverse(
#                    "internal-proposal-detail", kwargs={"pk": proposal.id}
#                ),
#            }
#            for proposal in proposals
#        ]
#        approvals = Approval.objects.filter(
#            Q(lodgement_number__icontains=search_term)
#            | Q(original_leaselicence_number__icontains=search_term)
#        )[:4]
#        approval_results = [
#            {
#                "id": approval.id,
#                "text": f"{ approval.lodgement_number } [Approval]",
#                "redirect_url": reverse(
#                    "internal-approval-detail", kwargs={"pk": approval.id}
#                ),
#            }
#            for approval in approvals
#        ]
#        compliances = Compliance.objects.filter(
#            lodgement_number__icontains=search_term
#        )[:4]
#        compliance_results = [
#            {
#                "id": compliance.id,
#                "text": f"{ compliance.lodgement_number } [Compliance]",
#                "redirect_url": reverse(
#                    "internal-compliance-detail",
#                    kwargs={"pk": compliance.id},
#                ),
#            }
#            for compliance in compliances
#        ]
#        data_transform = proposal_results + approval_results + compliance_results
#
#        return Response({"results": data_transform})



