r"""回路図を目視用 PNG にする(kicad-cli sch export svg -> headless Chrome)。

    python -X utf8 pcb\render_sch.py CHILD_PWR [PARENT_PWR ...]
    python -X utf8 pcb\render_sch.py --all

出力: pcb/<BOARD>/<BOARD>_sch.png (2600x1840 相当)。
cairosvg は Windows で DLL 不足のため使えない。headless Chrome が確実。
**目視は全チェック合格後に1回だけ**(トークン規律)。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from kicadgen import KICAD_CLI  # noqa: E402

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BOARDS = ['CHILD_MAIN', 'CHILD_PWR', 'PARENT_MAIN', 'PARENT_PWR']


def render(board: str, width=1590, height=1125, scale=1.8):
    """width/height は CSS px。A3 の SVG 自然サイズ(96dpi で約 1587x1123)に合わせると
    シートが画面いっぱいに出る。scale で実PNG解像度が決まる(1.8 -> 約2860x2025)。"""
    d = HERE / board
    sch = d / f'{board}.kicad_sch'
    if not sch.exists():
        raise SystemExit(f'{sch} が無い(先に build_*.py を回す)')
    svgdir = d / 'svg'
    r = subprocess.run([KICAD_CLI, 'sch', 'export', 'svg', '-o', str(svgdir),
                        '--no-background-color', str(sch)],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        raise SystemExit(r.stdout + r.stderr)
    svg = svgdir / f'{board}.svg'
    png = d / f'{board}_sch.png'
    subprocess.run([CHROME, '--headless=new', '--disable-gpu',
                    f'--screenshot={png}', f'--window-size={width},{height}',
                    f'--force-device-scale-factor={scale}',
                    '--default-background-color=FFFFFFFF',
                    svg.resolve().as_uri()],
                   capture_output=True, text=True)
    print(f'{board} -> {png}')
    return png


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    if '--all' in sys.argv or not args:
        args = BOARDS
    for b in args:
        render(b)
