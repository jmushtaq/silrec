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

from silrec.components.users import api as users_api
from silrec.components.lookups import api as lookup_tbls_api
from silrec.components.forest_blocks import api as forest_blocks_api
from silrec.components.main import api as main_api
from silrec.components.proposals import api as proposal_api
#from silrec.components.proposals import views as proposal_views
from silrec.components.proposals.views import ProposalExcelExportView
from silrec.components.proposals import views as proposal_views
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

# API patterns
router = routers.DefaultRouter()
router.include_root_view = False

if settings.INCLUDE_ROOT_VIEW:
    router.include_root_view = True

#router.register(r"users", users_api.UserViewSet)
router.register(r'users', users_api.UserViewSet, basename='users')
#router.register("proposal", proposal_api.ProposalViewSet, basename="proposal")
#router.register(r"lookup_tbls", lookup_tbls_api.MainViewSet, basename="lookup_tbls")
router.register(r'cohorts', forest_blocks_api.CohortViewSet, basename='cohorts')
router.register(r'treatments', forest_blocks_api.TreatmentViewSet, basename='treatments')
router.register(r'polygon', forest_blocks_api.PolygonViewSet, basename='polygon')
router.register(r'polygon2', forest_blocks_api.Polygon2ViewSet, basename='polygon2')
router.register(r'polygon3', forest_blocks_api.PolygonGeometryViewSet, basename='polygon3')
router.register(r'polygoncohorts', forest_blocks_api.PolygonCohortViewSet, basename='polygoncohorts')

router.register(r'ply_paginated',forest_blocks_api.PolygonPaginatedViewSet,"ply_paginated")
#router.register(r"proposal_paginated", proposal_api.ProposalPaginatedViewSet, basename="proposal_paginated")

router.register(r"application_types", main_api.ApplicationTypeViewSet)

router.register(r'proposals', proposal_api.ProposalViewSet, basename='proposal')
router.register(r'proposal-uploads', proposal_api.ProposalUploadShapefileViewSet, basename='proposal-upload')


# The URLs will now be:
# GET /api/proposals/ - List all proposals (using ProposalSerializer)
# GET /api/proposals/{id}/ - Get specific proposal
# PUT /api/proposals/{id}/ - Update proposal
# GET /api/proposals/status_choices/ - Get status choices for filter
# GET /api/proposals/datatable/ - DataTable endpoint

# Django OpenLayers
#router.register(r'proposal-datatable', proposal_api.ProposalDatatableViewSet, basename='proposal-datatable')
#urlpatterns = [
#    path('api/proposal-datatable/', ProposalDatatableAPIView.as_view(), name='proposal-datatable'),
#]


api_patterns = [
    #re_path(r'api/', include(router.urls)),
    re_path(r"^api/", include(router.urls)),
    #re_path(r'api/profile$', users_api.GetProfile.as_view(), name='get-profile'),
    #re_path(r"^api/user$", users_api.UserViewSet.as_view(), name="get-user"),
    #re_path(r"^api/cohorts/<int:cohort_id>/get_cohort$", forest_blocks_api.CohortViewSet.as_view({'get': 'get_cohort'}), name="get-cohort"),
    #re_path(r'^api/cohorts/<int:cohort_id>/get_cohort$', forest_blocks_api.CohortViewSet.as_view({'get': 'get_cohort'}), name='get-cohort'),
#    re_path(r"^api/proposal_type$", proposal_api.GetProposalType.as_view(), name="get-proposal-type"),

]

