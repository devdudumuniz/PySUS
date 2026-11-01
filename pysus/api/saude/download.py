"""Async download helpers for Saude (CKAN) resources.

Mirrors ``epidatasets.sources.opendatasus.OpenDataSUSAccessor
.download_resource`` / ``.download_dataset`` but uses ``httpx.AsyncClient
.stream`` and a progress callback shaped like the rest of PySUS.

Resources whose ``format`` is ``API`` are documentation links and are
skipped automatically.
"""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse

from .errors import ResourceNotFound
from .resources import CKANPackage, Resource

_DOWNLOAD_CHUNK = 1 << 16
_NON_SAFE = re.compile(r"[^\w.\- ]")


def _digest_spec(value: str) -> tuple[str, str] | None:
    """Recognise CKAN hashes whose algorithm is unambiguous."""
    raw = value.strip().lower()
    if ":" in raw:
        algorithm, raw = raw.split(":", 1)
        if algorithm not in {"md5", "sha256"}:
            return None
    else:
        algorithm = {32: "md5", 64: "sha256"}.get(len(raw), "")
    if len(raw) != {"md5": 32, "sha256": 64}.get(algorithm):
        return None
    if not re.fullmatch(r"[0-9a-f]+", raw):
        return None
    return algorithm, raw


def _matches_metadata(path: Path, resource: Resource) -> bool:
    """Check only the size and digest that the catalog can identify."""
    if resource.size is not None and resource.size > 0:
        if path.stat().st_size != resource.size:
            return False
    digest = _digest_spec(resource.hash)
    return digest is None or _matches_digest(path, digest)


def _matches_digest(path: Path, digest: tuple[str, str]) -> bool:
    algorithm, expected = digest
    actual = hashlib.new(algorithm)
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(_DOWNLOAD_CHUNK), b""):
            actual.update(chunk)
    return actual.hexdigest() == expected


def filename_for(resource: Resource, slug: str, index: int) -> str:
    """Derive a safe filename for a resource download.

    Ported verbatim from the epidatasets reference implementation.
    """
    base = (
        resource.name
        or Path(urlparse(resource.url).path).name
        or f"resource_{index}"
    )
    base = _NON_SAFE.sub("_", base).strip() or f"resource_{index}"
    fmt = (resource.format or "").strip().lower()
    if fmt and fmt != "api" and not base.lower().endswith(f".{fmt}"):
        base = f"{base}.{fmt}"
    return base


def _select_resource(
    package: CKANPackage,
    *,
    resource_id: str | None,
    name: str | None,
    fmt: str | None,
) -> Resource:
    """Pick the unique resource matching the selector, else raise."""
    if (resource_id is None) == (name is None):
        raise ValueError("Provide exactly one of 'resource_id' or 'name'.")
    matches = []
    for resource in package.resources:
        if resource_id is not None and resource.id != resource_id:
            continue
        if name is not None and resource.name != name:
            continue
        if fmt is not None and resource.format.upper() != fmt.upper():
            continue
        if resource.format.upper() == "API":
            continue
        matches.append(resource)
    if not matches:
        raise ResourceNotFound(
            f"No downloadable resource matches resource_id={resource_id!r}, "
            f"name={name!r}, fmt={fmt!r} for dataset '{package.name}'.",
            candidates=len(package.resources),
        )
    return matches[0]


async def download_resource(
    client,  # httpx.AsyncClient
    package: CKANPackage,
    *,
    resource_id: str | None = None,
    name: str | None = None,
    fmt: str | None = None,
    dest_dir: Path | None = None,
    progress: Callable[[int, int], None] | None = None,
    overwrite: bool = False,
) -> Path:
    """Download a single resource of a dataset to disk.

    Parameters
    ----------
    client : httpx.AsyncClient
    package : CKANPackage
    resource_id, name, fmt : optional selectors (exactly one of id/name)
    dest_dir : pathlib.Path, optional
        Defaults to ``<cache_dir>/downloads/<slug>/``.
    progress : callable, optional
        ``(downloaded_bytes, total_bytes)`` callback.
    overwrite : bool, optional
        When ``False`` (default), an existing file is reused.

    Returns
    -------
    pathlib.Path
        Path to the downloaded file.
    """
    resource = _select_resource(
        package, resource_id=resource_id, name=name, fmt=fmt
    )
    target_dir = (
        Path(dest_dir) if dest_dir else Path(f"./{package.name}-downloads")
    )
    target_dir.mkdir(parents=True, exist_ok=True)
    index = resource.position or 0
    dest_path = target_dir / filename_for(resource, package.name, index)

    if (
        dest_path.exists()
        and not overwrite
        and _matches_metadata(dest_path, resource)
    ):
        return dest_path

    # The temporary file is on the destination filesystem, and its exclusive
    # name lets concurrent downloads keep their in-progress bytes separate.
    with tempfile.NamedTemporaryFile(
        mode="wb",
        prefix=f".{dest_path.name}.",
        suffix=".part",
        dir=target_dir,
        delete=False,
    ) as fh:
        tmp_path = Path(fh.name)
    try:
        async with client.stream("GET", resource.url) as response:
            response.raise_for_status()
            total = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            with tmp_path.open("wb") as fh:
                async for chunk in response.aiter_bytes(
                    chunk_size=_DOWNLOAD_CHUNK
                ):
                    fh.write(chunk)
                    downloaded += len(chunk)
                    if progress:
                        progress(downloaded, total)
        # httpx may decode content before yielding it; compare byte counts
        # only when the response did not declare an encoding.
        identity = response.headers.get("Content-Encoding", "identity").lower()
        if total > 0 and identity == "identity" and downloaded != total:
            raise OSError("Downloaded resource has an incomplete response body")
        # CKAN's size may be stale. Prefer the current response length when
        # the two disagree; absent that signal, a known catalog size applies.
        if (
            identity == "identity"
            and resource.size is not None
            and resource.size > 0
        ):
            if (
                total <= 0 or total == resource.size
            ) and downloaded != resource.size:
                raise OSError("Downloaded resource does not match CKAN size")
        digest = _digest_spec(resource.hash)
        if digest is not None and not _matches_digest(tmp_path, digest):
            raise OSError("Downloaded resource does not match CKAN hash")
        if (
            dest_path.exists()
            and not overwrite
            and _matches_metadata(dest_path, resource)
        ):
            return dest_path
        # Close the writer before replacement so this also works on Windows.
        os.replace(tmp_path, dest_path)
    finally:
        tmp_path.unlink(missing_ok=True)
    return dest_path


async def download_dataset(
    client,  # httpx.AsyncClient
    package: CKANPackage,
    *,
    dest_dir: Path | None = None,
    fmt: str | None = None,
    progress: Callable[[int, int], None] | None = None,
    overwrite: bool = False,
) -> list[Path]:
    """Download every downloadable resource of a dataset.

    Returns the list of paths written. API-format resources are
    skipped.
    """
    dest = Path(dest_dir) if dest_dir else Path(f"./{package.name}-downloads")
    dest.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    fmt_upper = fmt.upper() if fmt else None
    for resource in package.resources:
        if resource.format.upper() == "API":
            continue
        if fmt_upper and resource.format.upper() != fmt_upper:
            continue
        path = await download_resource(
            client,
            package,
            resource_id=resource.id,
            dest_dir=dest,
            progress=progress,
            overwrite=overwrite,
        )
        paths.append(path)
    return paths


__all__ = [
    "filename_for",
    "download_resource",
    "download_dataset",
]
