"""TX_improved.asc 最終検証: 通常動作(9V/12V) + 故障ケース(トランスデューサ外れ)。
定格: 2SK4017 VDSS=60V, VGSS=+-20V, ID=5A (データシート値)。
"""
import sys, re, json, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import ltspice_sim as lt

EXE = r'C:\Users\ryupc\AppData\Local\Programs\ADI\LTspice\LTspice.exe'
ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'LTspice' / 'TX_improved.asc'

VDSS, VGSS, IDMAX = 60.0, 20.0, 5.0


def edit(pattern, repl):
    s = P.read_text(encoding='ascii')
    s2, n = re.subn(pattern, repl, s)
    assert n == 1, f'pattern not unique/found: {pattern} (n={n})'
    P.write_text(s2, encoding='ascii')


def run_case(vsup, c0):
    edit(r'\.param Vsup=\S+ C0=\S+', f'.param Vsup={vsup} C0={c0}')
    raw = str(lt.run_batch(str(P), ltspice_path=EXE))
    return dict(
        vsup=vsup, c0=c0,
        vds_max=lt.measure_max(raw, 'V(drain)'),
        vds_min=lt.measure_min(raw, 'V(drain)'),
        vg_max=lt.measure_max(raw, 'V(gate)'),
        vg_min=lt.measure_min(raw, 'V(gate)'),
        id_max=lt.measure_max(raw, 'Id(M1)'),
        itvs_d=lt.measure_max(raw, 'I(D_TVS_D)'),
        xd_pp=lt.measure_vpp(raw, 'V(xd)'),
    )


if __name__ == '__main__':
    out = []
    # 通常動作: 9V/12V
    for vs in (9, 12):
        r = run_case(vs, '1260p')
        out.append(r)
        print(f"normal  {vs:2d}V: Vds={r['vds_max']:6.2f}  Vgs={r['vg_max']:.2f}/{r['vg_min']:.2f}  "
              f"Id={r['id_max']:.3f}A  XDpp={r['xd_pp']:.2f}V  Itvs={r['itvs_d']*1e3:.1f}mA")
        assert r['vds_max'] < VDSS, 'VDSS exceeded'
        assert r['vds_max'] < VDSS * 0.8, 'derating 80% exceeded (normal op)'
        assert -VGSS < r['vg_min'] and r['vg_max'] < VGSS, 'VGS rating exceeded'
        assert r['id_max'] < IDMAX, 'ID rating exceeded'
    # 故障ケース: トランスデューサ外れ (C0を1fF=実質開放)
    for vs in (9, 12):
        r = run_case(vs, '1f')
        out.append(r)
        print(f"fault   {vs:2d}V: Vds={r['vds_max']:6.2f}  Vgs={r['vg_max']:.2f}/{r['vg_min']:.2f}  "
              f"Id={r['id_max']:.3f}A  Itvs={r['itvs_d']*1e3:.1f}mA")
        assert r['vds_max'] < VDSS, 'FAULT: VDSS exceeded even with TVS'
        assert -VGSS < r['vg_min'] and r['vg_max'] < VGSS, 'FAULT: VGS rating exceeded'
    # 元に戻す (12V, 1260p)
    edit(r'\.param Vsup=\S+ C0=\S+', '.param Vsup=12 C0=1260p')
    d = ROOT / 'sim' / 'runs' / 'tx_improved'
    d.mkdir(parents=True, exist_ok=True)
    (d / 'measure.json').write_text(json.dumps(out, indent=2))
    shutil.copy(P, d / P.name)
    print('ALL ASSERTS PASSED')
