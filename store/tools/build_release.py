"""Build the Sculpt-Paint Wheel extension zip for GitHub releases and the stores.

Usage:
    python store/tools/build_release.py [--store] [--blender PATH]

Output (ignored by git):
    build/store/spwheel-<version>.zip             GitHub release (free download)
    build/store/superhive/spwheel-<version>.zip   --store: the copy sold on Superhive. Same add-on, without the
                                                  "Support Development" box in the preferences (buyers already did).

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

# Store build: changes made to the staging copy only (the repository is never modified).
# (path in the zip, regex, replacement): each must match exactly once, so a refactor can't silently skip it.
STORE_PATCHES = [
    # The "Support Development" box at the top of the add-on preferences.
    ("prefs.py", r"[ \t]*self\.draw_support_ui\(layout\)\r?\n[ \t]*layout\.separator\(\)\r?\n", ""),
]


def apply_store_patches(staging):
    for rel, pattern, repl in STORE_PATCHES:
        path = staging / rel
        with open(path, encoding="utf-8", newline="") as f:
            text = f.read()
        text, count = re.subn(pattern, repl, text)
        if count != 1:
            sys.exit(f"Store patch for {rel} matched {count} times (expected 1): update STORE_PATCHES.")
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        print(f"Patched:  {rel} (store build)")


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
    parser.add_argument("--store", action="store_true", help="Build the store copy (no support box in the preferences)")
    args = parser.parse_args()
    out = OUT / "superhive" if args.store else OUT

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
        if args.store:
            apply_store_patches(staging)

        out.mkdir(parents=True, exist_ok=True)
        zip_path = out / f"spwheel-{version}.zip"
        zip_path.unlink(missing_ok=True)
        run([blender, "--factory-startup", "--command", "extension", "build",
             "--source-dir", str(staging), "--output-dir", str(out)])

    run([blender, "--factory-startup", "--command", "extension", "validate", str(zip_path)])

    with zipfile.ZipFile(zip_path) as z:
        names = [n for n in z.namelist() if not n.endswith("/")]
    expected = {rel.split("/", 1)[1] for rel in tracked}
    if set(names) != expected:
        sys.exit(f"Zip contents differ from git-tracked files: {sorted(set(names) ^ expected)[:10]}")

    print(f"Built:    {zip_path}  ({zip_path.stat().st_size / 1e6:.1f} MB, {len(names)} files, validated)")


if __name__ == "__main__":
    main()
