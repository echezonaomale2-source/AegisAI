"""
AegisAI Brain (Phase 10).

Central decision coordinator. Never analyzes raw images or detects structures.
Receives validated engine outputs and produces the final recommendation.
"""

__all__ = ["AIBrain"]


def __getattr__(name: str):
    if name == "AIBrain":
        from brain.coordinator import AIBrain

        return AIBrain
    raise AttributeError(name)
