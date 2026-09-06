"""
exception_handler.py — Wraps DRF's default exception handling so every
error response has a consistent shape:

    {"error": {"code": "validation_error", "message": "...", "detail": ...}}

and every 5xx is logged server-side with a stack trace while returning a
generic message to the client — never leaking internals (SQL, file
paths, stack traces) in the HTTP response body.
"""

import logging
import uuid

from django.http import Http404
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_default_handler

logger = logging.getLogger("story")

_CODE_BY_STATUS = {
    400: "validation_error",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    429: "throttled",
}


def structured_exception_handler(exc, context):
    response = drf_default_handler(exc, context)

    if response is not None:
        code = _CODE_BY_STATUS.get(response.status_code, "error")
        message = response.data if isinstance(response.data, str) else None
        response.data = {
            "error": {
                "code": code,
                "message": message or _summarize(response.data),
                "detail": response.data,
            }
        }
        if response.status_code >= 500:
            logger.error("Unhandled API error: %s", exc, exc_info=True)
        return response

    # Anything DRF didn't recognize (raw exceptions escaping a view) is a
    # server error. Log it fully server-side; return only a correlation id
    # to the client so support can find the matching log line without
    # exposing internals.
    if isinstance(exc, Http404):
        return Response(
            {"error": {"code": "not_found", "message": "Not found.", "detail": None}},
            status=404,
        )

    incident_id = str(uuid.uuid4())
    logger.error("Unhandled exception [%s]: %s", incident_id, exc, exc_info=True)
    return Response(
        {
            "error": {
                "code": "internal_error",
                "message": "Something went wrong on our end.",
                "incident_id": incident_id,
            }
        },
        status=500,
    )


def _summarize(detail) -> str:
    if isinstance(detail, dict):
        first_key = next(iter(detail), None)
        if first_key is not None:
            value = detail[first_key]
            if isinstance(value, list) and value:
                return f"{first_key}: {value[0]}"
        return "Invalid request."
    if isinstance(detail, list) and detail:
        return str(detail[0])
    return "Invalid request."
