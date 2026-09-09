from pathlib import Path
import re
import subprocess
import sys
import tempfile
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
    def test_apk_core_feed_keeps_upstream_packages_index_path(self):
        script = ROOT / "immortalwrt" / "diy-part1.sh"
        script_text = script.read_text(encoding="utf-8")

        self.assertNotIn(
            r"targets/%S/\$(LINUX_VERSION)",
            script_text,
            "the APK core repository must keep the upstream packages index path",
        )

    def test_video_feed_is_compile_only_when_no_runtime_index_is_published(self):
        config = ROOT / "immortalwrt" / "config" / "rockchip.config"

        self.assertEqual(
            config_value(config, "CONFIG_FEED_video"),
            "m",
            "the unpublished video feed must not be emitted in the runtime repository list",
        )

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

    def test_passwall2_uses_official_feeds_and_is_selected(self):
        feed_lines = active_lines(ROOT / "immortalwrt" / "diy-part1.sh")
        config = ROOT / "immortalwrt" / "config" / "rockchip.config"

        self.assertIn(
            "sed -i '$a src-git passwall_packages https://github.com/Openwrt-Passwall/openwrt-passwall-packages.git;main' feeds.conf.default",
            feed_lines,
        )
        self.assertIn(
            "sed -i '$a src-git passwall2 https://github.com/Openwrt-Passwall/openwrt-passwall2.git;main' feeds.conf.default",
            feed_lines,
        )
        self.assertIn("./scripts/feeds install -a -p passwall_packages -f", feed_lines)
        self.assertIn("./scripts/feeds install -a -p passwall2 -f", feed_lines)
        self.assertEqual(config_value(config, "CONFIG_PACKAGE_luci-app-passwall2"), "y")
        self.assertEqual(config_value(config, "CONFIG_PACKAGE_luci-i18n-passwall2-zh-cn"), "y")
        self.assertEqual(config_value(config, "CONFIG_PACKAGE_openwrt-keyring"), "y")
        for feed in ("kiddin9", "passwall_packages", "passwall2"):
            with self.subTest(runtime_feed=feed):
                self.assertEqual(
                    config_value(config, f"CONFIG_FEED_{feed}"),
                    "m",
                    "compile-only feeds must be disabled in the generated runtime repository list",
                )


