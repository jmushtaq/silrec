from rest_framework import serializers
from .models import Proposal

from rest_framework import serializers
from .models import Proposal

class ProposalSerializer(serializers.ModelSerializer):
    proposal_type_name = serializers.CharField(source='proposal_type.description', read_only=True)
    proposal_type_id = serializers.IntegerField(source='proposal_type.id', read_only=True)
    lodgement_date_formatted = serializers.SerializerMethodField()
    processing_status_display = serializers.CharField(source='get_processing_status_display', read_only=True)
    submitter_email = serializers.SerializerMethodField()
    previous_application_title = serializers.CharField(source='previous_application.title', read_only=True, allow_null=True)
    is_admin = serializers.SerializerMethodField()
    can_assess = serializers.SerializerMethodField()
    can_review = serializers.SerializerMethodField()
    is_read_only = serializers.SerializerMethodField()

    class Meta:
        model = Proposal
        fields = [
            # Basic identification
            'id', 'lodgement_number', 'title',
            'lodgement_date', 'lodgement_date_formatted',
            'processing_status', 'processing_status_display', 'prev_processing_status',
            'proposal_type', 'proposal_type_name', 'proposal_type_id',
            'application_type', 'previous_application', 'previous_application_title',
            'submitter', 'submitter_email',
            'proposed_issuance_approval', 'shapefile_json', 'geojson_data_processed',
            'migrated', 'is_admin', 'can_assess', 'can_review', 'is_read_only',
        ]
        read_only_fields = ['lodgement_number', 'lodgement_date']

    def get_lodgement_date_formatted(self, obj):
        if obj.lodgement_date:
            return obj.lodgement_date.strftime('%Y-%m-%d %H:%M')
        return ''

    def get_submitter_email(self, obj):
        # You might need to adjust this based on how you get the submitter's email
        # This is a placeholder - replace with your actual logic
        from django.contrib.auth.models import User
        try:
            if obj.submitter:
                user = User.objects.get(id=obj.submitter)
                return user.email
        except User.DoesNotExist:
            pass
        return ''

    def get_is_admin(self, obj):
        #import ipdb; ipdb.set_trace()
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.is_admin(request.user)

    def get_can_assess(self, obj):
        return True

    def get_can_review(self, obj):
        return True

    def get_is_read_only(self, obj):
        return obj.processing_status in obj.READ_ONLY_STATES


class ProposalDatatableSerializer(ProposalSerializer):
    class Meta(ProposalSerializer.Meta):
        fields = [
            'id',
            'lodgement_number',
            'title',
            'proposal_type_name',
            'lodgement_date_formatted',
            'processing_status_display',
            'processing_status',  # Include the raw value for filtering
            'migrated',
            'is_admin',
            'can_assess',
            'can_review',
            'is_read_only',
        ]


class _ProposalDatatableSerializer(serializers.ModelSerializer):
    # Use CharField with source for related fields
    proposal_type_name = serializers.CharField(source='proposal_type.description', read_only=True, default='')

    # Use method fields for custom formatting
    lodgement_date_formatted = serializers.SerializerMethodField()
    processing_status_display = serializers.SerializerMethodField()

    class Meta:
        model = Proposal
        fields = [
            'id',
            'lodgement_number',
            'title',
            'proposal_type_name',
            'lodgement_date_formatted',
            'processing_status_display',
        ]

    def get_lodgement_date_formatted(self, obj):
        if obj.lodgement_date:
            return obj.lodgement_date.strftime('%Y-%m-%d %H:%M')
        return ''

    def get_processing_status_display(self, obj):
        return obj.get_processing_status_display()


