"""各基板の .kicad_pcb を 3Dモデル(部品込み)としてエクスポートする。

出力先は pcb/3d/ (基板ディレクトリには一切書き込まない = 他エージェントとの衝突回避)。
  <board>.step       銅箔+シルク+レジスト+部品。機械CAD/Fusion/FreeCAD 用
  <board>.glb        同上。ブラウザ/Windows "3D ビューアー" でそのまま開ける
  <board>_mech.stl   基板外形+部品のみ(銅箔なし)。筐体干渉チェック/OpenSCAD import 用

使い方:
  & "C:\\Program Files\\KiCad\\10.0\\bin\\kicad-cli.exe" は内部で呼ぶので普通のpythonでよい
  python -X utf8 pcb\\export_3d.py                 # 全基板 (UI_BOARD は廃止なので除外)
  python -X utf8 pcb\\export_3d.py CHILD_MAIN       # 基板指定
  python -X utf8 pcb\\export_3d.py --no-stl         # STL を作らない
  python -X utf8 pcb\\export_3d.py --list           # 対象一覧だけ表示

3Dモデル未割当の部品は「見えない部品」になるので、実行後に必ず警告一覧を確認する。
footprints/AquaBeacon.pretty の自作FPは (model) 行を持たないため無警告で欠落する
-> スクリプトが .kicad_pcb を走査して "no 3D model assigned" として別途報告する。
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

KICAD_CLI = r'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe'
HERE = Path(__file__).parent
OUTDIR = HERE / '3d'

# UI基板は2026-07-23に廃止(C/P-MAINへ統合)。_test はパイプラインのテスト用。
SKIP = {'UI_BOARD', '_test'}

# 銅箔まで含める指定 (STEP/GLB用)。STLは機械外形だけにするので付けない。
COPPER_OPTS = ['--include-tracks', '--include-pads', '--include-zones',
               '--include-silkscreen', '--include-soldermask']


def boards():
    found = []
    for pcb in sorted(HERE.glob('*/*.kicad_pcb')):
        if pcb.parent.name in SKIP or pcb.stem != pcb.parent.name:
            continue
        found.append(pcb)
    return found


def run(fmt, pcb, out, extra):
    cmd = [KICAD_CLI, 'pcb', 'export', fmt, '--subst-models', *extra,
           '-f', '-o', str(out), str(pcb)]
    p = subprocess.run(cmd, capture_output=True, text=True, errors='replace')
    log = (p.stdout or '') + (p.stderr or '')
    if p.returncode != 0 or not out.exists():
        print('  [FAIL] %s: rc=%d' % (fmt, p.returncode))
        print('  ' + log.strip().replace('\n', '\n  '))
        return None
    print('  [ OK ] %-4s %8.1f KB  %s' % (fmt, out.stat().st_size / 1024, out.name))
    return log


def missing_models(pcb):
    """(model)行を持たないフットプリントの ref を返す = 3Dモデル未割当で無警告に欠落する部品。"""
    txt = pcb.read_text(encoding='utf-8', errors='replace')
    out = []
    # footprint ブロックを素朴に切り出す(生成物は1行1要素の整形済みなので括弧深さで足りる)
    # KiCad 10 の footprint は行頭カラム0から始まる(インデント前提にすると全件取り逃す)
    for m in re.finditer(r'(?m)^[ \t]*\(footprint ', txt):
        start = m.end() - len('(footprint ')
        depth, i = 0, start
        while i < len(txt):
            if txt[i] == '(':
                depth += 1
            elif txt[i] == ')':
                depth -= 1
                if depth == 0:
                    break
            elif txt[i] == '"':                      # 文字列内の括弧は数えない
                i += 1
                while i < len(txt) and txt[i] != '"':
                    i += 2 if txt[i] == '\\' else 1
            i += 1
        block = txt[start:i + 1]
        if '(model ' in block:
            continue
        ref = re.search(r'\(property "Reference" "([^"]*)"', block)
        fp = re.search(r'\(footprint "([^"]*)"', block)
        out.append((ref.group(1) if ref else '?', fp.group(1) if fp else '?'))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('board', nargs='*', help='基板名 (省略時は全基板)')
    ap.add_argument('--no-stl', action='store_true')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--gaps', action='store_true', help='エクスポートせず3Dモデル欠落だけ調べる')
    a = ap.parse_args()

    targets = boards()
    if a.board:
        want = {b.rstrip('/\\').upper() for b in a.board}
        targets = [p for p in targets if p.stem.upper() in want]
        if not targets:
            sys.exit('no such board: %s' % a.board)
    if a.list:
        for p in targets:
            print(p.stem)
        return

    OUTDIR.mkdir(exist_ok=True)
    warns, gaps = {}, {}
    for pcb in targets:
        name = pcb.stem
        print('== %s' % name)
        logs = []
        for fmt, ext, extra in (('step', '.step', COPPER_OPTS),
                                ('glb', '.glb', COPPER_OPTS),
                                ('stl', '_mech.stl', [])):
            if a.gaps or (fmt == 'stl' and a.no_stl):
                continue
            log = run(fmt, pcb, OUTDIR / (name + ext), extra)
            if log:
                logs.append(log)
        w = sorted(set(re.findall(r'Could not add 3D model for (\S+?)\.', '\n'.join(logs))))
        if w:
            warns[name] = w
        g = missing_models(pcb)
        if g:
            gaps[name] = g

    print('\n---- 3D model gaps (これらは3Dに出てこない) ----')
    if not warns and not gaps:
        print('none')
    for name in sorted(set(warns) | set(gaps)):
        print('[%s]' % name)
        for ref in warns.get(name, []):
            print('  model file missing : %s' % ref)
        for ref, fp in gaps.get(name, []):
            print('  no model assigned  : %-8s %s' % (ref, fp))
    print('\nout: %s' % OUTDIR)


if __name__ == '__main__':
    main()
