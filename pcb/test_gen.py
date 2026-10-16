"""kicadgen の座標変換・形式の検証: 回転0/90/180/270のRと極性部品で
ネットリストが意図どおりに出るかを kicad-cli で確認する。"""
import subprocess, sys, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from kicadgen import Part, Schematic, write_project, KICAD_CLI, parse, tokenize


def parse_netlist_nets(net_text):
    root = parse(tokenize(net_text))[0]
    got = {}
    for node in root:
        if isinstance(node, list) and node and node[0] == 'nets':
            for net in node[1:]:
                name = None
                nodes = set()
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

HERE = Path(__file__).parent
OUT = HERE / '_test'

RFP = 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal'
parts = [
    Part('R1', 'Device', 'R', '1k', RFP, {'1': 'N1', '2': 'N2'}, at=(50, 50), rot=0),
    Part('R2', 'Device', 'R', '1k', RFP, {'1': 'N2', '2': 'N3'}, at=(70, 50), rot=90),
    Part('R3', 'Device', 'R', '1k', RFP, {'1': 'N3', '2': 'N4'}, at=(90, 50), rot=180),
    Part('R4', 'Device', 'R', '1k', RFP, {'1': 'N4', '2': 'GND'}, at=(110, 50), rot=270),
    Part('D1', 'Device', 'D_Zener', 'BZX', 'Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal',
         {'1': 'GND', '2': 'N1'}, at=(130, 50), rot=0),
    Part('U1', 'Comparator', 'TLV3501AIDBV', 'TLV3501', 'Package_TO_SOT_SMD:SOT-23-6',
         {'1': 'N1', '2': 'GND', '3': 'N2', '4': 'V3A', '5': 'N3', '6': 'N4'}, at=(160, 60), rot=0),
]
sch = Schematic('testgen', parts, power_flag_nets=('GND', 'V3A'),
                # 注記・機能ブロック枠(グラフィックのみ。ネットには影響しないこと)
                blocks=[(40, 35, 145, 65, 'SIGNAL CHAIN'),
                        (150, 45, 185, 75, 'COMPARATOR')],
                texts=[(42, 70, 'R1-R4: divider chain'),
                       (42, 74, 'D1: clamp (Vz=15V)', 1.27, 0)])
f = write_project(OUT, 'testgen', sch)
print('wrote', f)

r = subprocess.run([KICAD_CLI, 'sch', 'erc', str(f), '-o', str(OUT / 'erc.rpt'),
                    '--severity-error', '--exit-code-violations'],
                   capture_output=True, text=True, encoding='utf-8', errors='replace')
print('ERC exit:', r.returncode)
print((OUT / 'erc.rpt').read_text(encoding='utf-8')[-2500:])

r = subprocess.run([KICAD_CLI, 'sch', 'export', 'netlist', str(f), '-o', str(OUT / 'test.net')],
                   capture_output=True, text=True, encoding='utf-8', errors='replace')
print('netlist exit:', r.returncode, r.stderr[-500:] if r.stderr else '')
net_text = (OUT / 'test.net').read_text(encoding='utf-8')

# ネット照合
want = sch.net_map()
got = parse_netlist_nets(net_text)
ok = True
for net, nodes in want.items():
    g = got.get(net, set())
    if g != nodes:
        print(f'MISMATCH {net}: want={sorted(nodes)} got={sorted(g)}')
        ok = False
print('NETLIST MATCH' if ok else 'NETLIST MISMATCH')
