"""TX_improved.asc: TVS BVとVsupを振ってドレインピーク/クランプ動作を測定する。"""
import sys, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import ltspice_sim as lt

EXE = r'C:\Users\ryupc\AppData\Local\Programs\ADI\LTspice\LTspice.exe'
P = Path(__file__).resolve().parents[1] / 'LTspice' / 'TX_improved.asc'


def edit(pattern, repl):
    s = P.read_text(encoding='ascii')
    s2, n = re.subn(pattern, repl, s)
    assert n == 1, f'pattern not unique/found: {pattern} (n={n})'
    P.write_text(s2, encoding='ascii')


def run():
    raw = str(lt.run_batch(str(P), ltspice_path=EXE))
    return raw


if __name__ == '__main__':
    results = []
    for bv, label in [(200, 'no-clamp'), (44.4, 'SMBJ40A')]:
        edit(r'\.model SMBJ33A D\(BV=[0-9.]+', f'.model SMBJ33A D(BV={bv}')
        for vs in (9, 12):
            edit(r'\.param Vsup=\S+', f'.param Vsup={vs}')
            raw = run()
            row = dict(
                label=label, vsup=vs,
                vds_max=lt.measure_max(raw, 'V(drain)'),
                vds_min=lt.measure_min(raw, 'V(drain)'),
                itvs_max=lt.measure_max(raw, 'I(D_TVS_D)'),
                xd_pp=lt.measure_vpp(raw, 'V(xd)'),
                vg_max=lt.measure_max(raw, 'V(gate)'),
                vg_min=lt.measure_min(raw, 'V(gate)'),
                id_max=lt.measure_max(raw, 'Id(M1)'),
            )
            results.append(row)
            print(f"{label:8s} Vsup={vs:2d}: Vds={row['vds_max']:6.2f}/{row['vds_min']:6.2f}  "
                  f"Itvs={row['itvs_max']*1e3:8.2f}mA  XDpp={row['xd_pp']:6.2f}  "
                  f"Vg={row['vg_max']:.2f}/{row['vg_min']:.2f}  Id_max={row['id_max']:.3f}")
