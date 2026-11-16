"""Build the Sculpt-Paint Wheel extension zip for GitHub releases and the stores.

Usage:
    python store/tools/build_release.py [--blender PATH]

Output (ignored by git):
    build/store/spwheel-<version>.zip

Blender is found from --blender, then the BLENDER environment variable, then the newest
"Blender X.Y" folder under C:/Program Files/Blender Foundation, then `blender` on PATH.
The zip is built and validated with Blender's own extension tools, and contains only files tracked by git.
"""
import argparse
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "spwheel"
OUT = ROOT / "build" / "store"


def find_blender(cli_path):
    if cli_path:
        return cli_path
    if os.environ.get("BLENDER"):
        return os.environ["BLENDER"]
    foundation = pathlib.Path("C:/Program Files/Blender Foundation")
    if foundation.is_dir():
        def version(p):
            m = re.search(r"(\d+)\.(\d+)", p.name)
            return (int(m.group(1)), int(m.group(2))) if m else (0, 0)
        for folder in sorted(foundation.iterdir(), key=version, reverse=True):
            exe = folder / "blender.exe"
            if exe.exists():
                return str(exe)
    found = shutil.which("blender")
    if found:
        return found
    sys.exit("Blender not found: pass --blender PATH or set the BLENDER environment variable.")


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout, result.stderr, sep="\n")
        sys.exit(f"Command failed: {' '.join(cmd)}")
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--blender", help="Path to the Blender executable")
    args = parser.parse_args()

    blender = find_blender(args.blender)
    version = re.search(r'^version\s*=\s*"([^"]+)"', (SRC / "blender_manifest.toml").read_text(encoding="utf-8"), re.M).group(1)
    print(f"Blender:  {blender}")
    print(f"Version:  {version}")

    # Build from a clean copy of the git-tracked files, so local caches and untracked files never ship.
    tracked = run(["git", "-C", str(ROOT), "ls-files", "spwheel"]).splitlines()
    with tempfile.TemporaryDirectory() as tmp:
        staging = pathlib.Path(tmp) / "spwheel"
        for rel in tracked:
            dst = pathlib.Path(tmp) / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, dst)

        OUT.mkdir(parents=True, exist_ok=True)
        zip_path = OUT / f"spwheel-{version}.zip"
        zip_path.unlink(missing_ok=True)
        run([blender, "--factory-startup", "--command", "extension", "build",
             "--source-dir", str(staging), "--output-dir", str(OUT)])

    run([blender, "--factory-startup", "--command", "extension", "validate", str(zip_path)])

    with zipfile.ZipFile(zip_path) as z:
        names = [n for n in z.namelist() if not n.endswith("/")]
    expected = {rel.split("/", 1)[1] for rel in tracked}
    if set(names) != expected:
        sys.exit(f"Zip contents differ from git-tracked files: {sorted(set(names) ^ expected)[:10]}")

    print(f"Built:    {zip_path}  ({zip_path.stat().st_size / 1e6:.1f} MB, {len(names)} files, validated)")


if __name__ == "__main__":
    main()
