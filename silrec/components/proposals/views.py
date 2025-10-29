import json
from django.urls import reverse_lazy
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import View, TemplateView, CreateView, UpdateView
from django.views import View
from django.db.models import Q
from django.contrib.auth.mixins import UserPassesTestMixin

import pandas as pd
import openpyxl
from datetime import datetime

from silrec.components.proposals.models import Proposal
from silrec.components.proposals.forms import ProposalForm


class AddProposalView(CreateView):
    model = Proposal
    form_class = ProposalForm
    template_name = 'proposals/proposal_form.html'
    success_url = reverse_lazy('internal')

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.submitter = self.request.user.id

        # Handle shapefile JSON data
        shapefile_json = self.request.POST.get('shapefile_json')
        if shapefile_json:
            try:
                self.object.shapefile_json = json.loads(shapefile_json)
            except json.JSONDecodeError:
                pass

        self.object.save()
        messages.success(self.request, 'Proposal created successfully!')

        if 'save_continue' in self.request.POST:
            return redirect('add-proposal')
        else:
            return redirect(self.success_url)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return self.render_to_response(self.get_context_data(form=form))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['mode'] = 'add'
        context['read_only'] = False
        return context


class ViewProposalView(UserPassesTestMixin, UpdateView):
    model = Proposal
    form_class = ProposalForm
    template_name = 'proposals/proposal_form.html'
    success_url = reverse_lazy('internal')

    def test_func(self):
        """Only staff users can view proposals"""
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['mode'] = 'view'

        # Check if user can process this proposal
        proposal = self.get_object()
        can_process = self.can_process_proposal(proposal)
        context['read_only'] = not can_process
        context['can_process'] = can_process

        return context

    def can_process_proposal(self, proposal):
        """Check if user can process this proposal"""
        user = self.request.user

        # User must be staff
        if not user.is_staff:
            return False

        # Check if proposal is in processable status
        processable_statuses = ['With Assessor']
        if proposal.processing_status not in processable_statuses:
            return False

        # Check user groups and permissions
        allowed_groups = ['Assessors', 'Reviewers', 'Silrec Admin']
        user_groups = user.groups.values_list('name', flat=True)

        if (any(group in user_groups for group in allowed_groups) or
            user.is_superuser):
            return True

        return False

    def form_valid(self, form):
        if not self.can_process_proposal(self.get_object()):
            messages.error(self.request, 'You do not have permission to process this proposal.')
            return redirect(self.success_url)

        self.object = form.save(commit=False)

        # Handle shapefile JSON data
        shapefile_json = self.request.POST.get('shapefile_json')
        if shapefile_json:
            try:
                self.object.shapefile_json = json.loads(shapefile_json)
            except json.JSONDecodeError:
                pass

        self.object.save()
        messages.success(self.request, 'Proposal updated successfully!')

        if 'save_continue' in self.request.POST:
            return redirect('view-proposal', pk=self.object.pk)
        else:
            return redirect(self.success_url)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if self.request.method == 'GET':
            # Set form to read-only if user cannot process
            if not self.can_process_proposal(self.get_object()):
                for field in form.fields.values():
                    field.disabled = True
        return form


class ProposalExcelExportView(View):
    def get(self, request):
        """Export proposals to Excel with filtering"""
        try:
            # Extract filter parameters from request
            search_value = request.GET.get('search', '')
            status_filter = request.GET.getlist('status', []) or request.GET.get('status', '').split(',')
            from_date = request.GET.get('from_date', '')
            to_date = request.GET.get('to_date', '')

            # Remove empty strings from status filter
            status_filter = [s for s in status_filter if s]

            print(f"Export filters - Search: '{search_value}', Status: {status_filter}, From: {from_date}, To: {to_date}")

            # Apply filters to queryset
            queryset = Proposal.objects.select_related('proposal_type').all()

            if search_value:
                queryset = queryset.filter(
                    Q(lodgement_number__icontains=search_value) |
                    Q(title__icontains=search_value) |
                    Q(proposal_type__description__icontains=search_value) |
                    Q(processing_status__icontains=search_value)
                )

            if status_filter:
                queryset = queryset.filter(processing_status__in=status_filter)

            if from_date:
                try:
                    from_date_obj = datetime.strptime(from_date, '%Y-%m-%d').date()
                    queryset = queryset.filter(lodgement_date__gte=from_date_obj)
                except ValueError:
                    print(f"Invalid from_date format: {from_date}")

            if to_date:
                try:
                    to_date_obj = datetime.strptime(to_date, '%Y-%m-%d').date()
                    queryset = queryset.filter(lodgement_date__lte=to_date_obj)
                except ValueError:
                    print(f"Invalid to_date format: {to_date}")

            # Prepare data for Excel
            data = []
            for proposal in queryset:
                data.append({
                    'Lodgement Number': proposal.lodgement_number or '',
                    'Title': proposal.title or '',
                    'Proposal Type': proposal.proposal_type.description if proposal.proposal_type else '',
                    'Lodgement Date': proposal.lodgement_date.strftime('%Y-%m-%d %H:%M') if proposal.lodgement_date else '',
                    'Status': proposal.get_processing_status_display(),
                })

            if not data:
                return HttpResponse("No data to export", status=404)

            # Create DataFrame and Excel response
            df = pd.DataFrame(data)

            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename="proposals_export.xlsx"'

            with pd.ExcelWriter(response, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Proposals', index=False)

                # Auto-adjust column widths
                worksheet = writer.sheets['Proposals']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min((max_length + 2), 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width

            return response

        except Exception as e:
            print(f"Excel export error: {str(e)}")
            import traceback
            traceback.print_exc()
            return HttpResponse(f"Error generating Excel export: {str(e)}", status=500)


class ProposalDashboardView(TemplateView):
    #template_name = 'proposals_section.html'
    template_name = 'index3.html'  # or whatever template uses this

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['proposal_columns'] = [
            {'field': 'lodgement_number', 'title': 'Lodgement Number'},
            {'field': 'title', 'title': 'Title'},
            {'field': 'proposal_type_name', 'title': 'Proposal Type'},
            {'field': 'lodgement_date_formatted', 'title': 'Lodgement Date'},
            {'field': 'processing_status_display', 'title': 'Status'},
        ]
        return context

from django.views.generic import TemplateView

class DashboardView(TemplateView):
    template_name = 'index3.html'  # or whatever template uses this
    #template_name = 'proposals_section.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['proposal_columns'] = [
            {'field': 'lodgement_number', 'title': 'Lodgement Number'},
            {'field': 'title', 'title': 'Title'},
            {'field': 'proposal_type_name', 'title': 'Proposal Type'},
            {'field': 'lodgement_date_formatted', 'title': 'Lodgement Date'},
            {'field': 'processing_status_display', 'title': 'Status'},
        ]
        return context


class PreviewLicencePDFView(View):
    def post(self, request, *args, **kwargs):
        response = HttpResponse(content_type="application/pdf")

        proposal = self.get_object()
        details = json.loads(request.POST.get("formData"))

        response.write(proposal.preview_approval(request, details))
        return response

    def get_object(self):
        return get_object_or_404(Proposal, id=self.kwargs["proposal_pk"])


#class TestEmailView(View):
#    def get(self, request, *args, **kwargs):
#        test_proposal_emails(request)
#        return HttpResponse("Test Email Script Completed")
