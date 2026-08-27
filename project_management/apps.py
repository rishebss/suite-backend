from django.apps import AppConfig


class ProjectManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'project_management'
    verbose_name = 'HertexFlow — Project & Work Management'

    def ready(self):
        import project_management.signals  # noqa
