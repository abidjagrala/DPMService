from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'api'

router = DefaultRouter()
router.register(r'states', views.StateViewSet)
router.register(r'cities', views.CityViewSet)
router.register(r'service-types', views.ServiceTypeViewSet)
router.register(r'asset-types', views.AssetTypeViewSet)
router.register(r'transport-types', views.TransportTypeViewSet)
router.register(r'users', views.UserViewSet)
router.register(r'clients', views.ClientViewSet)
router.register(r'employees', views.EmployeeViewSet)
router.register(r'assets', views.AssetViewSet)
router.register(r'assignments', views.AssetAssignmentViewSet)
router.register(r'subnets', views.SubnetViewSet)
router.register(r'ip-addresses', views.IPAddressViewSet)
router.register(r'devices', views.NetworkDeviceViewSet)
router.register(r'tickets', views.ServiceTicketViewSet)
router.register(r'comments', views.TicketCommentViewSet)

from authorization import api_views as auth_api

auth_router = DefaultRouter()
auth_router.register(r'groups', auth_api.GroupViewSet)
auth_router.register(r'roles', auth_api.RoleViewSet)
auth_router.register(r'modules', auth_api.ModuleViewSet)
auth_router.register(r'module-permissions', auth_api.ModulePermissionViewSet)
auth_router.register(r'model-permissions', auth_api.ModelPermissionViewSet)
auth_router.register(r'menu-permissions', auth_api.MenuPermissionViewSet)
auth_router.register(r'user-assignments', auth_api.UserRoleAssignmentViewSet)
auth_router.register(r'audit-logs', auth_api.AuditLogViewSet)

urlpatterns = [
    path('v1/', include(router.urls)),
    path('v1/auth/token/', views.api_token_view, name='token'),
    path('v1/auth/me/', views.api_user_me_view, name='user-me'),
    path('v1/dashboard/', views.api_dashboard_view, name='dashboard'),
    path('v1/auth/', include(auth_router.urls)),
    path('v1/auth/roles/<int:pk>/clone/', auth_api.api_role_clone_view, name='role-clone'),
    path('v1/auth/seed/', auth_api.api_seed_view, name='auth-seed'),
    path('auth/', include('rest_framework.urls')),
]
