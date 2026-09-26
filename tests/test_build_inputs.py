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


FIXTURES = ROOT / "tests" / "fixtures"


def repair_upstream_patches(checkout: Path):
    subprocess.run(
        [sys.executable, str(ROOT / "lede" / "repair_upstream_patches.py"), str(checkout)],
        check=True,
    )


def assert_hunk_headers_match_bodies(test, patch_text: str):
    """Every `@@ -a,b +c,d @@` header must count exactly the lines it claims.

    `patch(1)`/`git apply` reject a unified diff whose hunk headers disagree with
    their bodies, which is the failure mode of editing a patch file.
    """
    old_left = new_left = 0
    header = None
    for line in patch_text.splitlines():
        headline = re.match(r"^@@ -(\d+),(\d+) \+(\d+),(\d+) @@", line)
        if headline:
            test.assertEqual(
                (old_left, new_left), (0, 0),
                f"hunk header {header!r} claims fewer lines than its body has",
            )
            header = line
            old_left, new_left = int(headline.group(2)), int(headline.group(4))
            continue

        marker = line[:1]
        if (old_left, new_left) == (0, 0):
            test.assertFalse(
                line.startswith((" ", "+")) and not line.startswith(("+++ ", "--- ")),
                f"diff line outside any hunk: {line!r}",
            )
        elif marker == " ":
            old_left -= 1
            new_left -= 1
        elif marker == "-":
            old_left -= 1
        elif marker == "+":
            new_left -= 1
        elif marker != "\\":
            test.fail(f"malformed hunk body line: {line!r}")

    test.assertEqual((old_left, new_left), (0, 0), f"hunk header {header!r} over-claims lines")


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

    def test_vim_fuller_does_not_clash_with_vim_runtime(self):
        config = ROOT / "lede" / "config" / "rockchip.config"
        # vim 8.2 (coolsnowwolf/packages) bundles runtime in vim-fuller install:
        #   $(CP) $(PKG_INSTALL_DIR)/usr/share/vim/vim$(VIMVER) $(1)/usr/share/vim
        # Selecting vim-runtime alongside vim-fuller causes opkg file clash
        #   check_data_file_clashes: Package vim-runtime wants to install file .../vim82/...
        #   But that file is already provided by package * vim-fuller (logs_93037651892:13969, 1166 errors)
        if config_value(config, "CONFIG_PACKAGE_vim-fuller") == "y":
            self.assertNotEqual(
                config_value(config, "CONFIG_PACKAGE_vim-runtime"),
                "y",
                "vim-fuller (8.2) already bundles runtime files; selecting vim-runtime as well "
                "causes 1166 check_data_file_clashes at package/install (logs_93037651892:13969)",
            )

    def test_vim_fuller_runtime_build_is_patched(self):
        # Build/Compile/vim-runtime only runs when CONFIG_PACKAGE_vim-runtime or vim-help is y.
        # With only vim-fuller=y, installrtbase never ran and vim-fuller install failed:
        #   cp: cannot stat .../vim82/ipkg-install/usr/share/vim/vim82: No such file or directory
        #   (logs_92971291339:12461)
        # Fix: lede/diy-part1.sh must patch Makefile guard to also trigger on vim-fuller.
        script = (ROOT / "lede" / "diy-part1.sh").read_text(encoding="utf-8")
        self.assertIn(
            "CONFIG_PACKAGE_vim-fuller",
            script,
            "lede/diy-part1.sh must patch feeds/packages/utils/vim/Makefile so that "
            "Build/Compile/vim-runtime runs even when only vim-fuller is selected "
            "(fixes logs_92971291339 without reintroducing logs_93037651892 clash)",
        )
        self.assertIn(
            "feeds/packages/utils/vim/Makefile",
            script,
            "vim fix must target feeds/packages/utils/vim/Makefile",
        )


class UpstreamPatchRepairs(unittest.TestCase):
    GN_PATCH_NAME = "030-fix-clang-18-and-earlier-expected.patch"
    GN_REPAIR_CALL = 'python3 "$GITHUB_WORKSPACE/lede/repair_upstream_patches.py" .'

    def stage_gn_patch(self, fixture: str) -> Path:
        temporary_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_dir.cleanup)
        patch = (
            Path(temporary_dir.name)
            / "feeds/helloworld/gn/patches"
            / self.GN_PATCH_NAME
        )
        patch.parent.mkdir(parents=True)
        patch.write_bytes((FIXTURES / fixture).read_bytes())
        return patch

    def test_gn_result_fallback_gains_constrained_conversion(self):
        # helloworld's gn package patches gn's std::expected fallback `Result<T>`
        # with value constructors only (`Result(const T&)`, `Result(T&&)`).
        # Returning a lambda from a function declared `Result<std::function<...>>`
        # then requires two user-defined conversions (lambda -> std::function ->
        # Result), which C++ rejects, so the gn host build dies on clang 18 and
        # earlier (whose standard library never takes the std::expected branch):
        #   error: no viable conversion from returned value of type '(lambda at
        #   ../src/gn/edit_subcommands.cc:73:12)' to function return type
        #   'Result<ParseNodeGenerator>'   (logs_97647408555:12266)
        # The repaired patch must apply the fix upstream shipped in
        # fw876/helloworld@69fd3c8e ("gn: fix converting constructors in Result
        # fallback").
        patch = self.stage_gn_patch("gn-030-result-fallback-broken.patch")
        fixed = (FIXTURES / "gn-030-result-fallback-fixed.patch").read_bytes()

        repair_upstream_patches(patch.parents[4])
        repaired = patch.read_bytes()

        self.assertIn(b"std::in_place_type<T>", repaired)
        self.assertIn(b"+#include <type_traits>", repaired)
        assert_hunk_headers_match_bodies(self, repaired.decode("utf-8"))
        self.assertEqual(
            repaired.split(b"--- a/", 1)[1],
            fixed.split(b"--- a/", 1)[1],
            "the repaired patch must match the upstream fix byte for byte",
        )

    def test_gn_result_fallback_repair_is_idempotent(self):
        for fixture in (
            "gn-030-result-fallback-broken.patch",
            "gn-030-result-fallback-fixed.patch",
        ):
            with self.subTest(fixture=fixture):
                patch = self.stage_gn_patch(fixture)
                checkout = patch.parents[4]

                repair_upstream_patches(checkout)
                once_repaired = patch.read_bytes()
                repair_upstream_patches(checkout)

                self.assertEqual(once_repaired, patch.read_bytes())

    def test_gn_result_fallback_repair_ignores_a_checkout_without_feeds(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repair_upstream_patches(Path(temp_dir))

    def test_gn_result_fallback_repair_runs_after_feed_update(self):
        # gn ships that fallback patch inside the helloworld feed, so the feed has
        # to be cloned before the repair can reach it.
        for variant in ("lede", "official", "immortalwrt"):
            with self.subTest(variant=variant):
                lines = active_lines(ROOT / variant / "diy-part1.sh")
                self.assertIn("./scripts/feeds update -a", lines)
                self.assertIn(self.GN_REPAIR_CALL, lines)
                self.assertGreater(
                    max(index for index, line in enumerate(lines) if line == self.GN_REPAIR_CALL),
                    lines.index("./scripts/feeds update -a"),
                    "the gn Result fallback repair must run after the feeds are cloned",
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
