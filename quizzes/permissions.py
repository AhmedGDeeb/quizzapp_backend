from rest_framework.permissions import BasePermission

class IsInstructor(BasePermission):
    """
    Permission class to check if user is an instructor or admin
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['instructor', 'admin']

    def has_object_permission(self, request, view, obj):
        """
        Check if user has permission on a specific object
        """
        if request.user.role == 'admin':
            return True
        
        if request.user.role == 'instructor':
            # Check if user is the creator of the quiz
            if hasattr(obj, 'creator'):
                return obj.creator == request.user
            # Check if user is the quiz creator (for questions/choices)
            if hasattr(obj, 'quiz'):
                return obj.quiz.creator == request.user
        
        return False


class IsAdminUser(BasePermission):
    """
    Permission class to check if user is an admin
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'