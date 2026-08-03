import os

def get_current_version() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    version_file = os.path.join(here, "..", "..", "..", "VERSION")
    try:
        with open(version_file, "r", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return "0.0.0"
