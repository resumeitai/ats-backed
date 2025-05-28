from django.apps import AppConfig


class AtsCheckerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ats_checker'
    verbose_name = 'ATS Score Checker'