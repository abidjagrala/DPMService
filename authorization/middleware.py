from .services.permission_engine import get_user_permissions, has_any_permission


class AuthorizationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            request.user_permissions = get_user_permissions(request.user)
            request.user_has_dynamic_perms = has_any_permission(request.user)
        else:
            request.user_permissions = {}
            request.user_has_dynamic_perms = False

        response = self.get_response(request)
        return response
