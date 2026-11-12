"""Talk to the local wp-env shop only. Never calls ydu.com.au or Zoho."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JOBS = ROOT / "data" / "studio-jobs"
CONTAINER_REQ = "/var/www/html/wp-content/ydu-seed/data/studio-jobs/request.json"
CONTAINER_PHP = "/var/www/html/wp-content/ydu-seed/tools/studio-woo.php"
PNG_PHP = "/var/www/html/wp-content/ydu-seed/tools/studio-png.php"
MEDIA_PREFIX = "/var/www/html/wp-content/ydu-seed/data/studio-media/"


def _run(args: list[str], timeout: float) -> str:
    """Run a local docker command. Kill it if it does not finish, so a page cannot wait forever."""
    proc = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        out, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        raise RuntimeError("local shop command timed out")
    if proc.returncode != 0:
        lines = [line.strip() for line in (out or "").splitlines() if line.strip()]
        raise RuntimeError(lines[-1][:400] if lines else "local shop command failed")
    return out or ""


def _cli_container(timeout: float = 2) -> str:
    out = _run(["docker", "ps", "--format", "{{.Names}}"], timeout)
    names = [
        line.strip()
        for line in out.splitlines()
        if "wp-env-yduv2" in line and line.endswith("-cli-1") and "tests" not in line
    ]
    if not names:
        raise RuntimeError("Local wp-env cli container is not running.")
    return names[0]


def _wp_container() -> str:
    out = subprocess.check_output(["docker", "ps", "--format", "{{.Names}}"], text=True)
    names = [
        line.strip()
        for line in out.splitlines()
        if "wp-env-yduv2" in line and line.endswith("-wordpress-1") and "tests" not in line
    ]
    if not names:
        raise RuntimeError("Local WordPress container is not running.")
    return names[0]


def _call(payload: dict, timeout: float = 30) -> dict:
    JOBS.mkdir(parents=True, exist_ok=True)
    (JOBS / "request.json").write_text(json.dumps(payload), encoding="utf-8")
    deadline = time.monotonic() + timeout
    container = _cli_container(timeout=max(0.1, deadline - time.monotonic()))
    _run(
        [
            "docker",
            "exec",
            container,
            "php",
            "-d",
            "memory_limit=512M",
            "/usr/local/bin/wp",
            "eval-file",
            CONTAINER_PHP,
        ],
        max(0.1, deadline - time.monotonic()),
    )
    return json.loads((JOBS / "response.json").read_text(encoding="utf-8"))


def list_skus() -> list[str]:
    data = _call({"action": "skus"})
    if not data.get("ok"):
        raise RuntimeError(data.get("error") or "local shop list failed")
    return data["skus"]


def one_product(sku: str, timeout: float = 30) -> dict | None:
    data = _call({"action": "one", "sku": sku}, timeout=timeout)
    if not data.get("ok"):
        raise RuntimeError(data.get("error") or "local shop read failed")
    return data.get("product")


def upsert(payload: dict) -> dict:
    payload = dict(payload)
    payload["action"] = "upsert"
    hero = payload.get("hero_path") or ""
    if hero:
        rel = Path(hero).resolve()
        media_root = (ROOT / "data" / "studio-media").resolve()
        if not str(rel).startswith(str(media_root)):
            raise RuntimeError("hero is outside studio media")
        payload["hero_path"] = MEDIA_PREFIX + rel.relative_to(media_root).as_posix()
    return _call(payload)


def to_png(src: Path) -> tuple[Path, int]:
    rel = src.resolve().relative_to((ROOT / "data" / "studio-media").resolve())
    container_src = MEDIA_PREFIX + rel.as_posix()
    dest = src.with_suffix(".png")
    container_dest = MEDIA_PREFIX + dest.resolve().relative_to((ROOT / "data" / "studio-media").resolve()).as_posix()
    proc = subprocess.run(
        ["docker", "exec", _wp_container(), "php", PNG_PHP, container_src, container_dest],
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "png conversion failed")
    return dest, int(proc.stdout.strip() or "0")
