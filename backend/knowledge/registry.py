"""Load and cache versioned knowledge catalogs."""

from __future__ import annotations

from functools import lru_cache

from knowledge.catalog import v1_0
from knowledge.models import ConceptDefinition, Relationship
from knowledge.versioning import CURRENT_VERSION, VERSION_LOADERS, list_versions


_LOADERS = {
    "v1_0": v1_0,
}


class KnowledgeRegistry:
    def __init__(self, version: str | None = None) -> None:
        self.version = version or CURRENT_VERSION
        if self.version not in VERSION_LOADERS:
            raise ValueError(f"Unknown knowledge version: {self.version}")
        loader_name = VERSION_LOADERS[self.version]
        mod = _LOADERS[loader_name]
        self._concepts = {c.id: c for c in mod.build_concepts()}
        self._relationships = mod.build_relationships()
        self._by_feature: dict[str, list[ConceptDefinition]] = {}
        for concept in self._concepts.values():
            for ft in concept.feature_types:
                self._by_feature.setdefault(ft, []).append(concept)

    def get_concept(self, concept_id: str) -> ConceptDefinition | None:
        return self._concepts.get(concept_id)

    def list_concepts(self) -> list[ConceptDefinition]:
        return list(self._concepts.values())

    def concepts_for_feature(self, feature_type: str) -> list[ConceptDefinition]:
        return list(self._by_feature.get(feature_type, []))

    def list_relationships(self) -> list[Relationship]:
        return list(self._relationships)

    def relationships_for(self, concept_id: str) -> list[Relationship]:
        return [
            r
            for r in self._relationships
            if r.source == concept_id or r.target == concept_id
        ]

    def meta(self) -> dict:
        return {
            "version": self.version,
            "concept_count": len(self._concepts),
            "relationship_count": len(self._relationships),
            "available_versions": list_versions(),
            "description": "AegisAI Smart Money Concepts knowledge base",
        }


@lru_cache(maxsize=8)
def get_registry(version: str | None = None) -> KnowledgeRegistry:
    return KnowledgeRegistry(version)
