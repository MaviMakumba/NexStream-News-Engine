"""Dockerfile.embedder yalnızca embedder'ın import kapanışını kopyalar (tüm src/ DEĞİL).

Neden: backend'deki her değişiklik ağır embedder image'ını (model gömülü) yeniden
build/recreate ettirmesin. Risk: embedder koduna yeni bir `src.*` import'u eklenip
Dockerfile'a dosya eklenmezse prod'da ImportError ile açılışta ölür — bu test onu
CI'da yakalar.
"""
import ast
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.drift

ROOT = Path(__file__).resolve().parents[2]
ENTRY = "src/adapters/search/embedder_service.py"


def _module_to_path(module: str) -> Path | None:
    p = ROOT / (module.replace(".", "/") + ".py")
    return p if p.exists() else None


def _src_imports(path: Path) -> set[str]:
    found = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("src."):
            found.add(node.module)
        elif isinstance(node, ast.Import):
            found.update(a.name for a in node.names if a.name.startswith("src."))
    return found


def _import_closure(entry: str) -> set[str]:
    """Giriş dosyasından başlayıp src.* import'larını (dosya + __init__) toplar."""
    seen, todo = set(), [ROOT / entry]
    while todo:
        path = todo.pop()
        rel = path.relative_to(ROOT).as_posix()
        if rel in seen:
            continue
        seen.add(rel)
        for module in _src_imports(path):
            target = _module_to_path(module)
            if target:
                todo.append(target)
    return seen


def _copied_files() -> set[str]:
    copied = set()
    for line in (ROOT / "Dockerfile.embedder").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*COPY\s+(?:--\S+\s+)*(.+)", line)
        if not m:
            continue
        parts = m.group(1).split()
        sources, dest = parts[:-1], parts[-1]
        for src in sources:
            if src.startswith("src/") and src.endswith(".py"):
                copied.add(src)
    return copied


def test_dockerfile_copies_every_file_the_embedder_imports():
    missing = _import_closure(ENTRY) - _copied_files()
    assert not missing, f"Dockerfile.embedder şu dosyaları kopyalamıyor: {sorted(missing)}"


def test_dockerfile_does_not_copy_the_whole_src_tree():
    text = (ROOT / "Dockerfile.embedder").read_text(encoding="utf-8")
    assert not re.search(r"COPY\s+(?:--\S+\s+)*src/\s", text), "tüm src/ kopyalanıyor"


def test_search_package_init_is_copied():
    assert "src/adapters/search/__init__.py" in _copied_files()
