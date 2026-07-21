"""Knowledge version registry — never deletes prior versions."""

from __future__ import annotations

CURRENT_VERSION = "1.0"

# Immutable map of version → loader module path attribute name in catalog package.
VERSION_LOADERS: dict[str, str] = {
    "1.0": "v1_0",
}


def list_versions() -> list[str]:
    return sorted(VERSION_LOADERS.keys(), key=lambda v: tuple(int(x) for x in v.split(".")))
