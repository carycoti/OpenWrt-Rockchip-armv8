"""Repair known transient defects in a freshly cloned LEDE source tree."""

from pathlib import Path
import sys


def repair_yt921x_patch(source_root: Path) -> None:
    patch = source_root / "target/linux/rockchip/patches-6.18/0130-net-dsa-add-motorcomm-yt921x.patch"
    if not patch.is_file():
        return

    content = patch.read_text(encoding="utf-8")
    repaired = "".join(
        line.replace(r"\t", "\t") if "DSA_TAG_PROTO_" in line else line
        for line in content.splitlines(keepends=True)
    )
    if repaired != content:
        patch.write_text(repaired, encoding="utf-8")


if __name__ == "__main__":
    repair_yt921x_patch(Path(sys.argv[1] if len(sys.argv) > 1 else "."))
