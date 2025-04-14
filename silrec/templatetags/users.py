from django.template import Library
from django.conf import settings
from silrec import helpers as silrec_helpers
from datetime import datetime, timedelta
from django.utils import timezone
import pytz

register = Library()


@register.simple_tag(takes_context=True)
def is_sqs_admin(context):
    # checks if user is an AdminUser
    request = context['request']
    return silrec_helpers.is_sqs_admin(request)

@register.simple_tag(takes_context=True)
def is_internal(context):
    # checks if user is a departmentuser and logged in via single sign-on
    request = context['request']
    return silrec_helpers.is_internal(request)

@register.simple_tag(takes_context=True)
def is_model_backend(context):
    # Return True if user logged in via single sign-on (or False via social_auth i.e. an external user signing in with a login-token)
    request = context['request']
    return silrec_helpers.is_model_backend(request)

@register.simple_tag(takes_context=True)
def is_payment_officer(context):
    request = context['request']
    #TODO: fix this
    return False #is_payment_admin(request.user)

@register.simple_tag()
def dept_support_phone2():
    return settings.DEPT_NAME

