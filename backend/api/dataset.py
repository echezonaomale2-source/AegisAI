"""Dataset annotation API — never invents labels."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from dataset.toolkit import compare_to_ai, import_images, validate_dataset

router = APIRouter(tags=["dataset"])


class ImportRequest(BaseModel):
    source: str = Field(description="Folder or file path of chart screenshots")
    version: str = Field(description="Dataset version id, e.g. v1")


@router.post("/dataset/import")
async def dataset_import(body: ImportRequest) -> dict:
    source = Path(body.source)
    if not source.exists():
        raise HTTPException(status_code=404, detail=f"Source not found: {body.source}")
    return import_images(source, version=body.version)


@router.get("/dataset/{version}/validate")
async def dataset_validate(version: str) -> dict:
    return validate_dataset(version)


@router.post("/dataset/{version}/compare")
async def dataset_compare(version: str) -> dict:
    """Compare AI detections against human-labeled annotations only."""
    try:
        return compare_to_ai(version)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
