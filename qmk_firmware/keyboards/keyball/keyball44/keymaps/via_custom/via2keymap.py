#!/usr/bin/env python3
"""
via2keymap.py - Convert VIA backup JSON to keymap.c for Keyball44.

Usage:
    python3 via2keymap.py [--via-backup FILE] [--via-def FILE] [--keymap FILE] [--dry-run]

Reads a VIA backup JSON (exported from usevia.app), converts matrix-order
keycodes to LAYOUT_universal argument order, resolves CUSTOM(N) to actual
keycode names, and patches the keymaps[][] array in keymap.c in-place.
Code outside the keymaps array (custom functions, OLED, etc.) is preserved.
"""

from __future__ import annotations

import json
import re
import sys
import argparse
from pathlib import Path
from typing import Dict, List

SCRIPT_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Matrix-order (VIA backup) → LAYOUT_universal argument order
#
# VIA stores 48 keys per layer in matrix order (row 0-7, cols 0-5).
# LAYOUT_no_ball (= LAYOUT_universal) expects:
#   L00..L05,  R05..R00,   (row 0: left then right-reversed)
#   L10..L15,  R15..R10,   (row 1)
#   L20..L25,  R25..R20,   (row 2)
#   L31..L35,  R35..R31    (row 3 thumb: skip col0=KC_NO on each half)
# ---------------------------------------------------------------------------

# VIA backup indices for each LAYOUT_universal argument position
LAYOUT_INDEX_MAP = [
    # Row 0: left 6 keys, then right 6 keys (reversed)
    0, 1, 2, 3, 4, 5,      29, 28, 27, 26, 25, 24,
    # Row 1
    6, 7, 8, 9, 10, 11,    35, 34, 33, 32, 31, 30,
    # Row 2
    12, 13, 14, 15, 16, 17, 41, 40, 39, 38, 37, 36,
    # Row 3 thumb (skip idx 18 and 42 which are KC_NO padding)
    19, 20, 21, 22, 23,     47, 46, 45, 44, 43,
]

# How many keys per LAYOUT_universal row (for formatting)
ROW_SIZES = [12, 12, 12, 10]  # 6+6, 6+6, 6+6, 5+5
LEFT_COUNTS = [6, 6, 6, 5]

# ---------------------------------------------------------------------------
# VIA keycode alias → QMK C keycode normalization
# ---------------------------------------------------------------------------

VIA_ALIAS_MAP = {
    "KC_MS_BTN1": "KC_BTN1",
    "KC_MS_BTN2": "KC_BTN2",
    "KC_MS_BTN3": "KC_BTN3",
    "KC_MS_BTN4": "KC_BTN4",
    "KC_MS_BTN5": "KC_BTN5",
    "KC_HANJ":    "KC_LNG2",
    "KC_HAEN":    "KC_LNG1",
    "KC_RO":      "KC_INT1",
    "KC_JYEN":    "KC_INT3",
}


def load_custom_keycodes(via_def_path: Path) -> dict[int, str]:
    """Load CUSTOM(N) → keycode name mapping from via_v3.json."""
    with open(via_def_path) as f:
        via_def = json.load(f)
    mapping = {}
    for i, entry in enumerate(via_def.get("customKeycodes", [])):
        mapping[i] = entry["name"]
    return mapping


def normalize_keycode(kc: str, custom_map: dict[int, str]) -> str:
    """Normalize a single VIA keycode string to QMK C form."""

    # CUSTOM(N) → actual keycode name
    m = re.match(r"^CUSTOM\((\d+)\)$", kc)
    if m:
        idx = int(m.group(1))
        if idx in custom_map:
            return custom_map[idx]
        return f"/* CUSTOM({idx}) UNKNOWN */"

    # KC_TRNS → _______
    if kc == "KC_TRNS":
        return "_______"

    # Remove spaces inside MOD expressions: "MOD_LCTL | MOD_RCTL" → "MOD_LCTL|MOD_RCTL"
    if " | " in kc:
        kc = kc.replace(" | ", "|")

    # Simple alias replacement (applied recursively inside wrapper macros too)
    for via_name, qmk_name in VIA_ALIAS_MAP.items():
        kc = kc.replace(via_name, qmk_name)

    # MT(MOD_LCTL,KC_TAB) → LCTL_T(KC_TAB) shorthand (optional, cosmetic)
    m = re.match(r"^MT\(MOD_LCTL,(.+)\)$", kc)
    if m:
        kc = f"LCTL_T({m.group(1)})"

    return kc


def via_layer_to_layout(layer: list[str], custom_map: dict[int, str]) -> list[str]:
    """Reorder a VIA matrix-order layer to LAYOUT_universal argument order."""
    return [normalize_keycode(layer[i], custom_map) for i in LAYOUT_INDEX_MAP]


