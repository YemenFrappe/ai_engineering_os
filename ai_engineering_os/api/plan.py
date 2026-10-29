"""Plan API facade for future Frappe installation."""

from __future__ import annotations

from ai_engineering_os.api._core import optional_import, unavailable_response


def create_plan(payload=None):
    module = optional_import("ai_engineering_os.frappe_app.api.plan")
    if module is None:
        return unavailable_response("create_plan")
    return module.create_plan(payload or {})
