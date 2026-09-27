from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "ari_smart_ro_app" / "lib"
DASHBOARD = APP / "screens" / "dashboard" / "dashboard_screen.dart"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"Expected pattern not found for {label}")
    return text.replace(old, new, 1)


def patch_dashboard() -> None:
    text = DASHBOARD.read_text(encoding="utf-8")

    text = replace_once(
        text,
        "    final isWindows = defaultTargetPlatform == TargetPlatform.windows;\n    final items = allItems",
        "    final isWindows = defaultTargetPlatform == TargetPlatform.windows;\n"
        "    final useWindowsDesktopLayout =\n"
        "        isWindows && MediaQuery.sizeOf(context).width >= 980;\n"
        "    final items = allItems",
        "responsive breakpoint",
    )
    text = replace_once(
        text,
        "        appBar: isWindows ? null : AppBar(",
        "        appBar: useWindowsDesktopLayout ? null : AppBar(",
        "responsive app bar",
    )
    text = replace_once(
        text,
        "        body: isWindows\n            ? _buildWindowsDashboard(items: items, isCustomer: isCustomer)\n            : RefreshIndicator(",
        "        body: useWindowsDesktopLayout\n"
        "            ? _buildWindowsDashboard(items: items, isCustomer: isCustomer)\n"
        "            : RefreshIndicator(",
        "responsive body",
    )

    # Desktop dashboard InkWells are explicit interactive surfaces. Give them a
    # Windows-native hand cursor so clickability is obvious.
    text = text.replace(
        "child: InkWell(\n",
        "child: InkWell(\n              mouseCursor: SystemMouseCursors.click,\n",
    )
    text = text.replace(
        "return MouseRegion(\n      onEnter:",
        "return MouseRegion(\n      cursor: SystemMouseCursors.click,\n      onEnter:",
    )

    DASHBOARD.write_text(text, encoding="utf-8")


def patch_clickable_inkwells() -> None:
    """Add click cursors to remaining obvious InkWell(onTap: ...) surfaces.

    Flutter buttons already provide their own pointer cursors. This only touches
    InkWell blocks with an onTap callback and leaves disabled/non-clickable
    InkWells unchanged.
    """
    for path in APP.rglob("*.dart"):
        if path == DASHBOARD:
            continue
        text = path.read_text(encoding="utf-8")
        original = text
        lines = text.splitlines(keepends=True)
        out = []
        i = 0
        while i < len(lines):
            line = lines[i]
            out.append(line)
            if "InkWell(" in line:
                preview = "".join(lines[i : min(i + 24, len(lines))])
                if "onTap:" in preview and "mouseCursor:" not in preview:
                    indent = re.match(r"\s*", line).group(0) + "  "
                    out.append(f"{indent}mouseCursor: SystemMouseCursors.click,\n")
            i += 1
        updated = "".join(out)
        if updated != original:
            path.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    patch_dashboard()
    patch_clickable_inkwells()
    print("Applied Windows responsive breakpoint and pointer-cursor patch.")
