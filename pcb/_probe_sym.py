"""回路図レイアウト用: 使用シンボルのピンオフセット(lib座標, y上向き)一覧。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from kicadgen import symbol_pins, symbol_units

SYMS = [
    ('Device', 'R', None),
    ('Device', 'C', None),
    ('Device', 'C_Polarized', None),
    ('Device', 'L', None),
    ('Device', 'D', None),
    ('Device', 'D_Zener', None),
    ('Device', 'D_Schottky', None),
    ('Connector_Generic', 'Conn_01x02', None),
    ('Connector_Generic', 'Conn_01x03', None),
    ('Connector_Generic', 'Conn_01x05', None),
    ('Connector_Generic', 'Conn_01x06', None),
    ('Transistor_FET', 'IRLZ44N', None),
    ('Amplifier_Operational', 'TL072', 1),
    ('Amplifier_Operational', 'TL072', 2),
    ('Amplifier_Operational', 'TL072', 3),
    ('Comparator', 'TLV3501AIDBV', None),
    ('power', 'GND', None),
]

for lib, sym, unit in SYMS:
    pins = symbol_pins(lib, sym, unit=unit)
    u = f' u{unit}' if unit else ''
    items = ', '.join(f'{n}@({x},{y},{int(a)})' for n, (x, y, a) in
                      sorted(pins.items(), key=lambda kv: int(kv[0])))
    print(f'{lib}:{sym}{u} -> {items}')
