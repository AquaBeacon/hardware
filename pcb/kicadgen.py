"""KiCad 10 schematic generator.

単一の回路記述(Part/pinsマップ)から .kicad_sch を生成する。
- シンボル定義は KiCad 標準ライブラリ (.kicad_sym) から S式ごと抽出して lib_symbols に埋め込む
- 各ピンにワイヤスタブ + グローバルラベル(ネット名)を付けて結線する(生成回路図の定石)
- 検証は kicad-cli sch erc / export netlist で行う(このモジュールは生成のみ)
"""
from __future__ import annotations

import re
import uuid as uuidlib
from dataclasses import dataclass, field
from pathlib import Path

KICAD_BIN = r"C:\Program Files\KiCad\10.0\bin"
KICAD_CLI = KICAD_BIN + r"\kicad-cli.exe"
SYMDIR = Path(r"C:\Program Files\KiCad\10.0\share\kicad\symbols")


# ---------------------------------------------------------------------------
# 最小S式パーサ
# ---------------------------------------------------------------------------

def tokenize(text: str):
    # 文字列リテラルを守りつつトークン化
    token = re.compile(r'"(?:[^"\\]|\\.)*"|[()]|[^\s()"]+')
    for m in token.finditer(text):
        yield m.group(0)


def parse(tokens):
    stack = [[]]
    for t in tokens:
        if t == '(':
            new = []
            stack[-1].append(new)
            stack.append(new)
        elif t == ')':
            stack.pop()
        else:
            stack[-1].append(t)
    assert len(stack) == 1
    return stack[0]


def dumps(node, indent=0) -> str:
    """S式を文字列化する(KiCadが読める形式)。"""
    if isinstance(node, str):
        return node
    pad = '\t' * indent
    # 全要素が文字列なら1行にする
    if all(isinstance(x, str) for x in node):
        return '(' + ' '.join(node) + ')'
    parts = []
    head = []
    i = 0
    while i < len(node) and isinstance(node[i], str):
        head.append(node[i])
        i += 1
    inner = '\n'.join(pad + '\t' + dumps(x, indent + 1) for x in node[i:])
    return '(' + ' '.join(head) + ('\n' + inner if inner else '') + '\n' + pad + ')'


def q(s: str) -> str:
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


# ---------------------------------------------------------------------------
# ライブラリからシンボル抽出
# ---------------------------------------------------------------------------

_libcache: dict[str, list] = {}


def _load_lib(libname: str) -> list:
    if libname not in _libcache:
        text = (SYMDIR / f'{libname}.kicad_sym').read_text(encoding='utf-8')
        _libcache[libname] = parse(tokenize(text))[0]
    return _libcache[libname]


def get_symbol(libname: str, symname: str) -> list:
    """ライブラリからシンボル定義ノード(deep copyでない、変更禁止)を返す。"""
    root = _load_lib(libname)
    for node in root:
        if isinstance(node, list) and node and node[0] == 'symbol' and node[1] == q(symname):
            return node
    raise KeyError(f'{libname}:{symname} not found')


import copy


def embedded_symbol(libname: str, symname: str) -> list:
    """lib_symbols に埋め込む形(名前を Lib:Name に)へ変換したコピーを返す。
    (extends を持つ派生シンボルは親のグラフィック/ピンをマージする)"""
    node = copy.deepcopy(get_symbol(libname, symname))
    ext = None
    for ch in node:
        if isinstance(ch, list) and ch and ch[0] == 'extends':
            ext = ch[1].strip('"')
    if ext:
        parent = copy.deepcopy(get_symbol(libname, ext))
        # 親の子シンボル(グラフィック単位)と pin_names 等を取り込み、名前を子に合わせる
        merged = [x for x in node if not (isinstance(x, list) and x and x[0] == 'extends')]
        have = {x[0] if isinstance(x, list) else None for x in merged}
        for ch in parent:
            if not isinstance(ch, list):
                continue
            if ch[0] == 'symbol':
                # 親のユニット名 Parent_U_S -> Child_U_S
                pname = ch[1].strip('"')
                suffix = pname[len(ext):]
                ch[1] = q(symname + suffix)
                merged.append(ch)
            elif ch[0] == 'property':
                pass  # プロパティは子のものを優先
            elif ch[0] not in have:
                merged.append(ch)
        node = merged
    # KiCad 10.0の標準RaspberryPi_PicoシンボルはGND/AGND 8ピンを
    # power_outとして定義しており、同一GNDへ結ぶだけでpin_to_pin ERCエラーになる。
    # PicoモジュールのGNDは外部回路を駆動する電源出力ではないためpassiveへ補正する。
    if libname == 'MCU_Module' and symname == 'RaspberryPi_Pico':
        ground_pins = {'3', '8', '13', '18', '23', '28', '33', '38'}
        patched = set()

        def patch_ground_pin_types(n):
            for ch in n:
                if not isinstance(ch, list):
                    continue
                if ch and ch[0] == 'pin':
                    number = next((e[1].strip('"') for e in ch
                                   if isinstance(e, list) and e and e[0] == 'number'), None)
                    if number in ground_pins:
                        ch[1] = 'passive'
                        patched.add(number)
                patch_ground_pin_types(ch)

        patch_ground_pin_types(node)
        assert patched == ground_pins, f'Pico GND pin patch incomplete: {patched}'

    node[1] = q(f'{libname}:{symname}')
    return node


