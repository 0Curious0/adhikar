import json
from pathlib import Path

from .exceptions import SchemeLoadError
from .models import SchemeDocument

DATA_DIR = Path(__file__).parent / "data"


def load_scheme(path: Path) -> SchemeDocument:
    return SchemeDocument.model_validate(json.loads(path.read_text(encoding="utf-8")))


def load_all_schemes(directory: Path = DATA_DIR) -> dict[str, SchemeDocument]:
    """Load every scheme file under `directory` (recursively), keyed by `scheme_id`.

    Every file is attempted; if any fail to load/validate or collide on `scheme_id`,
    all failures are reported together in one `SchemeLoadError` rather than stopping
    at the first bad file.
    """
    schemes: dict[str, SchemeDocument] = {}
    errors: list[str] = []

    for path in sorted(directory.rglob("*.json")):
        try:
            scheme = load_scheme(path)
        except Exception as e:
            errors.append(f"{path}: {e}")
            continue

        if scheme.scheme_id in schemes:
            errors.append(f"{path}: duplicate scheme_id '{scheme.scheme_id}'")
            continue

        schemes[scheme.scheme_id] = scheme

    if errors:
        raise SchemeLoadError("\n".join(errors))

    return schemes