"""System Manager-only canonical skill preview record sync API."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:  # pragma: no cover - Frappe is not installed in local unit runs.
    import frappe  # type: ignore
except Exception:  # pragma: no cover
    frappe = None  # type: ignore

ALLOWED_DTYPES = {
    "AI Skill Source",
    "AI Skill Package",
    "AI Skill Version",
    "AI Skill Capability",
    "AI Distribution Target",
}
COLLECTIONS = (
    "skill_source_payloads",
    "skill_package_payloads",
    "skill_version_payloads",
    "skill_capability_payloads",
    "distribution_target_payloads",
)
P12G_APPROVED_INTERNAL = {"codex-task-compiler", "project-memory-maintainer"}
P12G_BLOCKED_INTERNAL = {
    "ai-performance-orchestrator",
    "frappe-engineering-master",
    "frappe-testing-quality-engine",
}


def _whitelist(methods: list[str]):
    def decorate(func):
        if frappe is None:
            return func
        return frappe.whitelist(methods=methods)(func)

    return decorate


def require_system_manager() -> None:
    if frappe is None:
        return
    user = frappe.session.user
    if user == "Guest" or "System Manager" not in frappe.get_roles(user):
        frappe.throw("System Manager role is required.", frappe.PermissionError)


@_whitelist(["GET"])
def get_preview_skill_packages() -> dict[str, Any]:
    require_system_manager()
    if frappe is None:
        return {"ok": False, "reason": "Frappe is not available."}
    records = frappe.get_all(
        "AI Skill Package",
        filters={"skill_name": ["in", _target_skills()]},
        fields=["name", "skill_name", "display_name", "status", "primary_provider_targets", "benchmark_score", "notes"],
        order_by="skill_name asc",
    )
    packages = [_package_status(record) for record in records]
    return {
        "ok": True,
        "activation_allowed": any(item["internal_active"] for item in packages),
        "ready_for_activation": any(item["internal_active"] for item in packages),
        "global_export_allowed": False,
        "buildfast_auto_use": False,
        "packages": packages,
    }


@_whitelist(["POST"])
def apply_preview_skill_records(payloads_path: str | None = None, payloads: dict | str | None = None) -> dict[str, Any]:
    require_system_manager()
    if frappe is None:
        return {"ok": False, "reason": "Frappe is not available."}
    bundle = _load_payloads(payloads_path, payloads)
    errors = _validate_bundle(bundle)
    if errors:
        frappe.throw("; ".join(errors))
    counts: dict[str, int] = {collection: 0 for collection in COLLECTIONS}
    source_names: dict[str, str] = {}
    package_names: dict[str, str] = {}

    for record in bundle.get("skill_source_payloads", []):
        actual = _upsert_record(record)
        source_names[record["source_name"]] = actual
        counts["skill_source_payloads"] += 1

    for record in bundle.get("skill_package_payloads", []):
        actual = _upsert_record(record)
        package_names[record["skill_name"]] = actual
        counts["skill_package_payloads"] += 1

    for record in bundle.get("skill_version_payloads", []):
        record = dict(record)
        record["skill_package"] = package_names.get(record["skill_package"], record["skill_package"])
        record["source"] = source_names.get(record["source"], record["source"])
        _upsert_record(record)
        counts["skill_version_payloads"] += 1

    for record in bundle.get("skill_capability_payloads", []):
        record = dict(record)
        record["skill_package"] = package_names.get(record["skill_package"], record["skill_package"])
        _upsert_record(record)
        counts["skill_capability_payloads"] += 1

    for record in bundle.get("distribution_target_payloads", []):
        _upsert_record(record)
        counts["distribution_target_payloads"] += 1
    frappe.db.commit()
    return {
        "ok": True,
        "applied": True,
        "counts": counts,
        "activation_allowed": False,
        "ready_for_activation": False,
    }


@_whitelist(["POST"])
def apply_internal_skill_activation(payloads_path: str | None = None, payloads: dict | str | None = None) -> dict[str, Any]:
    require_system_manager()
    if frappe is None:
        return {"ok": False, "reason": "Frappe is not available."}
    bundle = _load_internal_payloads(payloads_path, payloads)
    errors = _validate_internal_activation_bundle(bundle)
    if errors:
        frappe.throw("; ".join(errors))
    updated: list[str] = []
    for record in bundle.get("activation_payloads", []):
        name = frappe.db.get_value("AI Skill Package", {"skill_name": record["skill_name"]}, "name")
        if not name:
            frappe.throw(f"AI Skill Package not found: {record['skill_name']}")
        doc = frappe.get_doc("AI Skill Package", name)
        doc.status = "active"
        doc.notes = record["notes"]
        doc.save()
        updated.append(record["skill_name"])
    frappe.db.commit()
    return {
        "ok": True,
        "applied": True,
        "activation_scope": "internal_aios_only",
        "activated_internal_skills": updated,
        "kept_inactive": sorted(P12G_BLOCKED_INTERNAL),
        "global_export_allowed": False,
        "codex_global_export": False,
        "claude_global_export": False,
        "buildfast_auto_use": False,
    }


@_whitelist(["GET"])
def get_internal_skill_activation_status() -> dict[str, Any]:
    require_system_manager()
    if frappe is None:
        return {"ok": False, "reason": "Frappe is not available."}
    records = frappe.get_all(
        "AI Skill Package",
        filters={"skill_name": ["in", _target_skills()]},
        fields=["name", "skill_name", "display_name", "status", "notes"],
        order_by="skill_name asc",
    )
    packages = [_package_status(record) for record in records]
    return {
        "ok": True,
        "activation_scope": "internal_aios_only",
        "global_export_allowed": False,
        "codex_global_export": False,
        "claude_global_export": False,
        "buildfast_auto_use": False,
        "packages": packages,
        "activated_internal_count": sum(1 for item in packages if item["internal_active"]),
        "inactive_count": sum(1 for item in packages if not item["internal_active"]),
    }


def _load_payloads(payloads_path: str | None, payloads: dict | str | None) -> dict[str, list[dict[str, Any]]]:
    if payloads:
        if isinstance(payloads, str):
            return json.loads(payloads)
        return dict(payloads)
    path = Path(payloads_path or "")
    if not str(path).startswith("/tmp/") or not path.name.startswith("aios_p12e_canonical_skill_sync"):
        raise ValueError("payloads_path must point to a P12E sync file under /tmp.")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_internal_payloads(payloads_path: str | None, payloads: dict | str | None) -> dict[str, Any]:
    if payloads:
        if isinstance(payloads, str):
            return json.loads(payloads)
        return dict(payloads)
    path = Path(payloads_path or "")
    if not str(path).startswith("/tmp/") or not path.name.startswith("aios_p12g_internal_activation"):
        raise ValueError("payloads_path must point to a P12G internal activation file under /tmp.")
    return json.loads(path.read_text(encoding="utf-8"))


def _upsert_record(record: dict[str, Any]) -> str:
    doctype = record["doctype"]
    existing_name = _existing_name(record)
    data = dict(record)
    data.pop("name", None)
    if existing_name:
        doc = frappe.get_doc(doctype, existing_name)
        for key, value in data.items():
            if key != "doctype":
                doc.set(key, value)
        doc.save()
        return doc.name
    doc = frappe.get_doc(data)
    doc.insert()
    return doc.name


def _existing_name(record: dict[str, Any]) -> str | None:
    doctype = record["doctype"]
    if doctype == "AI Skill Source":
        return frappe.db.get_value(doctype, {"source_name": record["source_name"]}, "name")
    if doctype == "AI Skill Package":
        return frappe.db.get_value(doctype, {"skill_name": record["skill_name"]}, "name")
    if doctype == "AI Skill Version":
        return frappe.db.get_value(doctype, {"skill_package": record["skill_package"], "version": record["version"]}, "name")
    if doctype == "AI Skill Capability":
        return frappe.db.get_value(doctype, {"skill_package": record["skill_package"], "capability_name": record["capability_name"]}, "name")
    if doctype == "AI Distribution Target":
        return frappe.db.get_value(doctype, {"target_name": record["target_name"]}, "name")
    return None


def _validate_bundle(bundle: dict[str, list[dict[str, Any]]]) -> list[str]:
    errors: list[str] = []
    for collection in COLLECTIONS:
        for record in bundle.get(collection, []):
            errors.extend(_validate_record(collection, record))
    return errors


def _validate_record(collection: str, record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    doctype = record.get("doctype")
    name = record.get("name", "<unnamed>")
    if doctype not in ALLOWED_DTYPES:
        errors.append(f"{collection}:{name} has disallowed doctype {doctype}")
    if record.get("status") == "active":
        errors.append(f"{collection}:{name} is active")
    if record.get("activation_allowed") is True:
        errors.append(f"{collection}:{name} activation_allowed=true")
    if record.get("ready_for_activation") is True:
        errors.append(f"{collection}:{name} ready_for_activation=true")
    if doctype == "AI Distribution Target" and int(record.get("enabled", 0) or 0) != 0:
        errors.append(f"{collection}:{name} distribution target enabled")
    return errors


def _validate_internal_activation_bundle(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if bundle.get("global_export_allowed") or bundle.get("codex_global_export") or bundle.get("claude_global_export"):
        errors.append("global export flags must be false")
    if bundle.get("buildfast_auto_use"):
        errors.append("BuildFast auto-use must be false")
    records = bundle.get("activation_payloads", [])
    skills = {record.get("skill_name") for record in records}
    if skills != P12G_APPROVED_INTERNAL:
        errors.append(f"activation payload must target exactly {sorted(P12G_APPROVED_INTERNAL)}")
    if skills & P12G_BLOCKED_INTERNAL:
        errors.append("blocked skill requested for activation")
    for record in records:
        if record.get("doctype") != "AI Skill Package":
            errors.append(f"{record.get('skill_name')} has invalid doctype")
        if record.get("status") != "active":
            errors.append(f"{record.get('skill_name')} must use existing status active")
        if record.get("activation_scope") != "internal_aios_only":
            errors.append(f"{record.get('skill_name')} activation scope must be internal_aios_only")
        if record.get("global_export_allowed") or record.get("codex_global_export") or record.get("claude_global_export"):
            errors.append(f"{record.get('skill_name')} export flags must be false")
        if record.get("buildfast_auto_use"):
            errors.append(f"{record.get('skill_name')} buildfast_auto_use must be false")
    return errors


def _package_status(record: dict[str, Any]) -> dict[str, Any]:
    notes = record.get("notes") or ""
    internal_active = record.get("status") == "active" and "internal_aios_only" in notes
    return {
        "name": record.get("name"),
        "skill_name": record.get("skill_name"),
        "display_name": record.get("display_name"),
        "status": record.get("status"),
        "primary_provider_targets": record.get("primary_provider_targets"),
        "benchmark_score": record.get("benchmark_score"),
        "internal_active": internal_active,
        "activation_scope": "internal_aios_only" if internal_active else "preview",
        "activation_allowed": internal_active,
        "ready_for_activation": internal_active,
        "global_export_allowed": False,
        "codex_global_export": False,
        "claude_global_export": False,
        "buildfast_auto_use": False,
        "rollback_available": internal_active and "rollback_available=true" in notes,
    }


def _target_skills() -> list[str]:
    return [
        "ai-performance-orchestrator",
        "frappe-engineering-master",
        "codex-task-compiler",
        "project-memory-maintainer",
        "frappe-testing-quality-engine",
    ]
