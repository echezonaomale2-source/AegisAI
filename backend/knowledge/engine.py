"""Knowledge Engine — public API for definitions, validation, relationships."""

from __future__ import annotations

from typing import Any

from cognitive.models.features import FeatureCollection
from cognitive.models.market import MarketModel
from knowledge.models import ConceptDefinition, KnowledgeMeta, Relationship, ValidationResult
from knowledge.registry import KnowledgeRegistry, get_registry
from knowledge.validator import KnowledgeValidator, build_context
from knowledge.versioning import CURRENT_VERSION, list_versions


class KnowledgeEngine:
    """
    Authoritative Smart Money Concepts reference.

    Vision detects candidates → Knowledge validates → Evidence consumes validated only.
    """

    def __init__(self, version: str | None = None) -> None:
        self.version = version or CURRENT_VERSION
        self.registry: KnowledgeRegistry = get_registry(self.version)
        self.validator = KnowledgeValidator(self.registry)

    def get_concept(self, concept_id: str) -> ConceptDefinition | None:
        return self.registry.get_concept(concept_id)

    def list_concepts(self) -> list[ConceptDefinition]:
        return self.registry.list_concepts()

    def get_relationships(self, concept_id: str | None = None) -> list[Relationship]:
        if concept_id:
            return self.registry.relationships_for(concept_id)
        return self.registry.list_relationships()

    def get_meta(self) -> KnowledgeMeta:
        meta = self.registry.meta()
        return KnowledgeMeta(
            version=meta["version"],
            concept_count=meta["concept_count"],
            relationship_count=meta["relationship_count"],
            description=meta["description"],
        )

    def available_versions(self) -> list[str]:
        return list_versions()

    def validate_concept(
        self,
        concept_id: str,
        context: dict[str, Any],
    ) -> ValidationResult:
        concept = self.registry.get_concept(concept_id)
        if concept is None:
            return ValidationResult(
                concept_id=concept_id,
                concept_name="Unknown",
                status="unknown",
                knowledge_version=self.version,
                notes=["Concept not found in this knowledge version."],
            )
        return self.validator.validate_concept(concept, context)

    def validate_features(
        self,
        features: FeatureCollection,
        market: MarketModel | None = None,
    ) -> FeatureCollection:
        return self.validator.validate_feature_collection(features, market)

    def build_context_from_market(self, market: MarketModel) -> dict[str, Any]:
        return build_context(market)

    def rule_metadata(self) -> dict[str, Any]:
        return {
            "knowledge_version": self.version,
            "available_versions": self.available_versions(),
            "concepts": [
                {
                    "id": c.id,
                    "name": c.name,
                    "version": c.version,
                    "validation_rules": c.validation_rules,
                    "feature_types": c.feature_types,
                    "required_count": len(c.required_conditions),
                    "invalid_count": len(c.invalid_conditions),
                }
                for c in self.list_concepts()
            ],
            "relationships": [r.model_dump() for r in self.get_relationships()],
        }
