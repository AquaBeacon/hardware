"""シンボルのピン番号・名前・オフセット(lib座標, y上向き)を出力する汎用プローブ。

使い方 (KiCad同梱pythonで):
    python probe_pins.py <Lib> <Symbol> [unit]
    python probe_pins.py --list <Lib> [prefix]     # ライブラリ内シンボル名の一覧
例:
    python probe_pins.py Device R
    python probe_pins.py Amplifier_Operational TL072
    python probe_pins.py --list Amplifier_Operational OPA

出力の読み方:
    pin番号 name @(x, y, angle)。angleは「接続点から本体へ向かう」方向(度)。
    回路図座標(y下向き)でのピン位置 = place + rot回転(x,y) の後 yを符号反転。
    外向き(スタブ/ラベルが伸びる方向)は angle+180。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from kicadgen import get_symbol, symbol_pins, symbol_units, _load_lib


def pin_names(lib, sym):
    node = get_symbol(lib, sym)
    for ch in node:
        if isinstance(ch, list) and ch and ch[0] == 'extends':
            return pin_names(lib, ch[1].strip('"'))
    names = {}

    def walk(n):
        for ch in n:
            if isinstance(ch, list) and ch:
                if ch[0] == 'pin':
                    nm = num = None
                    for e in ch:
                        if isinstance(e, list) and e:
                            if e[0] == 'name':
                                nm = e[1].strip('"')
                            elif e[0] == 'number':
                                num = e[1].strip('"')
                    if num is not None:
                        names[num] = nm
                elif ch[0] == 'symbol':
                    walk(ch)
    walk(node)
    return names


if len(sys.argv) < 3:
    print(__doc__)
    sys.exit(1)

if sys.argv[1] == '--list':
    lib = sys.argv[2]
    prefix = sys.argv[3] if len(sys.argv) > 3 else ''
    root = _load_lib(lib)
    names = [n[1].strip('"') for n in root
             if isinstance(n, list) and n and n[0] == 'symbol']
    for x in names:
        if x.startswith(prefix):
            print(x)
    sys.exit(0)

lib, sym = sys.argv[1], sys.argv[2]
unit = int(sys.argv[3]) if len(sys.argv) > 3 else None
names = pin_names(lib, sym)
units = symbol_units(lib, sym)


def show(u):
    pins = symbol_pins(lib, sym, unit=u)
    def _k(kv):
        try:
            return (0, int(kv[0]), '')
        except ValueError:
            return (1, 0, kv[0])
    for n, (x, y, a) in sorted(pins.items(), key=_k):
        print(f'  pin {n} {names.get(n, "")!r} @({x}, {y}, {int(a)})')


if units and unit is None:
    print(f'{lib}:{sym} マルチユニット {sorted(units)}')
    for u in sorted(units):
        print(f' unit {u}:')
        show(u)
else:
    print(f'{lib}:{sym}' + (f' unit {unit}' if unit else ''))
    show(unit)
