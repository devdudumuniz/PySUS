"""Tests for the resource / dataset download helpers."""

from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime

import httpx
import pytest
from pysus.api.saude.download import (
    _select_resource,
    download_dataset,
    download_resource,
    filename_for,
)
from pysus.api.saude.errors import ResourceNotFound
from pysus.api.saude.resources import CKANPackage, Resource


class TestFilenameFor:
    def test_uses_resource_name(self):
        resource = Resource.model_validate(
            {
                "id": "abc",
                "name": "Dengue - 2024",
                "format": "CSV",
                "url": "https://example.com/x.csv",
            }
        )
        assert (
            filename_for(resource, "arboviroses-dengue", 0)
            == "Dengue - 2024.csv"
        )

    def test_appends_format_extension_when_missing(self):
        resource = Resource.model_validate(
            {
                "id": "abc",
                "name": "Dengue 2024",
                "format": "JSON",
                "url": "https://example.com/x",
            }
        )
        assert (
            filename_for(resource, "arboviroses-dengue", 0)
            == "Dengue 2024.json"
        )

    def test_skips_extension_when_format_is_api(self):
        resource = Resource.model_validate(
            {
                "id": "abc",
                "name": "API docs",
                "format": "API",
                "url": "https://example.com/docs",
            }
        )
        assert filename_for(resource, "x", 0) == "API docs"

    def test_strips_unsafe_characters(self):
        resource = Resource.model_validate(
            {
                "id": "abc",
                "name": "weird/name?with&chars",
                "format": "CSV",
                "url": "https://example.com/x",
            }
        )
        name = filename_for(resource, "x", 0)
        assert "/" not in name
        assert "?" not in name
        assert "&" not in name


class TestDownloadResource:
    @pytest.mark.asyncio
    async def test_downloads_single_resource(
        self, saude_dataset_page_props, tmp_path, mocked_saude
    ):
        from pysus.api.saude.resources import CKANPackage

        package = CKANPackage.model_validate(saude_dataset_page_props)
        target = next(r for r in package.resources if r.format == "CSV")

        async with httpx.AsyncClient(transport=mocked_saude) as client:
            path = await download_resource(
                client, package, resource_id=target.id, dest_dir=tmp_path
            )
        assert path.exists()
        assert path.stat().st_size > 0

    @pytest.mark.asyncio
    async def test_skips_api_resources(
        self, saude_dataset_page_props, tmp_path, mocked_saude
    ):
        from pysus.api.saude.resources import CKANPackage

        package = CKANPackage.model_validate(saude_dataset_page_props)
        api_resource = next(r for r in package.resources if r.format == "API")
        async with httpx.AsyncClient(transport=mocked_saude) as client:
            with pytest.raises(ResourceNotFound):
                await download_resource(
                    client,
                    package,
                    resource_id=api_resource.id,
                    dest_dir=tmp_path,
                )

    @pytest.mark.asyncio
    async def test_ambiguous_selector_raises(
        self, saude_dataset_page_props, tmp_path, mocked_saude
    ):
        from pysus.api.saude.resources import CKANPackage

        package = CKANPackage.model_validate(saude_dataset_page_props)
        async with httpx.AsyncClient(transport=mocked_saude) as client:
            with pytest.raises(ValueError, match="exactly one"):
                await download_resource(client, package, dest_dir=tmp_path)

    @pytest.mark.asyncio
    async def test_no_match_raises_not_found(
        self, saude_dataset_page_props, tmp_path, mocked_saude
    ):
        from pysus.api.saude.resources import CKANPackage

        package = CKANPackage.model_validate(saude_dataset_page_props)
        async with httpx.AsyncClient(transport=mocked_saude) as client:
            with pytest.raises(ResourceNotFound):
                await download_resource(
                    client,
                    package,
                    resource_id="nonexistent-id",
                    dest_dir=tmp_path,
                )


