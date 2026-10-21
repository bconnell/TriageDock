from rest_framework.permissions import BasePermission


class IsIncidentOperator(BasePermission):
    message = "You do not have permission to change incidents."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.has_perm("incidents.change_incident")
