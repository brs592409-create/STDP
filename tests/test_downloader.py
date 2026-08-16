"""Unit tests for ManifestDownloader."""

import hashlib
from pathlib import Path
from unittest.mock import MagicMock
from src.depotbox.downloader import ManifestDownloader


def test_download_manifest_success_and_hash(tmp_path: Path):
    data = b"STREAMING_BINARY_DATA_MANIFEST"
    expected_sha = hashlib.sha256(data).hexdigest()

    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.headers = {"Content-Length": str(len(data))}
    mock_resp.iter_content.return_value = [data[:10], data[10:]]
    mock_resp.__enter__.return_value = mock_resp
    mock_session.get.return_value = mock_resp

    downloader = ManifestDownloader(session=mock_session)
    target = tmp_path / "1001_2002.manifest"

    progress_records = []

    def _progress(cur, total):
        progress_records.append((cur, total))

    success = downloader.download_manifest(
        url="https://example.com/manifest",
        target_path=target,
        expected_sha256=expected_sha,
        progress_callback=_progress,
    )

    assert success is True
    assert target.exists()
    assert target.read_bytes() == data
    assert len(progress_records) > 0


def test_download_manifest_hash_mismatch(tmp_path: Path):
    data = b"REAL_DATA"
    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.headers = {"Content-Length": str(len(data))}
    mock_resp.iter_content.return_value = [data]
    mock_resp.__enter__.return_value = mock_resp
    mock_session.get.return_value = mock_resp

    downloader = ManifestDownloader(session=mock_session)
    target = tmp_path / "corrupt.manifest"

    success = downloader.download_manifest(
        url="https://example.com/manifest",
        target_path=target,
        expected_sha256="wrong_hash_000000000000000000000000000000000000000000000000000000000000",
    )

    assert success is False
    assert not target.exists()
