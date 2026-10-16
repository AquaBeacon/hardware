"""回路記述 -> 回路図生成 -> ERC -> ネットリスト -> 照合 -> PCB生成 -> DRC の一括フロー。
KiCad同梱python (pcbnewが要る) で実行すること。"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from kicadgen import Part, Schematic, write_project, KICAD_CLI, parse, tokenize  # noqa: E402
import pcbgen  # noqa: E402


def run(args):
    return subprocess.run(args, capture_output=True, text=True,
                          encoding='utf-8', errors='replace')


def parse_netlist_nets(net_text):
    root = parse(tokenize(net_text))[0]
    got = {}
    for node in root:
        if isinstance(node, list) and node and node[0] == 'nets':
            for net in node[1:]:
                name, nodes = None, set()
                for e in net:
                    if isinstance(e, list) and e:
                        if e[0] == 'name':
                            name = e[1].strip('"').lstrip('/')
                        elif e[0] == 'node':
                            ref = pin = None
                            for f in e:
                                if isinstance(f, list) and f:
                                    if f[0] == 'ref':
                                        ref = f[1].strip('"')
                                    elif f[0] == 'pin':
                                        pin = f[1].strip('"')
                            nodes.add((ref, pin))
                got[name] = nodes
    return got


def drc_summary(report_text):
    m1 = re.search(r'\*\* Found (\d+) DRC violations \*\*', report_text)
    m2 = re.search(r'\*\* Found (\d+) unconnected pads \*\*', report_text)
    viol = int(m1.group(1)) if m1 else None
    unconn = int(m2.group(1)) if m2 else None
    return viol, unconn


def build(name, parts, placements, board_rect, tracks=(), vias=(),
          power_flag_nets=('GND',), values=None, texts=(), render=True,
          sch_wires=(), sch_junctions=(), gnd_symbol=True, sch_labels=None,
          seed_tracks=(), seed_vias=(), min_clearance=0.2, route_first=(),
          sch_texts=(), sch_blocks=()):
    outdir = HERE / name
    sch = Schematic(name, parts, power_flag_nets=power_flag_nets,
                    wires=list(sch_wires), junctions=list(sch_junctions),
                    gnd_symbol=gnd_symbol, labels_at=dict(sch_labels or {}),
                    texts=list(sch_texts), blocks=list(sch_blocks))
    sch_file = write_project(outdir, name, sch)
    print(f'[{name}] schematic written')

    # ERC
    erc_rpt = outdir / 'erc.rpt'
    r = run([KICAD_CLI, 'sch', 'erc', str(sch_file), '-o', str(erc_rpt),
             '--severity-error', '--exit-code-violations'])
    erc_text = erc_rpt.read_text(encoding='utf-8', errors='replace')
    if r.returncode != 0:
        # 許容例外: 同一シンボル内のピン同士の pin_to_pin (例: PicoモジュールのGNDとAGND。
        # モジュール内部で結ばれた power output 同士を同一ネットにすると必ず出る)
        blocks = re.split(r'\n(?=\[)', erc_text)
        real = []
        for b in blocks:
            m = re.match(r'\[(\w+)\]', b)
            if not m:
                continue
            refs = set(re.findall(r'Symbol (\S+) Pin', b))
            if m.group(1) == 'pin_to_pin' and len(refs) == 1:
                continue
            real.append(b)
        if real:
            print(erc_text)
            raise SystemExit(f'[{name}] ERC FAILED')
        print(f'[{name}] ERC passed (同一シンボル内pin_to_pinのみ・許容)')
    else:
        print(f'[{name}] ERC passed')

    # netlist
    net_file = outdir / f'{name}.net'
    r = run([KICAD_CLI, 'sch', 'export', 'netlist', str(sch_file), '-o', str(net_file)])
    assert r.returncode == 0, r.stderr

    # 照合
    want = sch.net_map()
    got = parse_netlist_nets(net_file.read_text(encoding='utf-8'))
    for net, nodes in want.items():
        assert got.get(net, set()) == nodes, \
            f'[{name}] net mismatch {net}: want={sorted(nodes)} got={sorted(got.get(net, set()))}'
    print(f'[{name}] netlist matches intent ({len(want)} nets)')

    # PCB
    pcb_file = outdir / f'{name}.kicad_pcb'
    vals = {p.ref: p.value for p in parts}
    if values:
        vals.update(values)
    pcbgen.build_board(pcb_file, net_file, placements, board_rect,
                       tracks=tracks, vias=vias, values=vals, texts=texts,
                       seed_tracks=seed_tracks, seed_vias=seed_vias,
                       min_clearance=min_clearance, route_first=route_first)
    print(f'[{name}] pcb written')

    # DRC
    drc_rpt = outdir / 'drc.rpt'
    r = run([KICAD_CLI, 'pcb', 'drc', str(pcb_file), '-o', str(drc_rpt),
             '--severity-error', '--exit-code-violations'])
    text = drc_rpt.read_text(encoding='utf-8', errors='replace')
    viol, unconn = drc_summary(text)
    print(f'[{name}] DRC: exit={r.returncode}')
    # 概要行が形式によって無い場合は本文から数える
    if 'violations' not in text:
        pass
    if r.returncode != 0:
        print(text)
    if render:
        png = outdir / f'{name}_render.png'
        run([KICAD_CLI, 'pcb', 'render', str(pcb_file), '-o', str(png),
             '--side', 'top', '--quality', 'basic', '-w', '1200', '-h', '900'])
        print(f'[{name}] render -> {png.name}')
    return r.returncode == 0, text
