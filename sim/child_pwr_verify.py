r"""CHILD_PWR (C-PWR) 電源基板の検証。

  1) 通常動作 (VBAT=12.6V 満充電 / 9.0V 終止)
     - SW_PWR ON のまま XT30 を挿した最悪突入
     - V5D/V3D/V3A レール成立、LXDC55の入力窓 6-14V、NJU7223F33のドロップアウト
     - ライトPWM(1A)のターンオフサージと Q2 の 3.3V ゲート駆動成立性
  2) 逆接続 (XT30裏返し)
     - Q1(2SJ349)が遮断すること
     - D1(SMBJ15A)が順方向導通して電池を短絡 -> ヒューズ溶断までの TVS 負担
       (速断/普通/遅動の I2t 別に評価)

実行: python sim\child_pwr_verify.py
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pwr_common import (  # noqa: E402
    FUSE_I2T_FAST, FUSE_I2T_NORM, FUSE_I2T_SLOW, LXDC55_IOUT, LXDC55_VIN_MAX,
    LXDC55_VIN_MIN, NJU7223_IOUT, NJU7223_RTH_JA, Q1_VDSS, Q1_VGSS,
    Q2_VDSS, Q2_VGSS, Q2_ID, ROOT, SW_TOGGLE_I, TVS_IFSM, TVS_VRWM,
    Checks, load, run, tcross, wavg, wmax, wmin,
)

NORMAL = ROOT / 'LTspice' / 'CHILD_PWR.cir'
REV = ROOT / 'LTspice' / 'CHILD_PWR_rev.cir'

TCON = 200e-6
W_STEADY = (5e-3, 9.5e-3)      # 起動完了後・ライト消灯中
W_LEDON = (10.1e-3, 10.45e-3)  # ライトPWM ONの区間
W_STEP = (16e-3, 24e-3)        # V3D +100mA ステップ後


def edit(path, pattern, repl):
    s = path.read_text(encoding='utf-8')
    s2, n = re.subn(pattern, repl, s)
    assert n == 1, f'pattern not unique/found: {pattern} (n={n}) in {path.name}'
    path.write_text(s2, encoding='utf-8')


def case_normal(vbat0):
    edit(NORMAL, r'\.param VBAT0=\S+', f'.param VBAT0={vbat0}')
    raw, t = load(run('CHILD_PWR.cir'))
    c = Checks(f'CHILD_PWR 通常動作 VBAT={vbat0}V')

    # --- 投入突入 ---
    inrush = wmax(raw, t, 'I(Rfuse)')
    i2t = wmax(raw, t, 'V(ni2t)')
    c.info('突入ピーク電流(F1/SW_PWR/Q1)', f'{inrush:.1f} A '
           f'(トグル定格{SW_TOGGLE_I:.0f}A の {inrush / SW_TOGGLE_I:.0f}倍)')
    c.le('突入I2t < 速断3Aヒューズ溶断I2t', i2t, FUSE_I2T_FAST, ' A^2s', '(投入で飛ばない)')
    c.le('Q1突入ピーク損失', wmax(raw, t, 'V(npq1)'), 200.0, ' W', '(単発150us, SOA内)')

    # --- 入力保護チェーン ---
    c.le('VBAT_F 最大 < TVS VRWM', wmax(raw, t, 'V(vbatf)'), TVS_VRWM, ' V')
    c.le('|Vgs(Q1)| < VGSS', abs(wmin(raw, t, 'V(nvgs1)')), Q1_VGSS, ' V')
    c.le('|Vds(Q1)| < VDSS*0.8', abs(wmin(raw, t, 'V(nvds1)')), Q1_VDSS * 0.8, ' V')
    p_q1 = wavg(raw, t, 'V(npq1)', *W_LEDON)
    c.le('Q1定常損失(ライト点灯時)', p_q1, 1.0, ' W', f'(Tj上昇 {p_q1 * 62.5:.1f}K @62.5K/W)')

    # --- レール ---
    vbm = wmin(raw, t, 'V(vbatm)', *W_LEDON)
    c.between('LXDC55入力 VBAT_M', vbm, LXDC55_VIN_MIN, LXDC55_VIN_MAX, ' V')
    c.between('V5D 定常', wavg(raw, t, 'V(v5d)', *W_STEADY), 4.75, 5.25, ' V')
    c.between('V3D 定常', wavg(raw, t, 'V(v3d)', *W_STEADY), 3.20, 3.40, ' V')
    c.between('V3A 定常', wavg(raw, t, 'V(v3a)', *W_STEADY), 3.20, 3.40, ' V')
    c.between('V3D (WiFiバースト+100mA時)', wavg(raw, t, 'V(v3d)', *W_STEP), 3.20, 3.40, ' V')
    i5d = wavg(raw, t, 'I(V5s)', *W_STEADY)
    c.le('LXDC55 出力電流', i5d, LXDC55_IOUT, ' A')
    i3d = wavg(raw, t, 'I(V3Ds)', *W_STEP)
    c.le('REG3D 出力電流', i3d, NJU7223_IOUT, ' A')
    p3d = (wavg(raw, t, 'V(v5d)', *W_STEP) - wavg(raw, t, 'V(v3d)', *W_STEP)) * i3d
    c.le('REG3D 損失 -> Tj上昇', p3d * NJU7223_RTH_JA, 65.0, ' K',
         f'({p3d:.2f}W x {NJU7223_RTH_JA:.0f}K/W, Ta=40degC想定で Tj<105degC)')

    # --- ライト駆動 Q2 ---
    c.le('LED_N ターンオフサージ < VDSS*0.8', wmax(raw, t, 'V(ledn)'), Q2_VDSS * 0.8, ' V')
    c.le('Q2 Vgs < VGSS', wmax(raw, t, 'V(qgl)'), Q2_VGSS, ' V')
    iled = wavg(raw, t, 'Id(M2)', *W_LEDON)
    vds_on = wavg(raw, t, 'V(ledn)', *W_LEDON)
    if iled > 0.1:
        c.le('ライト電流', iled, Q2_ID, ' A')
        c.le('Q2 オン電圧(Vth最悪2.5V/ゲート3.3V)', vds_on, 0.30, ' V',
             f'(Rds_on={vds_on / iled * 1e3:.0f}mohm, 損失{vds_on * iled * 1e3:.0f}mW)')
    else:
        # ライトモデル= Vf 9V + Rs 3.6ohm の12V系LEDストリング(仮定)。
        # 電池が終止電圧に近づくと Vf を割って消灯する = ライト側の仕様依存。
        c.info('ライト電流', f'{iled * 1e3:.1f} mA (VBAT={vbat0}V ではVf=9Vを割り消灯: '
                             f'ライトの実Vf次第。Q2の駆動判定は12.6Vケースを参照)')

    return c, dict(vbat0=vbat0, inrush_a=inrush, i2t=i2t, vbatm_min=vbm,
                   v5d=wavg(raw, t, 'V(v5d)', *W_STEADY),
                   v3d=wavg(raw, t, 'V(v3d)', *W_STEADY),
                   v3a=wavg(raw, t, 'V(v3a)', *W_STEADY),
                   ledn_spike=wmax(raw, t, 'V(ledn)'), led_i=iled,
                   q2_vds_on=vds_on, q1_p=p_q1, reg3d_p=p3d)


def case_rev(i2t_melt, label, required=True):
    """required=False のケースは「使ってはいけない構成」の実証(NGでも全体は落とさない)。"""
    edit(REV, r'\.param I2TMELT=\S+', f'.param I2TMELT={i2t_melt}')
    raw, t = load(run('CHILD_PWR_rev.cir'))
    c = Checks(f'CHILD_PWR 逆接続 ヒューズ{label} (溶断I2t={i2t_melt} A^2s)'
               + ('' if required else ' ※採用不可の実証'))

    ipk = abs(wmin(raw, t, 'I(Rfuse)'))
    tblow = tcross(raw, t, 'V(ni2t)', i2t_melt * 0.999) - TCON
    tvs_i2t = wmax(raw, t, 'V(ni2ttvs)')
    c.info('逆接短絡電流ピーク', f'{ipk:.1f} A (TVS順方向)')
    c.info('ヒューズ溶断時間', f'{tblow * 1e3:.2f} ms')
    # 8.3ms半波 100A 相当の I2t = (100^2/2)*8.3ms = 41.5 A^2s が定格。
    # 単発破壊限界そのものなので 50% ディレーティングして判定する。
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

    d = ROOT / 'sim' / 'runs' / 'child_pwr'
    d.mkdir(parents=True, exist_ok=True)
    (d / 'measure.json').write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding='utf-8')

    ok = all([c.report() for c in checks])
    print('\nALL CHECKS PASSED' if ok else '\nSOME CHECKS FAILED')
    sys.exit(0 if ok else 1)
