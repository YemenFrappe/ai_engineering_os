"""System Manager-only Command Center API for AI Engineering OS."""

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
def create_plan(payload: dict | str | None = None) -> dict[str, Any]:
    require_system_manager()
    data = _coerce_payload(payload)
    service = _service()
    if service is not None:
        return service.create_plan(data)
    return _fallback_plan(data)


@_whitelist(["POST"])
def export_codex_task(payload: dict | str | None = None) -> dict[str, Any]:
    require_system_manager()
    data = _coerce_payload(payload)
    service = _service()
    if service is not None:
        return service.export_codex_task(data)
    return _fallback_export(data, "codex")


@_whitelist(["POST"])
def export_claude_task(payload: dict | str | None = None) -> dict[str, Any]:
    require_system_manager()
    data = _coerce_payload(payload)
    service = _service()
    if service is not None:
        return service.export_claude_task(data)
    return _fallback_export(data, "claude")


@_whitelist(["GET", "POST"])
def get_canonical_pack_preview(payload: dict | str | None = None) -> dict[str, Any]:
    require_system_manager()
    service = _service()
    if service is not None:
        return service.get_canonical_pack_preview(_coerce_payload(payload))
    return _fallback_pack_preview(_coerce_payload(payload))


@_whitelist(["GET"])
def get_aios_health() -> dict[str, Any]:
    require_system_manager()
    return {
        "ok": True,
        "app": "AI Engineering OS",
        "feature": "command_center",
        "mode": "preview",
        "activation_allowed": False,
    }


@_whitelist(["GET"])
def get_internal_skill_activation_status() -> dict[str, Any]:
    require_system_manager()
    if frappe is not None:
        from ai_engineering_os.api.skill_preview_sync import get_internal_skill_activation_status as get_status

        return get_status()
    service = _service()
    if service is not None:
        return service.get_internal_skill_activation_status()
    return _fallback_internal_skill_activation_status()


def _service():
    return optional_import("ai_engineering_os.frappe_app.api.command_center")


def _coerce_payload(payload: dict | str | None) -> dict[str, Any]:
    if payload is None and frappe is not None:
        payload = frappe.form_dict.get("payload")
    if payload is None:
        return {}
    if isinstance(payload, str):
        return json.loads(payload) if payload.strip() else {}
    return dict(payload)


def _fallback_pack_preview(payload: dict[str, Any]) -> dict[str, Any]:
    provider = str(payload.get("provider", "both")).lower()
    providers = ("codex", "claude") if provider not in {"codex", "claude"} else (provider,)
    order = {
        "codex": [
            "ai-performance-orchestrator",
            "codex-task-compiler",
            "frappe-engineering-master",
            "frappe-testing-quality-engine",
            "project-memory-maintainer",
        ],
        "claude": [
            "ai-performance-orchestrator",
            "project-memory-maintainer",
            "frappe-engineering-master",
            "codex-task-compiler",
            "frappe-testing-quality-engine",
        ],
    }
    packs = {}
    for name in providers:
        packs[name] = {
            "provider": name,
            "ready_for_preview": True,
            "ready_for_activation": False,
            "skills": [
                {
                    "name": skill,
                    "status": "draft",
                    "activation_allowed": False,
                    "ready_for_preview": True,
                    "ready_for_activation": False,
                    "provider_targets": [name],
                    "purpose": "Canonical AI Engineering OS preview skill.",
                    "warnings": [],
                }
                for skill in order[name]
            ],
        }
    return {"ok": True, "mode": "preview", "activation_allowed": False, "packs": packs}


def _fallback_internal_skill_activation_status() -> dict[str, Any]:
    active = {"codex-task-compiler", "project-memory-maintainer"}
    skills = [
        "ai-performance-orchestrator",
        "codex-task-compiler",
        "frappe-engineering-master",
        "frappe-testing-quality-engine",
        "project-memory-maintainer",
    ]
    return {
        "ok": True,
        "activation_scope": "internal_aios_only",
        "global_export_allowed": False,
        "codex_global_export": False,
        "claude_global_export": False,
        "buildfast_auto_use": False,
        "packages": [
            {
                "skill_name": skill,
                "internal_active": skill in active,
                "activation_scope": "internal_aios_only" if skill in active else "preview",
                "global_export_allowed": False,
                "buildfast_auto_use": False,
            }
            for skill in skills
        ],
    }


