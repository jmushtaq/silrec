from confy import env
from django.conf import settings
import logging


logger = logging.getLogger(__name__)

def silrec_url(request):
    PUBLIC_URL = 'https://silrec.dbca.wa.gov.au'
    displayed_system_name = settings.SYSTEM_NAME
    support_email = settings.SUPPORT_EMAIL

    return {
        #'DOMAIN_DETECTED': settings.DOMAIN_DETECTED,
        'DEBUG': settings.DEBUG,
        'DEV_STATIC': settings.DEV_STATIC,
        'DEV_STATIC_URL': settings.DEV_STATIC_URL,
        #'TEMPLATE_GROUP': settings.DOMAIN_DETECTED,
        'SYSTEM_NAME': settings.SYSTEM_NAME,
        'PUBLIC_URL': PUBLIC_URL,
        #'APPLICATION_GROUP': settings.DOMAIN_DETECTED,
        'DISPLAYED_SYSTEM_NAME': displayed_system_name,
        'SUPPORT_EMAIL': support_email,
        'build_tag': settings.BUILD_TAG,
        #'KMI_SERVER_URL': settings.KMI_SERVER_URL,
        #'SHOW_DAS_MAP': settings.SHOW_DAS_MAP,
        #'MAX_LAYERS_PER_SQQ': settings.MAX_LAYERS_PER_SQQ,
    }