class LedeBuildInputs(unittest.TestCase):
    def test_official_golang_feed_is_kept_for_hysteria_compatibility(self):
        lines = active_lines(ROOT / "lede" / "diy-part1.sh")

        self.assertNotIn(
            "rm -rf feeds/packages/lang/golang",
            lines,
            "the LEDE Go toolchain must not be replaced by an older third-party feed",
        )
        self.assertNotIn(
            "git clone https://github.com/kenzok8/golang feeds/packages/lang/golang",
            lines,
            "hysteria requires the newer Go toolchain selected by the LEDE packages feed",
        )

    def test_gn_host_build_requires_clang_toolchain(self):
        depends = (ROOT / "lede" / "depends-ubuntu-latest").read_text(encoding="utf-8")
        tokens = depends.split()
        self.assertIn(
            "clang",
            tokens,
            "helloworld/gn host build invokes clang++ (C++23); lede/depends-ubuntu-latest must include clang "
            "or every build selecting naiveproxy/bypass/passwall fails with '/bin/sh: 1: clang++: not found'",
        )

    def test_stable_kernel_selection_is_not_overridden_by_testing_kernel(self):
        config = ROOT / "lede" / "config" / "rockchip.config"

        self.assertEqual(config_value(config, "CONFIG_LINUX_6_12"), "y")
        self.assertNotEqual(
            config_value(config, "CONFIG_TESTING_KERNEL"),
            "y",
            "testing-kernel selection overrides the requested stable 6.12 kernel",
        )

    def test_broken_upstream_patch_escapes_are_normalized(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            checkout = Path(temp_dir)
            patch = checkout / "target/linux/rockchip/patches-6.18/0130-net-dsa-add-motorcomm-yt921x.patch"
            patch.parent.mkdir(parents=True)
            patch.write_text(
                " \\tDSA_TAG_PROTO_MXL862\\t\\t= DSA_TAG_PROTO_MXL862_VALUE,\n"
                "+\\tDSA_TAG_PROTO_YT921X\\t\\t= DSA_TAG_PROTO_YT921X_VALUE,\n"
                '+\tconst char *separator = "\\t";\n',
                encoding="utf-8",
            )

            subprocess.run(
                [sys.executable, str(ROOT / "lede" / "repair_upstream_patches.py"), str(checkout)],
                check=True,
            )

            repaired = patch.read_text(encoding="utf-8")
            self.assertIn("\tDSA_TAG_PROTO_YT921X\t\t=", repaired)
            self.assertIn(r'const char *separator = "\t";', repaired)

    def test_upstream_patch_repair_runs_before_customizations(self):
        lines = active_lines(ROOT / "lede" / "diy-part1.sh")

        self.assertIn(
            'python3 "$GITHUB_WORKSPACE/lede/repair_upstream_patches.py" .',
            lines,
        )

    def test_vim_fuller_requires_vim_runtime(self):
        config = ROOT / "lede" / "config" / "rockchip.config"
        if config_value(config, "CONFIG_PACKAGE_vim-fuller") == "y":
            self.assertEqual(
                config_value(config, "CONFIG_PACKAGE_vim-runtime"),
                "y",
                "vim-fuller install copies $(PKG_INSTALL_DIR)/usr/share/vim/vim$(VIMVER); "
                "without vim-runtime the Build/Compile/vim-runtime step never runs and packaging fails with "
                "'cp: cannot stat .../vim82/ipkg-install/usr/share/vim/vim82' (logs_92971291339:12461)",
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

    def test_gn_host_build_requires_clang_toolchain(self):
        depends = (ROOT / "official" / "depends-ubuntu-latest").read_text(encoding="utf-8")
        tokens = depends.split()
        self.assertIn(
            "clang",
            tokens,
            "helloworld/gn host build invokes clang++ (C++23); official/depends must include clang",
        )


class ImmortalWrtHostToolchain(unittest.TestCase):
    def test_gn_host_build_requires_clang_toolchain(self):
        depends = (ROOT / "immortalwrt" / "depends-ubuntu-latest").read_text(encoding="utf-8")
        tokens = depends.split()
        self.assertIn(
            "clang",
            tokens,
            "helloworld/gn host build invokes clang++ (C++23); immortalwrt/depends must include clang",
        )


class ReleaseMetadata(unittest.TestCase):
    def test_release_uses_resolved_build_kernel_version(self):
        for variant in ("lede", "official", "immortalwrt"):
            with self.subTest(variant=variant):
                workflow = ROOT / ".github" / "workflows" / f"{variant}-builder.yml"
                text = workflow.read_text(encoding="utf-8")
                resolver = 'KERNEL_VERSION="$(make -s --no-print-directory -C target/linux TOPDIR="$PWD" val.LINUX_VERSION)"'

                self.assertIn(resolver, text)
                self.assertLess(
                    text.index("make defconfig"),
                    text.index(resolver),
                    "kernel version must be resolved from the normalized build config",
                )
                self.assertIn(
                    'echo "KERNEL_VERSION=$KERNEL_VERSION" >> "$GITHUB_ENV"',
                    text,
                )
                self.assertIn("内核版本：${{ env.KERNEL_VERSION }}", text)
                self.assertIn("linux-${{ env.KERNEL_VERSION }}-", text)
                self.assertNotIn("linux-6.6-", text)
                self.assertNotRegex(
                    text,
                    r'(?m)^\s*echo "KERNEL_(?:PATCHVER|VERSION)=.*kernel-6\.(?:6|12)',
                    "release metadata must not read a hard-coded kernel series",
                )


if __name__ == "__main__":
    unittest.main()
