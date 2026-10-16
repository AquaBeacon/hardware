"""Audit footprint existence and pad coverage for all active AquaBeacon boards.

Run with KiCad's bundled Python.  This imports build scripts with a stubbed
build() function, so no generated KiCad files are modified.
"""
from __future__ import annotations

import importlib.util
import sys
import types
from collections import defaultdict
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from pcbgen import load_footprint  # noqa: E402


BOARDS = (
    "build_child_main",
    "build_parent_main",
    "build_child_pwr",
    "build_parent_pwr",
    "build_tx_improved",
    "build_tx_advanced",
    "build_rx_improved",
    "build_rx_improved_mini",
    "build_rx_advanced",
    "build_rx_advanced_mini",
)


def load_parts(module_name: str):
    captured = {}

    def build(board_name, parts, *args, **kwargs):
        captured["board"] = board_name
        captured["parts"] = parts
        return True, None

    old = sys.modules.get("buildlib")
    stub = types.ModuleType("buildlib")
    stub.build = build
    sys.modules["buildlib"] = stub
    try:
        spec = importlib.util.spec_from_file_location(module_name, HERE / f"{module_name}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        if old is None:
            del sys.modules["buildlib"]
        else:
            sys.modules["buildlib"] = old
    return captured["board"], captured["parts"]


def footprint_pads(fpid: str):
    fp = load_footprint(fpid)
    if fp is None:
        return None
    return {pad.GetPadName() for pad in fp.Pads()}


def main() -> int:
    errors = 0
    footprint_uses = defaultdict(list)
    selected = tuple(sys.argv[1:]) or BOARDS
    unknown = sorted(set(selected) - set(BOARDS))
    if unknown:
        print(f"Unknown board modules: {unknown}")
        return 2
    for module_name in selected:
        board, parts = load_parts(module_name)
        by_ref = {}
        for part in parts:
            footprint_uses[part.footprint].append((board, part.ref, part.value))
            if part.ref in by_ref:
                prev = by_ref[part.ref]
                if part.footprint != prev.footprint:
                    print(f"ERROR {board} {part.ref}: units use different footprints")
                    errors += 1
                prev.pins.update(part.pins)
            else:
                by_ref[part.ref] = part

        for ref, part in sorted(by_ref.items()):
            pads = footprint_pads(part.footprint)
            if pads is None:
                print(f"ERROR {board} {ref}: footprint not found: {part.footprint}")
                errors += 1
                continue
            required = {str(pin) for pin in part.pins}
            missing = sorted(required - pads)
            if missing:
                print(f"ERROR {board} {ref}: missing pads {missing} in {part.footprint}")
                errors += 1

        print(f"PASS {board}: {len(by_ref)} refs, footprint files and mapped pads present")

    print(f"UNIQUE_FOOTPRINTS {len(footprint_uses)}")
    for fpid, uses in sorted(footprint_uses.items()):
        examples = ", ".join(f"{b}:{r}={v}" for b, r, v in uses[:4])
        suffix = f" (+{len(uses) - 4})" if len(uses) > 4 else ""
        print(f"  {fpid}: {examples}{suffix}")
    print(f"RESULT {'PASS' if errors == 0 else 'FAIL'} errors={errors}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
