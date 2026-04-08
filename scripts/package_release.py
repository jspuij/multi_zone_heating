"""Package the custom integration as a release artifact."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        default="dist",
        help="Directory where the release archive will be written.",
    )
    return parser.parse_args()


def write_github_output(name: str, value: str) -> None:
    """Write a step output when running inside GitHub Actions."""
    github_output = os.environ.get("GITHUB_OUTPUT")
    if not github_output:
        return

    with open(github_output, "a", encoding="utf-8") as output_file:
        output_file.write(f"{name}={value}\n")


def main() -> None:
    """Build a zip archive for the integration."""
    args = parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    manifest_path = repo_root / "custom_components" / "multi_zone_heating" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    domain = manifest["domain"]
    version = manifest["version"]
    component_dir = manifest_path.parent
    output_dir = repo_root / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    archive_name = f"{domain}-{version}.zip"
    archive_path = output_dir / archive_name

    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
        for file_path in sorted(component_dir.rglob("*")):
            if file_path.is_file():
                archive.write(file_path, file_path.relative_to(repo_root))

    print(f"Created {archive_path}")
    write_github_output("archive_name", archive_name)
    write_github_output("archive_path", str(archive_path))
    write_github_output("version", version)


if __name__ == "__main__":
    main()
