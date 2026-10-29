"""Benchmark API facade for future Frappe installation."""

from __future__ import annotations

from ai_engineering_os.api._core import optional_import, unavailable_response


def list_benchmark_scenarios(payload=None):
    module = optional_import("ai_engineering_os.frappe_app.api.benchmarks")
    if module is None:
        return unavailable_response("list_benchmark_scenarios")
    return module.list_benchmark_scenarios(payload or {})


def run_benchmark_suite(payload=None):
    module = optional_import("ai_engineering_os.frappe_app.api.benchmarks")
    if module is None:
        return unavailable_response("run_benchmark_suite")
    return module.run_benchmark_suite(payload or {})
