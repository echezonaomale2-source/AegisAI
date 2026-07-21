"""
AegisAI Trading Knowledge Base (Phase 8).

Authoritative, versioned Smart Money Concepts rules — separate from AI logic.
"""

__all__ = ["KnowledgeEngine", "CURRENT_VERSION", "list_versions"]


def __getattr__(name: str):
    if name == "KnowledgeEngine":
        from knowledge.engine import KnowledgeEngine

        return KnowledgeEngine
    if name in {"CURRENT_VERSION", "list_versions"}:
        from knowledge import versioning

        return getattr(versioning, name)
    raise AttributeError(name)
