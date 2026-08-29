# -*- coding: utf-8 -*-
"""Request logging middleware (Development Plan Day 10 observability).

Logs a summary line per request at INFO. Never logs bodies, credentials, or
authorization headers (decision log DG-6/DG-15 and Overview §29.4 require
credentials never logged). The request path is safe; query strings are
stripped to avoid leaking tokens.
"""
import logging
import time

logger = logging.getLogger("apps")


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)
        duration_ms = (time.perf_counter() - start) * 1000
        path = request.path
        # Never log query strings (may contain sensitive params) or the request body.
        logger.info(
            "%s %s -> %s (%.1f ms)",
            request.method,
            path,
            response.status_code,
            duration_ms,
        )
        return response