class TestDownloadDataset:
    @pytest.mark.asyncio
    async def test_downloads_only_csv_resources(
        self, saude_dataset_page_props, tmp_path, mocked_saude
    ):
        from pysus.api.saude.resources import CKANPackage

        package = CKANPackage.model_validate(saude_dataset_page_props)
        expected_csvs = sum(1 for r in package.resources if r.format == "CSV")
        assert expected_csvs > 0

        async with httpx.AsyncClient(transport=mocked_saude) as client:
            paths = await download_dataset(
                client,
                package,
                dest_dir=tmp_path,
                fmt="CSV",
            )
        assert len(paths) == expected_csvs
        for path in paths:
            assert path.exists()
            assert path.stat().st_size > 0


class TestSelectResource:
    def _make_package(self):
        resources = [
            Resource(
                id="csv-1",
                name="Dengue CSV",
                format="CSV",
                url="https://example.com/dengue.csv",
            ),
            Resource(
                id="api-1",
                name="Dengue API",
                format="API",
                url="https://example.com/docs",
            ),
            Resource(
                id="json-1",
                name="Dengue JSON",
                format="JSON",
                url="https://example.com/dengue.json",
            ),
        ]
        return CKANPackage(
            id="pkg-1",
            name="arboviroses-dengue",
            title="Arboviroses",
            resources=resources,
            num_resources=len(resources),
            metadata_created="2024-01-01T00:00:00",
            metadata_modified="2024-01-01T00:00:00",
        )

    def test_select_by_id(self):
        pkg = self._make_package()
        r = _select_resource(pkg, resource_id="json-1", name=None, fmt=None)
        assert r.id == "json-1"

    def test_select_by_name(self):
        pkg = self._make_package()
        r = _select_resource(pkg, resource_id=None, name="Dengue CSV", fmt=None)
        assert r.format == "CSV"

    def test_select_by_fmt(self):
        pkg = self._make_package()
        r = _select_resource(
            pkg, resource_id=None, name="Dengue JSON", fmt="JSON"
        )
        assert r.format == "JSON"

    def test_name_mismatch_raises(self):
        pkg = self._make_package()
        with pytest.raises(ResourceNotFound):
            _select_resource(
                pkg, resource_id=None, name="Nonexistent", fmt=None
            )

    def test_fmt_mismatch_raises(self):
        pkg = self._make_package()
        with pytest.raises(ResourceNotFound):
            _select_resource(
                pkg, resource_id=None, name="Dengue CSV", fmt="PDF"
            )

    def test_fmt_filters_out_non_matching(self):
        pkg = self._make_package()
        with pytest.raises(ResourceNotFound):
            _select_resource(
                pkg, resource_id=None, name="Dengue CSV", fmt="XML"
            )


class TestDownloadResourceEdgeCases:
    @pytest.mark.asyncio
    async def test_existing_file_not_overwritten(
        self, saude_dataset_page_props, tmp_path, mocked_saude
    ):
        from pysus.api.saude.resources import CKANPackage

        package = CKANPackage.model_validate(saude_dataset_page_props)
        csv_resource = next(r for r in package.resources if r.format == "CSV")
        async with httpx.AsyncClient(transport=mocked_saude) as client:
            path1 = await download_resource(
                client,
                package,
                resource_id=csv_resource.id,
                dest_dir=tmp_path,
            )
            path2 = await download_resource(
                client,
                package,
                resource_id=csv_resource.id,
                dest_dir=tmp_path,
            )
        assert path1 == path2

    @pytest.mark.asyncio
    async def test_progress_callback_called(
        self, saude_dataset_page_props, tmp_path, mocked_saude
    ):
        from pysus.api.saude.resources import CKANPackage

        package = CKANPackage.model_validate(saude_dataset_page_props)
        csv_resource = next(r for r in package.resources if r.format == "CSV")
        progress_calls = []

        def progress(downloaded: int, total: int):
            progress_calls.append((downloaded, total))

        async with httpx.AsyncClient(transport=mocked_saude) as client:
            await download_resource(
                client,
                package,
                resource_id=csv_resource.id,
                dest_dir=tmp_path,
                progress=progress,
            )
        assert len(progress_calls) > 0

    @pytest.mark.asyncio
    async def test_no_dest_dir_uses_slug_dir(
        self, saude_dataset_page_props, tmp_path, mocked_saude
    ):
        from pysus.api.saude.resources import CKANPackage

        package = CKANPackage.model_validate(saude_dataset_page_props)
        csv_resource = next(r for r in package.resources if r.format == "CSV")
        original_dir = tmp_path / "cwd"
        original_dir.mkdir()

        import os

        old_cwd = os.getcwd()
        try:
            os.chdir(original_dir)
            async with httpx.AsyncClient(transport=mocked_saude) as client:
                path = await download_resource(
                    client,
                    package,
                    resource_id=csv_resource.id,
                )
            assert path.exists()
        finally:
            os.chdir(old_cwd)

    @pytest.mark.asyncio
    async def test_select_by_name(
        self, saude_dataset_page_props, tmp_path, mocked_saude
    ):
        from pysus.api.saude.resources import CKANPackage

        package = CKANPackage.model_validate(saude_dataset_page_props)
        csv_resource = next(r for r in package.resources if r.format == "CSV")
        async with httpx.AsyncClient(transport=mocked_saude) as client:
            path = await download_resource(
                client,
                package,
                name=csv_resource.name,
                dest_dir=tmp_path,
            )
        assert path.exists()

    @pytest.mark.asyncio
    async def test_select_by_fmt(
        self, saude_dataset_page_props, tmp_path, mocked_saude
    ):
        from pysus.api.saude.resources import CKANPackage

        package = CKANPackage.model_validate(saude_dataset_page_props)
        csv_resource = next(r for r in package.resources if r.format == "CSV")
        async with httpx.AsyncClient(transport=mocked_saude) as client:
            path = await download_resource(
                client,
                package,
                name=csv_resource.name,
                fmt="CSV",
                dest_dir=tmp_path,
            )
        assert path.exists()


