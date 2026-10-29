"""Providers API facade for future Frappe installation."""

from __future__ import annotations

from ai_engineering_os.api._core import optional_import, unavailable_response


def explain_provider_decision(payload=None):
    module = optional_import("ai_engineering_os.frappe_app.api.providers")
    if module is None:
        return unavailable_response("explain_provider_decision")
    return module.explain_provider_decision(payload or {})
