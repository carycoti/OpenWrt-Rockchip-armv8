"""Repair known transient defects in a freshly cloned OpenWrt source tree.

The repairs are idempotent, so the script can run before and after
`./scripts/feeds update -a`: feed patches only show up once the feeds are cloned.
"""

from pathlib import Path
import re
import sys


def repair_yt921x_patch(source_root: Path) -> None:
    patch = source_root / "target/linux/rockchip/patches-6.18/0130-net-dsa-add-motorcomm-yt921x.patch"
    if not patch.is_file():
        return

    content = patch.read_bytes().decode("utf-8")
    repaired = "".join(
        line.replace(r"\t", "\t") if "DSA_TAG_PROTO_" in line else line
        for line in content.splitlines(keepends=True)
    )
    if repaired != content:
        patch.write_bytes(repaired.encode("utf-8"))


# gn's `Result<T>` fallback - the branch taken when the standard library has no
# std::expected, i.e. clang 18 and earlier - was shipped with value constructors
# only. `return <lambda>;` from a function declared `Result<std::function<...>>`
# then needs two user-defined conversions (lambda -> std::function -> Result)
# and C++ rejects that chain, so the gn host build dies on:
#   error: no viable conversion from returned value of type '(lambda at
#   ../src/gn/edit_subcommands.cc:73:12)' to function return type
#   'Result<ParseNodeGenerator>'                                (logs_97647408555)
# The repair adds the constrained converting constructor upstream shipped in
# fw876/helloworld@69fd3c8e ("gn: fix converting constructors in Result
# fallback"). It edits the feed patch in place instead of replacing it, so the
# patch keeps matching the gn revision it was written against.
GN_FALLBACK_PATCH_GLOB = "feeds/*/gn/patches/*.patch"
GN_FALLBACK_STORAGE = "+  std::variant<T, Err> storage_;"
GN_FALLBACK_VALUE_ANCHOR = "+  Result(T&& value) : storage_(std::move(value)) {}"
GN_FALLBACK_INCLUDE_ANCHOR = " #include <utility>"
GN_RESULT_CONVERSION_MARKER = "std::in_place_type<T>"
GN_RESULT_CONVERSION = (
    "+  // Match std::expected's converting constructor without requiring two",
    "+  // user-defined conversions (for example, lambda -> std::function -> Result).",
    "+  template <typename U>",
    "+    requires(!std::is_same_v<std::remove_cvref_t<U>, Result> &&",
    "+             !std::is_same_v<std::remove_cvref_t<U>, Err> &&",
    "+             std::is_constructible_v<T, U&&>)",
    "+  explicit(!std::is_convertible_v<U&&, T>) Result(U&& value)",
    "+      : storage_(std::in_place_type<T>, std::forward<U>(value)) {}",
    "+",
)
GN_TYPE_TRAITS_LINE = "+#include <type_traits>"

HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")


def repair_gn_result_fallback(source_root: Path) -> None:
    for patch in sorted(source_root.glob(GN_FALLBACK_PATCH_GLOB)):
        repair_gn_result_fallback_patch(patch)


def repair_gn_result_fallback_patch(patch: Path) -> bool:
    """Repair one feed patch; returns True when the file was rewritten."""
    content = patch.read_bytes().decode("utf-8")
    repaired = add_constrained_result_conversion(content)
    if repaired == content:
        return False
    patch.write_bytes(repaired.encode("utf-8"))
    return True


