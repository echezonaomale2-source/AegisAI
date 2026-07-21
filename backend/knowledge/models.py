"""Knowledge data models — editable, versioned SMC concepts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


ConditionOp = Literal["eq", "neq", "gte", "lte", "gt", "lt", "in", "truthy", "falsy", "exists"]


class Condition(BaseModel):
    """Declarative validation condition evaluated against a context dict."""

    field: str
    op: ConditionOp
    value: Any = None
    description: str = ""


class ConceptExample(BaseModel):
    title: str
    valid: bool
    context: dict[str, Any] = Field(default_factory=dict)
    notes: str = ""


class ConfidenceGuidelines(BaseModel):
    min_detect: float = Field(ge=0, le=100, default=50.0)
    high_confidence: float = Field(ge=0, le=100, default=80.0)
    notes: str = ""


class Relationship(BaseModel):
    source: str
    target: str
    relation: str
    description: str
    strengthens_trade: bool = False
    notes: str = "Does not guarantee a trade."


class ConceptDefinition(BaseModel):
    id: str
    name: str
    definition: str
    validation_rules: list[str] = Field(default_factory=list)
    required_conditions: list[Condition] = Field(default_factory=list)
    invalid_conditions: list[Condition] = Field(default_factory=list)
    relationships: list[str] = Field(
        default_factory=list,
        description="Relationship ids referencing the relationship registry",
    )
    examples: list[ConceptExample] = Field(default_factory=list)
    confidence_guidelines: ConfidenceGuidelines = Field(default_factory=ConfidenceGuidelines)
    version: str
    feature_types: list[str] = Field(
        default_factory=list,
        description="Cognitive feature_type values this concept validates",
    )
    tags: list[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    concept_id: str
    concept_name: str
    status: Literal["valid", "invalid", "unknown"]
    confidence: float = Field(ge=0, le=100, default=0.0)
    knowledge_version: str
    failed_required: list[str] = Field(default_factory=list)
    triggered_invalid: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class KnowledgeMeta(BaseModel):
    version: str
    concept_count: int
    relationship_count: int
    description: str = ""
