from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, FormView
from django.views.generic.base import View, TemplateView
from django.conf import settings
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.views.decorators.csrf import csrf_protect
from django.core.exceptions import ValidationError
from django.db import transaction

from datetime import datetime, timedelta

from silrec.helpers import is_internal
from silrec.forms import *

from django.core.management import call_command
import json
from decimal import Decimal

import logging
logger = logging.getLogger('payment_checkout')

from django.contrib.auth import logout
from django.contrib.auth.views import LogoutView

class UserLogoutView(LogoutView):

    def get(self, request):
        logout(request)
        return redirect('/')


class InternalView(UserPassesTestMixin, TemplateView):
    #template_name = 'sqs/dash/index.html'
    template_name = 'silrec/index2.html'

    def test_func(self):
        return is_internal(self.request)

    def get_context_data(self, **kwargs):
        context = super(InternalView, self).get_context_data(**kwargs)
        context['dev'] = settings.DEV_STATIC
        context['dev_url'] = settings.DEV_STATIC_URL
        return context

class ExternalView(LoginRequiredMixin, TemplateView):
    #template_name = 'sqs/dash/index.html'
    template_name = 'silrec/index2.html'

    def get_context_data(self, **kwargs):
        context = super(ExternalView, self).get_context_data(**kwargs)
        context['dev'] = settings.DEV_STATIC
        context['dev_url'] = settings.DEV_STATIC_URL
        return context


class SilrecRoutingView(TemplateView):
    template_name = 'silrec/index2.html'

    def get(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            if is_internal(self.request):
                return redirect('internal')
            return redirect('external')
        kwargs['form'] = LoginForm
        return super(SilrecRoutingView, self).get(*args, **kwargs)
        #return redirect('/accounts/login')


class SilrecContactView(TemplateView):
    template_name = 'silrec/contact.html'


class SilrecFurtherInformationView(TemplateView):
    template_name = 'silrec/further_info.html'

'''
FROM DAS!!!
class DisturbanceRoutingView(TemplateView):
    template_name = 'disturbance/index.html'

    def get(self, *args, **kwargs):
        if self.request.user.is_authenticated():
            if is_internal(self.request):
                return redirect('internal')
            return redirect('external')
        kwargs['form'] = LoginForm
        return super(DisturbanceRoutingView, self).get(*args, **kwargs)


class MasterlistContactView(TemplateView):
    template_name = 'sqs/contact.html'

class MasterlistFurtherInformationView(TemplateView):
    template_name = 'sqs/further_info.html'

@login_required(login_url='ds_home')
def first_time(request):
    context = {}
    if request.method == 'POST':
        form = FirstTimeForm(request.POST)
        redirect_url = form.data['redirect_url']
        if not redirect_url:
            redirect_url = '/'
        if form.is_valid():
            # set user attributes
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.dob = form.cleaned_data['dob']
            request.user.save()
            return redirect(redirect_url)
        context['form'] = form
        context['redirect_url'] = redirect_url
        return render(request, 'sqs/user_profile.html', context)
    # GET default
    if 'next' in request.GET:
        context['redirect_url'] = request.GET['next']
    else:
        context['redirect_url'] = '/'
    context['dev'] = settings.DEV_STATIC
    context['dev_url'] = settings.DEV_STATIC_URL
    #return render(request, 'sqs/user_profile.html', context)
    return render(request, 'sqs/dash/index.html', context)


class HelpView(LoginRequiredMixin, TemplateView):
    template_name = 'sqs/help.html'

    def get_context_data(self, **kwargs):
        context = super(HelpView, self).get_context_data(**kwargs)

        if self.request.user.is_authenticated:
            application_type = kwargs.get('application_type', None)
            if kwargs.get('help_type', None)=='assessor':
                if is_internal(self.request):
                    qs = HelpPage.objects.filter(application_type__name__icontains=application_type, help_type=HelpPage.HELP_TEXT_INTERNAL).order_by('-version')
                    context['help'] = qs.first()
#                else:
#                    return TemplateResponse(self.request, 'sqs/not-permitted.html', context)
#                    context['permitted'] = False
            else:
                qs = HelpPage.objects.filter(application_type__name__icontains=application_type, help_type=HelpPage.HELP_TEXT_EXTERNAL).order_by('-version')
                context['help'] = qs.first()
        return context
'''


class ManagementCommandsView(LoginRequiredMixin, TemplateView):
    template_name = 'sqs/mgt-commands.html'

    def post(self, request):
        data = {}
        command_script = request.POST.get('script', None)
        if command_script:
            print ('running {}'.format(command_script))
            call_command(command_script)
            data.update({command_script: 'true'})

        return render(request, self.template_name, data)


