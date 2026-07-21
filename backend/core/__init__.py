"""
AegisAI Core AI Architecture (Phase 5.5).

Separates image understanding from market reasoning.

Pipeline:
  Screenshots → Image Validation → Chart Extraction → Chart Reconstruction
  → Feature Extraction → Smart Money Engine → Decision Engine
  → Confidence Engine → Trade Recommendation → Trade Memory → Learning Engine

Downstream modules consume ChartModel only — never raw images.
"""

from core.container import ServiceContainer, get_container
from core.pipeline import CorePipeline

__all__ = ["CorePipeline", "ServiceContainer", "get_container"]
