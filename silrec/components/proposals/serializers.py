from rest_framework import serializers
from .models import Proposal

#class ProposalDatatableSerializer(serializers.ModelSerializer):
#    proposal_type_name = serializers.SerializerMethodField()
#    lodgement_date_formatted = serializers.SerializerMethodField()
#    processing_status_display = serializers.SerializerMethodField()
#
#    class Meta:
#        model = Proposal
#        fields = [
#            'id',
#            'lodgement_number',
#            'title',
#            'proposal_type_name',
#            'lodgement_date_formatted',
#            'processing_status_display',
#        ]
#
#    def get_proposal_type_name(self, obj):
#        return obj.proposal_type.name if obj.proposal_type else 'NA'
#
#    def get_lodgement_date_formatted(self, obj):
#        return obj.lodgement_date.strftime('%Y-%m-%d %H:%M') if obj.lodgement_date else ''
#
#    def get_processing_status_display(self, obj):
#        return obj.get_processing_status_display() if obj.processing_status else ''


class ProposalDatatableSerializer(serializers.ModelSerializer):
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


