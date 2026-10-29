"""Health API facade for future Frappe installation."""

from __future__ import annotations

from ai_engineering_os.version import get_version_info


def get_health() -> dict:
    health = {
        "ok": True,
        "app": "AI Engineering OS",
        "status": "repo_local_frappe_layout",
    }
    health.update(get_version_info())
    return health
