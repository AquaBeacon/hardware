"""RXさらに改良版: 4次バターワースBPF(2段スタガードMFB)の設計計算。
LPプロトタイプ(2次バターワース) -> BP変換で2つの2次セクション(f0i, Qi)を求め、
MFB素子値 R1,R2,R3 (C=330p固定) を算出する。セクションゲインgは
中心周波数200kHzでの合成利得=2.0となるよう数値的に解く。
"""
import numpy as np

f0, bw = 200e3, 80e3
w0 = 2 * np.pi * f0
Qbp = f0 / bw
C = 330e-12

# 2次バターワースLPプロトタイプの極
lp_poles = [np.exp(1j * np.pi * 3 / 4), np.exp(1j * np.pi * 5 / 4)]

# BP変換 s_lp = Qbp*(s/w0 + w0/s) -> s^2 - (p*w0/Qbp)*s + w0^2 = 0
bp_poles = []
for p in lp_poles:
    a, b, c = 1.0, -p * w0 / Qbp, w0 ** 2
    bp_poles += list(np.roots([a, b, c]))
# 上半平面の極2つがセクションを定義
up = [p for p in bp_poles if p.imag > 0]
assert len(up) == 2
sections = []
for p in sorted(up, key=lambda z: abs(z)):
    w0i = abs(p)
    Qi = w0i / (2 * abs(p.real))
    sections.append((w0i, Qi))
    print(f'section: f0i={w0i/2/np.pi/1e3:.2f}kHz  Qi={Qi:.3f}')


def mfb_tf(w, w0i, Qi, g):
    # MFB BP: H(s) = -(g*w0i/Qi * s) / (s^2 + w0i/Qi*s + w0i^2)
    s = 1j * w
    return -(g * w0i / Qi * s) / (s ** 2 + w0i / Qi * s + w0i ** 2)


# 合成利得(200kHz)=2.0 となる g (両セクション同一) を解く
g = 1.0
for _ in range(50):
    h = abs(mfb_tf(w0, *sections[0], g) * mfb_tf(w0, *sections[1], g))
    g *= np.sqrt(2.0 / h)
print(f'section gain g = {g:.4f} (combined@200k = {abs(mfb_tf(w0, *sections[0], g)*mfb_tf(w0, *sections[1], g)):.4f})')

for i, (w0i, Qi) in enumerate(sections, 1):
    R2 = 2 * Qi / (w0i * C)
    R1 = R2 / (2 * g)
    inv_r3 = w0i ** 2 * C ** 2 * R2 - 1 / R1
    assert inv_r3 > 0, 'R3 infeasible: increase Q or lower g'
    R3 = 1 / inv_r3
    # 検証: 設計式に戻して f0, Q, G を確認
    f_chk = 1 / (2 * np.pi * C) * np.sqrt((1 / R2) * (1 / R1 + 1 / R3))
    Q_chk = np.pi * f_chk * C * R2
    G_chk = R2 / (2 * R1)
    print(f'MFB{i}: R1={R1:.1f} R2={R2:.1f} R3={R3:.1f}  (f0={f_chk/1e3:.2f}k Q={Q_chk:.3f} G={G_chk:.3f})')
    assert abs(f_chk - w0i / 2 / np.pi) < 1
# 帯域外改善の理論値: 4次 vs 2次 @400kHz
h2 = abs(mfb_tf(2 * w0, w0, 2.5, 2.0))
h4 = abs(mfb_tf(2 * w0, *sections[0], g) * mfb_tf(2 * w0, *sections[1], g))
print(f'@400kHz: single MFB {20*np.log10(h2/2):.1f}dBc vs staggered {20*np.log10(h4/2):.1f}dBc (vs center)')
