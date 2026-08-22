"""Terminal agent package."""

from __future__ import annotations

from importlib import metadata


def version() -> str:
    try:
        return metadata.version("mate")
    except metadata.PackageNotFoundError:
        return "0+unknown"
