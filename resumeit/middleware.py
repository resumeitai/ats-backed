import logging
import time

logger = logging.getLogger('resumeit.request')


class RequestLoggingMiddleware:
    """Logs method, path, status code, and response time for every request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()
        response = self.get_response(request)
        duration = time.time() - start_time

        logger.info(
            '%s %s %s %.2fms',
            request.method,
            request.get_full_path(),
            response.status_code,
            duration * 1000,
        )
        return response
