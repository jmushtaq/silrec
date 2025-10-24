import json

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic import View

from silrec.components.proposals.models import Proposal
#from silrec.components.proposals.utils import test_proposal_emails
from django.views.generic import TemplateView


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
