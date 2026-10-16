"""実 F.CrtYd(コートヤード)だけの外形寸法を出す。配置設計の一次データ。

probe_fp.py の "courtyard" は `fp.GetBoundingBox()` = Ref/Value テキストまで含む
バウンディングボックスなので過大になる(GH4 で 43.5mm 等)。実際に配置の可否を
決めるのは F.CrtYd なのでこちらを使う。

pcbnew に依存しない(.kicad_mod を直接読む)ので**普通の python で実行できる**。
KiCad 10 の swig は GetCourtyard()/GraphicalItems() が不安定なため意図的に使わない。

    python probe_crtyd.py <Lib:Footprint> [...]

回転の規則は KiCad と同じ: rot90 (x,y)->(y,-x) / rot180 (-x,-y) / rot270 (-y,x)。
"""
import re
import sys
from pathlib import Path

FPDIRS = [
    Path(r'C:\Program Files\KiCad\10.0\share\kicad\footprints'),
    Path(__file__).parent / 'footprints',
]
NUM = re.compile(r'-?\d+\.?\d*')
COORD_KEYS = ('(start ', '(end ', '(center ', '(mid ', '(xy ')


def find_fp(fpid):
    lib, name = fpid.split(':', 1)
    for d in FPDIRS:
        p = d / f'{lib}.pretty' / f'{name}.kicad_mod'
        if p.exists():
            return p
    return None


def elements(text):
    """トップレベルの (fp_*/gr_* ...) 要素を括弧の対応で切り出す。"""
    for m in re.finditer(r'\((fp_|gr_)\w+', text):
        i = m.start()
        depth = 0
        for j in range(i, len(text)):
            if text[j] == '(':
                depth += 1
            elif text[j] == ')':
                depth -= 1
                if depth == 0:
                    yield text[i:j + 1]
                    break


def crtyd_bbox(path):
    text = path.read_text(encoding='utf-8', errors='replace')
    xs, ys = [], []
    for el in elements(text):
        if 'CrtYd' not in el:
            continue
        if el.startswith('(fp_circle') or el.startswith('(gr_circle'):
            # 円は center と end(円周上の一点)で書かれる → 半径を展開しないと
            # bbox が線分になってしまう(CP_Radial / MountingHole が該当)。
            c = NUM.findall(el[el.find('(center '):][:60])
            e = NUM.findall(el[el.find('(end '):][:60])
            if len(c) >= 2 and len(e) >= 2:
                cx, cy = float(c[0]), float(c[1])
                r = ((float(e[0]) - cx) ** 2 + (float(e[1]) - cy) ** 2) ** 0.5
                xs += [cx - r, cx + r]
                ys += [cy - r, cy + r]
                continue
        for key in COORD_KEYS:
            pos = 0
            while True:
                k = el.find(key, pos)
                if k < 0:
                    break
                nums = NUM.findall(el[k:k + 60])
                if len(nums) >= 2:
                    xs.append(float(nums[0]))
                    ys.append(float(nums[1]))
                pos = k + 1
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def rotated(bb, rot):
    x0, y0, x1, y1 = bb
    corners = [(x0, y0), (x1, y0), (x0, y1), (x1, y1)]
    if rot == 90:
        corners = [(y, -x) for x, y in corners]
    elif rot == 180:
        corners = [(-x, -y) for x, y in corners]
    elif rot == 270:
        corners = [(-y, x) for x, y in corners]
    xs = [c[0] for c in corners]
    ys = [c[1] for c in corners]
    return min(xs), min(ys), max(xs), max(ys)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    rc = 0
    for fpid in sys.argv[1:]:
        p = find_fp(fpid)
        if p is None:
            print(f'{fpid}: NOT FOUND')
            rc = 1
            continue
        bb = crtyd_bbox(p)
        print(p.stem)
        if bb is None:
            print('  NO F.CrtYd')
            rc = 1
            continue
        for rot in (0, 90, 180, 270):
            x0, y0, x1, y1 = rotated(bb, rot)
            print(f'  crtyd rot{rot}: x[{x0:.2f},{x1:.2f}] y[{y0:.2f},{y1:.2f}]'
                  f'  ({x1 - x0:.2f} x {y1 - y0:.2f})')
    return rc


if __name__ == '__main__':
    sys.exit(main())
