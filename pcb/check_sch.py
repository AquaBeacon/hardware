r"""回路図の「重なり」検査 (build 不要・普通のpythonで数秒)。

    python -X utf8 pcb\check_sch.py build_child_pwr [--all]

build_<name>.py を **PCB を作らずに** import して回路図だけ生成し、
生成された .kicad_sch の実ジオメトリ(シンボル本体・Ref/Value・自動スタブラベル・
GNDシンボル・PWR_FLAG・ブロック枠・見出し・注記)を突き合わせて衝突を報告する。

「見づらい回路図」の原因はほぼ全部この5種:
  1. ブロック枠どうしの交差 / 近すぎ
  2. ブロック見出し(枠の外・左上の上に出る)が上のブロックの中身を踏む
  3. シンボル本体どうしの重なり
  4. Ref/Value/ラベル が他のシンボル本体に乗る
  5. sch_texts の注記が部品・枠に乗る

テキスト幅は KiCad ストロークフォントの実測近似(ASCII 0.95*size / 全角 1.9*size)。
**目安であって証明ではない**ので、0 になった後に必ず1回だけ目視する。

終了コード: 衝突が1件でもあれば 1。
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import kicadgen  # noqa: E402
from kicadgen import Schematic, parse, tokenize, write_project  # noqa: E402

BOARDS = ['build_child_main', 'build_child_pwr', 'build_parent_main', 'build_parent_pwr']

# ブロック見出しの寸法(kicadgen: _sch_text(title, x1, y1-1.27, 2.0) / justify left,bottom)
TITLE_SIZE = 2.0
TITLE_DY = 1.27

# 判定の余白(mm)。これ未満しか離れていなければ「近すぎ」として報告する。
GAP_BLOCK_V = 8.0    # 上下に並ぶ枠どうし(見出し 2.0*1.63 + Ref/Value のぶら下がり)
GAP_BLOCK_H = 6.0    # 左右に並ぶ枠どうし


# --------------------------------------------------------------------------
# 1. build_*.py を「PCBを作らずに」実行して回路図の引数だけ取る
# --------------------------------------------------------------------------

def capture(module_name: str) -> Schematic:
    # pcbnew(KiCad同梱python専用)を空モジュールで置き換える。
    # 回路図だけ見るので pcbgen は一切呼ばれない。
    if 'pcbnew' not in sys.modules:
        import types
        stub = types.ModuleType('pcbnew')
        stub.__getattr__ = lambda n: None      # pcbgen のモジュール定数参照を吸収
        sys.modules['pcbnew'] = stub
    import buildlib
    grabbed = {}

    def fake_build(name, parts, placements, board_rect, **kw):
        grabbed.update(name=name, parts=parts, kw=kw)
        return True, ''

    real, buildlib.build = buildlib.build, fake_build
    try:
        for m in (module_name, 'pcbgen'):
            sys.modules.pop(m, None)
        __import__(module_name)
    finally:
        buildlib.build = real
        sys.modules.pop(module_name, None)
    if not grabbed:
        raise SystemExit(f'{module_name}: build() が呼ばれなかった')
    kw = grabbed['kw']
    return Schematic(grabbed['name'], grabbed['parts'],
                     power_flag_nets=kw.get('power_flag_nets', ('GND',)),
                     wires=list(kw.get('sch_wires', ())),
                     junctions=list(kw.get('sch_junctions', ())),
                     gnd_symbol=kw.get('gnd_symbol', True),
                     labels_at=dict(kw.get('sch_labels') or {}),
                     texts=list(kw.get('sch_texts', ())),
                     blocks=list(kw.get('sch_blocks', ())))


# --------------------------------------------------------------------------
# 2. 生成 .kicad_sch から実ジオメトリを拾う
# --------------------------------------------------------------------------

def _f(x):
    return float(x)


def _kids(node, head):
    return [c for c in node if isinstance(c, list) and c and c[0] == head]


def _first(node, head):
    k = _kids(node, head)
    return k[0] if k else None


def _unq(s):
    return s.strip('"')


def text_extent(s: str, size: float) -> float:
    """KiCad ストロークフォントの横幅近似(mm)。"""
    w = 0.0
    for ch in str(s):
        w += 1.9 * size if ord(ch) > 0x2E80 else 0.95 * size
    return w


def _bbox_of_graphics(node, acc):
    """lib シンボルのグラフィック要素から lib 座標の bbox を集める。"""
    for ch in node:
        if not isinstance(ch, list) or not ch:
            continue
        h = ch[0]
        if h == 'rectangle':
            for e in ('start', 'end'):
                p = _first(ch, e)
                if p:
                    acc.append((_f(p[1]), _f(p[2])))
        elif h == 'polyline':
            pts = _first(ch, 'pts')
            if pts:
                for xy in _kids(pts, 'xy'):
                    acc.append((_f(xy[1]), _f(xy[2])))
        elif h == 'circle':
            c, r = _first(ch, 'center'), _first(ch, 'radius')
            if c and r:
                cx, cy, rr = _f(c[1]), _f(c[2]), _f(r[1])
                acc += [(cx - rr, cy - rr), (cx + rr, cy + rr)]
        elif h == 'arc':
            for e in ('start', 'mid', 'end'):
                p = _first(ch, e)
                if p:
                    acc.append((_f(p[1]), _f(p[2])))
        elif h == 'pin':
            p = _first(ch, 'at')
            if p:
                acc.append((_f(p[1]), _f(p[2])))
        elif h == 'symbol':
            _bbox_of_graphics(ch, acc)


def load_geometry(sch_path: Path):
    root = parse(tokenize(sch_path.read_text(encoding='utf-8')))[0]

    libs = {}
    ls = _first(root, 'lib_symbols')
    if ls:
        for sym in _kids(ls, 'symbol'):
            acc = []
            _bbox_of_graphics(sym, acc)
            if acc:
                xs = [p[0] for p in acc]
                ys = [p[1] for p in acc]
                libs[_unq(sym[1])] = (min(xs), min(ys), max(xs), max(ys))

    import math
    bodies, texts, rects, titles = [], [], [], []

    for sym in _kids(root, 'symbol'):
        lid = _unq(_first(sym, 'lib_id')[1])
        at = _first(sym, 'at')
        X, Y, rot = _f(at[1]), _f(at[2]), _f(at[3]) if len(at) > 3 else 0.0
        mir = _first(sym, 'mirror')
        mir = mir[1] if mir else None
        ref = val = ''
        own = []
        for pr in _kids(sym, 'property'):
            nm, vv = _unq(pr[1]), _unq(pr[2])
            if nm == 'Reference':
                ref = vv
            elif nm == 'Value':
                val = vv
            if _first(pr, 'hide'):
                continue
            pat = _first(pr, 'at')
            if not pat:
                continue
            px, py = _f(pat[1]), _f(pat[2])
            eff = _first(pr, 'effects')
            fs = 1.27
            if eff:
                fo = _first(eff, 'font')
                if fo and _first(fo, 'size'):
                    fs = _f(_first(fo, 'size')[1])
            if vv:
                w = text_extent(vv, fs)
                just = _first(eff, 'justify') if eff else None
                left = px if (just and 'left' in just) else px - w / 2
                own.append((left, py - fs * 0.7, left + w, py + fs * 0.7,
                            f'{nm}:{vv}', None))
        # owner タグ(自分の Ref/Value が自分の本体に乗るのは既定レイアウト由来なので別枠)
        oid = ref or lid
        texts += [(*t[:4], t[4], oid) for t in own]
        if lid in libs:
            x0, y0, x1, y1 = libs[lid]
            pts = []
            for (px, py) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
                if mir == 'y':
                    px = -px
                elif mir == 'x':
                    py = -py
                r = math.radians(rot)
                rx = px * math.cos(r) - py * math.sin(r)
                ry = px * math.sin(r) + py * math.cos(r)
                pts.append((X + rx, Y - ry))
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            bodies.append((min(xs), min(ys), max(xs), max(ys),
                           ref or lid.split(':')[-1], oid))

    for gl in _kids(root, 'global_label'):
        s = _unq(gl[1])
        at = _first(gl, 'at')
        x, y, ang = _f(at[1]), _f(at[2]), _f(at[3]) if len(at) > 3 else 0.0
        w = text_extent(s, 1.27) + 3.0
        h = 2.2
        if ang == 0:
            box = (x, y - h / 2, x + w, y + h / 2)
        elif ang == 180:
            box = (x - w, y - h / 2, x, y + h / 2)
        elif ang == 90:
            box = (x - h / 2, y - w, x + h / 2, y)
        else:
            box = (x - h / 2, y, x + h / 2, y + w)
        texts.append((*box, f'label:{s}', 'label'))

    for tx in _kids(root, 'text'):
        s = _unq(tx[1])
        at = _first(tx, 'at')
        x, y, ang = _f(at[1]), _f(at[2]), _f(at[3]) if len(at) > 3 else 0.0
        eff = _first(tx, 'effects')
        fs = 1.27
        if eff:
            fo = _first(eff, 'font')
            if fo and _first(fo, 'size'):
                fs = _f(_first(fo, 'size')[1])
        w = text_extent(s, fs)
        box = (x, y - fs * 1.15, x + w, y + fs * 0.25)
        entry = (*box, s, 'note')
        if abs(fs - TITLE_SIZE) < 0.01:
            titles.append(entry)
        else:
            texts.append(entry)

    for rc in _kids(root, 'rectangle'):
        a, b = _first(rc, 'start'), _first(rc, 'end')
        rects.append((min(_f(a[1]), _f(b[1])), min(_f(a[2]), _f(b[2])),
                      max(_f(a[1]), _f(b[1])), max(_f(a[2]), _f(b[2]))))

    return bodies, texts, rects, titles


# --------------------------------------------------------------------------
# 3. 判定
# --------------------------------------------------------------------------

def _ov(a, b, pad=0.0):
    """矩形の重なり面積的判定。pad だけ膨らませて判定する。"""
    ix = min(a[2], b[2] + pad) - max(a[0], b[0] - pad)
    iy = min(a[3], b[3] + pad) - max(a[1], b[1] - pad)
    return ix > 0.01 and iy > 0.01


def _inside(a, r):
    return a[0] >= r[0] and a[2] <= r[2] and a[1] >= r[1] and a[3] <= r[3]


def _crosses_border(a, r):
    """矩形 a が枠 r の線をまたぐ(内でも外でもない)。"""
    return _ov(a, r) and not _inside(a, r)


def check(sch: Schematic, verbose=True):
    with tempfile.TemporaryDirectory() as td:
        p = write_project(Path(td), sch.name, sch)
        bodies, texts, rects, titles = load_geometry(p)

    issues = []

    # (1) ブロック枠どうし
    for i, r1 in enumerate(rects):
        for r2 in rects[i + 1:]:
            if _ov(r1, r2):
                issues.append(('BLOCK x BLOCK', f'{r1} と {r2} が交差'))
                continue
            dx = max(r1[0] - r2[2], r2[0] - r1[2])
            dy = max(r1[1] - r2[3], r2[1] - r1[3])
            if dx < 0 and 0 <= dy < GAP_BLOCK_V:
                issues.append(('BLOCK gap', f'上下の枠が {dy:.1f}mm しか離れていない '
                                            f'(>= {GAP_BLOCK_V}) {r1} / {r2}'))
            elif dy < 0 and 0 <= dx < GAP_BLOCK_H:
                issues.append(('BLOCK gap', f'左右の枠が {dx:.1f}mm しか離れていない '
                                            f'(>= {GAP_BLOCK_H}) {r1} / {r2}'))

    # (2) ブロック見出しが他の枠 / シンボル / 注記を踏む
    for t in titles:
        for r in rects:
            if _ov(t, r):
                issues.append(('TITLE x BLOCK', f'見出し "{t[4]}" が枠 {r} に掛かる'))
        for b in bodies:
            if _ov(t, b):
                issues.append(('TITLE x SYMBOL', f'見出し "{t[4]}" が {b[4]} に掛かる'))
        for x in texts:
            if _ov(t, x):
                issues.append(('TITLE x TEXT', f'見出し "{t[4]}" が "{x[4]}" に掛かる'))
    for i, t1 in enumerate(titles):
        for t2 in titles[i + 1:]:
            if _ov(t1, t2):
                issues.append(('TITLE x TITLE', f'"{t1[4]}" と "{t2[4]}"'))

    # (3) シンボル本体どうし。
    #  ただし **完全に同座標のもの同士は除外**する: KiCad の Pico シンボルは GND 8本が
    #  同一点(0,-35.56)にまとめられており、kicadgen が GND シンボルを 8 個重ねて置く。
    #  見た目は1個なので指摘しても直せない(直すには接続を変えるしかない)。
    for i, b1 in enumerate(bodies):
        for b2 in bodies[i + 1:]:
            if all(abs(b1[k] - b2[k]) < 0.01 for k in range(4)):
                continue
            if _ov(b1, b2):
                issues.append(('SYMBOL x SYMBOL', f'{b1[4]} と {b2[4]}'))

    # (4) テキスト(Ref/Value/ラベル/注記)が「他の」シンボル本体に乗る
    #     自分の Ref/Value が自分の本体に掛かるのは kicadgen 既定の置き方なので除外する
    for x in texts:
        for b in bodies:
            if x[5] is not None and x[5] == b[5]:
                continue
            if _ov(x, b):
                issues.append(('TEXT x SYMBOL', f'"{x[4]}" が {b[4]} に乗る'))

    # (5) テキストどうし
    for i, t1 in enumerate(texts):
        for t2 in texts[i + 1:]:
            if _ov(t1, t2):
                issues.append(('TEXT x TEXT', f'"{t1[4]}" と "{t2[4]}"'))

    # (6) シンボル / 注記 がブロック枠の線をまたぐ
    for b in bodies:
        for r in rects:
            if _crosses_border(b, r):
                issues.append(('SYMBOL on FRAME', f'{b[4]} が枠 {r} の線をまたぐ'))
    for x in texts:
        if x[5] != 'note':
            continue
        for r in rects:
            if _crosses_border(x, r):
                issues.append(('NOTE on FRAME', f'"{x[4]}" が枠 {r} の線をまたぐ'))

    # (7) KiCad の A3 タイトルブロック(右下)との重なり。
    #  シート枠と一緒に描かれるので .kicad_sch 側のジオメトリには出てこない = 実測値で予約する。
    TB = (296.0, 257.0, 412.0, 290.0)
    for b in bodies:
        if _ov(b, TB):
            issues.append(('TITLE BLOCK', f'{b[4]} がシートのタイトルブロックに掛かる'))
    for x in texts + titles:
        if _ov(x, TB):
            issues.append(('TITLE BLOCK', f'"{x[4]}" がシートのタイトルブロックに掛かる'))
    for r in rects:
        if _ov(r, TB):
            issues.append(('TITLE BLOCK', f'枠 {r} がシートのタイトルブロックに掛かる'))

    # (8) A3 用紙(420x297)からのはみ出し。枠罫を考慮して 10..410 / 10..287
    for b in bodies:
        if b[0] < 8 or b[2] > 412 or b[1] < 8 or b[3] > 285:
            issues.append(('OUT OF SHEET', f'{b[4]} {b[:4]}'))
    for x in texts + titles:
        if x[0] < 8 or x[2] > 412 or x[1] < 8 or x[3] > 285:
            issues.append(('OUT OF SHEET', f'"{x[4]}" {tuple(round(v, 1) for v in x[:4])}'))
    for r in rects:
        if r[0] < 8 or r[2] > 412 or r[1] < 8 or r[3] > 285:
            issues.append(('OUT OF SHEET', f'枠 {r}'))

    if verbose:
        used = [b for b in bodies]
        if used:
            print(f'  範囲 x[{min(b[0] for b in used):.0f},{max(b[2] for b in used):.0f}] '
                  f'y[{min(b[1] for b in used):.0f},{max(b[3] for b in used):.0f}] '
                  f'/ シンボル{len(bodies)} テキスト{len(texts)} 枠{len(rects)}')
        by = {}
        for kind, msg in issues:
            by.setdefault(kind, []).append(msg)
        for kind in sorted(by):
            print(f'  [{kind}] {len(by[kind])}件')
            for m in by[kind][:12]:
                print(f'      {m}')
            if len(by[kind]) > 12:
                print(f'      ... 他 {len(by[kind]) - 12} 件')
    return issues


def main(argv):
    names = [a for a in argv if not a.startswith('-')]
    if '--all' in argv or not names:
        names = BOARDS
    total = 0
    for n in names:
        n = n if n.startswith('build_') else f'build_{n.lower()}'
        sch = capture(n)
        print(f'=== {sch.name} ===')
        iss = check(sch)
        print(f'  --> 衝突 {len(iss)} 件')
        total += len(iss)
    print(f'合計 {total} 件')
    return 1 if total else 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
