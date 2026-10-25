"""Small provenance helpers for frozen experiment reports."""
from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def source_fingerprints(features: str | Path, transactions: str | Path) -> dict:
    return dict(
        features_sha256=sha256_file(features),
        transactions_sha256=sha256_file(transactions),
    )
