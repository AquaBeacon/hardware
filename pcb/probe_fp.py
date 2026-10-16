"""フットプリントのパッドオフセット(回転別)とコートヤード寸法を出力する汎用プローブ。

使い方 (KiCad同梱pythonで):
    python probe_fp.py <Lib:Footprint> [<Lib:Footprint> ...]
    python probe_fp.py --list <Lib> [substr]      # ライブラリ内フットプリント名の一覧
例:
    python probe_fp.py Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal
    python probe_fp.py --list Fuse 5x20

出力: rot0/rot90/rot180/rot270 それぞれの原点からのパッドオフセット(mm)と
      コートヤード範囲。placements のコメントに書き写して配線の基礎データにする。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import pcbnew
from pcbgen import FPDIR

if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(1)

if sys.argv[1] == '--list':
    lib = sys.argv[2]
    sub = sys.argv[3] if len(sys.argv) > 3 else ''
    for p in sorted((FPDIR / f'{lib}.pretty').glob('*.kicad_mod')):
        if sub.lower() in p.stem.lower():
            print(p.stem)
    sys.exit(0)

board = pcbnew.CreateEmptyBoard()
for fpid in sys.argv[1:]:
    lib, name = fpid.split(':', 1)
    fp = pcbnew.FootprintLoad(str(FPDIR / f'{lib}.pretty'), name)
    if fp is None:
        print(f'{fpid}: NOT FOUND')
        continue
    board.Add(fp)
    fp.SetPosition(pcbnew.VECTOR2I(0, 0))
    print(name)
    for rot in (0, 90, 180, 270):
        fp.SetOrientationDegrees(rot)
        pads = {p.GetPadName(): (round(pcbnew.ToMM(p.GetPosition().x), 3),
                                 round(pcbnew.ToMM(p.GetPosition().y), 3))
                for p in fp.Pads()}
        print(f'  pads rot{rot}: {pads}')
    fp.SetOrientationDegrees(0)
    bb = fp.GetBoundingBox()
    cw = pcbnew.ToMM(bb.GetWidth()); ch = pcbnew.ToMM(bb.GetHeight())
    cx0 = pcbnew.ToMM(bb.GetLeft()); cy0 = pcbnew.ToMM(bb.GetTop())
    print(f'  courtyard rot0: x[{cx0:.2f},{cx0+cw:.2f}] y[{cy0:.2f},{cy0+ch:.2f}] ({cw:.1f}x{ch:.1f})')
    board.Remove(fp)
