"""RX_advanced.asc 検証 (4次スタガードMFB版):
 1) AC: f_peak≈200kHz, 利得≈60dB, BW≈80kHz, 帯域外抑圧 @400kHz が -20dBc 以下 (単段MFBは約-12dBc)
 2) 過渡(1mVバースト): コンパレータ発火、誤発火なし
 3) 過大入力 300mV/5V: クランプとオペアンプピン電流制限の確認
"""
import sys, re, json, shutil
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import ltspice_sim as lt

EXE = r'C:\Users\ryupc\AppData\Local\Programs\ADI\LTspice\LTspice.exe'
ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'LTspice' / 'RX_advanced.asc'


def edit(pattern, repl):
    s = P.read_text(encoding='ascii')
    s2, n = re.subn(pattern, repl, s)
    assert n == 1, f'pattern mismatch: {pattern} (n={n})'
    P.write_text(s2, encoding='ascii')


def set_analysis(ac: bool):
    s = P.read_text(encoding='ascii')
    if ac:
        s = s.replace('!.tran 0 300u 0 50n', ';.tran 0 300u 0 50n')
        s = s.replace(';.ac dec 200 1k 10Meg', '!.ac dec 200 1k 10Meg')
    else:
        s = s.replace(';.tran 0 300u 0 50n', '!.tran 0 300u 0 50n')
        s = s.replace('!.ac dec 200 1k 10Meg', ';.ac dec 200 1k 10Meg')
    P.write_text(s, encoding='ascii')


if __name__ == '__main__':
    out = {}
    set_analysis(ac=True)
    raw = str(lt.run_batch(str(P), ltspice_path=EXE))
    rr = lt.read_raw(raw)
    f = np.abs(np.array(rr.get_trace('frequency').get_wave()))
    h = np.abs(np.array(rr.get_trace('V(st3_out)').get_wave()))
    g_db = 20 * np.log10(np.maximum(h, 1e-30))
    i_pk = int(np.argmax(g_db))
    f_pk, g_pk = float(f[i_pk]), float(g_db[i_pk])
    above = np.where(g_db >= g_pk - 3.0)[0]
    bw = float(f[above[-1]] - f[above[0]])
    g400 = float(g_db[np.argmin(np.abs(f - 400e3))]) - g_pk
    g100 = float(g_db[np.argmin(np.abs(f - 100e3))]) - g_pk
    print(f'AC: f_peak={f_pk/1e3:.1f}kHz gain={g_pk:.2f}dB BW={bw/1e3:.1f}kHz  '
          f'rej@400k={g400:.1f}dBc rej@100k={g100:.1f}dBc')
    out['ac'] = dict(f_peak=f_pk, gain_db=g_pk, bw=bw, rej400=g400, rej100=g100)
    assert 190e3 < f_pk < 210e3, 'f0 out of range'
    assert 57 < g_pk < 63, 'gain not ~60dB'
    assert 60e3 < bw < 100e3, 'BW not ~80kHz'
    assert g400 < -20, 'out-of-band rejection @400k should beat single MFB (-12dBc)'
    assert g100 < -20, 'out-of-band rejection @100k insufficient'

    set_analysis(ac=False)
    edit(r'\.param Vin=\S+ Vth=\S+', '.param Vin=1m Vth=0.35')
    raw = str(lt.run_batch(str(P), ltspice_path=EXE))
    rr = lt.read_raw(raw)
    t = np.abs(np.array(rr.get_trace('time').get_wave()))
    cmp_ = np.array(rr.get_trace('V(cmp_out)').get_wave()).real
    env = np.array(rr.get_trace('V(env)').get_wave()).real
    pre = t < 15e-6
    fire_idx = np.where(cmp_ > 1.65)[0]
    t_fire = float(t[fire_idx[0]]) if len(fire_idx) else None
    print(f'tran1m: ENVmax={env.max():.3f}V CMPmax={cmp_.max():.2f}V pre-burst={cmp_[pre].max():.2f}V '
          f'fire@{t_fire*1e6:.1f}us' if t_fire else 'no fire')
    out['tran_1mV'] = dict(env_max=float(env.max()), cmp_max=float(cmp_.max()), t_fire=t_fire)
    assert cmp_.max() > 3.0, 'comparator did not fire at 1mV'
    assert cmp_[pre].max() < 0.5, 'false fire before burst'

    for vin, key, bmin, bmax in [('300m', 'overload_300mV', -0.8, 4.1), ('5', 'overload_5V', -1.0, 4.3)]:
        edit(r'\.param Vin=\S+ Vth=\S+', f'.param Vin={vin} Vth=0.35')
        raw = str(lt.run_batch(str(P), ltspice_path=EXE))
        inp_min = lt.measure_min(raw, 'V(st1_inp)')
        inp_max = lt.measure_max(raw, 'V(st1_inp)')
        u1_min = lt.measure_min(raw, 'V(u1_inp)')
        u1_max = lt.measure_max(raw, 'V(u1_inp)')
        print(f'over{vin}: ST1_INP={inp_min:.2f}..{inp_max:.2f}V  U1_INP={u1_min:.2f}..{u1_max:.2f}V')
        out[key] = dict(inp_min=inp_min, inp_max=inp_max, u1_min=u1_min, u1_max=u1_max)
        assert inp_min > bmin and inp_max < bmax, f'{vin} clamp failed'

    edit(r'\.param Vin=\S+ Vth=\S+', '.param Vin=1m Vth=0.35')
    d = ROOT / 'sim' / 'runs' / 'rx_advanced'
    d.mkdir(parents=True, exist_ok=True)
    (d / 'measure.json').write_text(json.dumps(out, indent=2))
    shutil.copy(P, d / P.name)
    print('ALL ASSERTS PASSED')
