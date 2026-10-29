"""Skills API facade for future Frappe installation."""

from __future__ import annotations

from ai_engineering_os.api._core import optional_import, unavailable_response


def explain_skill_selection(payload=None):
    module = optional_import("ai_engineering_os.frappe_app.api.skills")
    if module is None:
        return unavailable_response("explain_skill_selection")
    return module.explain_skill_selection(payload or {})
