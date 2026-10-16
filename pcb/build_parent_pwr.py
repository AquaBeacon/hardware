"""PARENT_PWR (P-PWR) v1.5: 親機電源基板 100x84mm。

v1.5 変更点 (2026-08-04 可読性): **回路図を A3 全面へ再配置した(電気的変更ゼロ)**。
 触ったのは `at` / `rot` / `sch_wires` / `sch_labels` / `sch_junctions` / `sch_blocks` /
 `sch_texts` / `ref_at` / `val_at` / `gnd_style` だけで、`{pin: net}` / `placements` /
 `seed_*` は不変。ネットリスト意図照合 15ネット一致 + DRC 0違反/未接続0 で
 「読みやすくしただけ」を担保している。主な内容: 枠間隔を 4mm -> 縦10mm/横12mm(見出しが上のブロックを踏んでいた)、
 TX 12V 分岐を VBAT_M レールからの縦線に整理、SW_PWR-R_SH を実線化、
 INA226/J_I2C と NOTES を右列へ、取付穴を専用の帯へ。
 検算は `python -X utf8 pcb\\check_sch.py build_parent_pwr` (build不要・数秒)。
**銅箔は完全同一ではない**: `placements` / `seed_*` / `tracks` は不変だがオートルータが
 再実行され、0.3mm 級のトラックが数セグメント別経路になった(ネット番号の並びが変わるため)。
 ドリル/マスク/ペースト/外形/BOM/CPL はバイト一致、DRC 0違反・未接続0 も維持している。
 → **シルクの版数も v1.5 へ上げた**(基板が入れ替わったことを実物で識別できるようにするため)。
v1.4(2026-08-03 レビュー残件): **`TP_GND1`(THT GND テストポイント)追加**とブリングアップ用シルク。
 各レールは既存の THT パッドで測れる(VBAT_M=C_BLK.1 / VBAT_TX=J_TX.2 / V5L=PS_A.3 /
 V3S=REG3S.1 / V5C=C_5C1.1)ので電圧用TPは足していない。手順書は `pcb/BRINGUP_BOARDS.md`。
v1.3(2026-08-03 レビュー反映): 回路図に機能ブロック枠(`sch_blocks`)と注記(`sch_texts`)を追加し、
 未対策の既知リスク(**SW_TX の活線突入**)を図面上に明記した。未使用のFP定数
 (TB2/PSK2/PSK4/PSK6/PH2/XH4)を削除。**ネット・部品・配置・配線は一切変更していない**
 (ネットリスト意図照合 15ネット一致で担保)。
 ★ SW_TX 活線投入は **2026-08-03 に LTspice で検証済み**(`LTspice/PARENT_PWR_SWTX.cir` /
   `sim/parent_pwr_swtx_verify.py`、結果は sim/notes.md 2026-08-03節)。要点:
    - 突入ピーク 36.1A(12.6V) / 25.4A(9.0V)。**R 制限(過減衰)なので Ctx を減らしても
      13% しか下がらない** -> 「TX側 C1 を減らす」案は無効。
    - I²t は最大 0.107 A²s で速断3Aの 5 A²s を大きく下回る -> ヒューズは飛ばない。
    - 本当の問題は VBAT_M のディップ。**電池終止(9.0V)で 5.13V まで落ち、LXDC55 の
      Vin 下限 6.0V を 74us 割る**(V5L 自体は 4.81V で保持されるのでリセットはしない)。
   **対策(部品追加ゼロ)**: **SW_TX は SW_PWR より先に入れる**運用にする。そうすれば
   冷間投入 = 既に検証済みのケースに戻る。運用中の送信停止は `TX_PWM` Low 固定で行えるので
   (GPIO表に既記載)、SW_TX を通電中に操作する必然性が無い。BRINGUP_BOARDS.md に手順として明記。
v1.2(2026-07-31 基板間コネクタ整合): J_I2C を XH4->XH5 にして INA226 の ALERT を同居させ、
 別建ての J_ALT(PH2) を廃止。C-PWR J_I2C と完全同一ピン順(V3x/GND/SDA/SCL/INA_AL)になり、
 P-MAIN 側の受け口 J_I2CP(XH5) とストレート5芯1本で繋がる(旧構成はP-MAIN側に受け口が無かった)。
v1.1: カメラ5V(PS_B)を実物 秋月AE-MYMGK00506ERSR-5V0(5V/6A, 28.5x16, 12pad)へ整合し下段左に専用ゾーン化。基板を70->84mmに拡張。
SPEC_MAIN_PWR_2026-07-19.md の確定ネット表に一致(ピン→ネットは変更禁止)。

電流経路: J_BAT(XT30) -> F1(3A速断) -> Q1(2SJ349逆接保護) -> SW_PWR(トグル)
 -> R_SH(20mR SMDシャント) -> VBAT_M -> BUCKx2(V5L/V5C) + J_TX(12V) 配電。
V5L -> NJU7223F33(REG3S) -> V3S (INA226 VCC / I2C / J_MAIN)。
電流検出は U_INA(INA226 MSOP-10 SMD直載せ, addr0x40) を R_SH でKelvin検出、I2C+ALERT->J_I2C(XH5)。
※MSOP0.5mmピッチのため min_clearance=0.13mm(JLC 5mil可)で発注。

トラック幅: 電池電流経路(VBAT*)2.0 / 5V系・V3S 1.0 / 信号0.6。GNDは両面ベタ任せ。
実行: & "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" -u pcb\\build_parent_pwr.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from kicadgen import Part
from buildlib import build

RFP = 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal'
CDISC = 'Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm'
CPRAD = 'Capacitor_THT:CP_Radial_D5.0mm_P2.50mm'
CPBLK = 'Capacitor_THT:CP_Radial_D8.0mm_P3.50mm'
TOGGLE = 'AquaBeacon:SW_Toggle_2MD1_6P'  # 秋月g104028(Cosland 2MD1, 28VDC/3A)実データシート準拠のカスタムFP
# rot0: pad1(0,0) 2(0,2.54) 3(0,5.08) / 4(5.08,0) 5(5.08,2.54) 6(5.08,5.08)。poleA=1/2/3(2=COM)
# rot90: pad1(0,0) 2(2.54,0) 3(5.08,0) / 4(0,-5.08) 5(2.54,-5.08) 6(5.08,-5.08)。SW_SPSTでpad1-pad2使用
PSK3 = 'Connector_PinSocket_2.54mm:PinSocket_1x03_P2.54mm_Vertical'  # LXDC55(SIP3: VIN/GND/VOUT)用
# (v1.3: 未使用の TB2/PSK2/PSK4/PSK6/PH2/XH4 定義を削除)
FUSE = 'Fuse:Fuseholder_Clip-5x20mm_Keystone_3517_Inline_P23.11x6.76mm_D1.70mm_Horizontal'
XT30 = 'Connector_AMASS:AMASS_XT30PW-M_1x02_P2.50mm_Horizontal'  # 購入済(横型・基板端実装, pad1='-'=GND pad2='+')
# 実測(pcbnew) rot90(開口=左端): pin1(X,Y) pin2(X,Y+5) 機構穴(X-10,Y+8)(X-10,Y-3)
#   コートヤード x[X-13.6,X+2.25] y[Y-4.65,Y+9.65]。本体は基板上、開口を左端(x=0)へ向ける。
XH2 = 'Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical'
XH5 = 'Connector_JST:JST_XH_B5B-XH-A_1x05_P2.50mm_Vertical'
XH6 = 'Connector_JST:JST_XH_B6B-XH-A_1x06_P2.50mm_Vertical'
XLED = 'LED_THT:LED_D3.0mm'
TO220 = 'Package_TO_SOT_THT:TO-220-3_Vertical'
MSOP10 = 'Package_SO:MSOP-10_3x3mm_P0.5mm'  # INA226AIDGSR(DGS)。左1-5=A1/A0/Alert/SDA/SCL 右6-10=VS/GND/VBUS/IN-/IN+
R2512 = 'Resistor_SMD:R_2512_6332Metric'    # 電流検出シャント。rot270 pad1(0,-2.962)上 pad2(0,+2.962)下
C0603 = 'Capacitor_SMD:C_0603_1608Metric'   # INA226 VSパスコン

# probe_pins 結果 (sch座標 = 配置(X,Y)基準, y符号反転済み):
#  Transistor_FET:IRF9540N rot0: G1=(X-5.08,Y), D2=(X+2.54,Y-5.08)上, S3=(X+2.54,Y+5.08)下
#   -> rot90: G1=(X,Y+5.08)下, D2=(X-5.08,Y-2.54)左, S3=(X+5.08,Y-2.54)右
#  Device:LED rot0: K1=(X-3.81,Y)左, A2=(X+3.81,Y)右 -> rot90: A2=(X,Y-3.81)上, K1=(X,Y+3.81)下
#  Conn_01x02 rot0: 1=(X-5.08,Y) 2=(X-5.08,Y+2.54) / mirror'y': x=+5.08
#  Conn_01x03 rot0: 1=(X-5.08,Y-2.54) .. 3=(X-5.08,Y+2.54)
#  Conn_01x04 rot0: 1=(X-5.08,Y-2.54) .. 4=(X-5.08,Y+5.08)
#  Conn_01x06 rot0: 1=(X-5.08,Y-5.08) .. 6=(X-5.08,Y+7.62)
#  Device:Fuse rot90: 1=(X-3.81,Y) 2=(X+3.81,Y) (Rと同じ)

# ===================== 回路図レイアウト (v1.5 で全面再配置) =====================
# A3(420x297)。左列 x18-244 に機能ブロックを縦積み、右列 x256-405 に INA226/I2C と
# DESIGN NOTES を置く。**枠どうしは縦10mm・横12mm 以上あける**(見出しは枠の外側・上に
# 出るので、詰めると必ず上のブロックの中身を踏む)。PWR_FLAG は kicadgen が
# (20,20)+i*25.4 に固定配置し(本基板は6個 = x175まで)、下向きラベルが **y=33 付近**まで伸びる。
# そのため B1 の枠上辺だけ 38(見出しは 34.7-36.7)まで下げてある。
# 検算は `python -X utf8 pcb\check_sch.py build_parent_pwr`(build不要・数秒)。
parts = [
    # ===== B1 (枠 18,34,244,84) 電池レール y=50.8:
    #        J_BAT -> F1 -> D1(TVS) -> Q1(逆接PFET) -> SW_PWR -> R_SH -> VBAT_M
    #        + TX 12V 分岐 (y=70: VBAT_M -> SW_TX -> J_TX) =====
    # XT30 FP刻印は pad1=「-」pad2=「+」(AMASS実物準拠) -> 1=GND 2=正極 に統一
    # rot180でピン右向き・pin2が上段(レール直結)になる
    Part('J_BAT', 'Connector_Generic', 'Conn_01x02', 'LiPo3S_XT30', XT30,
         {'1': 'GND', '2': 'VBAT'}, at=(32, 53.34), rot=180,          # 1(37.08,53.34) 2(37.08,50.8)
         ref_at=(32, 45.0), val_at=(32, 62.0)),
    Part('F1', 'Device', 'Fuse', '3A F速断', FUSE,                   # 速断必須(遅動だと逆接時TVS/D1が先に破壊, LTspice実証)
         {'1': 'VBAT', '2': 'VBAT_F'}, at=(56, 50.8), rot=90),       # 1(52.19,50.8) 2(59.81,50.8)
    Part('D1', 'Device', 'D', 'SMBJ15A', 'Diode_SMD:D_SMB',
         {'1': 'VBAT_F', '2': 'GND'}, at=(80, 54.61), rot=270),      # K(80,50.8) A(80,58.42)
    # 実購入品=東芝2SJ349(秋月g102413, IRF9540N代替)。DS実測 pcb/datasheets/2SJ349_toshiba_akizuki.pdf:
    # SC-67(2-10R1B) 1=G 2=D 3=S でIRF9540Nと同配置 -> シンボル/FP/配線は流用、Valueのみ実物に合わせる
    Part('Q1', 'Transistor_FET', 'IRF9540N', '2SJ349', TO220,
         {'1': 'QG', '2': 'VBAT_F', '3': 'VBAT_P'}, at=(98, 53.34), rot=90,
         ref_at=(90, 43.5), val_at=(106, 43.5)),
         # rot90: D2=(92.92,50.8)左 S3=(103.08,50.8)右 G1=(98,58.42)下
    Part('R_G', 'Device', 'R', '100k', RFP,                         # 在庫の汎用値。Pchゲートプルダウン
         {'1': 'QG', '2': 'GND'}, at=(98, 68.58)),                   # 1(98,64.77) 2(98,72.39)
    # 主電源トグルスイッチ(基板実装, VBAT_P->VBAT_SW を入切)
    Part('SW_PWR', 'Switch', 'SW_SPST', 'PWR', TOGGLE,
         {'1': 'VBAT_P', '2': 'VBAT_SW'}, at=(128, 50.8)),           # 1(122.92,50.8) 2(133.16,50.8)
    # INA226電流検出をSMD直載せ化(旧J_INAS/J_INAモジュール廃止, CHILD_PWRと同方式)。addr=0x40。
    Part('R_SH', 'Device', 'R', '20m', R2512,
         {'1': 'VBAT_SW', '2': 'VBAT_M'}, at=(160, 50.8), rot=90),   # シャント 20mohm 2512 FS~4A
    Part('C_BLK', 'Device', 'C_Polarized', '100u/25V', CPBLK,       # 突入低減で470u->100u(LTspice検証済:TXバーストサグ0.089V/余裕)
         {'1': 'VBAT_M', '2': 'GND'}, at=(186, 54.61)),              # FPはD8/P3.5据置。1(186,50.8) 2(186,58.42)
    Part('C_BK1', 'Device', 'C', '10u/25V', CDISC,
         {'1': 'VBAT_M', '2': 'GND'}, at=(204, 54.61)),              # 1(204,50.8) 2(204,58.42)
    # 12V(TX)出力トグルスイッチ: VBAT_M -> [SW_TX] -> VBAT_TX -> J_TX で出力を単独ON/OFF
    Part('SW_TX', 'Switch', 'SW_SPST', 'TX_12V', TOGGLE,
         {'1': 'VBAT_M', '2': 'VBAT_TX'}, at=(175.08, 70),           # 1(170,70) 2(180.16,70)
         ref_at=(175.08, 62.0), val_at=(175.08, 76.0)),
    # GND は **ラベル**にする: GNDシンボルだと J_TX.1 の右下 (224.38,70) に落ち、
    #  VBAT_TX ワイヤ(y=70)の上に乗って短絡する
    Part('J_TX', 'Connector_Generic', 'Conn_01x02', 'TX_XT30', XT30,
         {'1': 'GND', '2': 'VBAT_TX'}, at=(232, 67.46), gnd_style='label',
         ref_at=(232, 60.0), val_at=(232, 78.0)),                    # 1(226.92,67.46) 2(226.92,70)

    # ===== B2 (枠 18,94,244,130) V5L レール y=113.03: 5V BUCK -> V5L -> REG3S(V3S) =====
    # ロジック5V: 購入品 AE-LXDC55-5V(SIP3: VIN/GND/VOUT)に整合 -> 1x03
    Part('PS_A', 'Connector_Generic', 'Conn_01x03', 'BUCK_5V_LXDC55', PSK3,
         {'1': 'VBAT_M', '2': 'GND', '3': 'V5L'},
         at=(34, 110.49), mirror='y', gnd_style='label',             # 1(39.08,107.95)VIN 2 GND 3(39.08,113.03)V5L
         ref_at=(34, 100.5), val_at=(34, 103.5)),
    Part('C_5L1', 'Device', 'C', '10u/25V', CDISC,
         {'1': 'V5L', '2': 'GND'}, at=(66, 116.84)),                 # 1(66,113.03) 2(66,120.65)
    Part('C_5L2', 'Device', 'C', '100n', CDISC,
         {'1': 'V5L', '2': 'GND'}, at=(88, 116.84)),
    # NJU7223F33 (TO-220F): 1=VOUT 2=VIN 3=GND (78xx系と逆順・データシート照合済み)
    Part('REG3S', 'Connector_Generic', 'Conn_01x03', 'NJU7223F33', TO220,
         {'1': 'V3S', '2': 'V5L', '3': 'GND'}, at=(124, 113.03),     # 1(118.92,110.49) 2(118.92,113.03) 3(118.92,115.57)
         gnd_style='label', ref_at=(124, 104.5), val_at=(124, 123.5)),
    Part('C_3S1', 'Device', 'C_Polarized', '10u', CPRAD,
         {'1': 'V3S', '2': 'GND'}, at=(156, 116.84)),
    Part('C_3S2', 'Device', 'C', '100n', CDISC,
         {'1': 'V3S', '2': 'GND'}, at=(180, 116.84)),

    # ===== B3 (枠 18,140,244,186) カメラ5V BUCK -> V5C / 電源表示LED, レール y=160 =====
    # カメラ5V(Pi Zero 2W用): 実物 秋月 AE-MYMGK00506ERSR-5V0(Murata MYMGK00506ERSR, 5V/6A, Vin8-15V)
    #  実測FP=AquaBeacon:MYMGK00506ERSR_AE(28.5x16, 列間25.4/縦2.54, 2x6=12pad)。
    #  左列1-6=PG/CTRL/GND/GND/VIN/VIN(CN1) 右列7-12=GND/GND/GND/VOUT/VOUT/VOUT(CN2)。
    #  DS指示によりVIN(5,6)/VOUT(10,11,12)/GNDは全ピン結線(1ピン定格対策)。PG(1)=開放/CTRL(2)=開放で出力ON。
    #  Vin窓8-15VにLiPo3S(9.0-12.6V)適合(sim/notes.md)。組立時に実物シルクで挿し向き確認。
    Part('PS_B', 'Connector_Generic', 'Conn_01x12', 'MYMGK00506ERSR_AE', 'AquaBeacon:MYMGK00506ERSR_AE',
         {'1': 'NC', '2': 'NC', '3': 'GND', '4': 'GND', '5': 'VBAT_M', '6': 'VBAT_M',
          '7': 'GND', '8': 'GND', '9': 'GND', '10': 'V5C', '11': 'V5C', '12': 'V5C'},
         at=(40, 160), gnd_style='label',                            # 1(34.92,146.03) .. 12(34.92,173.97)
         ref_at=(40, 142.0), val_at=(40, 180.0)),
    Part('C_5C1', 'Device', 'C', '10u/25V', CDISC,
         {'1': 'V5C', '2': 'GND'}, at=(70, 163.81)),                 # 1(70,160) 2(70,167.62)
    Part('C_5C2', 'Device', 'C', '100n', CDISC,
         {'1': 'V5C', '2': 'GND'}, at=(92, 163.81)),
    Part('R_LED', 'Device', 'R', '1k', RFP,                         # 在庫の汎用値。電源表示LED直列
         {'1': 'V5L', '2': 'LED_A'}, at=(130, 160), rot=90),         # 1(126.19,160) 2(133.81,160)
    Part('LED1', 'Device', 'LED', 'PWR', XLED,                      # rot180: A2(148.19,160)左 K1(155.81,160)右
         {'1': 'GND', '2': 'LED_A'}, at=(152, 160), rot=180),

    # ===== B4 (枠 18,196,244,242) 出力コネクタ / GND テストポイント =====
    Part('J_MAIN', 'Connector_Generic', 'Conn_01x06', 'TO_PMAIN_PWR', XH6,
         {'1': 'V5L', '2': 'V5L', '3': 'GND', '4': 'GND', '5': 'V3S', '6': 'V3S'},
         at=(46, 216), gnd_style='label',                            # 1(40.92,209.65)..6(40.92,222.35)
         ref_at=(46, 202.0), val_at=(46, 230.0)),
    Part('J_POD', 'Connector_Generic', 'Conn_01x02', 'POD_5V', XH2,
         {'1': 'V5C', '2': 'GND'}, at=(110, 214.73), gnd_style='label',
         ref_at=(110, 206.0), val_at=(110, 224.0)),                  # 1(104.92,214.73) 2(104.92,217.27)
    # v1.4: スコープのグランドクリップ用 GND テストポイント(THT)。
    #  各レールは既に THT パッドで測れる(VBAT_M=C_BLK.1 / VBAT_TX=J_TX.2 / V5L=PS_A.3 /
    #  V3S=REG3S.1 / V5C=C_5C1.1)ので電圧用TPは足さない。手順書 pcb/BRINGUP_BOARDS.md。
    Part('TP_GND1', 'Connector', 'TestPoint', 'GND',
         'TestPoint:TestPoint_THTPad_D1.5mm_Drill0.7mm', {'1': 'GND'},
         at=(170, 214), gnd_style='label', ref_at=(178, 213.0), val_at=(178, 216.5)),

    # ===== B5 (枠 256,34,405,116) INA226 電流検出 / P-MAIN への I2C(右列) =====
    Part('U_INA', 'Sensor_Energy', 'INA226', 'INA226AIDGSR', MSOP10,
         {'1': 'GND', '2': 'GND', '3': 'INA_AL', '4': 'I2C_SDA', '5': 'I2C_SCL',
          '6': 'V3S', '7': 'GND', '8': 'VBAT_M', '9': 'VBAT_M', '10': 'VBAT_SW'},
         at=(300, 62), gnd_style='label',                            # 1A1 2A0 3AL 4SDA 5SCL 6VS 7GND 8Vbus 9Vin- 10Vin+
         ref_at=(300, 38.0), val_at=(300, 90.0)),
    Part('C_VS', 'Device', 'C', '100n', C0603,                      # INA226 VSパスコン(V3S)。U_INA の近くに置く
         {'1': 'V3S', '2': 'GND'}, at=(340, 98)),
    # v1.2: J_I2C を XH4→**XH5** にして ALERT を同居させ、別建てだった J_ALT(PH2) を廃止。
    #  C-PWR の J_I2C と完全同一のピン順になり、P-MAIN/C-MAIN 側のコネクタ・ケーブルを共通化できる
    #  (旧構成は P-MAIN 側に受け口が無く、ピン順も本数も噛み合っていなかった)。
    Part('J_I2C', 'Connector_Generic', 'Conn_01x05', 'I2C_PMAIN', XH5,
         {'1': 'V3S', '2': 'GND', '3': 'I2C_SDA', '4': 'I2C_SCL', '5': 'INA_AL'},
         at=(380, 70), gnd_style='label',                            # 1(374.92,64.92)..5(374.92,75.08)
         ref_at=(380, 54.0), val_at=(380, 86.0)),

    # 取付穴。どのブロック枠にも入らない専用の帯(y=256)に並べる
    Part('H1', 'Mechanical', 'MountingHole', 'M3', 'MountingHole:MountingHole_3.2mm_M3', {}, at=(40, 256)),
    Part('H2', 'Mechanical', 'MountingHole', 'M3', 'MountingHole:MountingHole_3.2mm_M3', {}, at=(70, 256)),
    Part('H3', 'Mechanical', 'MountingHole', 'M3', 'MountingHole:MountingHole_3.2mm_M3', {}, at=(100, 256)),
    Part('H4', 'Mechanical', 'MountingHole', 'M3', 'MountingHole:MountingHole_3.2mm_M3', {}, at=(130, 256)),
]

sch_wires = [
    ('VBAT', ['J_BAT.2', 'F1.1']),
    ('VBAT_F', ['F1.2', 'D1.1', 'Q1.2']),          # D1タップにジャンクション
    ('QG', ['Q1.1', 'R_G.1']),
    ('VBAT_P', ['Q1.3', 'SW_PWR.1']),
    # v1.5: SW_PWR.2 -> R_SH.1 を実線化(スタブ+ラベルだと左右から突き合って重なる)
    ('VBAT_SW', ['SW_PWR.2', 'R_SH.1']),
    ('VBAT_M', ['R_SH.2', (170, 50.8), 'C_BLK.1', 'C_BK1.1']),
    ('VBAT_M', [(170, 50.8), 'SW_TX.1']),          # TX 12V 分岐は x=170 の縦線で降ろす
    ('VBAT_TX', ['SW_TX.2', 'J_TX.2']),
    ('V5L', ['PS_A.3', 'C_5L1.1', 'C_5L2.1', 'REG3S.2']),
    ('V3S', ['C_3S1.1', 'C_3S2.1']),
    ('V5C', ['C_5C1.1', 'C_5C2.1']),
    ('LED_A', ['R_LED.2', 'LED1.2']),
]
sch_junctions = [
    (80, 50.8),          # VBAT_F: D1タップ
    (170, 50.8),         # VBAT_M: SW_TX への縦分岐
    (186, 50.8),         # VBAT_M: C_BLKタップ
    (66, 113.03), (88, 113.03),   # V5Lレールのタップ
]
# ワイヤ化ネットのキーパーラベル位置。自動配置(最長水平セグメントの始点+2.54)が
# 部品や他のラベルに当たるものだけ明示する。
sch_labels = {
    'VBAT_F': (63.5, 50.8, 0),
    'QG': (98, 61.5, 0),          # Q1 -> R_G の縦セグメント上(x はワイヤに載せる)
    'VBAT_SW': (137, 50.8, 0),
    'VBAT_M': (172, 50.8, 0),
    'V5L': (44, 113.03, 0),
    'V3S': (159, 113.03, 0),
    'V5C': (73, 160, 0),
    'LED_A': (136.5, 160, 0),
}

# ===== 回路図の機能ブロック枠と注記 =====
# グラフィックのみ。ネット・ERC・ネットリスト照合には影響しない。
# **縦に積む枠は10mm、横に並ぶ枠は12mm あける**(v1.3 の 4mm では見出しが上の枠を踏んだ)。
sch_blocks = [
    # 本基板は PWR_FLAG が6個あり、そのラベル(下向き)が y=32.7 まで伸びる。
    # B1 の見出しは枠上辺-3.27 に出るので、枠上辺は 38 まで下げる(34 だと見出しが噛む)。
    (18, 38, 244, 84, 'BATTERY INPUT / PROTECTION / CURRENT SENSE / TX 12V OUT'),
    (18, 94, 244, 130, '5V LOGIC BUCK (AE-LXDC55) -> V5L -> LDO V3S'),
    (18, 140, 244, 186, 'CAMERA 5V BUCK (MYMGK 5V/6A) -> V5C / PWR LED'),
    (18, 196, 244, 242, 'OUTPUT CONNECTORS / GND TEST POINT'),
    (256, 34, 405, 116, 'INA226 CURRENT SENSE (0x40) / I2C TO P-MAIN'),
]
# 注記は部品と重ならないよう、右列下段に NOTES パネルとしてまとめる
# (この基板は sch_wires で結線しているため、枠の中に文字を置くと必ず線か Ref に当たる)。
sch_blocks.append((256, 128, 405, 244, 'DESIGN NOTES'))
sch_texts = [
    (260, 136, '[1] 電流経路', 1.6),
    (260, 141, '  J_BAT -> F1(3A 速断) -> Q1(2SJ349 逆接保護) -> SW_PWR', 1.27),
    (260, 146, '  -> R_SH(20m, INA226 Kelvin 検出) -> VBAT_M -> BUCKx2 + SW_TX/J_TX(12V)', 1.27),
    (260, 151, '  F1 は速断(F)必須: 遅動だと逆接時に TVS(D1) が先に破壊する (LTspice 実証)', 1.27),
    (260, 156, '  C_BLK 470u -> 100u で投入突入を低減済み (SW_PWR 3A 接点の保護)', 1.27),
    (260, 166, '[2] SW_TX は必ず SW_PWR より先に入れること', 1.6),
    (260, 171, '  活線投入すると突入 36A(12.6V)/25A(9.0V) が接点を通り、VBAT_M が', 1.27),
    (260, 176, '  電池終止時に 5.13V まで落ちて LXDC55 の Vin 下限 6.0V を 74us 割る。', 1.27),
    (260, 181, '  先に入れておけば検証済みの冷間投入に収まる。運用中の送信停止は', 1.27),
    (260, 186, '  TX_PWM を Low 固定で行う (LTspice: sim/parent_pwr_swtx_verify.py)', 1.27),
    (260, 196, '[3] 電源レール', 1.6),
    (260, 201, '  PS_A / PS_B とも Vin 窓 8-15V。LiPo 3S(9.0-12.6V)は下端が近い', 1.27),
    (260, 206, '  REG3S = NJU7223F33 (TO-220F, 1=VOUT 2=VIN 3=GND / Io max 500mA)', 1.27),
    (260, 211, '  PS_B: VIN(5,6) / VOUT(10,11,12) / GND は全ピン結線 (1ピン定格対策, DS 指示)。', 1.27),
    (260, 216, '        PG(1)=開放 / CTRL(2)=開放 で出力 ON', 1.27),
    (260, 226, '[4] 基板間', 1.6),
    (260, 231, '  J_MAIN = P-MAIN J_PWR1 / J_I2C = P-MAIN J_I2CP (どちらもストレート)。', 1.27),
    (260, 236, '  I2C プルアップは本基板に無い (P-MAIN 側 R_SDA/R_SCL が既定 DNP)', 1.27),
]

# --- PCB 100x84mm ---
# FPパッド絶対座標 (probe_fp結果を配置に適用):
#  XT30 rot0: 1=(X,Y) 2=(X+5,Y) / rot180: 2=(X-5,Y)
#  FUSE rot0: 1=(X+6.76,Y) 2=(X+23.11,Y)  実クリップ体 x[X-1.3,X+24.4] y±5.35
#  TO-220 rot0: 1=(X,Y) 2=(X+2.54,Y) 3=(X+5.08,Y) / rot90: 2=(X,Y-2.54) 3=(X,Y-5.08)
#  D_SMB rot270: K1=(X,Y-2.15) A2=(X,Y+2.15) SMD(F.Cuのみ)
#  PSK2 rot180: 1=(X,Y) 2=(X,Y-2.54) / PSK4 rot90: 1..4=(X..X+7.62,Y) / PSK6 rot180: 1..6=(X,Y..Y-12.7)
#  CDISC rot0: 2=(X+5,Y) rot90: 2=(X,Y-5) rot180: 2=(X-5,Y) rot270: 2=(X,Y+5)
#  CPRAD rot270: 2=(X,Y+2.5) / CPBLK(D8 P3.5) rot270: 2=(X,Y+3.5)
#  RFP rot0: 2=(X+10.16,Y) rot270: 2=(X,Y+10.16)
#  XH ピッチ2.5 +x方向 / PH2 rot0: 2=(X,Y+2.54) / LED rot180: K1=(X,Y) A2=(X-2.54,Y)
placements = {
    # 上段: 電池電流経路 (左->右)
    'J_BAT': (14, 14, 90),     # XT30PW-M rot90(開口=左端): pin1(14,14)=GND('-') pin2(14,19)=VBAT('+')
                               # 機構穴(4,22)(4,11) crtyd x[0.4,16.25] y[9.35,23.65]
    'F1': (26, 10, 0),         # 1(32.76,10)=VBAT 2(49.11,10)=VBAT_F 実体x[24.7,50.4]
    'D1': (56, 12.15, 270),    # K(56,10)=VBAT_F A(56,14.3)=GND(F.Cuベタ)
    'Q1': (66, 10, 0),         # G(66,10)=QG D(68.54,10)=VBAT_F S(71.08,10)=VBAT_P
    'R_G': (66, 16, 270),      # 1(66,16)=QG 2(66,26.16)=GND
    'SW_PWR': (82, 10, 90),    # トグルrot90: pad1(82,10)VBAT_P pad2(84.54,10)VBAT_SW pad3(87.08,10)/pad4-6(y4.92)
    'SW_TX': (18, 35, 270),    # トグルrot270(12V出力制御): pad1(18,35)VBAT_M pad2(15.46,35)VBAT_TX
                               # pad3(12.92,35)/pad4-6(y40.08) crtyd x[10.82,20.1]y[32.9,42.18]
    'R_SH': (87.5, 26, 270),   # rot270: pad1 VBAT_SW=(87.5,23.04)top pad2 VBAT_M=(87.5,28.96)bottom / pad x[85.9,89.1]
    'C_VS': (93, 21, 0),       # rot0: pad1 V3S=(92.225,21) pad2 GND=(93.775,21)
    'U_INA': (93, 26, 180),    # rot180 左列x90.9: 6VS=25 7GND=25.5 8VBUS=26 9IN-=26.5 10IN+=27
                               #         右列x95.1: 1A1=27 2A0=26.5 3AL=26 4SDA=25.5 5SCL=25 / R_SHとコートヤード分離
    'C_BLK': (81, 26, 270),    # 1(81,26)=VBAT_M 2(81,29.5)=GND
    'C_BK1': (74, 26, 270),    # 1(74,26)=VBAT_M 2(74,31)=GND
    # 中段: BUCKx2 + LDO
    'PS_A': (30, 32, 90),      # 1(30,32)=VBAT_M 2(32.54,32)=GND 3(35.08,32)=V5L 4(37.62,32)=GND
    # カメラBUCK(28.5x16)は下段左に独立ゾーン。rot0で左列VIN側=x11.3, 右列VOUT側=x36.7, 縦2.54ピッチ。
    #  左列 x11.3: p1(63.65)PG p2(66.19)CTRL p3(68.73)GND p4(71.27)GND p5(73.81)VIN p6(76.35)VIN
    #  右列 x36.7: p7(63.65)GND p8(66.19)GND p9(68.73)GND p10(71.27)VOUT p11(73.81)VOUT p12(76.35)VOUT
    'PS_B': (24, 70, 0),
    'C_5L1': (40, 28, 180),    # 1(40,28)=V5L 2(35,28)=GND
    'C_5L2': (48, 28, 0),      # 1(48,28)=V5L 2(53,28)=GND
    'REG3S': (60, 38, 90),     # 1(60,38)=V3S 2(60,35.46)=V5L 3(60,32.92)=GND
    'C_3S1': (66, 42, 270),    # 1(66,42)=V3S 2(66,44.5)=GND
    'C_3S2': (74, 42, 90),     # 1(74,42)=V3S 2(74,37)=GND (refテキスト重なり回避で+2)
    'C_5C1': (46, 66, 0),      # V5C出力パスコン(モジュール右のVOUT近傍) 1(46,66)=V5C 2(51,66)=GND
    'C_5C2': (46, 74, 0),      # 1(46,74)=V5C 2(51,74)=GND
    'R_LED': (52, 50, 0),      # 1(52,50)=V5L 2(62.16,50)=LED_A
    'LED1': (68, 50, 180),     # K1(68,50)=GND A2(65.46,50)=LED_A
    # 下段: 出力コネクタ / 左: J_TX
    'J_TX': (14, 48, 90),      # XT30PW-M rot90(開口=左端): pin1(14,48)=GND('-') pin2(14,53)=VBAT_M('+')
                               # 機構穴(4,56)(4,45) crtyd x[0.4,16.25] y[43.35,57.65]
    'J_POD': (62, 70, 0),      # カメラモジュールVOUT近傍(C_5Cの右)へ移設。1(62,70)=V5C 2(64.5,70)=GND
    'J_MAIN': (42, 60, 0),     # 1(42,60)=V5L 2(44.5,60)=V5L 3(47,60)=GND 4(49.5,60)=GND
                               # 5(52,60)=V3S 6(54.5,60)=V3S
    'J_I2C': (72, 60, 0),      # 1(72,60)=V3S 2(74.5,60)=GND 3(77,60)=I2C_SDA 4(79.5,60)=I2C_SCL
                               # 5(82,60)=INA_AL (v1.2でXH5化。pins1-4の座標は据置=既存配線そのまま)
    # v1.4: GND テストポイント。x88-98 / y40-55 の空き(V3S B.Cu 登り x86.5 と
    #  I2C B.Cu 南下 x97-98.9 の間。両側とも 4mm 以上離れる)
    'TP_GND1': (92, 45, 0),
    'H1': (5, 5, 0), 'H2': (95, 5, 0), 'H3': (5, 79, 0), 'H4': (95, 79, 0),
}

tracks = [
    # 電池電流経路 2.0mm
    ('VBAT',    'F.Cu', 2.0, ['J_BAT.2', (26, 19), (26, 10)]),   # pin2(14,19)=+ を右へ、GNDパッド(14,14)を避けy=19で迂回
    # Keystone 3517 は各クリップに2孔(同名パッド x=+0/+6.76, +16.35/+23.11) -> 連結スタブ
    ('VBAT',    'F.Cu', 2.0, [(26, 10), (32.76, 10)]),
    ('VBAT_F',  'F.Cu', 2.0, [(42.35, 10), (49.11, 10)]),
    ('VBAT_F',  'F.Cu', 2.0, ['F1.2', 'D1.1']),
    ('VBAT_F',  'F.Cu', 2.0, ['D1.1', (58, 10), (58, 5), (68.54, 5), 'Q1.2']),  # Gパッド(66,10)回避ジョグ
    ('VBAT_P',  'F.Cu', 2.0, ['Q1.3', 'SW_PWR.1']),
    # VBAT_SW: SW_PWR.2 -> シャントR_SH.1(高側 pad1=(89,23.04))。IN+(pin10)はKelvinでB.Cuホップ
    ('VBAT_SW', 'F.Cu', 2.0, ['SW_PWR.2', (84.54, 18), (87.5, 18), 'R_SH.1']),
    ('VBAT_SW', 'F.Cu', 0.25, ['U_INA.10', (90.9, 29)]),
    ('VBAT_SW', 'B.Cu', 0.25, [(90.9, 29), (88, 29), (88, 23.04)]),   # via(88,23.04)はpad1上=同ネット
    # VBAT_M幹線 -> SW_TX.1(12V出力トグル入力, J_TX上)
    ('VBAT_M',  'F.Cu', 2.0, ['R_SH.2', (87.5, 32), (84, 32), (84, 22), (20, 22), (20, 35), 'SW_TX.1']),
    ('VBAT_M',  'F.Cu', 0.25, ['U_INA.9', (89, 26.5), 'R_SH.2']),    # Vin-(pin9) 真西 -> pad2(IN+パッド回避)
    ('VBAT_M',  'F.Cu', 0.25, ['U_INA.8', (89, 26.0), 'R_SH.2']),    # Vbus(pin8) 真西 -> pad2
    # VBAT_TX: SW_TX.2(15.46,35)から上→左→下でJ_TX.2へ(未使用pad/V5C/VBAT_M交差を回避)
    ('VBAT_TX', 'F.Cu', 1.5, ['SW_TX.2', (15.46, 32), (10, 32), (10, 53), 'J_TX.2']),
    ('VBAT_M',  'F.Cu', 2.0, [(81, 22), 'C_BLK.1']),
    ('VBAT_M',  'F.Cu', 2.0, [(74, 22), 'C_BK1.1']),
    ('VBAT_M',  'F.Cu', 2.0, [(30, 22), 'PS_A.1']),
    # VBAT_M -> カメラBUCK VIN(左列下 p5,6)。中央spine(x30)を下げ、モジュール下(y77)から左へ回り込む
    ('VBAT_M',  'F.Cu', 2.0, ['PS_A.1', (30, 77), (11.3, 77), 'PS_B.6', 'PS_B.5']),
    ('QG',      'F.Cu', 0.6, ['Q1.1', 'R_G.1']),
    # V5L (BUCK_A -> LDO / J_MAIN / LED) 1.0mm
    ('V5L',     'F.Cu', 1.0, ['PS_A.3', (35.08, 36), (52, 36), (52, 35.46), 'REG3S.2']),
    ('V5L',     'F.Cu', 1.0, [(40, 36), 'C_5L1.1']),
    ('V5L',     'F.Cu', 1.0, [(48, 36), 'C_5L2.1']),
    ('V5L',     'F.Cu', 1.0, [(44, 36), (44, 52), (44.5, 56), 'J_MAIN.2']),
    ('V5L',     'F.Cu', 1.0, ['J_MAIN.2', 'J_MAIN.1']),
    ('V5L',     'F.Cu', 0.6, [(44, 50), 'R_LED.1']),
    ('LED_A',   'F.Cu', 0.6, ['R_LED.2', 'LED1.2']),
    # V5C (カメラBUCK VOUT -> パスコン -> POD) 1.0mm
    ('V5C',     'F.Cu', 1.0, ['PS_B.10', 'PS_B.11', 'PS_B.12']),        # 右列3本のVOUTを連結(x36.7)
    ('V5C',     'F.Cu', 1.0, ['PS_B.10', (46, 71.27), (62, 71.27), 'J_POD.1']),
    ('V5C',     'F.Cu', 1.0, ['C_5C1.1', (46, 71.27), 'C_5C2.1']),
    # V3S (LDO -> INA226 / J_MAIN / I2C) 1.0mm
    ('V3S',     'F.Cu', 1.0, ['REG3S.1', (60, 42), 'C_3S1.1', 'C_3S2.1', (86.5, 42)]),
    ('V3S',     'B.Cu', 1.0, [(86.5, 42), (86.5, 16)]),                      # VBAT_M/SW障害物をB.Cuで登り回避(VBAT_SWから離隔)
    ('V3S',     'F.Cu', 1.0, [(86.5, 16), (92.225, 16), 'C_VS.1']),          # 北を東進 -> C_VS(V3S pad)
    ('V3S',     'F.Cu', 0.25, ['U_INA.6', (90.9, 23), (92.225, 23), 'C_VS.1']),   # VS(pin6) -> C_VS
    ('V3S',     'F.Cu', 1.0, [(60, 42), (60, 56), (54.5, 58), 'J_MAIN.6']),
    ('V3S',     'F.Cu', 1.0, ['J_MAIN.6', 'J_MAIN.5']),
    ('V3S',     'F.Cu', 1.0, [(72, 42), 'J_I2C.1']),
    # 信号 0.6mm (I2CはB.Cu回廊で降ろす)
    # I2C/ALERT: U_INA右列(x96.6) -> F.Cu東ファン -> via -> B.Cu南下降 -> J_I2C(XH5, y60)
    # 目標が西なので「深い目標ほど東レーン」に割当てて水平部が縦部を跨がない: SDA(y52)=x97.5 / SCL(y54)=x98.1 / AL(y58)=x98.7
    # SDA=水平で西レーンx97.3(浅い目標77), SCL=上げてmid x98.1(目標79.5), AL=東へ出て下げ東レーンx98.9(深い目標88)
    ('I2C_SDA', 'F.Cu', 0.25, ['U_INA.4', (97, 25.5)]),
    ('I2C_SDA', 'B.Cu', 0.3,  [(97, 25.5), (97, 52), (77, 52), 'J_I2C.3']),
    ('I2C_SCL', 'F.Cu', 0.25, ['U_INA.5', (97.7, 22.0)]),
    ('I2C_SCL', 'B.Cu', 0.3,  [(97.7, 22.0), (97.7, 54), (79.5, 54), 'J_I2C.4']),
    ('INA_AL',  'F.Cu', 0.25, ['U_INA.3', (96.3, 26.0), (96.3, 28.0), (98.9, 29.0)]),   # x96.3で東->南(A1パッドとSDA viaの間)
    # AL は J_I2C の最東端 pin5(82,60) へ。y58 の横走りは SCL縦(x79.5)より東で止めるので交差ゼロ
    ('INA_AL',  'B.Cu', 0.3,  [(98.9, 29.0), (98.9, 58), (82, 58), 'J_I2C.5']),
    # pin7 GND -> gap内viaへ(A1/A0/C_VS.2はGNDゾーン接続に委譲)
    ('GND',     'F.Cu', 0.25, ['U_INA.7', (89.5, 25.5), (89.0, 25.0)]),
]

vias = [
    ('VBAT_SW', 90.9, 29), ('VBAT_SW', 88, 23.04),     # IN+ B.Cuホップ(2つ目はpad1上=同ネット)
    ('V3S', 86.5, 42), ('V3S', 86.5, 16),              # V3S B.Cu登りの両端
    ('I2C_SDA', 97, 25.5), ('I2C_SCL', 97.7, 22.0), ('INA_AL', 98.9, 29.0),  # I2C/AL東ファン後via
    ('GND', 89.0, 25.0),   # pin7 GND落とし(A1/A0/C_VSはゾーン接続)
]

texts = [
    ('AquaBeacon PARENT_PWR v1.5', 40, 2.5, 'F.SilkS'),
    # コネクタ用途 (XT30の+/-はFP刻印 pad1=- pad2=+ をそのまま使用)
    ('BAT 3S LiPo', 7, 26.5, 'F.SilkS'),
    ('PWR SW', 77, 16, 'F.SilkS'),
    ('TX 12V SW', 7, 30, 'F.SilkS'),
    ('SHUNT 20m', 82, 20, 'F.SilkS'),
    ('INA226', 92, 20, 'F.SilkS'),
    ('TX 12V OUT', 6, 60, 'F.SilkS'),
    ('POD 5V', 62, 76.5, 'F.SilkS'),
    ('TO P-MAIN', 46, 54, 'F.SilkS'),     # コネクタ列(y60)据置、下段はカメラBUCKが占有 -> ラベルは上へ(ref回避でy54)
    ('I2C+ALERT', 75, 54, 'F.SilkS'),
    ('BUCK 5V LOGIC', 34, 37, 'F.SilkS'),
    ('CAM 5V', 24, 57, 'F.SilkS'),        # カメラBUCK(下段左, PS_B)。詳細シルクはモジュールFP側に有り
    ('LDO 3V3', 68, 32, 'F.SilkS'),
    ('PWR LED', 60, 53, 'F.SilkS'),
    # v1.4: ブリングアップ用の測定点表示。**GND TP だけ**にしてある(C-PWR と同じ理由)。
    #  どのパッドで何を測るかは pcb/BRINGUP_BOARDS.md §2 の表を見る。
    ('GND TP', 89, 42, 'F.SilkS'),
]

ok, rpt = build('PARENT_PWR', parts, placements, (0, 0, 100, 84),
                tracks=tracks, vias=vias,
                power_flag_nets=('GND', 'VBAT', 'VBAT_M', 'V5L', 'V5C', 'V3S'),
                texts=texts, sch_wires=sch_wires, sch_junctions=sch_junctions,
                sch_labels=sch_labels, sch_blocks=sch_blocks, sch_texts=sch_texts,
                min_clearance=0.13)   # INA226(MSOP0.5mm)固有0.15mmパッド間のため
print('OK' if ok else 'DRC ISSUES')
