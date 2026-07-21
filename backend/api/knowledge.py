"""Knowledge Engine API — definitions, validation, relationships, metadata."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from cognitive.models.features import FeatureCollection
from cognitive.models.market import MarketModel
from knowledge.engine import KnowledgeEngine
from knowledge.versioning import CURRENT_VERSION, list_versions

router = APIRouter(tags=["knowledge"])
_default_engine = KnowledgeEngine()


def _resolve_engine(version: str | None = None) -> KnowledgeEngine:
    """Return a KnowledgeEngine for *version*, or 404 if unknown."""
    if version is None or version == CURRENT_VERSION:
        return _default_engine if version is None else KnowledgeEngine(version)
    if version not in list_versions():
        raise HTTPException(
            status_code=404,
            detail=f"Unknown knowledge version: {version}. Available: {list_versions()}",
        )
    try:
        return KnowledgeEngine(version)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


class ValidateRequest(BaseModel):
    concept_id: str
    context: dict[str, Any] = Field(default_factory=dict)
    version: str | None = None


class ValidateFeaturesRequest(BaseModel):
    features: FeatureCollection
    market: MarketModel | None = None
    version: str | None = None


@router.get("/knowledge/version")
async def knowledge_version() -> dict:
    return {
        "current": CURRENT_VERSION,
        "available": list_versions(),
    }


@router.get("/knowledge/meta")
async def knowledge_meta(version: str | None = None) -> dict:
    eng = _resolve_engine(version)
    return eng.rule_metadata()


@router.get("/knowledge/concepts")
async def list_concepts(version: str | None = None) -> dict:
    eng = _resolve_engine(version)
    return {
        "knowledge_version": eng.version,
        "concepts": [c.model_dump(mode="json") for c in eng.list_concepts()],
    }


@router.get("/knowledge/concepts/{concept_id}")
async def get_concept(concept_id: str, version: str | None = None) -> dict:
    eng = _resolve_engine(version)
    concept = eng.get_concept(concept_id)
    if concept is None:
        raise HTTPException(status_code=404, detail=f"Concept '{concept_id}' not found")
    return {
        "knowledge_version": eng.version,
        "concept": concept.model_dump(mode="json"),
        "relationships": [r.model_dump(mode="json") for r in eng.get_relationships(concept_id)],
    }


@router.get("/knowledge/relationships")
async def list_relationships(concept_id: str | None = None, version: str | None = None) -> dict:
    eng = _resolve_engine(version)
    rels = eng.get_relationships(concept_id)
    return {
        "knowledge_version": eng.version,
        "relationships": [r.model_dump(mode="json") for r in rels],
    }


@router.post("/knowledge/validate")
async def validate_concept(body: ValidateRequest) -> dict:
    eng = _resolve_engine(body.version)
    result = eng.validate_concept(body.concept_id, body.context)
    return result.model_dump(mode="json")


@router.post("/knowledge/validate/features")
async def validate_features(body: ValidateFeaturesRequest) -> dict:
    """Validate a FeatureCollection against the catalog (SSOT gate before Evidence)."""
    eng = _resolve_engine(body.version)
    validated = eng.validate_features(body.features, body.market)
    return {
        "knowledge_version": eng.version,
        "features": validated.model_dump(mode="json"),
    }
