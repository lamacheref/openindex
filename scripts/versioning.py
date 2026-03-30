#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


@dataclass(frozen=True)
class SemVer:
    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


def parse_version(raw: str) -> SemVer:
    match = SEMVER_RE.fullmatch(raw.strip())
    if not match:
        raise ValueError(f"Version invalide: {raw}")
    return SemVer(*(int(part) for part in match.groups()))


def bump_version(version: SemVer, bump_type: str) -> SemVer:
    if bump_type == "fix":
        return SemVer(version.major, version.minor, version.patch + 1)
    if bump_type == "minor":
        return SemVer(version.major, version.minor + 1, 0)
    raise ValueError(f"Type de bump non supporte: {bump_type}")


def detect_bump_type(pr_title: str, labels: set[str]) -> str:
    normalized_title = pr_title.strip().lower()
    if "minor" in labels or normalized_title.startswith("minor:"):
        return "minor"
    if "fix" in labels or normalized_title.startswith("fix:"):
        return "fix"
    raise ValueError("La PR doit porter un label 'minor' ou 'fix', ou un titre commencant par 'minor:' ou 'fix:'.")


def validate_pr(base_version: str, target_version: str, bump_type: str) -> None:
    base = parse_version(base_version)
    target = parse_version(target_version)
    expected = bump_version(base, bump_type)
    if target != expected:
        raise ValueError(
            f"Version cible invalide pour un bump {bump_type}: attendue {expected}, obtenue {target}."
        )


def read_version_file(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def load_pr_context(event_path: Path) -> tuple[str, set[str]]:
    payload = json.loads(event_path.read_text(encoding="utf-8"))
    pull_request = payload.get("pull_request") or {}
    title = pull_request.get("title") or ""
    labels = {
        (label.get("name") or "").strip().lower()
        for label in pull_request.get("labels", [])
        if (label.get("name") or "").strip()
    }
    return title, labels


def read_base_branch_version(base_ref: str) -> str:
    return subprocess.check_output(
        ["git", "show", f"origin/{base_ref}:VERSION"],
        text=True,
    ).strip()


def version_changed_against_base(base_ref: str) -> bool:
    diff = subprocess.check_output(
        ["git", "diff", "--name-only", f"origin/{base_ref}...HEAD"],
        text=True,
    )
    return "VERSION" in {line.strip() for line in diff.splitlines()}


def cmd_show(_: argparse.Namespace) -> int:
    print(read_version_file(Path("VERSION")))
    return 0


def cmd_bump_local(args: argparse.Namespace) -> int:
    version_path = Path(args.version_file)
    current = parse_version(read_version_file(version_path))
    target = bump_version(current, "fix")
    version_path.write_text(f"{target}\n", encoding="utf-8")
    if args.stage:
        subprocess.run(["git", "add", str(version_path)], check=True)
    print(str(target))
    return 0


def cmd_validate_pr(args: argparse.Namespace) -> int:
    base_version = args.base_version
    target_version = args.target_version
    bump_type = args.bump_type

    if args.event_path:
        title, labels = load_pr_context(Path(args.event_path))
        detected_bump = detect_bump_type(title, labels)
        if bump_type and bump_type != detected_bump:
            raise ValueError(f"Type de bump incoherent: argument={bump_type}, PR={detected_bump}.")
        bump_type = detected_bump

    if args.base_ref:
        if not version_changed_against_base(args.base_ref):
            raise ValueError("Le fichier VERSION doit etre modifie dans la PR.")
        base_version = read_base_branch_version(args.base_ref)

    if not base_version or not target_version or not bump_type:
        raise ValueError("base_version, target_version et bump_type sont requis pour valider la PR.")

    validate_pr(base_version, target_version, bump_type)
    print(
        json.dumps(
            {
                "base_version": base_version,
                "target_version": target_version,
                "bump_type": bump_type,
            }
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Outils de versionning OpenIndex")
    subparsers = parser.add_subparsers(dest="command", required=True)

    show_parser = subparsers.add_parser("show", help="Affiche la version courante")
    show_parser.set_defaults(func=cmd_show)

    bump_local_parser = subparsers.add_parser("bump-local", help="Incremente localement la version patch")
    bump_local_parser.add_argument("--version-file", default="VERSION")
    bump_local_parser.add_argument("--stage", action="store_true")
    bump_local_parser.set_defaults(func=cmd_bump_local)

    validate_pr_parser = subparsers.add_parser("validate-pr", help="Valide la version d'une PR")
    validate_pr_parser.add_argument("--base-version")
    validate_pr_parser.add_argument("--target-version")
    validate_pr_parser.add_argument("--bump-type", choices=["fix", "minor"])
    validate_pr_parser.add_argument("--base-ref")
    validate_pr_parser.add_argument("--event-path", default=os.getenv("GITHUB_EVENT_PATH"))
    validate_pr_parser.set_defaults(func=cmd_validate_pr)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