def add_constrained_result_conversion(content: str) -> str:
    """Add the converting constructor to gn's fallback `Result<T>` patch hunk.

    Returns `content` unchanged when the patch carries no fallback `Result<T>`,
    when the constructor is already present, or when the fallback no longer
    matches the shape this repair knows about.
    """
    if GN_FALLBACK_STORAGE not in content or GN_RESULT_CONVERSION_MARKER in content:
        return content

    lines = content.splitlines(keepends=True)
    hunks = _parse_hunks(lines)
    for hunk in hunks:
        anchor = _find_line(hunk["body"], GN_FALLBACK_VALUE_ANCHOR)
        if anchor is None:
            continue
        body = hunk["body"]
        ending = _line_ending(body[anchor])
        block = list(GN_RESULT_CONVERSION)
        position = anchor + 1
        if position < len(body) and body[position].rstrip("\r\n") == "+":
            position += 1
        else:
            block.insert(0, "+")
        body[position:position] = [line + ending for line in block]
        if "#include <type_traits>" not in content:
            _insert_include(hunks)
        return _render_patch(lines, hunks)

    print(
        f"warning: {GN_FALLBACK_STORAGE.strip()} found but not the value constructor "
        f"anchor {GN_FALLBACK_VALUE_ANCHOR.strip()!r}; leaving the patch unchanged",
        file=sys.stderr,
    )
    return content


def _insert_include(hunks) -> None:
    """Add <type_traits> (used by the constrained constructor) to the patch."""
    for hunk in hunks:
        include = _find_line(hunk["body"], GN_FALLBACK_INCLUDE_ANCHOR)
        if include is not None:
            ending = _line_ending(hunk["body"][include])
            hunk["body"].insert(include, GN_TYPE_TRAITS_LINE + ending)
            return


def _parse_hunks(lines):
    """Split `lines` into unified diff hunks, using the declared hunk counts."""
    hunks = []
    index = 0
    while index < len(lines):
        header = HUNK_HEADER.match(lines[index])
        if header is None:
            index += 1
            continue
        old_left = int(header.group(2) or 1)
        new_left = int(header.group(4) or 1)
        body = []
        cursor = index + 1
        while cursor < len(lines) and (old_left > 0 or new_left > 0):
            marker = lines[cursor][:1]
            if marker == " ":
                old_left -= 1
                new_left -= 1
            elif marker == "-":
                old_left -= 1
            elif marker == "+":
                new_left -= 1
            elif marker != "\\":
                break
            body.append(lines[cursor])
            cursor += 1
        if old_left or new_left:
            raise ValueError(f"malformed hunk header on line {index + 1}")

        hunks.append(
            {
                "header_index": index,
                "header_tail": header.group(5),
                "old_start": int(header.group(1)),
                "new_start": int(header.group(3)),
                "old_count": int(header.group(2) or 1),
                "new_count": int(header.group(4) or 1),
                "body": body,
                "body_length": cursor - index - 1,
            }
        )
        index = cursor
    return hunks


def _render_patch(lines, hunks):
    """Rewrite hunk headers from the (edited) bodies and splice the patch back.

    Hunk start offsets are absolute line numbers of the file being patched, so a
    hunk that gained lines shifts every following hunk by that amount.
    """
    rewritten = {}
    old_shift = new_shift = 0
    for hunk in hunks:
        old_count = sum(1 for line in hunk["body"] if line[:1] in (" ", "-"))
        new_count = sum(1 for line in hunk["body"] if line[:1] in (" ", "+"))
        hunk["old_start"] += old_shift
        hunk["new_start"] += new_shift
        old_shift += old_count - hunk["old_count"]
        new_shift += new_count - hunk["new_count"]

        ending = lines[hunk["header_index"]][len(lines[hunk["header_index"]].rstrip("\r\n")):]
        rewritten[hunk["header_index"]] = (
            f"@@ -{hunk['old_start']},{old_count} +{hunk['new_start']},{new_count} @@"
            f"{hunk['header_tail']}{ending}",
            hunk["body"],
            hunk["body_length"],
        )

    output = []
    index = 0
    while index < len(lines):
        replacement = rewritten.get(index)
        if replacement is None:
            output.append(lines[index])
            index += 1
            continue
        header, body, skipped = replacement
        output.append(header)
        output.extend(body)
        index += 1 + skipped
    return "".join(output)


def _find_line(lines, needle):
    for index, line in enumerate(lines):
        if line[:len(needle)] == needle:
            return index
    return None


def _line_ending(line: str) -> str:
    return line[len(line.rstrip("\r\n")):]


if __name__ == "__main__":
    source_root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    repair_yt921x_patch(source_root)
    repair_gn_result_fallback(source_root)