"""System Manager-only BuildFast connector API for AI Engineering OS."""

from __future__ import annotations

import json
from typing import Any

from ai_engineering_os.api._core import optional_import

try:  # pragma: no cover - Frappe is not installed in local unit runs.
    import frappe  # type: ignore
except Exception:  # pragma: no cover
    frappe = None  # type: ignore


def _whitelist(methods: list[str]):
    def decorate(func):
        if frappe is None:
            return func
        return frappe.whitelist(methods=methods)(func)

    return decorate


def require_system_manager() -> None:
    """Require an authenticated System Manager when running inside Frappe."""

    if frappe is None:
        return
    user = frappe.session.user
    if user == "Guest" or "System Manager" not in frappe.get_roles(user):
        frappe.throw("System Manager role is required.", frappe.PermissionError)


@_whitelist(["POST"])
def plan_from_buildfast(payload: dict | str | None = None) -> dict[str, Any]:
    require_system_manager()
    data = _coerce_payload(payload)
    service = _service()
    if service is not None:
        return service.plan_from_buildfast(data)
    return _fallback_plan(data)


@_whitelist(["POST"])
def export_codex_from_buildfast(payload: dict | str | None = None) -> dict[str, Any]:
    require_system_manager()
    data = _coerce_payload(payload)
    service = _service()
    if service is not None:
        return service.export_codex_from_buildfast(data)
    return _fallback_export(data, "codex")


@_whitelist(["POST"])
def export_claude_from_buildfast(payload: dict | str | None = None) -> dict[str, Any]:
    require_system_manager()
    data = _coerce_payload(payload)
    service = _service()
    if service is not None:
        return service.export_claude_from_buildfast(data)
    return _fallback_export(data, "claude")


@_whitelist(["GET"])
def get_buildfast_connector_health() -> dict[str, Any]:
    require_system_manager()
    return {
        "ok": True,
        "app": "AI Engineering OS",
        "feature": "buildfast_connector",
        "integration_target": "buildfast",
        "mode": "preview",
        "activation_allowed": False,
        "writes_files": False,
    }


def _service():
    return optional_import("ai_engineering_os.frappe_app.api.buildfast_connector")


def _coerce_payload(payload: dict | str | None) -> dict[str, Any]:
    if payload is None and frappe is not None:
        payload = frappe.form_dict.get("payload")
    if payload is None:
        return {}
    if isinstance(payload, str):
        return json.loads(payload) if payload.strip() else {}
    return dict(payload)


def _fallback_plan(payload: dict[str, Any]) -> dict[str, Any]:
    text = " ".join(str(payload.get(key, "")) for key in ("goal", "request_text", "project_type", "risk_hint"))
    lowered = text.lower()
    high_risk = any(term in lowered for term in ("production", "deploy", "restart", "migrate", "ssh"))
    planning = any(term in lowered for term in ("architecture", "planning", "review"))
    provider = "both" if high_risk else "claude" if planning else "codex"
    blocked = ["write", "ssh", "deploy", "migrate", "restart"] if high_risk else ["ssh", "deploy", "migrate", "restart"]
    export_codex = _fallback_export(payload, "codex")
    export_claude = _fallback_export(payload, "claude")
    return {
        "ok": True,
        "mode": "preview",
        "integration_target": "buildfast",
        "provider": provider,
        "review_provider": "claude" if provider in {"codex", "both"} else "",
        "primary_skill": "frappe-engineering-master" if provider != "claude" else "pmo-product-execution-engine",
        "supporting_skills": ["codex-task-compiler", "frappe-testing-quality-engine"],
        "tools": ["local_repo", "frappe_metadata"],
        "risk_level": "high" if high_risk else "low",
        "autonomy_mode": "approval_required" if high_risk else "auto_execute",
        "blocked_actions": blocked,
        "task_prompt": str(payload.get("request_text") or payload.get("goal") or "BuildFast connector preview."),
        "acceptance_criteria": ["Preview response only", "No BuildFast mutation", "No skill activation"],
        "validation_steps": ["Review provider, skills, risk, and blocked actions"],
        "codex_export_preview": export_codex,
        "claude_export_preview": export_claude,
        "warnings": [],
        "next_actions": ["Request explicit approval before SSH, migrate, deploy, restart, or write actions."],
        "activation_allowed": False,
        "writes_files": False,
    }


def _fallback_export(payload: dict[str, Any], provider: str) -> dict[str, Any]:
    text = " ".join(str(payload.get(key, "")) for key in ("goal", "request_text", "risk_hint"))
    high_risk = any(term in text.lower() for term in ("production", "deploy", "restart", "migrate", "ssh"))
    return {
        "ok": True,
        "mode": "preview",
        "integration_target": "buildfast",
        "provider": provider,
        "task_id": f"buildfast-preview-{provider}",
        "selected_skills": ["frappe-engineering-master", "codex-task-compiler"],
        "risk_level": "high" if high_risk else "low",
        "blocked_actions": ["write", "ssh", "deploy", "migrate", "restart"] if high_risk else ["ssh", "deploy", "migrate", "restart"],
        "task_prompt": str(payload.get("request_text") or payload.get("goal") or "BuildFast connector preview."),
        "acceptance_criteria": ["Preview response only", "No BuildFast mutation", "No skill activation"],
        "validation_steps": ["Review payload and safety gates"],
        "files_preview": ["task_prompt.md", "skill_bundle.json", "risk_policy.json"],
        "warnings": [],
        "next_actions": ["Keep this response as a preview until explicitly approved."],
        "writes_files": False,
        "activation_allowed": False,
    }