urlpatterns = [
    re_path(r'admin/', admin.site.urls),
    #re_path(r'', include(api_patterns)),
    re_path(r"", include(api_patterns)),
    re_path(r"^$", views.SilrecRoutingView.as_view(), name="home"),

    re_path('logout/', views.UserLogoutView.as_view(http_method_names = ['get', 'post', 'options']), name='logout'),
    #re_path(r'^$', TemplateView.as_view(template_name='base.html'), name='home'),
    #re_path(r'^$', views.SilrecRoutingView.as_view(), name='home'),

    #re_path(r'^internal/dash/', ProposalDashboardView.as_view(), name='proposal-dashboard-view'),
    re_path(r'^internal/', views.InternalView.as_view(), name='internal'),
    re_path(r'^external/', views.ExternalView.as_view(), name='external'),
    re_path(r'^contact/', views.SilrecContactView.as_view(), name='contact'),
    re_path(r'^further_info/', views.SilrecFurtherInformationView.as_view(), name='further_info'),
    re_path(r'^mgt-commands/$', views.ManagementCommandsView.as_view(), name='mgt-commands'),

    re_path(
        r"^internal/proposal/(?P<pk>\d+)/$",
        views.InternalProposalView.as_view(),
        name="internal-proposal-detail",
    ),
    #re_path('api/proposal-datatable/', proposal_api.ProposalDatatableAPIView.as_view(), name='proposal-datatable'),
    #re_path('api/', include(router.urls)),
    re_path('export/proposals/excel/', proposal_views.ProposalExcelExportView.as_view(), name='export_proposals_excel'),
    re_path(r'^proposals/add/$', proposal_views.AddProposalView.as_view(), name='add-proposal'),
    re_path(r'^proposals/view/(?P<pk>\d+)/$', proposal_views.ViewProposalView.as_view(), name='view-proposal'),

#    re_path(r'^api/proposal-uploads/upload_shapefile/$',
#            proposal_api.ProposalUploadShapefileViewSet.as_view({'post': 'upload_shapefile'}),
#            name='upload-shapefile'
#    ),

#    re_path(
#        r"^api/application_statuses_dict$",
#        proposal_api.GetApplicationStatusesDict.as_view(),
#        name="get-application-statuses-dict",
#    ),
]

if settings.ENABLE_DJANGO_LOGIN:
    urlpatterns.append(
        re_path(r"^ssologin/", LoginView.as_view(), name="ssologin")
    )


# see all registered URLs
# Add this to your urls.py temporarily
def show_urls(request):
    from django.urls import get_resolver
    from django.http import JsonResponse
    import json

    def extract_urls(urlpatterns, base=''):
        patterns = []
        for pattern in urlpatterns:
            if hasattr(pattern, 'url_patterns'):
                # This is an include - recurse into it
                patterns.extend(extract_urls(pattern.url_patterns, base + str(pattern.pattern)))
            else:
                url_info = {
                    'pattern': base + str(pattern.pattern),
                    'name': getattr(pattern, 'name', 'N/A'),
                }
                # For API views, try to get more info
                if hasattr(pattern, 'callback'):
                    url_info['view'] = pattern.callback.__name__
                elif hasattr(pattern, 'lookup_str'):
                    url_info['lookup_str'] = pattern.lookup_str
                patterns.append(url_info)
        return patterns

    resolver = get_resolver()
    all_patterns = extract_urls(resolver.url_patterns)

    return JsonResponse(all_patterns, safe=False)

urlpatterns.append(re_path(r'^debug/urls/$', show_urls, name='debug-urls'))

# Add this to urls.py
# Add this to urls.py - Working debug view
def show_api_urls(request):
    from django.http import JsonResponse
    from django.urls import get_resolver
    import json

    def extract_urls(urlpatterns, base=''):
        patterns = []
        for pattern in urlpatterns:
            if hasattr(pattern, 'url_patterns'):
                # This is an include - recurse into it
                patterns.extend(extract_urls(pattern.url_patterns, base + str(pattern.pattern)))
            elif hasattr(pattern, 'pattern'):
                url_info = {
                    'pattern': base + str(pattern.pattern),
                    'name': getattr(pattern, 'name', 'N/A'),
                }
                patterns.append(url_info)
        return patterns

    resolver = get_resolver()
    all_patterns = extract_urls(resolver.url_patterns)

    return JsonResponse(all_patterns, safe=False)

urlpatterns.append(re_path(r'^debug/api-urls/$', show_api_urls, name='debug-api-urls'))

#if settings.SHOW_DEBUG_TOOLBAR:
#    from debug_toolbar.toolbar import debug_toolbar_urls
#
#    urlpatterns = [
#        *urlpatterns,
#    ] + debug_toolbar_urls()
