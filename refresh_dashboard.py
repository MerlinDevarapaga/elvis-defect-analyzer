import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"
GENERATOR = ROOT / "scripts" / "update_overview_live.py"
CURRENT_RELEASE_MILESTONE = os.getenv("CURRENT_RELEASE_MILESTONE", "R10.50")
CURRENT_RELEASE_TARGET_DATE = os.getenv("CURRENT_RELEASE_TARGET_DATE", "2026-10-13")
NONYTB_TARGET_DATE = os.getenv("NONYTB_TARGET_DATE", "2026-10-31")


def run_generator():
    if not VENV_PY.exists():
        raise FileNotFoundError(
            f"Python environment not found at {VENV_PY}. "
            "Activate the existing .venv or recreate it before running this script."
        )
    if not GENERATOR.exists():
        raise FileNotFoundError(f"Generator script not found at {GENERATOR}")

    env = os.environ.copy()
    env["CURRENT_RELEASE_MILESTONE"] = CURRENT_RELEASE_MILESTONE
    env["CURRENT_RELEASE_TARGET_DATE"] = CURRENT_RELEASE_TARGET_DATE
    env["NONYTB_TARGET_DATE"] = NONYTB_TARGET_DATE
    subprocess.run([str(VENV_PY), str(GENERATOR)], check=True, env=env)


def git(*args, allow_fail=False):
    result = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)
    if not allow_fail and result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "git command failed")
    return result


def publish_live():
    git("status", "--short")
    git("add", "index.html", "overview.html", "ytb.html", "non-ytb.html", "current-release.html")

    commit = git("commit", "-m", "Refresh dashboard with live Elvis DB data", allow_fail=True)
    combined = (commit.stdout or "") + (commit.stderr or "")
    if commit.returncode != 0 and "nothing to commit" not in combined.lower():
        raise RuntimeError(combined.strip() or "git commit failed")

    git("push", "origin", "gh-pages")
    git("push", "harman", "gh-pages")
    print("Published dashboard to both origin and harman gh-pages remotes.")


def main():
    parser = argparse.ArgumentParser(description="Refresh the MSIL DA2.8 dashboard and optionally publish to gh-pages.")
    parser.add_argument("--local-only", action="store_true", help="Refresh the HTML locally without pushing to GitHub Pages.")
    args = parser.parse_args()

    run_generator()

    if not args.local_only:
        publish_live()
    else:
        print("Local dashboard refresh complete. No git push performed (--local-only).")


if __name__ == "__main__":
    main()
