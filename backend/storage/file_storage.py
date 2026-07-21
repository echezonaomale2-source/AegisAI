from __future__ import annotations

import uuid
from pathlib import Path

import aiofiles
from fastapi import UploadFile, HTTPException

from config.settings import settings


ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def _extension_for(filename: str | None, content_type: str | None) -> str:
    if filename:
        suffix = Path(filename).suffix.lower()
        if suffix in ALLOWED_EXTENSIONS:
            return suffix

    if content_type in {"image/png"}:
        return ".png"
    if content_type in {"image/jpeg", "image/jpg"}:
        return ".jpg"

    raise HTTPException(status_code=400, detail="Only PNG, JPG, and JPEG images are accepted.")


async def save_upload(file: UploadFile, label: str) -> Path:
    content_type = (file.content_type or "").lower()
    if content_type and content_type not in settings.allowed_content_types:
        raise HTTPException(status_code=400, detail="Only PNG, JPG, and JPEG images are accepted.")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail=f"{label} image is empty.")
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=400, detail=f"{label} image exceeds size limit.")

    extension = _extension_for(file.filename, content_type)
    destination = settings.upload_dir / f"{uuid.uuid4().hex}_{label}{extension}"

    async with aiofiles.open(destination, "wb") as output:
        await output.write(data)

    return destination
