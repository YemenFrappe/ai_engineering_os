"""Memory API facade for future Frappe installation."""

from __future__ import annotations

from ai_engineering_os.api._core import optional_import, unavailable_response


def validate_memory_entry(payload=None):
    module = optional_import("ai_engineering_os.frappe_app.api.memory")
    if module is None:
        return unavailable_response("validate_memory_entry")
    return module.validate_memory_entry(payload or {})