def symbol_pins(libname: str, symname: str, unit: int | None = None
                ) -> dict[str, tuple[float, float, float]]:
    """ピン番号 -> (x, y, angle_deg) をシンボル座標系で返す(extends解決込み)。
    unit指定時は そのユニット(+共通ユニット0) のピンのみ返す(マルチユニット対応)。"""
    node = get_symbol(libname, symname)
    base = symname
    for ch in node:
        if isinstance(ch, list) and ch and ch[0] == 'extends':
            return symbol_pins(libname, ch[1].strip('"'), unit)
    pins = {}

    def collect(n):
        for ch in n:
            if isinstance(ch, list) and ch and ch[0] == 'pin':
                at = num = None
                for e in ch:
                    if isinstance(e, list) and e:
                        if e[0] == 'at':
                            at = (float(e[1]), float(e[2]), float(e[3]) if len(e) > 3 else 0.0)
                        elif e[0] == 'number':
                            num = e[1].strip('"')
                if at and num is not None:
                    pins[num] = at

    for ch in node:
        if isinstance(ch, list) and ch and ch[0] == 'symbol':
            subname = ch[1].strip('"')
            m = re.match(re.escape(base) + r'_(\d+)_(\d+)$', subname)
            u = int(m.group(1)) if m else 0
            if unit is None or u == 0 or u == unit:
                collect(ch)
    return pins


def symbol_units(libname: str, symname: str) -> set[int]:
    """シンボルの持つユニット番号(0=共通を除く)。"""
    node = get_symbol(libname, symname)
    for ch in node:
        if isinstance(ch, list) and ch and ch[0] == 'extends':
            return symbol_units(libname, ch[1].strip('"'))
    units = set()
    for ch in node:
        if isinstance(ch, list) and ch and ch[0] == 'symbol':
            m = re.match(re.escape(symname) + r'_(\d+)_(\d+)$', ch[1].strip('"'))
            if m and int(m.group(1)) > 0:
                units.add(int(m.group(1)))
    return units


def pin_sch_pos(place_xy, rot, pin_at, mirror=None):
    """シンボル配置(place, rot, mirror) + ピンlib座標 -> 回路図座標。
    KiCad: 回路図はy下向き、シンボル定義はy上向き。
    変換: p' = R(rot) @ (px, py) ののち y反転(=schへ)。mirrorは配置前のx/y反転。
    """
    import math
    px, py, _ = pin_at
    if mirror == 'x':
        py = -py
    elif mirror == 'y':
        px = -px
    r = math.radians(rot)
    rx = px * math.cos(r) - py * math.sin(r)
    ry = px * math.sin(r) + py * math.cos(r)
    return (round(place_xy[0] + rx, 4), round(place_xy[1] - ry, 4))


# ---------------------------------------------------------------------------
# 回路記述
# ---------------------------------------------------------------------------

@dataclass
class Part:
    ref: str
    lib: str          # 'Device'
    sym: str          # 'R'
    value: str
    footprint: str
    pins: dict[str, str]          # pin number -> net name
    at: tuple[float, float] = (0, 0)
    rot: float = 0
    mirror: str | None = None
    stub: float = 2.54            # ピンからラベルまでのワイヤ長
    unit: int = 1                 # マルチユニットシンボルのユニット番号
    fields: dict[str, str] = field(default_factory=dict)
    ref_at: tuple | None = None   # Referenceテキスト位置の明示指定 (x, y)
    val_at: tuple | None = None   # Valueテキスト位置の明示指定 (x, y)
    gnd_style: str = 'symbol'     # 'label'にするとGNDピンもラベル接続(ピン密集コネクタ用)


