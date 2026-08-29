# -*- coding: utf-8 -*-
"""Standard API response envelope used by every endpoint in the foundation.

Success: { "success": true, "data": <payload> }
Error:   { "success": false, "error": { "code": "...", "message": "...", "details": {...} } }

This gives the frontend a single, predictable shape and puts every error into
the documented structured-error form (Development Plan Phase 1 - BE-01..BE-23).
"""
from rest_framework.views import exception_handler as drf_exception_handler


def api_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None
    detail = response.data
    if isinstance(detail, dict) and "detail" in detail and len(detail) == 1:
        message = detail["detail"]
        details = {}
    else:
        message = "Validation failed."
        details = detail if isinstance(detail, dict) else {"detail": detail}
    response.data = {
        "success": False,
        "error": {
            "code": _code_for(response.status_code),
            "message": message,
            "details": details,
        },
    }
    return response


def _code_for(status_code):
    mapping = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        429: "THROTTLED",
        500: "INTERNAL_ERROR",
    }
    return mapping.get(status_code, "ERROR")


def ok(data=None, status=200):
    payload = {"success": True}
    if data is not None:
        payload["data"] = data
    from rest_framework.response import Response

    return Response(payload, status=status)
