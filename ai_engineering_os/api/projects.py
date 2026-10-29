"""Projects API facade for future Frappe installation."""

from __future__ import annotations

from ai_engineering_os.api._core import optional_import, unavailable_response


def validate_project_profile(payload=None):
    module = optional_import("ai_engineering_os.frappe_app.api.projects")
    if module is None:
        return unavailable_response("validate_project_profile")
    return module.validate_project_profile(payload or {})