class _InterruptedStream(httpx.AsyncByteStream):
    async def __aiter__(self):
        yield b"x" * (1 << 16)
        raise httpx.ReadError("connection interrupted")

    async def aclose(self):
        pass


class _WaitingStream(httpx.AsyncByteStream):
    def __init__(self, ready: asyncio.Event):
        self.ready = ready

    async def __aiter__(self):
        yield b"x" * (1 << 16)
        self.ready.set()
        await asyncio.Event().wait()

    async def aclose(self):
        pass


class _BarrierStream(httpx.AsyncByteStream):
    def __init__(self, data: bytes, arrivals: list[int], gate: asyncio.Event):
        self.data = data
        self.arrivals = arrivals
        self.gate = gate

    async def __aiter__(self):
        self.arrivals[0] += 1
        if self.arrivals[0] == 2:
            self.gate.set()
        await self.gate.wait()
        yield self.data

    async def aclose(self):
        pass


class _StaticStream(httpx.AsyncByteStream):
    def __init__(self, data: bytes):
        self.data = data

    async def __aiter__(self):
        yield self.data

    async def aclose(self):
        pass


class TestAtomicDownloadRegression:
    @staticmethod
    def _package(*, size: int | None = None, digest: str = ""):
        resource = Resource(
            id="csv-1",
            name="cases",
            format="CSV",
            url="https://example.invalid/cases.csv",
            size=size,
            hash=digest,
        )
        package = CKANPackage(
            id="pkg-1",
            name="synthetic-cases",
            title="Synthetic cases",
            resources=[resource],
            num_resources=1,
            metadata_created=datetime(2024, 1, 1),
            metadata_modified=datetime(2024, 1, 1),
        )
        return package, resource

    @pytest.mark.asyncio
    async def test_interrupted_stream_does_not_publish_partial_file(
        self, tmp_path
    ):
        package, resource = self._package()
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, stream=_InterruptedStream())
        )

        async with httpx.AsyncClient(transport=transport) as client:
            with pytest.raises(httpx.ReadError, match="connection interrupted"):
                await download_resource(
                    client, package, resource_id=resource.id, dest_dir=tmp_path
                )

        destination = tmp_path / filename_for(resource, package.name, 0)
        assert not destination.exists()
        assert list(tmp_path.iterdir()) == []

    @pytest.mark.asyncio
    async def test_failed_overwrite_keeps_previous_complete_file(
        self, tmp_path
    ):
        package, resource = self._package()
        destination = tmp_path / filename_for(resource, package.name, 0)
        destination.write_bytes(b"complete-before-overwrite")
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, stream=_InterruptedStream())
        )

        async with httpx.AsyncClient(transport=transport) as client:
            with pytest.raises(httpx.ReadError, match="connection interrupted"):
                await download_resource(
                    client,
                    package,
                    resource_id=resource.id,
                    dest_dir=tmp_path,
                    overwrite=True,
                )

        assert destination.read_bytes() == b"complete-before-overwrite"
        assert list(tmp_path.iterdir()) == [destination]

    @pytest.mark.asyncio
    async def test_successful_overwrite_replaces_complete_file(self, tmp_path):
        package, resource = self._package()
        destination = tmp_path / filename_for(resource, package.name, 0)
        destination.write_bytes(b"old")
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, content=b"new-complete")
        )

        async with httpx.AsyncClient(transport=transport) as client:
            result = await download_resource(
                client,
                package,
                resource_id=resource.id,
                dest_dir=tmp_path,
                overwrite=True,
            )

        assert result == destination
        assert destination.read_bytes() == b"new-complete"
        assert list(tmp_path.iterdir()) == [destination]

    @pytest.mark.asyncio
    async def test_invalid_cached_size_is_downloaded_again(self, tmp_path):
        package, resource = self._package(size=5)
        destination = tmp_path / filename_for(resource, package.name, 0)
        destination.write_bytes(b"old")
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, content=b"fresh")
        )

        async with httpx.AsyncClient(transport=transport) as client:
            await download_resource(
                client, package, resource_id=resource.id, dest_dir=tmp_path
            )

        assert destination.read_bytes() == b"fresh"
        assert list(tmp_path.iterdir()) == [destination]

    @pytest.mark.asyncio
    async def test_invalid_cached_hash_is_downloaded_again(self, tmp_path):
        fresh = b"new!"
        package, resource = self._package(
            digest=hashlib.sha256(fresh).hexdigest()
        )
        destination = tmp_path / filename_for(resource, package.name, 0)
        destination.write_bytes(b"old!")
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, content=fresh)
        )

        async with httpx.AsyncClient(transport=transport) as client:
            await download_resource(
                client, package, resource_id=resource.id, dest_dir=tmp_path
            )

        assert destination.read_bytes() == fresh
        assert list(tmp_path.iterdir()) == [destination]

    @pytest.mark.asyncio
    async def test_incomplete_content_length_is_not_published(self, tmp_path):
        package, resource = self._package()
        transport = httpx.MockTransport(
            lambda request: httpx.Response(
                200, content=b"x" * 10, headers={"Content-Length": "11"}
            )
        )

        async with httpx.AsyncClient(transport=transport) as client:
            with pytest.raises(IOError, match="incomplete response body"):
                await download_resource(
                    client, package, resource_id=resource.id, dest_dir=tmp_path
                )

        assert list(tmp_path.iterdir()) == []

    @pytest.mark.asyncio
    async def test_incomplete_ckan_size_without_header_is_not_published(
        self, tmp_path
    ):
        package, resource = self._package(size=5)
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, stream=_StaticStream(b"four"))
        )

        async with httpx.AsyncClient(transport=transport) as client:
            with pytest.raises(IOError, match="CKAN size"):
                await download_resource(
                    client, package, resource_id=resource.id, dest_dir=tmp_path
                )

        assert list(tmp_path.iterdir()) == []

    @pytest.mark.asyncio
    async def test_hash_mismatch_keeps_previous_file(self, tmp_path):
        package, resource = self._package(
            digest=hashlib.md5(b"expected").hexdigest()
        )
        destination = tmp_path / filename_for(resource, package.name, 0)
        destination.write_bytes(b"old")
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, content=b"actual")
        )

        async with httpx.AsyncClient(transport=transport) as client:
            with pytest.raises(IOError, match="CKAN hash"):
                await download_resource(
                    client,
                    package,
                    resource_id=resource.id,
                    dest_dir=tmp_path,
                    overwrite=True,
                )

        assert destination.read_bytes() == b"old"
        assert list(tmp_path.iterdir()) == [destination]

    @pytest.mark.asyncio
    async def test_http_error_keeps_previous_file(self, tmp_path):
        package, resource = self._package()
        destination = tmp_path / filename_for(resource, package.name, 0)
        destination.write_bytes(b"old")
        transport = httpx.MockTransport(
            lambda request: httpx.Response(503, content=b"unavailable")
        )

        async with httpx.AsyncClient(transport=transport) as client:
            with pytest.raises(httpx.HTTPStatusError):
                await download_resource(
                    client,
                    package,
                    resource_id=resource.id,
                    dest_dir=tmp_path,
                    overwrite=True,
                )

        assert destination.read_bytes() == b"old"
        assert list(tmp_path.iterdir()) == [destination]

    @pytest.mark.asyncio
    async def test_cancelled_stream_removes_temporary_file(self, tmp_path):
        package, resource = self._package()
        ready = asyncio.Event()
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, stream=_WaitingStream(ready))
        )

        async with httpx.AsyncClient(transport=transport) as client:
            task = asyncio.create_task(
                download_resource(
                    client, package, resource_id=resource.id, dest_dir=tmp_path
                )
            )
            await asyncio.wait_for(ready.wait(), timeout=2)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

        assert list(tmp_path.iterdir()) == []

    @pytest.mark.asyncio
    async def test_concurrent_downloads_do_not_interleave(self, tmp_path):
        package, resource = self._package()
        arrivals = [0]
        gate = asyncio.Event()
        calls = [0]

        def handler(request):
            calls[0] += 1
            data = bytes([64 + calls[0]]) * (1 << 16)
            return httpx.Response(
                200, stream=_BarrierStream(data, arrivals, gate)
            )

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as client:
            paths = await asyncio.wait_for(
                asyncio.gather(
                    download_resource(
                        client,
                        package,
                        resource_id=resource.id,
                        dest_dir=tmp_path,
                    ),
                    download_resource(
                        client,
                        package,
                        resource_id=resource.id,
                        dest_dir=tmp_path,
                    ),
                ),
                timeout=2,
            )

        destination = tmp_path / filename_for(resource, package.name, 0)
        assert paths == [destination, destination]
        assert destination.read_bytes() in {
            b"A" * (1 << 16),
            b"B" * (1 << 16),
        }
        assert list(tmp_path.iterdir()) == [destination]

    @pytest.mark.asyncio
    async def test_concurrent_non_overwrite_reuses_existing_file(
        self, tmp_path
    ):
        package, resource = self._package()
        destination = tmp_path / filename_for(resource, package.name, 0)
        destination.write_bytes(b"existing")

        def unexpected_request(request):
            raise AssertionError("an existing complete file should be reused")

        transport = httpx.MockTransport(unexpected_request)
        async with httpx.AsyncClient(transport=transport) as client:
            paths = await asyncio.gather(
                download_resource(
                    client, package, resource_id=resource.id, dest_dir=tmp_path
                ),
                download_resource(
                    client, package, resource_id=resource.id, dest_dir=tmp_path
                ),
            )

        assert paths == [destination, destination]
        assert destination.read_bytes() == b"existing"