@dataclass
class Schematic:
    name: str
    parts: list[Part]
    title: str = ''
    power_flag_nets: tuple = ('GND',)   # PWR_FLAGを置くネット
    # レビュー性向上(2026-07-12追加):
    # wires: (net, [pointspec...]) のリスト。pointspec は 'REF.PIN' か (x,y)。
    #   連続する点間にワイヤを描く。ワイヤに含まれるピンはスタブ+ラベルを省略し、
    #   ネットにラベルが1つも無くなる場合は最初のワイヤ上に自動でラベルを1つ置く。
    wires: list = field(default_factory=list)
    junctions: list = field(default_factory=list)   # (x, y) T分岐のジャンクション
    gnd_symbol: bool = True   # GNDピンにはラベルでなく power:GND シンボルを置く
    labels_at: dict = field(default_factory=dict)   # net -> (x, y, ang) キーパーラベル明示位置
    # レビュー性向上(2026-08-03追加): 図面上の注記。ネット/ERC/ネットリストには一切影響しない。
    # texts:  (x, y, '注記') / (x, y, s, size) / (x, y, s, size, ang)  ← 部品の役割・設計意図
    # blocks: (x1, y1, x2, y2, 'ブロック名')  ← 機能ブロックの破線枠+見出し
    texts: list = field(default_factory=list)
    blocks: list = field(default_factory=list)

    def net_map(self) -> dict[str, set[tuple[str, str]]]:
        nets: dict[str, set] = {}
        for p in self.parts:
            for pin, net in p.pins.items():
                if net == 'NC':   # 未接続マーカー(no_connect)はネットにしない
                    continue
                nets.setdefault(net, set()).add((p.ref, pin))
        return nets


def _uuid():
    return str(uuidlib.uuid4())


def _prop(name, val, x, y, hide=False, ang=0, justify=None):
    eff = ['effects', ['font', ['size', '1.27', '1.27']]]
    if justify:
        eff.append(['justify', justify])
    p = ['property', q(name), q(val), ['at', f'{x}', f'{y}', f'{int(ang)}'],
         ['show_name', 'no'], ['do_not_autoplace', 'yes']]
    if hide:
        p.append(['hide', 'yes'])
    p.append(eff)
    return p


def _sch_text(s, x, y, size=1.27, ang=0):
    """図面注記(graphic text)。ネットには繋がらない。"""
    return ['text', q(str(s)), ['exclude_from_sim', 'no'],
            ['at', f'{x}', f'{y}', f'{int(ang)}'],
            ['effects', ['font', ['size', f'{size}', f'{size}']],
             ['justify', 'left', 'bottom']],
            ['uuid', q(_uuid())]]


