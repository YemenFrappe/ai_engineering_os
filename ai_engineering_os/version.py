"""Safe AI Engineering OS version marker for server sync checks."""

from __future__ import annotations

__version__ = "0.0.0"
AIOS_LOCAL_VERSION = __version__
AIOS_BUILD_PHASE = "P12H internal skill routing observation"
AIOS_LAST_KNOWN_COMMIT = "09b893b"
AIOS_SYNC_POLICY = "controlled-copy-dev"
AIOS_INSTALL_CONTEXT = "lovable.yemenfrappe.com dev/UAT"
AIOS_TARGET_SITE = "lovable.yemenfrappe.com"
AIOS_SKILL_PREVIEW_SYNC = True
AIOS_INTERNAL_ROUTING_OBSERVED = True
AIOS_INTERNAL_ROUTING_ISSUES = 0
AIOS_BENCHMARK_GREEN = True


def get_version_info() -> dict[str, str | bool]:
    return {
        "version": AIOS_LOCAL_VERSION,
        "build_phase": AIOS_BUILD_PHASE,
        "commit": AIOS_LAST_KNOWN_COMMIT,
        "sync_policy": AIOS_SYNC_POLICY,
        "install_context": AIOS_INSTALL_CONTEXT,
        "target_site": AIOS_TARGET_SITE,
        "skill_preview_sync": AIOS_SKILL_PREVIEW_SYNC,
        "internal_routing_observed": AIOS_INTERNAL_ROUTING_OBSERVED,
        "internal_routing_issues": AIOS_INTERNAL_ROUTING_ISSUES,
        "benchmark_green": AIOS_BENCHMARK_GREEN,
    }
