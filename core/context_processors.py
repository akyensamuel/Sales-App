"""
Context processors for providing user data to templates
"""
import json


def user_groups_context(request):
    """
    Add user groups information to template context
    Provides both list and JSON format for template usage
    """
    user_groups = []
    user_groups_json = '[]'
    
    if request.user.is_authenticated:
        user_groups = list(request.user.groups.values_list('name', flat=True))
        user_groups_json = json.dumps(user_groups)
    
    return {
        'user_groups': user_groups,
        'user_groups_json': user_groups_json,
    }