def render_sch(sch: Schematic, project: str, root_uuid: str) -> str:
    used: dict[tuple[str, str], None] = {}
    for p in sch.parts:
        used[(p.lib, p.sym)] = None
    lib_symbols = ['lib_symbols']
    for (lib, sym) in used:
        lib_symbols.append(embedded_symbol(lib, sym))
    # PWR_FLAG
    if sch.power_flag_nets:
        lib_symbols.append(embedded_symbol('power', 'PWR_FLAG'))
    if sch.gnd_symbol:
        lib_symbols.append(embedded_symbol('power', 'GND'))

    body = ['kicad_sch',
            ['version', '20260306'],
            ['generator', q('eeschema')],
            ['generator_version', q('10.0')],
            ['uuid', q(root_uuid)],
            ['paper', q('A3')],
            lib_symbols]

    wires = []
    labels = []
    symbols = []

    def add_label(net, x, y, ang):
        lab = ['global_label', q(net), ['shape', 'passive'],
               ['at', f'{x}', f'{y}', f'{int(ang)}'],
               ['effects', ['font', ['size', '1.27', '1.27']],
                ['justify', 'left' if ang == 0 else ('right' if ang == 180 else 'left')]],
               ['uuid', q(_uuid())]]
        labels.append(lab)

    def add_wire(x1, y1, x2, y2):
        wires.append(['wire', ['pts', ['xy', f'{x1}', f'{y1}'], ['xy', f'{x2}', f'{y2}']],
                      ['stroke', ['width', '0'], ['type', 'default']],
                      ['uuid', q(_uuid())]])

    import math

    # --- パス1: 全ピンの回路図座標と外向き角度 ---
    # 注: シンボル定義のピン角度は「接続点から本体へ向かう」方向。従来コードは
    # これをそのままスタブ方向にしていたためラベルが本体に重なっていた。
    # ここでは +180 して外向き(本体から離れる方向)を格納する。
    # 方向ベクトルは sch座標(y下向き)で (cos ang, -sin ang)。
    pinpos: dict[tuple[str, str], tuple[float, float, float]] = {}
    for p in sch.parts:
        pins = symbol_pins(p.lib, p.sym, unit=p.unit)
        for num in pins:
            px, py = pin_sch_pos(p.at, p.rot, pins[num], p.mirror)
            ang = (pins[num][2] + p.rot) % 360
            if p.mirror == 'y':
                ang = (180 - ang) % 360
            elif p.mirror == 'x':
                ang = (-ang) % 360
            pinpos[(p.ref, num)] = (px, py, (ang + 180) % 360)

    # --- 明示ワイヤの解決(ラベル省略ピンの決定) ---
    def _respt(spec):
        if isinstance(spec, str):
            ref, num = spec.rsplit('.', 1)
            if (ref, num) not in pinpos:
                raise KeyError(f'wire: pin {spec} not found')
            x, y, _ = pinpos[(ref, num)]
            return (x, y)
        return (round(spec[0], 4), round(spec[1], 4))

    wired_pins: set[tuple[str, str]] = set()
    net_segs: dict[str, list] = {}
    for net, pts in sch.wires:
        rp = [_respt(s) for s in pts]
        for a, b in zip(rp, rp[1:]):
            add_wire(a[0], a[1], b[0], b[1])
            net_segs.setdefault(net, []).append((a, b))
        for s in pts:
            if isinstance(s, str):
                ref, num = s.rsplit('.', 1)
                wired_pins.add((ref, num))

    for jx, jy in sch.junctions:
        labels.append(['junction', ['at', f'{jx}', f'{jy}'],
                       ['diameter', '0'], ['color', '0', '0', '0', '0'],
                       ['uuid', q(_uuid())]])

    labeled_nets: set[str] = set()
    gnd_count = [0]

    def add_gnd_symbol(px, py, ang):
        """GNDピン(外向き角ang)にスタブ+power:GNDシンボルを置く。"""
        gnd_count[0] += 1
        ref = f'#PWR{gnd_count[0]:03d}'
        if ang == 270:      # 下向きピン: そのまま下へ
            add_wire(px, py, px, py + 2.54)
            gx, gy, grot = px, py + 2.54, 0
        elif ang == 0:      # 右向き: 右へ出て下げる
            add_wire(px, py, px + 2.54, py)
            add_wire(px + 2.54, py, px + 2.54, py + 2.54)
            gx, gy, grot = px + 2.54, py + 2.54, 0
        elif ang == 180:    # 左向き
            add_wire(px, py, px - 2.54, py)
            add_wire(px - 2.54, py, px - 2.54, py + 2.54)
            gx, gy, grot = px - 2.54, py + 2.54, 0
        else:               # 上向き: 逆さGND
            add_wire(px, py, px, py - 2.54)
            gx, gy, grot = px, py - 2.54, 180
        sym = ['symbol', ['lib_id', q('power:GND')],
               ['at', f'{gx}', f'{gy}', f'{grot}'],
               ['unit', '1'], ['body_style', '1'],
               ['exclude_from_sim', 'no'], ['in_bom', 'yes'], ['on_board', 'yes'],
               ['in_pos_files', 'yes'], ['dnp', 'no'],
               ['uuid', q(_uuid())],
               _prop('Reference', ref, gx, gy, hide=True),
               _prop('Value', 'GND', gx, gy + 3.81, hide=True),
               _prop('Footprint', '', gx, gy, hide=True),
               _prop('Datasheet', '', gx, gy, hide=True),
               _prop('Description', '', gx, gy, hide=True),
               ['pin', q('1'), ['uuid', q(_uuid())]],
               ['instances', ['project', q(project),
                              ['path', q('/' + root_uuid),
                               ['reference', q(ref)], ['unit', '1']]]]]
        symbols.append(sym)

    for p in sch.parts:
        pins = symbol_pins(p.lib, p.sym, unit=p.unit)
        sx, sy = p.at
        # Ref/Value の置き方: プロパティ角度はシンボル回転に加算されるので
        # 逆回転(-rot)を与えて常に水平に読めるようにする。
        # 2ピン部品はピン並びで縦/横を判定し、縦なら右横に、横なら上下に置く。
        # rot 0/180 はテキスト角0のまま(180はKiCadが可読方向へ自動反転)、90/270のみ逆回転
        cr = 0 if int(p.rot) % 180 == 0 else (360 - int(p.rot)) % 360
        ppos = [pinpos[(p.ref, n)] for n in p.pins if (p.ref, n) in pinpos]
        if p.lib == 'Device' and len(ppos) == 2 and abs(ppos[0][0] - ppos[1][0]) < 0.01:
            # 縦向き2ピン部品: 右横に左寄せで(上下ピンの配線と重ならない高さ)
            refp = (sx + 2.54, sy, 'left')
            valp = (sx + 2.54, sy + 2.54, 'left')
        elif p.lib == 'Device' and len(ppos) == 2 and abs(ppos[0][1] - ppos[1][1]) < 0.01:
            # 横向き2ピン部品: 上下に
            refp = (sx, sy - 2.54, None)
            valp = (sx, sy + 2.54, None)
        else:
            refp = (sx, sy - 5.08, None)
            valp = (sx, sy + 5.08, None)
        if p.ref_at:
            refp = (p.ref_at[0], p.ref_at[1], None)
        if p.val_at:
            valp = (p.val_at[0], p.val_at[1], None)
        sym = ['symbol', ['lib_id', q(f'{p.lib}:{p.sym}')],
               ['at', f'{sx}', f'{sy}', f'{int(p.rot)}']]
        if p.mirror:
            sym.append(['mirror', p.mirror])
        sym += [['unit', f'{p.unit}'], ['body_style', '1'],
               ['exclude_from_sim', 'no'], ['in_bom', 'yes'], ['on_board', 'yes'],
               ['in_pos_files', 'yes'], ['dnp', 'no'],
               ['uuid', q(_uuid())],
               _prop('Reference', p.ref, refp[0], refp[1], ang=cr, justify=refp[2]),
               _prop('Value', p.value, valp[0], valp[1], ang=cr, justify=valp[2]),
               _prop('Footprint', p.footprint, sx, sy, hide=True),
               _prop('Datasheet', '', sx, sy, hide=True),
               _prop('Description', '', sx, sy, hide=True)]
        for fname, fval in p.fields.items():
            sym.append(_prop(fname, fval, sx, sy, hide=True))
        for num in pins:
            sym.append(['pin', q(num), ['uuid', q(_uuid())]])
        sym.append(['instances',
                    ['project', q(project),
                     ['path', q('/' + root_uuid),
                      ['reference', q(p.ref)], ['unit', f'{p.unit}']]]])
        symbols.append(sym)

        # ピンごとのスタブ配線 + グローバルラベル
        # (明示ワイヤに含まれるピンは省略。GNDはラベルでなくGNDシンボル)
        for num, net in p.pins.items():
            if num not in pins:
                raise KeyError(f'{p.ref}: pin {num} not in {p.lib}:{p.sym} (has {sorted(pins)})')
            if (p.ref, num) in wired_pins:
                continue
            px, py, ang = pinpos[(p.ref, num)]
            if net == 'NC':   # 未接続ピン: no_connectマーカーを置く(ERCのpin_not_connected対策)
                labels.append(['no_connect', ['at', f'{px}', f'{py}'],
                               ['uuid', q(_uuid())]])
                continue
            if net == 'GND' and sch.gnd_symbol and p.gnd_style == 'symbol':
                add_gnd_symbol(px, py, ang)
                continue
            dx = round(math.cos(math.radians(ang)) * p.stub, 4)
            dy = round(-math.sin(math.radians(ang)) * p.stub, 4)
            ex, ey = round(px + dx, 4), round(py + dy, 4)
            add_wire(px, py, ex, ey)
            # ラベル角度: ワイヤ終端から外向き
            add_label(net, ex, ey, (ang % 360))
            labeled_nets.add(net)

    # ワイヤ化したネットには必ずラベルを1つ置く(ネット名の維持=ネットリスト照合の前提)。
    # スタブ側に同名ラベルが既にあっても、ワイヤ断片自体にラベルが無いと別ネットに
    # なってしまうため、labeled_nets ではスキップしない。GNDのみGNDシンボルが名前を
    # 与えるので不要。水平セグメントを優先し、縦書きラベルを避ける。
    for net, segs in net_segs.items():
        if net == 'GND' and sch.gnd_symbol:
            continue
        if net in sch.labels_at:
            lx, ly, lang = sch.labels_at[net]
            add_label(net, lx, ly, lang)
            labeled_nets.add(net)
            continue
        def seg_key(s):
            (a, b) = s
            horiz = abs(a[1] - b[1]) < 0.01
            return (horiz, abs(b[0] - a[0]) + abs(b[1] - a[1]))
        a, b = max(segs, key=seg_key)
        seglen = abs(b[0] - a[0]) + abs(b[1] - a[1])
        t = min(2.54, seglen / 2)
        ux = (b[0] - a[0]) / seglen if seglen else 0
        uy = (b[1] - a[1]) / seglen if seglen else 0
        lx = round(a[0] + ux * t, 4)
        ly = round(a[1] + uy * t, 4)
        add_label(net, lx, ly, 0 if abs(a[1] - b[1]) < 0.01 else 90)
        labeled_nets.add(net)

    # PWR_FLAG配置(各対象ネットに1個: スタブ+ラベルで接続)
    pf_x, pf_y = 20.0, 20.0
    pf_pins = symbol_pins('power', 'PWR_FLAG')
    for i, net in enumerate(sch.power_flag_nets):
        x = pf_x + i * 25.4
        ref = f'#FLG0{i+1}'
        sym = ['symbol', ['lib_id', q('power:PWR_FLAG')],
               ['at', f'{x}', f'{pf_y}', '0'],
               ['unit', '1'], ['body_style', '1'],
               ['exclude_from_sim', 'no'], ['in_bom', 'yes'], ['on_board', 'yes'],
               ['in_pos_files', 'yes'], ['dnp', 'no'],
               ['uuid', q(_uuid())],
               _prop('Reference', ref, x, pf_y - 5.08, hide=True),
               _prop('Value', 'PWR_FLAG', x, pf_y - 3.0),
               _prop('Footprint', '', x, pf_y, hide=True),
               _prop('Datasheet', '', x, pf_y, hide=True),
               _prop('Description', '', x, pf_y, hide=True),
               ['pin', q('1'), ['uuid', q(_uuid())]],
               ['instances', ['project', q(project),
                              ['path', q('/' + root_uuid),
                               ['reference', q(ref)], ['unit', '1']]]]]
        symbols.append(sym)
        px, py = pin_sch_pos((x, pf_y), 0, pf_pins['1'])
        add_wire(px, py, px, py + 2.54)
        add_label(net, px, py + 2.54, 270)
        labeled_nets.add(net)

    # --- 機能ブロック枠 + 注記(レビュー専用。ネット/ERC/ネットリストに影響しない) ---
    graphics = []
    for b in sch.blocks:
        x1, y1, x2, y2 = (float(v) for v in b[:4])
        graphics.append(['rectangle',
                         ['start', f'{x1}', f'{y1}'], ['end', f'{x2}', f'{y2}'],
                         ['stroke', ['width', '0.254'], ['type', 'dash']],
                         ['fill', ['type', 'none']],
                         ['uuid', q(_uuid())]])
        if len(b) > 4 and b[4]:
            # 見出しは枠の外側(左上の上)に置く。内側だと枠線・部品と噛む。
            graphics.append(_sch_text(b[4], x1, y1 - 1.27, 2.0, 0))
    for t in sch.texts:
        graphics.append(_sch_text(t[2], t[0], t[1],
                                  t[3] if len(t) > 3 else 1.27,
                                  t[4] if len(t) > 4 else 0))

    for w in wires:
        body.append(w)
    for l in labels:
        body.append(l)
    for g in graphics:
        body.append(g)
    for s in symbols:
        body.append(s)
    body.append(['sheet_instances', ['path', q('/'), ['page', q('1')]]])
    body.append(['embedded_fonts', 'no'])
    return dumps(body) + '\n'


def write_project(outdir: Path, name: str, sch: Schematic):
    outdir.mkdir(parents=True, exist_ok=True)
    root_uuid = str(uuidlib.uuid5(uuidlib.NAMESPACE_DNS, name + '.aquabeacon'))
    text = render_sch(sch, name, root_uuid)
    (outdir / f'{name}.kicad_sch').write_text(text, encoding='utf-8')
    pro = outdir / f'{name}.kicad_pro'
    if not pro.exists():
        pro.write_text('{\n  "meta": { "filename": "%s.kicad_pro", "version": 3 },\n  "boards": [],\n  "libraries": { "pinned_footprint_libs": [], "pinned_symbol_libs": [] },\n  "schematic": { "legacy_lib_dir": "", "legacy_lib_list": [] }\n}\n' % name, encoding='utf-8')
    return outdir / f'{name}.kicad_sch'
