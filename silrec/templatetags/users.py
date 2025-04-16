from django.template import Library
from django.conf import settings
from silrec import helpers as silrec_helpers
from datetime import datetime, timedelta
from django.utils import timezone
import pytz

register = Library()


@register.simple_tag(takes_context=True)
def is_silrec_admin(context):
    # checks if user is an AdminUser
    request = context['request']
    #return silrec_helpers.is_sqs_admin(request)
    return True

@register.simple_tag(takes_context=True)
def is_internal(context):
    # checks if user is a departmentuser and logged in via single sign-on
    request = context['request']
    #return silrec_helpers.is_internal(request)
    return True

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

@register.simple_tag(takes_context=True)
def is_silrec_admin(context):
    # checks if user is an AdminUser
    request = context['request']
    #return silrec_helpers.is_silrec_admin(request)
    return True

@register.simple_tag(takes_context=True)
def is_silrec_admin(context):
    # checks if user is an AdminUser
    request = context['request']
    #return silrec_helpers.is_silrec_admin(request)
    return True

@register.simple_tag(takes_context=True)
def is_internal(context):
    # checks if user is a departmentuser and logged in via single sign-on
    request = context['request']
    #eturn disturbance_helpers.is_internal(request)
    return True

@register.simple_tag(takes_context=True)
def is_internal_path(context):
    # checks if user is viewing page via '/internal/' or '/external/' url
    #return 'internal/' in context['url_path']
    return True

@register.simple_tag()
def system_maintenance_due():
    """ Returns True (actually a time str), if within <timedelta hours> of system maintenance due datetime """
    return False
'''
    tz = pytz.timezone(settings.TIME_ZONE)
    now = timezone.now()  # returns UTC time
    qs = SystemMaintenance.objects.filter(start_date__gte=now - timedelta(minutes=1))
    if qs:
        obj = qs.earliest('start_date')
        if now >= obj.start_date - timedelta(hours=settings.SYSTEM_MAINTENANCE_WARNING) and now <= obj.start_date + timedelta(minutes=1):
            # display time in local timezone
            return '{0} - {1} (Duration: {2} mins)'.format(obj.start_date.astimezone(tz=tz).strftime(TIME_FORMAT), obj.end_date.astimezone(tz=tz).strftime(TIME_FORMAT), obj.duration())
    return False
'''


