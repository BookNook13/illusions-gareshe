"""
health.py — Liveness/readiness endpoint for load balancers, container
orchestrators, and uptime monitors. Deliberately outside the story app
and outside DRF's auth stack: it must respond even if JWT config or the
story app itself is broken, and must never require a token.
"""

from django.db import connection
from django.http import JsonResponse


def healthz(request):
    """
    GET /healthz/ -> 200 if the app can reach its database, 503 otherwise.
    Kept dependency-free from DRF on purpose: this needs to work even in
    degraded states where the rest of the API stack might not.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"status": "ok"})
    except Exception as exc:  # noqa: BLE001 — deliberately broad for a health probe
        return JsonResponse({"status": "error", "detail": str(exc)}, status=503)
