"""RX_improved.asc 検証:
 1) AC解析: チェーン利得のピーク周波数≈200kHz、ピーク利得≈60dB、-3dB帯域幅≈80kHz(BPF支配)
 2) 過渡解析(1mVバースト): 包絡線が立ち上がりコンパレータが発火、バースト前は無発火
 3) 過大入力(300mV): 初段入力がクランプ範囲内(-0.7 .. 4.0V)
"""
import sys, re, json, shutil
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import ltspice_sim as lt

EXE = r'C:\Users\ryupc\AppData\Local\Programs\ADI\LTspice\LTspice.exe'
ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'LTspice' / 'RX_improved.asc'


def edit(pattern, repl, count=1):
    s = P.read_text(encoding='ascii')
    s2, n = re.subn(pattern, repl, s)
    assert n == count, f'pattern mismatch: {pattern} (n={n})'
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
    # --- AC ---
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
    print(f'AC: f_peak={f_pk/1e3:.1f}kHz  gain={g_pk:.2f}dB  BW(-3dB)={bw/1e3:.1f}kHz')
    out['ac'] = dict(f_peak=f_pk, gain_db=g_pk, bw=bw)
    assert 190e3 < f_pk < 210e3, 'f0 out of range'
    assert 57 < g_pk < 63, 'gain not ~60dB'
    assert 60e3 < bw < 100e3, 'BW not ~80kHz'

    # --- tran 1mV ---
    set_analysis(ac=False)
    edit(r'\.param Vin=\S+ Vth=\S+', '.param Vin=1m Vth=0.35')
    raw = str(lt.run_batch(str(P), ltspice_path=EXE))
    rr = lt.read_raw(raw)
    t = np.abs(np.array(rr.get_trace('time').get_wave()))
    cmp_ = np.array(rr.get_trace('V(cmp_out)').get_wave()).real
    env = np.array(rr.get_trace('V(env)').get_wave()).real
    pre = t < 15e-6
    print(f'tran1m: ENVmax={env.max():.3f}V  CMPmax={cmp_.max():.2f}V  CMP(pre-burst)max={cmp_[pre].max():.2f}V')
    fire_idx = np.where(cmp_ > 1.65)[0]
    t_fire = float(t[fire_idx[0]]) if len(fire_idx) else None
    print(f'  first fire at t={t_fire*1e6:.1f}us (burst starts 20us)' if t_fire else '  no fire')
    out['tran_1mV'] = dict(env_max=float(env.max()), cmp_max=float(cmp_.max()), t_fire=t_fire)
    assert cmp_.max() > 3.0, 'comparator did not fire at 1mV input'
    assert cmp_[pre].max() < 0.5, 'comparator fired before burst'

    # --- overload 300mV ---
    edit(r'\.param Vin=\S+ Vth=\S+', '.param Vin=300m Vth=0.35')
    raw = str(lt.run_batch(str(P), ltspice_path=EXE))
    inp_max = lt.measure_max(raw, 'V(st1_inp)')
    inp_min = lt.measure_min(raw, 'V(st1_inp)')
    cmp_max = lt.measure_max(raw, 'V(cmp_out)')
    print(f'over300m: ST1_INP={inp_min:.2f}..{inp_max:.2f}V  CMPmax={cmp_max:.2f}')
    out['overload_300mV'] = dict(inp_min=inp_min, inp_max=inp_max, cmp_max=cmp_max)
    assert inp_min > -0.8 and inp_max < 4.1, 'input clamp failed'
    assert cmp_max > 3.0, 'comparator should still fire on strong signal'

    # --- 過大入力 5V (TX近接ブラスト相当): R_IN=100 がクランプ電流を制限 ---
    edit(r'\.param Vin=\S+ Vth=\S+', '.param Vin=5 Vth=0.35')
    raw = str(lt.run_batch(str(P), ltspice_path=EXE))
    inp_max = lt.measure_max(raw, 'V(st1_inp)')
    inp_min = lt.measure_min(raw, 'V(st1_inp)')
    print(f'over5V:   ST1_INP={inp_min:.2f}..{inp_max:.2f}V')
    out['overload_5V'] = dict(inp_min=inp_min, inp_max=inp_max)
    assert inp_min > -1.0 and inp_max < 4.3, '5V input clamp failed'

    edit(r'\.param Vin=\S+ Vth=\S+', '.param Vin=1m Vth=0.35')
    d = ROOT / 'sim' / 'runs' / 'rx_improved'
    d.mkdir(parents=True, exist_ok=True)
    (d / 'measure.json').write_text(json.dumps(out, indent=2))
    shutil.copy(P, d / P.name)
    print('ALL ASSERTS PASSED')
