"""Valve KeyValues (VDF / ACF) parser and serializer for Steam files."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Union
import vdf

from src.core.logger import get_logger

logger = get_logger("steam.vdf_parser")


def parse_vdf_text(text: str) -> Dict[str, Any]:
    """Parse VDF KeyValues formatted string into a Python dictionary."""
    if not text or not text.strip():
        return {}
    try:
        return vdf.loads(text)
    except Exception as e:
        logger.error(f"Failed to parse VDF text: {e}")
        raise ValueError(f"Invalid VDF content: {e}") from e


def parse_vdf_file(file_path: Union[Path, str]) -> Dict[str, Any]:
    """Read and parse a VDF / ACF file with encoding fallbacks (utf-8, latin-1, cp1252)."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"VDF file not found: {path}")

    # Try utf-8 first, then fallback to common legacy encodings
    encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc) as f:
                content = f.read()
            return parse_vdf_text(content)
        except UnicodeDecodeError:
            continue
        except Exception as e:
            logger.error(f"Error parsing VDF file '{path}' with encoding '{enc}': {e}")
            raise

    raise ValueError(f"Unable to decode VDF file with supported encodings: {path}")


def dump_vdf_text(data: Dict[str, Any], pretty: bool = True) -> str:
    """Serialize a Python dictionary into a Valve KeyValues string."""
    try:
        return vdf.dumps(data, pretty=pretty)
    except Exception as e:
        logger.error(f"Failed to dump dictionary to VDF string: {e}")
        raise ValueError(f"Serialization failed: {e}") from e


def dump_vdf_file(file_path: Union[Path, str], data: Dict[str, Any], pretty: bool = True) -> None:
    """Serialize and write a Python dictionary to a VDF / ACF file safely."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    vdf_content = dump_vdf_text(data, pretty=pretty)
    with open(path, "w", encoding="utf-8") as f:
        f.write(vdf_content)
    logger.debug(f"Saved VDF file to {path}")
