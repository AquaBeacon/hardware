"""build_*.py の placements だけを取り出してコートヤード重なり/盤外/端クリアランスを検査する。

build() を差し替えて回路図生成・ERC・DRCを走らせずに配置のみ検証するので、
配置を詰める(小型化)ときの反復が安い。ASCIIマップも出すので空き領域の把握に使う。

使い方 (KiCad同梱python必須 = pcbnew):
    & "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" -u pcb\\check_placement.py build_child_main
オプション: --map で ASCIIマップ, --cell N でマップ解像度(mm/文字, 既定2)
"""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import pcbnew  # noqa: E402
import buildlib  # noqa: E402
from pcbgen import load_footprint  # noqa: E402

CAP = {}


def _fake_build(name, parts, placements, board_rect, **kw):
    CAP.update(name=name, parts=parts, placements=placements, rect=board_rect)
    return True, ''


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    show_map = '--map' in sys.argv
    cell = 2.0
    if '--cell' in sys.argv:
        cell = float(sys.argv[sys.argv.index('--cell') + 1])
    if not args:
        print(__doc__)
        return 1
    buildlib.build = _fake_build
    __import__(args[0])
    parts, placements = CAP['parts'], CAP['placements']
    x0, y0, x1, y1 = CAP['rect']
    print(f"[{CAP['name']}] board {x1 - x0:.1f} x {y1 - y0:.1f} mm "
          f"({(x1 - x0) * (y1 - y0):.0f} mm2), {len(parts)} parts")

    board = pcbnew.CreateEmptyBoard()
    boxes, padlist, area = {}, [], 0.0
    for p in parts:
        if p.ref not in placements:
            print(f'  !! placement missing: {p.ref}')
            continue
        fp = load_footprint(p.footprint)
        if fp is None:
            print(f'  !! footprint not found: {p.ref} {p.footprint}')
            continue
        board.Add(fp)
        pl = placements[p.ref]
        fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(pl[0]), pcbnew.FromMM(pl[1])))
        fp.SetOrientationDegrees(pl[2])
        # コートヤード優先(無ければパッド外形)。GetBoundingBox()はシルク文字を含むので使わない
        xs, ys = [], []
        for g in fp.GraphicalItems():
            if g.GetLayerName() in ('F.Courtyard', 'B.Courtyard'):
                bb = g.GetBoundingBox()
                xs += [pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetRight())]
                ys += [pcbnew.ToMM(bb.GetTop()), pcbnew.ToMM(bb.GetBottom())]
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            padlist.append((p.ref, pad.GetPadName(),
                            pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetRight()),
                            pcbnew.ToMM(bb.GetTop()), pcbnew.ToMM(bb.GetBottom())))
            if not xs:
                xs += [pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetRight())]
                ys += [pcbnew.ToMM(bb.GetTop()), pcbnew.ToMM(bb.GetBottom())]
        if not xs:
            continue
        bx = (min(xs), max(xs), min(ys), max(ys))
        boxes[p.ref] = bx
        area += (bx[1] - bx[0]) * (bx[3] - bx[2])

    print(f'  courtyard total {area:.0f} mm2 = {100 * area / ((x1 - x0) * (y1 - y0)):.0f}% fill')

    bad = 0
    refs = sorted(boxes)
    for i, a in enumerate(refs):
        ax0, ax1, ay0, ay1 = boxes[a]
        for b in refs[i + 1:]:
            bx0, bx1, by0, by1 = boxes[b]
            ox = min(ax1, bx1) - max(ax0, bx0)
            oy = min(ay1, by1) - max(ay0, by0)
            if ox > 0.001 and oy > 0.001:
                print(f'  OVERLAP {a} x {b}: {ox:.2f} x {oy:.2f} mm')
                bad += 1
    for r in refs:
        ax0, ax1, ay0, ay1 = boxes[r]
        if ax0 < x0 - 0.001 or ay0 < y0 - 0.001 or ax1 > x1 + 0.001 or ay1 > y1 + 0.001:
            print(f'  OUTSIDE {r}: x[{ax0:.2f},{ax1:.2f}] y[{ay0:.2f},{ay1:.2f}]')
            bad += 1
    # パッド-基板端 (銅箔は端から0.5mm以上離す。ルータの盤外マージンも0.6mm)
    for (ref, pn, px0, px1, py0, py1) in padlist:
        d = min(px0 - x0, y1 - py1, x1 - px1, py0 - y0)
        if d < 0.5:
            print(f'  EDGE {ref}.{pn}: {d:.2f} mm from board edge')
            bad += 1

    if show_map:
        nx = int((x1 - x0) / cell) + 1
        ny = int((y1 - y0) / cell) + 1
        grid = [[' '] * nx for _ in range(ny)]
        pool = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
        print('  ' + ' '.join(f'{pool[k % len(pool)]}={r}' for k, r in enumerate(refs)))
        for k, r in enumerate(refs):
            ch = pool[k % len(pool)]
            ax0, ax1, ay0, ay1 = boxes[r]
            for iy in range(max(0, int((ay0 - y0) / cell)), min(ny, int((ay1 - y0) / cell) + 1)):
                for ix in range(max(0, int((ax0 - x0) / cell)), min(nx, int((ax1 - x0) / cell) + 1)):
                    grid[iy][ix] = ch
        print('  ' + '-' * nx)
        for iy, row in enumerate(grid):
            print(f'{y0 + iy * cell:5.0f}|' + ''.join(row) + '|')
        print('  ' + '-' * nx)

    print('placement OK' if not bad else f'placement ISSUES: {bad}')
    return 0 if not bad else 2


if __name__ == '__main__':
    sys.exit(main())
