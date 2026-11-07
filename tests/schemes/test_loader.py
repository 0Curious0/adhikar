import json
from pathlib import Path

import pytest

from adhikar.schemes.exceptions import SchemeLoadError
from adhikar.schemes.loader import load_all_schemes, load_scheme

VALID_SCHEME = {
    "schema_version": "1.0.0",
    "scheme_id": "scheme-a",
    "jurisdiction": {"level": "central", "country": "IN"},
    "name": {"en": "Scheme A"},
}


def _write(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_load_scheme_returns_validated_document(tmp_path):
    path = _write(tmp_path / "scheme_a.json", VALID_SCHEME)

    doc = load_scheme(path)

    assert doc.scheme_id == "scheme-a"
    assert doc.jurisdiction.level == "central"


def test_load_all_schemes_walks_subdirectories(tmp_path):
    _write(tmp_path / "scheme_a.json", VALID_SCHEME)
    nested = tmp_path / "widow_pension"
    nested.mkdir()
    _write(nested / "central.json", {**VALID_SCHEME, "scheme_id": "scheme-b"})

    schemes = load_all_schemes(tmp_path)

    assert set(schemes) == {"scheme-a", "scheme-b"}


def test_load_all_schemes_reports_every_failure_together(tmp_path):
    _write(tmp_path / "bad_json.json", {})
    (tmp_path / "bad_json.json").write_text("{not valid json", encoding="utf-8")
    _write(tmp_path / "dup_a.json", VALID_SCHEME)
    _write(tmp_path / "dup_b.json", VALID_SCHEME)

    with pytest.raises(SchemeLoadError) as exc_info:
        load_all_schemes(tmp_path)

    message = str(exc_info.value)
    assert "bad_json.json" in message
    assert "duplicate scheme_id" in message