def format_layer(layer_idx: int, keys: list[str], comment: str = "") -> str:
    """Format a single layer as C code for LAYOUT_universal."""
    lines = []
    if comment:
        for cl in comment.strip().split("\n"):
            lines.append(f"  {cl}")
    lines.append(f"  [{layer_idx}] = LAYOUT_universal(")

    pos = 0
    for row_i, (row_size, left_n) in enumerate(zip(ROW_SIZES, LEFT_COUNTS)):
        right_n = row_size - left_n
        row_keys = keys[pos:pos + row_size]
        left_keys = row_keys[:left_n]
        right_keys = row_keys[left_n:]

        # Pad each keycode to consistent width for alignment
        col_width = 9

        # Build left side
        if row_i == 3:
            # Thumb row: extra indent to skip missing col0
            left_parts = [f"{k:>{col_width}}" for k in left_keys]
            left_str = "          " + ", ".join(left_parts)
        else:
            left_parts = [f"{k:>{col_width}}" for k in left_keys]
            left_str = "    " + ", ".join(left_parts)

        # Build right side
        right_parts = [f"{k:>{col_width}}" for k in right_keys]
        right_str = ", ".join(right_parts)

        # Determine separator
        is_last_row = (row_i == len(ROW_SIZES) - 1)
        trailing = "" if is_last_row else ","
        # Gap between left and right
        gap = "  "
        line = f"{left_str},{gap}{right_str}{trailing}"
        lines.append(line)
        pos += row_size

    lines.append("  ),")
    return "\n".join(lines)


# Default layer comments
LAYER_COMMENTS = {
    0: "// Layer 0: Base (QWERTY)",
    1: "// Layer 1: Auto Mouse Layer",
    2: "// Layer 2: Numbers + Arrows",
    3: "// Layer 3: Symbols",
}


def generate_keymaps_block(layers: list[list[str]], custom_map: dict[int, str]) -> str:
    """Generate the full keymaps[][] C block from VIA layers."""
    parts = []
    parts.append("// clang-format off")
    parts.append("const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {")

    for i, layer in enumerate(layers):
        if i > 0:
            parts.append("")
        layout_keys = via_layer_to_layout(layer, custom_map)
        comment = LAYER_COMMENTS.get(i, f"// Layer {i}")
        parts.append(format_layer(i, layout_keys, comment))

    parts.append("};")
    parts.append("// clang-format on")
    return "\n".join(parts)


def patch_keymap_c(keymap_path: Path, new_block: str) -> str:
    """Replace the keymaps array in keymap.c, preserving surrounding code."""
    content = keymap_path.read_text()

    # Match from "// clang-format off" before keymaps to "// clang-format on" after
    pattern = re.compile(
        r"// clang-format off\n"
        r"const uint16_t PROGMEM keymaps\[\]\[MATRIX_ROWS\]\[MATRIX_COLS\] = \{.*?\};\n"
        r"// clang-format on",
        re.DOTALL,
    )
    m = pattern.search(content)
    if not m:
        print("ERROR: Could not find keymaps[][] block in keymap.c", file=sys.stderr)
        sys.exit(1)

    return content[:m.start()] + new_block + content[m.end():]


def main():
    parser = argparse.ArgumentParser(description="Convert VIA backup JSON to keymap.c")
    parser.add_argument("--via-backup", type=Path,
                        default=SCRIPT_DIR / "via_backup.json",
                        help="Path to VIA backup JSON (default: via_backup.json)")
    parser.add_argument("--via-def", type=Path,
                        default=SCRIPT_DIR / "via_v3.json",
                        help="Path to VIA definition JSON with customKeycodes (default: via_v3.json)")
    parser.add_argument("--keymap", type=Path,
                        default=SCRIPT_DIR / "keymap.c",
                        help="Path to keymap.c to patch (default: keymap.c)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the generated keymaps block without writing")
    args = parser.parse_args()

    # Load inputs
    with open(args.via_backup) as f:
        via_backup = json.load(f)
    custom_map = load_custom_keycodes(args.via_def)

    layers = via_backup["layers"]
    print(f"Loaded {len(layers)} layers from {args.via_backup.name}")
    print(f"Loaded {len(custom_map)} custom keycodes from {args.via_def.name}")

    # Generate
    new_block = generate_keymaps_block(layers, custom_map)

    if args.dry_run:
        print("\n--- Generated keymaps block ---")
        print(new_block)
        return

    # Patch keymap.c
    new_content = patch_keymap_c(args.keymap, new_block)
    args.keymap.write_text(new_content)
    print(f"Patched {args.keymap.name} successfully.")


if __name__ == "__main__":
    main()
