from project_management.models import ProjectFieldVisibility


def filter_fields_by_role(data, project_id, role, fields_meta=None):
    """Strip hidden fields from serialized data based on project visibility rules."""
    try:
        rule = ProjectFieldVisibility.objects.get(project_id=project_id, role=role)
        hidden = set(rule.hidden_fields or [])
        visible = set(rule.visible_fields or [])
        if isinstance(data, dict):
            if hidden:
                return {k: v for k, v in data.items() if k not in hidden}
            if visible:
                return {k: v for k, v in data.items() if k in visible}
        return data
    except ProjectFieldVisibility.DoesNotExist:
        return data
