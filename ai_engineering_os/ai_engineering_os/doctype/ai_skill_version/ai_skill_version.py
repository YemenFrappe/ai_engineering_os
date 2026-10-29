"""Controller stub for repo-local AI Skill Version template.

This file is not installed into a Frappe site in P4B.
"""

from __future__ import annotations

try:
    from frappe.model.document import Document
except Exception:  # pragma: no cover - exercised when Frappe is unavailable
    class Document:
        """Fallback base so template stubs import without Frappe."""


class AISkillVersion(Document):
    """Placeholder controller for future Frappe installation."""

    pass
