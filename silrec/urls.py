from django.conf import settings
#from django.contrib import admin
from silrec.admin import admin
#from django.conf.urls import url, include
from django.conf.urls import include
from django.urls import path, re_path
from django.contrib.auth.views import LogoutView, LoginView
from django.views.decorators.csrf import csrf_exempt

from django.contrib.auth import logout, login # DEV ONLY
from django.views.generic import TemplateView

from django.conf.urls.static import static
from rest_framework import routers
from rest_framework_swagger.views import get_swagger_view
from silrec import views
#from sqs.components.gisquery import api as gisquery_api
#from sqs.components.gisquery import views as gisquery_views

#schema_view = get_swagger_view(title='SQS API')

# API patterns
'''
router = routers.DefaultRouter()
router.register(r'layers', gisquery_api.DefaultLayerViewSet, basename='layers')
router.register(r'logs', gisquery_api.LayerRequestLogViewSet, basename='logs')
router.register(r'point_query', gisquery_api.PointQueryViewSet, basename='point_query')
router.register(r'tasks', gisquery_api.TaskViewSet, basename='tasks')
router.register(r'task_paginated', gisquery_api.TaskPaginatedViewSet, basename='task_paginated')

api_patterns = [
    re_path(r'^api/v1/',include(router.urls)),
]

# URL Patterns
urlpatterns = [
    re_path(r'admin/', admin.site.urls),
    re_path(r'^logout/$', LogoutView.as_view(), {'next_page': '/'}, name='logout'),
    re_path(r'', include(api_patterns)),
    re_path(r'^$', TemplateView.as_view(template_name='sqs/base2.html'), name='home'),

    re_path(r'api/v1/das/task_queue', csrf_exempt(gisquery_views.DisturbanceLayerQueueView.as_view()), name='das_task_queue'),
    re_path(r'api/v1/das/spatial_query', csrf_exempt(gisquery_views.DisturbanceLayerView.as_view()), name='das_spatial_query'),
    re_path(r'api/v1/add_layer', csrf_exempt(gisquery_views.DefaultLayerProviderView.as_view()), name='add_layer'),
]
'''

urlpatterns = [
    re_path(r'admin/', admin.site.urls),
    re_path('logout/', views.UserLogoutView.as_view(http_method_names = ['get', 'post', 'options']), name='logout'),
    #re_path(r'^$', TemplateView.as_view(template_name='base.html'), name='home'),
    re_path(r'^$', views.SilrecRoutingView.as_view(), name='home'),

    re_path(r'^internal/', views.InternalView.as_view(), name='internal'),
    re_path(r'^external/', views.ExternalView.as_view(), name='external'),
    re_path(r'^contact/', views.SilrecContactView.as_view(), name='contact'),
    re_path(r'^further_info/', views.SilrecFurtherInformationView.as_view(), name='further_info'),
    re_path(r'^mgt-commands/$', views.ManagementCommandsView.as_view(), name='mgt-commands'),

]

if settings.ENABLE_DJANGO_LOGIN:
    urlpatterns.append(
        re_path(r"^ssologin/", LoginView.as_view(), name="ssologin")
    )

#if settings.SHOW_DEBUG_TOOLBAR:
#    from debug_toolbar.toolbar import debug_toolbar_urls
#
#    urlpatterns = [
#        *urlpatterns,
#    ] + debug_toolbar_urls()
