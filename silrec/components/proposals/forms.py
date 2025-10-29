from django import forms
from django.conf import settings
from django.contrib.auth.models import User

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Div, HTML, ButtonHolder
from crispy_forms.bootstrap import PrependedText, AppendedText
from silrec.components.proposals.models import Proposal, ProposalAssessorGroup, ProposalReviewerGroup, ProposalAdminGroup
from silrec.components.main.models import SystemMaintenance

from datetime import datetime, timedelta
import pytz


class ProposalForm(forms.ModelForm):
    class Meta:
        model = Proposal
        fields = [
            'title',
            'proposal_type',
            'application_type',
            'processing_status',
            # Add other fields you want users to input
        ]
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Enter proposal title'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = 'add-proposal-form'
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-3'
        self.helper.field_class = 'col-lg-9'

        self.helper.layout = Layout(
            # Map Section - Just a placeholder, actual map is in template
            Div(
                HTML("""
                    <div class="map-section">
                        <h4 class="mb-3"><i class="fas fa-map"></i> Map Section</h4>
                        <p class="text-muted">Use the map below to upload and view shapefiles for this proposal.</p>
                    </div>
                """),
                css_class='mb-4'
            ),

            # Form Fields Section
            Div(
                HTML('<h4 class="mb-3"><i class="fas fa-edit"></i> Proposal Details</h4>'),
                Row(
                    Column('title', css_class='form-group col-md-12 mb-3'),
                ),
                Row(
                    Column('proposal_type', css_class='form-group col-md-6 mb-3'),
                    Column('application_type', css_class='form-group col-md-6 mb-3'),
                ),
                Row(
                    Column('processing_status', css_class='form-group col-md-6 mb-3'),
                ),
                css_class='form-section mb-4',
            ),

            # Action Buttons
            ButtonHolder(
                Submit('cancel', 'Cancel', css_class='btn btn-secondary me-2'),
                Submit('save_continue', 'Save and Continue', css_class='btn btn-outline-primary me-2'),
                Submit('save', 'Save', css_class='btn btn-primary'),
            )
        )


class SystemMaintenanceAdminForm(forms.ModelForm):
    class Meta:
        model = SystemMaintenance
        fields = "__all__"

    def clean(self):
        cleaned_data = self.cleaned_data
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        try:
            latest_obj = SystemMaintenance.objects.exclude(id=self.instance.id).latest(
                "start_date"
            )
        except SystemMaintenance.DoesNotExist:
            latest_obj = SystemMaintenance.objects.none()
        tz_local = pytz.timezone(settings.TIME_ZONE)  # start_date.tzinfo

        if latest_obj:
            latest_end_date = latest_obj.end_date.astimezone(tz=tz_local)
            if self.instance.id:
                if (
                    start_date < latest_end_date
                    and start_date < self.instance.start_date.astimezone(tz_local)
                ):
                    raise forms.ValidationError(
                        "Start date cannot be before an existing records latest end_date. "
                        "Start Date must be after {}".format(latest_end_date.ctime())
                    )
            else:
                if start_date < latest_end_date:
                    raise forms.ValidationError(
                        "Start date cannot be before an existing records latest end_date. "
                        "Start Date must be after {}".format(latest_end_date.ctime())
                    )

        if self.instance.id:
            if start_date < datetime.now(tz=tz_local) - timedelta(
                minutes=5
            ) and start_date < self.instance.start_date.astimezone(tz_local):
                raise forms.ValidationError(
                    "Start date cannot be edited to be further in the past"
                )
        else:
            if start_date < datetime.now(tz=tz_local) - timedelta(minutes=5):
                raise forms.ValidationError("Start date cannot be in the past")

        if end_date < start_date:
            raise forms.ValidationError("End date cannot be before start date")

        super().clean()
        return cleaned_data


class ProposalAssessorGroupAdminForm(forms.ModelForm):
    class Meta:
        model = ProposalAssessorGroup
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(ProposalAssessorGroupAdminForm, self).__init__(*args, **kwargs)
        if self.instance:
            self.fields['members'].queryset = User.objects.filter(is_staff=True)

    def clean(self):
        super(ProposalAssessorGroupAdminForm, self).clean()
        if self.instance and ProposalAssessorGroup.objects.all().exists():
            try:
                original_members = ProposalAssessorGroup.objects.get(id=self.instance.id).members.all()
                current_members = self.cleaned_data.get('members')
                for o in original_members:
                    if o not in current_members:
                        if self.instance.member_is_assigned(o):
                            raise ValidationError('{} is currently assigned to a proposal(s)'.format(o.email))
            except:
                pass


class ProposalReviewerGroupAdminForm(forms.ModelForm):
    class Meta:
        model = ProposalReviewerGroup
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(ProposalReviewerGroupAdminForm, self).__init__(*args, **kwargs)
        if self.instance:
            self.fields['members'].queryset = User.objects.filter(is_staff=True)

    def clean(self):
        super(ProposalReviewerGroupAdminForm, self).clean()
        if self.instance:
            try:
                original_members = ProposalReviewerGroup.objects.get(id=self.instance.id).members.all()
                current_members = self.cleaned_data.get('members')
                for o in original_members:
                    if o not in current_members:
                        if self.instance.member_is_assigned(o):
                            raise ValidationError('{} is currently assigned to a proposal(s)'.format(o.email))
            except:
                pass


class ProposalAdminGroupAdminForm(forms.ModelForm):
    class Meta:
        model = ProposalAdminGroup
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(ProposalAdminGroupAdminForm, self).__init__(*args, **kwargs)
        if self.instance:
            self.fields['members'].queryset = User.objects.filter(is_staff=True)

    def clean(self):
        super(ProposalAdminGroupAdminForm, self).clean()
        if self.instance:
            try:
                original_members = ProposalAdminGroup.objects.get(id=self.instance.id).members.all()
                current_members = self.cleaned_data.get('members')
                for o in original_members:
                    if o not in current_members:
                        if self.instance.member_is_assigned(o):
                            raise ValidationError('{} is currently assigned to a proposal(s)'.format(o.email))
            except:
                pass
