"""Safe file storage for generated artifacts.

All generated files live under GENERATED_PROJECTS_DIR/execution_<id>/.
Every path is resolved and checked so nothing can escape that folder
(e.g. '../../etc/passwd' or absolute paths are rejected).
"""

import hashlib
import io
import zipfile
from pathlib import Path

from app.config import get_settings


class UnsafePathError(ValueError):
    pass


def generated_root() -> Path:
    root = get_settings().generated_root
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def safe_join(base: Path, relative: str) -> Path:
    """Join `relative` onto `base`, refusing anything that would leave `base`."""
    if not relative or relative.startswith(("/", "\\")) or "\x00" in relative:
        raise UnsafePathError(f"Unsafe path: {relative!r}")
    if ".." in Path(relative).parts or ":" in relative:
        raise UnsafePathError(f"Unsafe path: {relative!r}")
    base = base.resolve()
    target = (base / relative).resolve()
    if not target.is_relative_to(base):
        raise UnsafePathError(f"Path escapes storage folder: {relative!r}")
    return target


def execution_dir(execution_id: int) -> Path:
    return safe_join(generated_root(), f"execution_{int(execution_id)}")


def code_dir(execution_id: int, code_version: int) -> Path:
    return safe_join(execution_dir(execution_id), f"code_v{int(code_version)}")


def docs_dir(execution_id: int) -> Path:
    return safe_join(execution_dir(execution_id), "docs")


def write_text_file(base: Path, relative: str, content: str) -> tuple[Path, str]:
    """Write a file below `base`. Returns (absolute path, path relative to generated root)."""
    target = safe_join(base, relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target, target.relative_to(generated_root()).as_posix()


def resolve_stored_path(stored: str) -> Path:
    """Turn an Artifact.file_path (relative to generated root) back into a safe path."""
    return safe_join(generated_root(), stored)


def sha256(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def build_package(execution_id: int, code_version: int | None, extra: dict[str, str]) -> bytes:
    """Zip the latest code version + docs + extra in-memory files into a delivery package."""
    buffer = io.BytesIO()
    root = execution_dir(execution_id)
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        if code_version is not None:
            source = code_dir(execution_id, code_version)
            if source.exists():
                for path in sorted(source.rglob("*")):
                    if path.is_file() and not path.is_symlink():
                        archive.write(path, f"source/{path.relative_to(source).as_posix()}")
        documents = root / "docs"
        if documents.exists():
            for path in sorted(documents.rglob("*.md")):
                if path.is_file() and not path.is_symlink():
                    archive.write(path, f"docs/{path.relative_to(documents).as_posix()}")
        for name, content in extra.items():
            archive.writestr(name, content)
    return buffer.getvalue()
