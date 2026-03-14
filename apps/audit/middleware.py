import logging

logger = logging.getLogger(__name__)


class AuditLogMiddleware:
    """
    Middleware-заглушка для будущего расширения.
    Логирование login/logout реализовано через signals в apps.accounts.signals.
    Здесь можно добавить логирование POST-запросов или других событий.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response