def _fallback_plan(payload: dict[str, Any]) -> dict[str, Any]:
    request_text = str(payload.get("request_text") or payload.get("request") or "")
    lowered = request_text.lower()
    risk_level = "high" if any(term in lowered for term in ("production", "deploy", "restart", "migrate", "migration", "patch", "ssh", "secure", "portal users", "guest", "public", "allow_guest")) else "low"
    blocked = ["ssh", "deploy", "migrate", "restart"] if risk_level == "low" else ["write", "ssh", "deploy", "migrate", "restart"]
    primary, supporting = _fallback_selected_skills(request_text)
    selected = tuple(item for item in (primary, *supporting) if item)
    profiles = _fallback_compiled_profiles(selected)
    domain, task_type = _fallback_classification(request_text)
    task_prompt_preview = _fallback_task_prompt(request_text, risk_level, blocked)
    actionable_preview = _fallback_actionable_preview(request_text)
    return {
        "ok": True,
        "mode": "preview",
        "provider": "codex",
        "review_provider": "claude" if risk_level == "high" else "codex",
        "skills": {
            "primary": primary,
            "supporting": list(supporting),
            "selection_reasons": _fallback_selection_reasons(selected),
            "compiled_skill_profiles": profiles,
        },
        "output_contract": _fallback_output_contract(profiles),
        "tools": ["local_repo", "frappe_metadata"],
        "task_prompt_preview": task_prompt_preview,
        "actionable_preview": actionable_preview,
        "risk": {"level": risk_level, "blocked_actions": blocked, "warnings": []},
        "autonomy_mode": "approval_required" if risk_level == "high" else "high_autonomy_local",
        "acceptance_criteria": ["Preview response only", "No skill activation", "No global export"],
        "done_when": ["Preview response only", "No skill activation", "No global export"],
        "validation_steps": ["Review provider, skills, risk, and blocked actions"],
        "validation": ["Review provider, skills, risk, and blocked actions"],
        "domain": domain,
        "task_type": task_type,
        "memory_target_suggestion": list(_fallback_memory_targets(request_text)) if "project-memory-maintainer" in selected else [],
        "activation_allowed": False,
    }


def _fallback_export(payload: dict[str, Any], provider: str) -> dict[str, Any]:
    plan = _fallback_plan(payload)
    selected = [plan["skills"]["primary"], *plan["skills"]["supporting"]]
    selected = [skill for skill in selected if skill]
    return {
        "ok": True,
        "provider": provider,
        "mode": "preview",
        "task_id": f"preview-{provider}",
        "selected_skills": selected,
        "selection_reasons": plan["skills"]["selection_reasons"],
        "compiled_skill_profiles": plan["skills"]["compiled_skill_profiles"],
        "output_contract": plan["output_contract"],
        "task_prompt_preview": plan["task_prompt_preview"],
        "risk_level": plan["risk"]["level"],
        "blocked_actions": plan["risk"]["blocked_actions"],
        "done_when": plan["done_when"],
        "validation": plan["validation"],
        "files_preview": ["task_prompt.md", "skill_bundle.json", "risk_policy.json"],
        "writes_files": False,
        "activation_allowed": False,
    }


def _fallback_selected_skills(request_text: str) -> tuple[str, tuple[str, ...]]:
    lowered = request_text.lower()
    if any(term in lowered for term in ("project memory", "memory update", "development log", "decision log", "codex report into")):
        return "project-memory-maintainer", ()
    if any(term in lowered for term in ("codex task", "execution prompt", "doctype", "api", "endpoint", "patch", "migration")):
        return "codex-task-compiler", ()
    return "", ()


def _fallback_compiled_profiles(selected: tuple[str, ...]) -> dict[str, dict[str, Any]]:
    profiles = {
        "codex-task-compiler": {
            "skill_name": "codex-task-compiler",
            "purpose": "Convert a plan, decision, or request into a precise Codex implementation task.",
            "use_when": "Use for Codex-ready tasks, implementation briefs, acceptance criteria, or execution prompts.",
            "do_not_use_when": "Do not use when the request is already executable or analysis-only.",
            "output_contract": ["Goal", "Scope", "Files/paths", "Constraints", "Risk level", "Autonomy mode", "Suggested skills", "Validation", "Done when", "Final report format"],
            "key_rules": ["Preserve approval gates for destructive commands, migrations, restarts, remote writes, and secrets."],
            "final_report_expectation": "Return a Codex-ready task with Goal, Scope, Files/paths, Constraints, Risk, Validation, Done when, and Final report format.",
        },
        "project-memory-maintainer": {
            "skill_name": "project-memory-maintainer",
            "purpose": "Keep durable project memory accurate, bounded, and useful after decisions or execution reports.",
            "use_when": "Use after meaningful changes, validation runs, risk discoveries, milestone reports, or handoff.",
            "do_not_use_when": "Do not use for temporary notes, unverified claims, secrets, or unrelated project context.",
            "output_contract": ["Memory files updated", "Durable decisions", "Validation references", "Risks", "Next recommended action", "Summary", "Decisions", "Files changed", "Next action", "Memory target suggestion", "Concise update format"],
            "key_rules": ["Do not store credentials or customer data. Keep memory concise and project-scoped."],
            "final_report_expectation": "Return a concise memory update with summary, decisions, files changed, risks, next action, and suggested memory target.",
        },
    }
    return {skill: profiles[skill] for skill in selected if skill in profiles}


