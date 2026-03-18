import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from scripts.versioning import bump_version, detect_bump_type, parse_version, validate_pr
from src.versioning import get_current_version


def test_parse_and_bump_version():
    version = parse_version("1.4.9")

    assert str(bump_version(version, "fix")) == "1.4.10"
    assert str(bump_version(version, "minor")) == "1.5.0"


def test_detect_bump_type_accepts_label_or_title():
    assert detect_bump_type("minor: nouvelle fonctionnalite", set()) == "minor"
    assert detect_bump_type("correction divers", {"fix"}) == "fix"


def test_validate_pr_enforces_expected_semver_transition():
    validate_pr("0.1.0", "0.1.1", "fix")
    validate_pr("0.1.1", "0.2.0", "minor")


def test_project_version_file_is_available():
    version = get_current_version()

    assert version == Path("VERSION").read_text(encoding="utf-8").strip()


def test_package_json_version_matches_project_version():
    package = json.loads(Path("package.json").read_text(encoding="utf-8"))
    assert package["version"] == get_current_version()
