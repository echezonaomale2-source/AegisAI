"""
AegisAI Cognitive AI Architecture (Phase 6).

Independent reasoning engines that think like a professional trader.
Import engines from cognitive.pipeline / cognitive.container as needed.
"""

__all__ = ["CognitivePipeline", "CognitiveContainer", "get_cognitive_container"]


def __getattr__(name: str):
    if name == "CognitivePipeline":
        from cognitive.pipeline import CognitivePipeline

        return CognitivePipeline
    if name == "CognitiveContainer":
        from cognitive.container import CognitiveContainer

        return CognitiveContainer
    if name == "get_cognitive_container":
        from cognitive.container import get_cognitive_container

        return get_cognitive_container
    raise AttributeError(name)
