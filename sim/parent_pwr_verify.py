r"""PARENT_PWR (P-PWR) 電源基板の検証。

  1) 通常動作 (VBAT=12.6V 満充電 / 9.0V 終止)
     - SW_PWR ON のまま XT30 を挿した最悪突入
     - V5L(ロジック)/V5C(カメラ)/V3S レール成立、LXDC55入力窓 6-14V
     - Pi Zero 2W 起動ステップ (0.4A -> 1.2A @5V)
     - TXバースト (100us, 平均0.8A) による VBAT_M / TX基板レールのサグ
     - REG3S(NJU7223F33 TO-220F 放熱器なし)の熱
  2) 逆接続 (XT30裏返し) — CHILD と同じ保護チェーン

実行: python sim\parent_pwr_verify.py
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pwr_common import (  # noqa: E402
    FUSE_I2T_FAST, FUSE_I2T_NORM, FUSE_I2T_SLOW, LXDC55_IOUT, LXDC55_VIN_MAX,
    LXDC55_VIN_MIN, NJU7223_IOUT, NJU7223_RTH_JA, Q1_VDSS, Q1_VGSS,
    ROOT, SW_TOGGLE_I, TVS_IFSM, TVS_VRWM, Checks, load, run, tcross,
    wavg, wmax, wmin,
)

NORMAL = ROOT / 'LTspice' / 'PARENT_PWR.cir'
REV = ROOT / 'LTspice' / 'PARENT_PWR_rev.cir'

TCON = 200e-6
W_STEADY = (5e-3, 9.5e-3)        # 起動完了・カメラアイドル
W_CAM = (11e-3, 14.5e-3)         # カメラ 1.2A ステップ後
W_TX = (15.0e-3, 15.12e-3)       # TXバースト中
W_STEP3S = (21e-3, 24.5e-3)      # V3S +100mA 後
MYMGK_IOUT = 6.0                 # PS_B(Murata MYMGK)想定


def edit(path, pattern, repl):
    s = path.read_text(encoding='utf-8')
    s2, n = re.subn(pattern, repl, s)
    assert n == 1, f'pattern not unique/found: {pattern} (n={n}) in {path.name}'
    path.write_text(s2, encoding='utf-8')


def case_normal(vbat0):
    edit(NORMAL, r'\.param VBAT0=\S+', f'.param VBAT0={vbat0}')
    raw, t = load(run('PARENT_PWR.cir'))
    c = Checks(f'PARENT_PWR 通常動作 VBAT={vbat0}V')

    # --- 投入突入 ---
    inrush = wmax(raw, t, 'I(Rfuse)')
    i2t = wmax(raw, t, 'V(ni2t)')
    c.info('突入ピーク電流(F1/SW_PWR/Q1)', f'{inrush:.1f} A '
           f'(トグル定格{SW_TOGGLE_I:.0f}A の {inrush / SW_TOGGLE_I:.0f}倍)')
    c.le('突入I2t < 速断3Aヒューズ溶断I2t', i2t, FUSE_I2T_FAST, ' A^2s', '(投入で飛ばない)')
    c.le('Q1突入ピーク損失', wmax(raw, t, 'V(npq1)'), 200.0, ' W', '(単発, SOA内)')

    # --- 入力保護チェーン ---
    c.le('VBAT_F 最大 < TVS VRWM', wmax(raw, t, 'V(vbatf)'), TVS_VRWM, ' V')
    c.le('|Vgs(Q1)| < VGSS', abs(wmin(raw, t, 'V(nvgs1)')), Q1_VGSS, ' V')
    c.le('|Vds(Q1)| < VDSS*0.8', abs(wmin(raw, t, 'V(nvds1)')), Q1_VDSS * 0.8, ' V')
    p_q1 = wavg(raw, t, 'V(npq1)', *W_CAM)
    c.le('Q1定常損失(カメラ1.2A時)', p_q1, 1.0, ' W', f'(Tj上昇 {p_q1 * 62.5:.1f}K @62.5K/W)')

    # --- 全負荷での電池電流 (F1 3A / トグル 3A に対する連続定格) ---
    itot = wavg(raw, t, 'I(Rfuse)', *W_TX)
    c.le('最大同時負荷時の電池電流(カメラ+TX)', itot, SW_TOGGLE_I, ' A', '(F1=3A, トグル=3A)')

    # --- レール ---
    c.between('LXDC55入力 VBAT_M (TXバースト中)', wmin(raw, t, 'V(vbatm)', *W_TX),
              LXDC55_VIN_MIN, LXDC55_VIN_MAX, ' V')
    c.between('V5L 定常', wavg(raw, t, 'V(v5l)', *W_STEADY), 4.75, 5.25, ' V')
    c.between('V5C カメラ1.2A時', wavg(raw, t, 'V(v5c)', *W_CAM), 4.75, 5.25, ' V')
    c.between('V3S 定常', wavg(raw, t, 'V(v3s)', *W_STEADY), 3.20, 3.40, ' V')
    c.between('V3S (+100mAステップ時)', wavg(raw, t, 'V(v3s)', *W_STEP3S), 3.20, 3.40, ' V')
    c.le('LXDC55(PS_A) 出力電流', wavg(raw, t, 'I(V5Ls)', *W_STEP3S), LXDC55_IOUT, ' A')
    c.le('PS_B 出力電流', wavg(raw, t, 'I(V5Cs)', *W_CAM), MYMGK_IOUT, ' A')
    i3s = wavg(raw, t, 'I(V3Ss)', *W_STEP3S)
    c.le('REG3S 出力電流', i3s, NJU7223_IOUT, ' A')
    p3s = wavg(raw, t, 'V(npldo)', *W_STEP3S)
    c.le('REG3S 損失 -> Tj上昇', p3s * NJU7223_RTH_JA, 65.0, ' K',
         f'({p3s:.2f}W x {NJU7223_RTH_JA:.0f}K/W, Ta=40degC想定で Tj<105degC)')

    # --- TXバースト時のレール変動 ---
    vtx_sag = wavg(raw, t, 'V(ntx)', *W_CAM) - wmin(raw, t, 'V(ntx)', *W_TX)
    vbm_sag = wavg(raw, t, 'V(vbatm)', *W_CAM) - wmin(raw, t, 'V(vbatm)', *W_TX)
    c.le('TXバースト時 VBAT_M サグ', vbm_sag, 0.5, ' V')
    c.le('TXバースト時 TX基板12Vレール サグ', vtx_sag, 0.5, ' V')

    return c, dict(vbat0=vbat0, inrush_a=inrush, i2t=i2t,
                   i_total_a=itot, vbatm_min=wmin(raw, t, 'V(vbatm)', *W_TX),
                   v5l=wavg(raw, t, 'V(v5l)', *W_STEADY),
                   v5c=wavg(raw, t, 'V(v5c)', *W_CAM),
                   v3s=wavg(raw, t, 'V(v3s)', *W_STEADY),
                   reg3s_p=p3s, q1_p=p_q1,
                   vbatm_sag=vbm_sag, vtx_sag=vtx_sag)


def case_rev(i2t_melt, label, required=True):
    """required=False のケースは「使ってはいけない構成」の実証(NGでも全体は落とさない)。"""
    edit(REV, r'\.param I2TMELT=\S+', f'.param I2TMELT={i2t_melt}')
    raw, t = load(run('PARENT_PWR_rev.cir'))
    c = Checks(f'PARENT_PWR 逆接続 ヒューズ{label} (溶断I2t={i2t_melt} A^2s)'
               + ('' if required else ' ※採用不可の実証'))

    ipk = abs(wmin(raw, t, 'I(Rfuse)'))
    tblow = tcross(raw, t, 'V(ni2t)', i2t_melt * 0.999) - TCON
    tvs_i2t = wmax(raw, t, 'V(ni2ttvs)')
    c.info('逆接短絡電流ピーク', f'{ipk:.1f} A (TVS順方向)')
    c.info('ヒューズ溶断時間', f'{tblow * 1e3:.2f} ms')
    tvs_ok = (ipk <= TVS_IFSM) and (tvs_i2t <= 41.5 * 0.5)
    if required:
        c.le('TVS順方向ピーク < IFSM', ipk, TVS_IFSM, ' A', '(SMBJ IFSM=100A/8.3ms)')
        c.le('TVS順方向I2t < IFSM等価耐量x0.5', tvs_i2t, 41.5 * 0.5, ' A^2s',
             f'(溶断まで{tblow * 1e3:.2f}ms間 {ipk:.0f}A)')
    else:
        c.info('TVS順方向I2t',
               f'{tvs_i2t:.1f} A^2s vs 耐量x0.5={41.5 * 0.5:.1f} -> '
               + ('余裕あり' if tvs_ok else 'D1(SMBJ15A)破壊の恐れ: このヒューズは採用不可'))
    c.le('逆接時 下流 VBAT_M', abs(wmax(raw, t, 'V(vbatm)')), 0.10, ' V', '(Q1が遮断)')
    c.le('逆接時 |Vgs(Q1)|', abs(wmin(raw, t, 'V(nvgs1)')), Q1_VGSS, ' V')
    c.le('逆接時 |Vds(Q1)|', abs(wmin(raw, t, 'V(nvds1)')), Q1_VDSS * 0.8, ' V')
    return c, dict(fuse=label, i2t_melt=i2t_melt, ipk_a=ipk,
                   tblow_ms=tblow * 1e3, tvs_i2t=tvs_i2t,
                   vbatm_max=wmax(raw, t, 'V(vbatm)'))


if __name__ == '__main__':
    checks, out = [], []
    for vb in (12.6, 9.0):
        c, m = case_normal(vb)
        checks.append(c)
        out.append({'case': f'normal_{vb}V', **m})
    for i2t, lab, req in ((FUSE_I2T_FAST, '速断', True), (FUSE_I2T_NORM, '普通', True),
                          (FUSE_I2T_SLOW, '遅動', False)):
        c, m = case_rev(i2t, lab, required=req)
        checks.append(c)
        out.append({'case': f'reverse_{lab}', 'required': req, **m})

    edit(NORMAL, r'\.param VBAT0=\S+', '.param VBAT0=12.6')
    edit(REV, r'\.param I2TMELT=\S+', f'.param I2TMELT={FUSE_I2T_FAST}')

    d = ROOT / 'sim' / 'runs' / 'parent_pwr'
    d.mkdir(parents=True, exist_ok=True)
    (d / 'measure.json').write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding='utf-8')

    ok = all([c.report() for c in checks])
    print('\nALL CHECKS PASSED' if ok else '\nSOME CHECKS FAILED')
    sys.exit(0 if ok else 1)
