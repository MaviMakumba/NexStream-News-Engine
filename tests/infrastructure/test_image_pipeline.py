"""CI'da build → GHCR → EC2'de pull hattının parçaları birbiriyle senkron kalmalı.

7 Eki 2026: EC2'de `docker compose up --build` t3.small'ı kilitliyordu; imajlar artık
CI'da build ediliyor. Bu testler, compose'daki imaj adları / workflow matrisi / deploy
betiği arasında sessiz kopmayı (ör. yeni servis eklenip build matrisine unutulması
→ deploy'da `pull` hatası) CI'da yakalar.
"""
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.drift

ROOT = Path(__file__).resolve().parents[2]
PREFIX = "ghcr.io/mavimakumba/nexstream-"


def _compose():
    return yaml.safe_load((ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8"))["services"]


def _workflow():
    return yaml.safe_load((ROOT / ".github/workflows/tests.yml").read_text(encoding="utf-8"))


def _built_services() -> dict:
    return {name: svc for name, svc in _compose().items() if "build" in svc}


def test_every_built_prod_service_has_a_ghcr_image():
    for name, svc in _built_services().items():
        assert svc.get("image", "").startswith(PREFIX), f"{name}: image: {PREFIX}... yok"


def test_workflow_matrix_builds_exactly_the_images_compose_uses():
    compose_images = {svc["image"].split(":")[0].removeprefix(PREFIX) for svc in _built_services().values()}
    matrix = _workflow()["jobs"]["build-images"]["strategy"]["matrix"]["include"]
    assert {m["name"] for m in matrix} == compose_images


def test_matrix_dockerfiles_match_compose_build_definitions():
    matrix = {m["name"]: m for m in _workflow()["jobs"]["build-images"]["strategy"]["matrix"]["include"]}
    for name, svc in _built_services().items():
        image_name = svc["image"].split(":")[0].removeprefix(PREFIX)
        build = svc["build"]
        context = build if isinstance(build, str) else build.get("context", ".")
        dockerfile = "Dockerfile" if isinstance(build, str) else build.get("dockerfile", "Dockerfile")
        m = matrix[image_name]
        assert Path(m["context"]).as_posix().strip("./") == Path(context).as_posix().strip("./"), (name, m, build)
        assert Path(m["file"]).name == dockerfile, (name, m, build)


def test_deploy_script_pulls_every_service_that_has_a_built_image():
    script = (ROOT / "infra/scripts/deploy_images.sh").read_text(encoding="utf-8")
    declared = set(re.search(r'SERVICES="([^"]+)"', script).group(1).split())
    assert declared == set(_built_services())


def test_deploy_never_builds_on_the_server():
    script = (ROOT / "infra/scripts/deploy_images.sh").read_text(encoding="utf-8")
    code = "\n".join(line for line in script.splitlines() if not line.lstrip().startswith("#"))
    assert "--no-build" in code
    assert not re.search(r"\bup\s+[^\n]*--build", code)
    workflow = (ROOT / ".github/workflows/tests.yml").read_text(encoding="utf-8")
    assert "up --build" not in workflow.split("name: Deploy to production")[1]


def test_deploy_job_waits_for_image_build():
    assert "build-images" in _workflow()["jobs"]["deploy"]["needs"]


def test_builds_are_deterministic_so_unchanged_services_are_not_recreated():
    """Aynı içerik = aynı digest: aksi halde her deploy TÜM servisleri (özellikle RAM-ağır
    embedder'ı) yeniden yaratır."""
    steps = _workflow()["jobs"]["build-images"]["steps"]
    build = next(s for s in steps if "build-push-action" in s.get("uses", ""))["with"]
    assert "SOURCE_DATE_EPOCH=" in build["build-args"]
    assert "rewrite-timestamp=true" in build["outputs"]


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash yok")
def test_deploy_script_has_valid_shell_syntax():
    result = subprocess.run(["bash", "-n", str(ROOT / "infra/scripts/deploy_images.sh")], capture_output=True)
    if result.returncode == 127:  # Windows'ta `bash` = çalışmayan WSL kabuğu; CI (Linux) gerçek denetimi yapar
        pytest.skip("bash çalıştırılamadı")
    assert result.returncode == 0, result.stderr
