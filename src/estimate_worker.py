#!/usr/bin/env python3
"""
Worker éphémère de pré-estimation volumétrique SMB.
Monte temporairement un partage CIFS en lecture seule, exécute `du -sb`,
renvoie le volume total sur stdout au format JSON, puis démonte.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def format_subprocess_failure(exc: subprocess.CalledProcessError) -> str:
    stdout = (exc.stdout or "").strip()
    stderr = (exc.stderr or "").strip()
    details = []
    if stderr:
        details.append(f"stderr={stderr}")
    if stdout:
        details.append(f"stdout={stdout}")
    detail_suffix = f" ({', '.join(details)})" if details else ""
    return f"Commande {exc.cmd!r} en echec avec code {exc.returncode}{detail_suffix}"


def parse_unc_start_path(start_path: str):
    normalized = (start_path or "").strip().rstrip("\\")
    parts = [part for part in normalized.split("\\") if part]
    if len(parts) < 2:
        raise ValueError(f"Chemin UNC invalide: {start_path}")

    server = parts[0]
    share_name = parts[1]
    relative_parts = parts[2:]
    return server, share_name, relative_parts


def build_mount_dir(base_dir: str, share_name: str) -> Path:
    safe_share_name = "".join(
        ch if ch.isalnum() or ch in {"-", "_"} else "-"
        for ch in (share_name or "share").strip()
    ).strip("-") or "share"
    return Path(base_dir).joinpath(safe_share_name)


def build_credentials_file(username: str, password: str, domain: str) -> str:
    fd, credentials_path = tempfile.mkstemp(prefix="openindex-estimate-", suffix=".cred")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(f"username={username}\n")
            handle.write(f"password={password}\n")
            if domain:
                handle.write(f"domain={domain}\n")
    except Exception:
        os.unlink(credentials_path)
        raise
    os.chmod(credentials_path, 0o600)
    return credentials_path


def mount_share(source: str, mount_dir: Path, credentials_path: str) -> None:
    mount_dir.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            [
                "mount",
                "-t",
                "cifs",
                source,
                str(mount_dir),
                "-o",
                f"ro,credentials={credentials_path},iocharset=utf8",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(format_subprocess_failure(exc)) from exc


def unmount_share(mount_dir: Path) -> None:
    try:
        subprocess.run(
            ["umount", str(mount_dir)],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(format_subprocess_failure(exc)) from exc


def run_du(target_path: Path) -> int:
    try:
        du_result = subprocess.run(
            ["du", "-sb", str(target_path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(format_subprocess_failure(exc)) from exc
    return int(du_result.stdout.split()[0])


def main() -> int:
    run_id = os.getenv("OPENINDEX_RUN_ID", "")
    start_path = os.getenv("OPENINDEX_START_PATH", "")
    username = os.getenv("OPENINDEX_SMB_USERNAME", "")
    password = os.getenv("OPENINDEX_SMB_PASSWORD", "")
    domain = os.getenv("OPENINDEX_SMB_DOMAIN", "")
    mount_base_dir = os.getenv("OPENINDEX_ESTIMATE_MOUNT_BASE", "/mnt")

    mount_dir = None
    credentials_path = None
    try:
        server, share_name, relative_parts = parse_unc_start_path(start_path)
        mount_dir = build_mount_dir(mount_base_dir, share_name)
        credentials_path = build_credentials_file(username, password, domain)

        mount_source = f"//{server}/{share_name}"
        print(f"[estimate] montage read-only de {mount_source} sur {mount_dir}", file=sys.stderr, flush=True)
        mount_share(mount_source, mount_dir, credentials_path)

        target_path = mount_dir.joinpath(*relative_parts) if relative_parts else mount_dir
        if not target_path.exists():
            raise FileNotFoundError(f"Chemin cible introuvable apres montage: {target_path}")

        estimated_total_size = run_du(target_path)
        print(
            json.dumps(
                {
                    "status": "ok",
                    "run_id": run_id,
                    "estimated_total_size": estimated_total_size,
                    "target_path": str(target_path),
                }
            ),
            flush=True,
        )
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "error",
                    "run_id": run_id,
                    "error": str(exc),
                }
            ),
            file=sys.stderr,
            flush=True,
        )
        return 1
    finally:
        if mount_dir is not None and mount_dir.exists():
            try:
                if os.path.ismount(mount_dir):
                    print(f"[estimate] demontage de {mount_dir}", file=sys.stderr, flush=True)
                    unmount_share(mount_dir)
            except Exception as exc:
                print(f"[estimate] echec demontage {mount_dir}: {exc}", file=sys.stderr, flush=True)
            finally:
                shutil.rmtree(mount_dir, ignore_errors=True)
        if credentials_path and os.path.exists(credentials_path):
            os.unlink(credentials_path)


if __name__ == "__main__":
    raise SystemExit(main())