class TestDownloadDatasetEdgeCases:
    @pytest.mark.asyncio
    async def test_no_dest_dir(
        self, saude_dataset_page_props, tmp_path, mocked_saude
    ):
        from pysus.api.saude.resources import CKANPackage

        package = CKANPackage.model_validate(saude_dataset_page_props)
        original_dir = tmp_path / "cwd"
        original_dir.mkdir()

        import os

        old_cwd = os.getcwd()
        try:
            os.chdir(original_dir)
            async with httpx.AsyncClient(transport=mocked_saude) as client:
                paths = await download_dataset(
                    client,
                    package,
                    fmt="CSV",
                )
            assert len(paths) > 0
        finally:
            os.chdir(old_cwd)

    @pytest.mark.asyncio
    async def test_progress_forwarded(
        self, saude_dataset_page_props, tmp_path, mocked_saude
    ):
        from pysus.api.saude.resources import CKANPackage

        package = CKANPackage.model_validate(saude_dataset_page_props)
        calls = []

        def progress(downloaded: int, total: int):
            calls.append((downloaded, total))

        async with httpx.AsyncClient(transport=mocked_saude) as client:
            await download_dataset(
                client,
                package,
                dest_dir=tmp_path,
                fmt="CSV",
                progress=progress,
            )
        assert len(calls) > 0
