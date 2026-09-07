from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


def active_lines(path: Path):
    """Return non-empty shell/config lines that are not comments."""
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def config_value(path: Path, key: str):
    pattern = re.compile(rf"^(?:#\s+)?{re.escape(key)}=(.*)$")
    value = None
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line.strip())
        if match:
            value = match.group(1)
    return value


class ImmortalWrtBuildInputs(unittest.TestCase):
    def test_smartdns_source_is_not_deleted(self):
        for variant in ("immortalwrt", "official"):
            with self.subTest(variant=variant):
                script = ROOT / variant / "diy-part1.sh"
                removals = [line for line in active_lines(script) if line.startswith("rm -rf feeds/packages/net/")]

                self.assertTrue(removals, "the feed cleanup command should remain visible at the script seam")
                self.assertTrue(
                    all("smartdns" not in line for line in removals),
                    "the selected smartdns package must survive feed cleanup",
                )
                self.assertEqual(
                    config_value(ROOT / variant / "config" / "rockchip.config", "CONFIG_PACKAGE_smartdns"),
                    "y",
                )


class LedeBuildInputs(unittest.TestCase):
    def test_stable_kernel_selection_is_not_overridden_by_testing_kernel(self):
        config = ROOT / "lede" / "config" / "rockchip.config"

        self.assertEqual(config_value(config, "CONFIG_LINUX_6_12"), "y")
        self.assertNotEqual(
            config_value(config, "CONFIG_TESTING_KERNEL"),
            "y",
            "testing-kernel selection overrides the requested stable 6.12 kernel",
        )


class OfficialBuildInputs(unittest.TestCase):
    def test_official_golang_feed_is_kept_for_containerd_compatibility(self):
        lines = active_lines(ROOT / "official" / "diy-part1.sh")

        self.assertNotIn(
            "rm -rf feeds/packages/lang/golang",
            lines,
            "the official golang feed must not be replaced by an older third-party feed",
        )
        self.assertNotIn(
            "git clone https://github.com/kenzok8/golang feeds/packages/lang/golang",
            lines,
            "containerd must use the toolchain selected by the official OpenWrt feed",
        )


if __name__ == "__main__":
    unittest.main()