def _fallback_selection_reasons(selected: tuple[str, ...]) -> dict[str, str]:
    reasons = {
        "codex-task-compiler": "Selected for Codex task generation or execution prompt packaging.",
        "project-memory-maintainer": "Selected for durable memory update, report summarization, or next-step capture.",
    }
    return {skill: reasons[skill] for skill in selected if skill in reasons}


def _fallback_output_contract(profiles: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "skill_contracts": {
            name: {
                "output_contract": profile.get("output_contract", []),
                "final_report_expectation": profile.get("final_report_expectation", ""),
            }
            for name, profile in profiles.items()
        }
    }


def _fallback_memory_targets(request_text: str) -> tuple[str, ...]:
    lowered = request_text.lower()
    targets = []
    if "decision" in lowered:
        targets.append("DECISIONS")
    if "next" in lowered:
        targets.append("NEXT_STEPS")
    if any(term in lowered for term in ("done", "files changed", "risks", "codex report")):
        targets.append("DEVELOPMENT_LOG")
    return tuple(dict.fromkeys(targets or ["PROJECT_STATUS"]))


def _fallback_task_prompt(request_text: str, risk_level: str, blocked: list[str]) -> str:
    sections = [
        "## Goal",
        request_text or "Create a safe AI Engineering OS plan preview.",
        "## Risk level",
        risk_level,
        "## Constraints",
        "\n".join(f"- {item}" for item in blocked),
    ]
    for item in _fallback_actionable_preview(request_text)["checklists"]:
        sections.extend([f"## {item['title']}", "\n".join(f"- {line}" for line in item["items"])])
    return "\n\n".join(sections)


def _fallback_actionable_preview(request_text: str) -> dict[str, Any]:
    lowered = request_text.lower()
    checklists = []
    if "doctype" in lowered:
        checklists.append(
            {
                "title": "Frappe DocType checklist",
                "items": [
                    f"DocType name: {_fallback_doctype_name(request_text)}",
                    "Permissions, controller validation, tests, and validation commands are explicit.",
                ],
            }
        )
    if "api" in lowered or "endpoint" in lowered or "whitelisted" in lowered:
        checklists.append(
            {
                "title": "Frappe API security checklist",
                "items": [
                    "allow_guest=False by default.",
                    "Auth, permissions, Object-level access, input validation, and Portal negative tests are explicit.",
                ],
            }
        )
    if "patch" in lowered or "migrate" in lowered or "migration" in lowered:
        checklists.append(
            {
                "title": "Migration safety gate",
                "items": [
                    "Backup gate and Rollback gate are explicit before any mutation.",
                    "bench migrate, restart, deploy, and database writes remain blocked until approved.",
                ],
            }
        )
    if "buildfast" in lowered:
        checklists.append(
            {
                "title": "BuildFast to AIOS contract preview",
                "items": [
                    "AIOS is the control plane; BuildFast is the runtime consumer.",
                    "Request and response include provider, skills, tools, task prompt, validation, and risk notes.",
                    "Do not move the AIOS Skill Registry into BuildFast.",
                    "Do not modify BuildFast source unless explicitly scoped.",
                ],
            }
        )
    return {"checklists": checklists, "contract": {}, "summary": "Fallback preview only."}


def _fallback_classification(request_text: str) -> tuple[str | None, str | None]:
    lowered = request_text.lower()
    if any(term in lowered for term in ("project memory", "memory update", "development log", "decision log", "codex report into")):
        return "memory", "memory_update"
    if "buildfast" in lowered:
        return "buildfast", "planning_review"
    if "patch" in lowered or "migration" in lowered or "migrate" in lowered:
        return "frappe", "patch_migration"
    if "doctype" in lowered:
        return "frappe", "doctype"
    if any(term in lowered for term in ("api", "endpoint", "whitelisted")):
        return "frappe", "api_security" if any(term in lowered for term in ("secure", "portal", "guest", "public", "allow_guest")) else "api"
    return None, None


def _fallback_doctype_name(request_text: str) -> str:
    lowered = request_text.lower()
    marker = "doctype called "
    if marker in lowered:
        start = lowered.index(marker) + len(marker)
        fragment = request_text[start:]
        for stop in (" with ", ".", ","):
            if stop in fragment.lower():
                fragment = fragment[: fragment.lower().index(stop)]
                break
        value = " ".join(fragment.split())
        if value:
            return value
    return "TBD"
