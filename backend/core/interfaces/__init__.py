"""Service interfaces (Protocols) — implementations are swappable without rewriting callers."""

from core.interfaces.chart import ChartExtractorProtocol
from core.interfaces.confidence import ConfidenceEngineProtocol
from core.interfaces.decision import DecisionEngineProtocol
from core.interfaces.features import FeatureExtractorProtocol
from core.interfaces.image import ImageValidatorProtocol
from core.interfaces.learning import LearningEngineProtocol
from core.interfaces.memory import MemoryEngineProtocol
from core.interfaces.reconstruction import ChartReconstructorProtocol
from core.interfaces.similarity import SimilarityEngineProtocol
from core.interfaces.smc import SmartMoneyEngineProtocol

__all__ = [
    "ChartExtractorProtocol",
    "ChartReconstructorProtocol",
    "ConfidenceEngineProtocol",
    "DecisionEngineProtocol",
    "FeatureExtractorProtocol",
    "ImageValidatorProtocol",
    "LearningEngineProtocol",
    "MemoryEngineProtocol",
    "SimilarityEngineProtocol",
    "SmartMoneyEngineProtocol",
]
