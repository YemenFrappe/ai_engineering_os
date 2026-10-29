"""Helpers for optional Python core imports in the Frappe layout."""

from __future__ import annotations

from importlib import import_module


def optional_import(module_name: str):
    try:
        return import_module(module_name)
    except Exception:
        return None


def unavailable_response(feature: str) -> dict:
    return {
        "ok": False,
        "feature": feature,
        "reason": "Python core package is not importable in this environment.",
    }
