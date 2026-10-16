"""TX_advanced.asc (FETプッシュプル版) 検証:
 1) Ltune同調スイープ (12V)
 2) Rdmpスイープで駆動振幅の調整レンジ確認 (目標 XDpp 200-300Vpp @12V)
 3) 9V/12V 通常 + 故障(振動子外れ) で定格チェック
定格: 2SK4017 VDSS=60V, VGSS=+-20V, ID=5A / MIC4427 peak 1.5A (ゲート電流)
"""
import sys, re, json, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import ltspice_sim as lt

EXE = r'C:\Users\ryupc\AppData\Local\Programs\ADI\LTspice\LTspice.exe'
ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'LTspice' / 'TX_advanced.asc'


def edit(pattern, repl):
    s = P.read_text(encoding='ascii')
    s2, n = re.subn(pattern, repl, s)
    assert n == 1, f'pattern not unique/found: {pattern} (n={n})'
    P.write_text(s2, encoding='ascii')


def run_case(vsup, c0, ltune, rdmp):
    edit(r'\.param Vsup=\S+ C0=\S+ Ltune=\S+ Rdmp=\S+',
         f'.param Vsup={vsup} C0={c0} Ltune={ltune} Rdmp={rdmp}')
    raw = str(lt.run_batch(str(P), ltspice_path=EXE))
    return dict(
        vsup=vsup, c0=c0, ltune=ltune, rdmp=rdmp,
        vds_a=lt.measure_max(raw, 'V(pa)'), vds_b=lt.measure_max(raw, 'V(pb)'),
        vga=(lt.measure_max(raw, 'V(ga)'), lt.measure_min(raw, 'V(ga)')),
        id_a=lt.measure_max(raw, 'Id(M_A)'),
        ia_drv=max(abs(lt.measure_max(raw, 'I(VA)')), abs(lt.measure_min(raw, 'I(VA)'))),
        v12_max=lt.measure_max(raw, 'V(v12)'),
        sec_pp=lt.measure_vpp(raw, 'V(sec)'),
        xd_pp=lt.measure_vpp(raw, 'V(xd)'),
    )


if __name__ == '__main__':
    # 1) 同調スイープ
    best = None
    for lu in (380, 420, 450, 480, 503):
        r = run_case(12, '1260p', f'{lu}u', 100)
        print(f"tune {lu}uH: XDpp={r['xd_pp']:7.1f}V SECpp={r['sec_pp']:6.1f}V Vds={r['vds_a']:.1f}")
        if best is None or r['xd_pp'] > best['xd_pp']:
            best = r
    lt_best = best['ltune']
    print(f'-> best Ltune = {lt_best}')

    # 2) Rdmpスイープ
    chosen = None
    for rd in (47, 100, 150, 220, 330):
        r = run_case(12, '1260p', lt_best, rd)
        print(f"Rdmp={rd:3d}: XDpp={r['xd_pp']:7.1f}V  Id_A={r['id_a']:.2f}A  Vds_A={r['vds_a']:.1f}V")
        if chosen is None and r['xd_pp'] <= 300:
            chosen = rd
    if chosen is None:
        chosen = 330
    print(f'-> Rdmp = {chosen} (XDpp <= 300Vpp @12V)')

    out = []
    for vs in (9, 12):
        r = run_case(vs, '1260p', lt_best, chosen)
        out.append(r)
        print(f"normal {vs:2d}V: XDpp={r['xd_pp']:7.1f}V  Vds={max(r['vds_a'], r['vds_b']):.1f}V  "
              f"Vg={r['vga'][0]:.1f}/{r['vga'][1]:.1f}  Id={r['id_a']:.2f}A  Idrv={r['ia_drv']:.2f}A  V12max={r['v12_max']:.2f}")
        assert max(r['vds_a'], r['vds_b']) < 48, 'FET Vds derating (48V) exceeded in normal op'
        assert -20 < r['vga'][1] and r['vga'][0] < 20, 'VGS rating exceeded'
        assert r['id_a'] < 5, 'FET current rating exceeded'
        assert r['ia_drv'] < 1.5, 'MIC4427 peak current exceeded'
        assert r['v12_max'] < 17, 'V12 rail spike'
    for vs in (9, 12):
        r = run_case(vs, '1f', lt_best, chosen)
        out.append(r)
        print(f"fault  {vs:2d}V: Vds={max(r['vds_a'], r['vds_b']):.1f}V  Id={r['id_a']:.2f}A  V12max={r['v12_max']:.2f}")
        assert max(r['vds_a'], r['vds_b']) < 60, 'FAULT: VDSS exceeded'
        assert r['id_a'] < 5, 'FAULT: FET current exceeded'
    edit(r'\.param Vsup=\S+ C0=\S+ Ltune=\S+ Rdmp=\S+',
         f'.param Vsup=12 C0=1260p Ltune={lt_best} Rdmp={chosen}')
    d = ROOT / 'sim' / 'runs' / 'tx_advanced'
    d.mkdir(parents=True, exist_ok=True)
    (d / 'measure.json').write_text(json.dumps(out, indent=2))
    shutil.copy(P, d / P.name)
    print('ALL ASSERTS PASSED')
