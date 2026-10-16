r"""PARENT_PWR: SW_TX の「活線投入」検証 (2026-08-03 レビューで判明した未検証ケース)。

既存の `parent_pwr_verify.py` は .ic で全ノード0Vからの**冷間投入**しか見ていない。
しかし SW_TX は「12V TX 出力だけを運用中に ON/OFF する」ためのトグルなので、実際は
**VBAT_M が 12.6V まで充電済みの状態で、放電しきった Ctx(TX基板 C1)へ閉じる**。

見るもの:
  1. SW_TX 接点を通る突入ピーク (トグル定格 3A に対して何倍か) と I^2t
  2. **VBAT_M / V5L / V3S のディップ** ← 本命。Cblk(100u) から Ctx へ電荷が抜けるので、
     TX を入れた瞬間に Pico(V5L 経由) やカメラが落ちないかを見る
  3. TXバースト時の TX 側 12V サグ (Ctx を減らす代償)

Ctx = 470u(現行) / 220u / 100u を掃引して対策の判断材料を作る。

実行: python sim\parent_pwr_swtx_verify.py
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402

from pwr_common import (  # noqa: E402
    ROOT, SW_TOGGLE_I, FUSE_I2T_FAST, LXDC55_VIN_MIN, Checks, load, run, wavg,
    wmax, wmin, wv,
)


def t_below(raw, t, name, level, t0, t1):
    """t0-t1 の窓で信号が level を下回っていた合計時間[s]。"""
    y = wv(raw, name)
    m = (t >= t0) & (t <= t1)
    tt, yy = t[m], y[m]
    if len(tt) < 2:
        return 0.0
    dt = np.diff(tt)
    return float(dt[(yy[:-1] < level)].sum())

CIR = ROOT / 'LTspice' / 'PARENT_PWR_SWTX.cir'

TSWTX = 10e-3
W_BEFORE = (8.0e-3, 9.9e-3)        # SW_TX 投入直前(定常)
W_EVENT = (10.0e-3, 10.6e-3)       # 活線投入イベント中
W_TXBURST = (15.0e-3, 15.12e-3)    # TXバースト中
W_PRETX = (14.0e-3, 14.9e-3)       # バースト直前

# Pico は VSYS 1.8-5.5V で動くが、P-MAIN の V5D は LXDC55 出力そのもの。
# ここでは「5Vレールが 4.5V を割らない」ことを実用上のブラウンアウト判定にする。
V5L_MIN_OK = 4.5
V3S_MIN_OK = 3.0


def edit(pattern, repl):
    s = CIR.read_text(encoding='utf-8')
    s2, n = re.subn(pattern, repl, s)
    assert n == 1, f'pattern not unique/found: {pattern} (n={n})'
    CIR.write_text(s2, encoding='utf-8')


def case(ctx_label, vbat0='12.6', required=True):
    edit(r'\.param CTX=\S+', f'.param CTX={ctx_label}')
    edit(r'\.param VBAT0=\S+', f'.param VBAT0={vbat0}')
    raw, t = load(run('PARENT_PWR_SWTX.cir'))
    c = Checks(f'SW_TX 活線投入  Ctx={ctx_label} / VBAT={vbat0}V')

    # --- 1. 接点を通る突入 ---
    ipk = wmax(raw, t, 'I(Rsns)', *W_EVENT)
    i2t = wmax(raw, t, 'V(ni2ttx)')
    c.info('SW_TX 突入ピーク', f'{ipk:.1f} A '
           f'(トグル定格 {SW_TOGGLE_I:.0f}A の {ipk / SW_TOGGLE_I:.0f}倍)')
    c.info('SW_TX 突入 I^2t', f'{i2t:.4f} A^2s')
    if required:
        c.le('SW_TX 突入 I^2t < 速断3Aヒューズ溶断I^2t', i2t, FUSE_I2T_FAST, ' A^2s',
             '(TX を入れてもヒューズは飛ばない)')

    # --- 2. 活線投入で他レールが落ちないか(本命) ---
    vbm0 = wavg(raw, t, 'V(vbatm)', *W_BEFORE)
    vbm_dip = vbm0 - wmin(raw, t, 'V(vbatm)', *W_EVENT)
    v5l_min = wmin(raw, t, 'V(v5l)', *W_EVENT)
    v3s_min = wmin(raw, t, 'V(v3s)', *W_EVENT)
    # LXDC55 の Vin 窓を割っている時間(割ればロジック5Vが規格外動作になる)
    t_uv = t_below(raw, t, 'V(vbatm)', LXDC55_VIN_MIN, *W_EVENT)
    c.info('投入直前 VBAT_M', f'{vbm0:.3f} V')
    c.info('活線投入時 VBAT_M ディップ', f'{vbm_dip:.3f} V')
    c.info(f'VBAT_M が LXDC55 Vin下限({LXDC55_VIN_MIN}V)を割った時間',
           f'{t_uv * 1e6:.0f} us')
    if required:
        c.ge('活線投入時 V5L 最小値', v5l_min, V5L_MIN_OK, ' V', '(ロジック5Vが落ちない)')
        c.ge('活線投入時 V3S 最小値', v3s_min, V3S_MIN_OK, ' V', '(3.3V系が落ちない)')
    else:
        c.info('活線投入時 V5L 最小値', f'{v5l_min:.3f} V')
        c.info('活線投入時 V3S 最小値', f'{v3s_min:.3f} V')

    # --- 3. Ctx を減らす代償: TXバースト時のサグ ---
    vtx0 = wavg(raw, t, 'V(ntx)', *W_PRETX)
    vtx_sag = vtx0 - wmin(raw, t, 'V(ntx)', *W_TXBURST)
    c.info('TXバースト時 TX基板12Vレール サグ', f'{vtx_sag:.3f} V')
    if required:
        c.le('TXバースト時 TX基板12Vレール サグ', vtx_sag, 0.5, ' V')

    return c, dict(ctx=ctx_label, vbat0=vbat0, ipk_a=ipk, i2t=i2t,
                   vbatm_dip=vbm_dip, vbatm_min=vbm0 - vbm_dip, t_uv_us=t_uv * 1e6,
                   v5l_min=v5l_min, v3s_min=v3s_min, vtx_sag=vtx_sag)


def main():
    results, checks = [], []
    # 現行(470u)は「今どうなっているか」を知るためのケースなのでアサートせず数値だけ採る。
    # **電池終止電圧(9.0V)が本番の最悪条件**: VBAT_M のディップが同じだけ出ると
    # LXDC55 の入力窓を割ってロジック5Vが落ちる。ここを必ず見る。
    cases = (
        ('470u', '12.6', False), ('220u', '12.6', False), ('100u', '12.6', False),
        ('470u', '9.0', False), ('220u', '9.0', False), ('100u', '9.0', False),
    )
    for label, vbat0, required in cases:
        c, r = case(label, vbat0=vbat0, required=required)
        checks.append(c)
        results.append(r)

    # .cir を現行値へ戻す(掃引の副作用でファイルを書き換えたままにしない)
    edit(r'\.param CTX=\S+', '.param CTX=470u')
    edit(r'\.param VBAT0=\S+', '.param VBAT0=12.6')

    print()
    print('=== SW_TX 活線投入 まとめ ===')
    print(f'{"VBAT":>5} {"Ctx":>6} | {"突入ピーク":>9} | {"I^2t":>8} | '
          f'{"VBAT_M最小":>10} | {"Vin窓割れ":>9} | {"V5L min":>8} | {"TXサグ":>7}')
    for r in results:
        print(f'{r["vbat0"]:>5} {r["ctx"]:>6} | {r["ipk_a"]:8.1f}A | {r["i2t"]:7.4f} | '
              f'{r["vbatm_min"]:9.3f}V | {r["t_uv_us"]:8.0f}us | {r["v5l_min"]:7.3f}V | '
              f'{r["vtx_sag"]:6.3f}V')

    (ROOT / 'sim' / 'parent_pwr_swtx_results.json').write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')

    ok = all(c.report() for c in checks)
    print()
    print('ALL ASSERTS PASSED' if ok else 'SOME CHECKS FAILED')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
