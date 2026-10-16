"""CHILD_MAIN (C-MAIN) v4.6: 子機メイン基板。2026-07-21統合仕様。主制御 Raspberry Pi Pico 2 W。

v4.6 変更点 (2026-08-04 可読性): **回路図を A3 全面へ再配置した(電気的変更ゼロ)**。
 触ったのは `at` / `rot` / `sch_wires` / `sch_labels` / `sch_junctions` / `sch_blocks` /
 `sch_texts` / `ref_at` / `val_at` / `gnd_style` だけで、`{pin: net}` / `placements` /
 `seed_*` は不変。ネットリスト意図照合 40ネット一致 + DRC 0違反/未接続0 で
 「読みやすくしただけ」を担保している。主な内容: **3列 x 3段のブロックグリッド**へ全面再配置。
 旧版は枠が互いに交差し、注記が部品の上に乗り、図が用紙左上に固まっていた。
 注記は右中段の DESIGN NOTES パネルへ集約。LED/ADCラダーを横一列に直し、
 RS485 終端の斜め線を直角ジョグに変更。取付穴と TP は上端の帯(x>=200)へ。
 検算は `python -X utf8 pcb\\check_sch.py build_child_main` (build不要・数秒)。
**銅箔は完全同一ではない**: `placements` / `seed_*` / `tracks` は不変だがオートルータが
 再実行され、0.3mm 級のトラックが数セグメント別経路になった(ネット番号の並びが変わるため)。
 ドリル/マスク/ペースト/外形/BOM/CPL はバイト一致、DRC 0違反・未接続0 も維持している。
 → **シルクの版数も v4.6 へ上げた**(基板が入れ替わったことを実物で識別できるようにするため)。

v4.5変更(2026-08-03 レビュー残件):
 1. **`R_LEAK` 1M -> 100k + `C_LEAK` 10n 追加**。RP2350 の入力リークは最悪 ±1uA あり、1M では
    リークだけで最大 1.0V 落ちる(3.3-1.0=2.3V ≒ VIH 2.31V)。**漏水検知は見逃すと機体を失う**
    機能なので乾燥時 High の余裕がぎりぎりなのは不適切。100k なら最悪 0.1V。
    C_LEAK で tau=1ms のノイズ除去を入れ、電極線が拾うノイズでの誤検知を減らす。
 2. **`TP_GND1`(THT)追加**。各レールは既存の THT パッドで測れるので電圧用TPは足さず、
    足りていない「スコープのグランドクリップを咬ませる場所」だけを用意した。
 3. ブリングアップ用シルクを追加。手順書は `pcb/BRINGUP_BOARDS.md`。

v4.4変更(2026-08-03 ユーザ情報反映): **`J_TEMP1`(Celsius 水温センサ)を JST-GH -> XH4 へ変更**。
 v4.0 で「センサ付属ケーブルが 4極 JST-GH だから基板側も GH にすれば変換ケーブル不要」として
 SM04B-GHS-TB を採用していたが、**ユーザは Celsius のケーブルを XH コネクタで自作している**ため
 この前提が誤りだった(GH 1.25mm / XH 2.5mm でピッチが違い物理的に嵌合しない)。
 自作ケーブルなのでピン順は自由 -> **`1:V3D 2:GND 3:I2C_SDA 4:I2C_SCL`** に統一し、
 C-MAIN `J_PRS1` / P-MAIN `J_PRS1`・`J_MAG1`・`J_TEMP1` と**全く同じピン順**にした。
 これで I2C センサ用ケーブルが親子・センサ間で完全に共通化でき、挿し違えても致命傷にならない。
 crtyd が 9.46 -> 13.46mm に広がるため、y52 の行(J_TEMP1 / J_LEAK1 / R_LEAK)を東へ再配置した。

v4.3変更(2026-08-03 レビュー反映):
 1. **TH_PWM にケーブル前段RC(`R_THP` 1k + `C_THP` 100n)を追加**。TH_PWM は 125kHz PWM で、
    J_RX1(XH6) の pin3 = アナログ `ENV_ADC`(pin4) の**直隣**を走るためクロストーク源になる。
    RX 側は R15=10k -> C8=100n(tau=1ms) で VTH を作り、その先は LM393 の高インピーダンス入力
    なので **DC では電流が流れず、直列 1k による分圧誤差はゼロ**(Ib max 250nA x 1k = 0.25uV)。
    duty->VTH の関係もファームも不変のまま、ケーブルへ出る dv/dt だけを約1/1000にできる。
    ネット名: Pico 側 `TH_PWM` / コネクタ側 `TH_PWM_F`。
 2. **`R_SDCS` 10k(V3D -> SD_CS) を追加**。Pico の GPIO は起動〜ファーム初期化まで Hi-Z なので
    CS がフロートし、カードが未選択状態に落ち着かない(microSD の間欠不良の定番要因)。
 3. 回路図に機能ブロック枠(`sch_blocks`)と注記(`sch_texts`)を追加(ネット不変=可読性のみ)。
 4. シルクの版数を実体に合わせた(v4.1 表記のままだった)。
 5. 上記 1./2. を足したことで F.Cu の「R列東側脱出」動線が細り、**I2C_SDA と I2C_SCL が
    順に配線不能になった**ため、PICO1.6/.7 の東側脱出を入れ子レーンで手seedした(下記参照)。
    この基板は既に充填 55% で、東列に部品を1つ足すだけで I2C が落ちる状態にある。

⚠ **見送った改善(v4.3 では未実施。実施するなら単独の改版で)**:
 BNO085 の PS0/WAKE(pad8)は現在 V3D 固定だが、CEVA 1000-3927 §1.2.4 note5 は
 「Pin6(PS0/WAKE) must be connected to a GPIO」としている。v4.1 で GP7/GP9 が解放されたので
 「Pico に空きが無い」という従来の理由はもう成立しない。**ただし配線が極めて難しい**:
  - GP7(物理10)/GP9(物理12)はどちらも Pico **東列(x30)**。BNO は基板北端(pad8 = 20.19, 6.1)。
  - BNO 下列パッド(y23.9, 2.54ピッチ)の隙間は 0.84mm しかなく、0.3mm トラック+0.2mm
    クリアランスでぎりぎり(0.7mm)通るかどうか。
  - 左strip は J_PWR1 と I2C/V3A/V5D/BTN_ADC の幹線で完全に埋まっている。
  - 途中で I2C 幹線(B.Cu y25.5/27)と V3A 幹線(F.Cu y30)の両方を跨ぐ層替えが要る。
 加えて Adafruit 4754 の RST にプルアップがあるか未確認で、無い場合は P0 に 10k プルアップの
 追加も必要になる(「リセット前から High」要件のため)。現状(P0=V3D 固定)は Adafruit 公式
 ライブラリと同じ構成で実動作するので、緊急性は低い。

v4.2変更(2026-08-03): microSD を **TF-01A (LCSC C91145, push-push/自動排出)** へ変更し
 JLCPCB の SMT 実装対象にした(旧 Molex 104031-0811 は JLC 在庫が無く手はんだ前提)。
 自作FP AquaBeacon:microSD_TF-01A。**接点列が北向き(y72.65)になった**ので SPI は SD 直上の
 B.Cu 縦バス(y71 -> y40.5)で Pico へ上げる。R_CD を Cd パッド寄り(36,64)へ移動。
 STATUS LED を黄(JLC Extended)→**赤 C84256(Basic)**へ。

v4.1変更(2026-08-02): LCDをPARENT_MAINと同じNHD-C0216CiZ I2C品へ統一。
 J_LCD1をXH9からXH7へ変更し、旧LCD_CS/LCD_DC GPIOを解放。
 バックライトをV5D/100ohm給電へ変更。

v3.3変更(2026-07-31): DS3231(ZS-042)の実測 **40x20x10mm** を反映。40mm軸がピン列と直交する
 ことが判明したため FP を 38x22 -> 20x40 に作り直し、J_RTC1 を rot270 @(80,19.5) へ移設
 (本体を上帯へ西向きに寝かせる: body x41-81 / y9.5-29.5)。I2C幹線の立ち上げ位置と
 V3D上帯幹線の東端(パッド列回避)を作り直した。実装高さ 18.49mm(ソケット8.5+本体10)。

v2.1変更(ユーザ指摘反映):
 - RS485(Waveshare SS-9778)を**基板へキャステレーション直付け**。カスタムFP
   AquaBeacon:Waveshare_TTL_RS485_C(42.8x15.2, TTL側VCC/GND/RXD/TXD=pad1-4,
   RS485側PE/GND/A/B=pad5-8)。TTL側をPico向き、A/B/PE側をテザー向き。J_485AB廃止。
   絶縁を活かすためRS485側GND/PEは基板GNDと分離し SHLD 網に集約(テザー経由で筐体1点接地)。
 - BNO085を**DIP化(2列)モジュール**として 2x5 ピンソケット(PinSocket_2x05)へ実装。

上位仕様: ../docs/AquaBeacon_確定仕様メモ.md
ネット定義の正: ../docs/AquaBeacon_MAIN_UI_GPIO_コネクタ表.md
実行: & "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" -u pcb\\build_child_main.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from kicadgen import Part
from buildlib import build

# SMD受動部品(JLCPCB Basic志向)。RFP/CDISCは既存コードの流用名のままSMDへ差し替え
RFP = 'Resistor_SMD:R_0603_1608Metric'      # 全抵抗 0603
CDISC = 'Capacitor_SMD:C_0603_1608Metric'   # 100n等 0603
C0805 = 'Capacitor_SMD:C_0805_2012Metric'   # 10uF積セラ 0805
CPRAD = C0805                                # 旧電解10uF→積セラ0805
XLED = 'LED_SMD:LED_0805_2012Metric'         # 表示LED 0805
SWP = 'Button_Switch_THT:SW_PUSH_6mm'        # タクトSW THT 6mm(押しやすさ優先)
FETSMD = 'Package_TO_SOT_SMD:SOT-23'         # 2N7002(G1/S2/D3)
# 実際に使う XH のみ定義する(v4.3 で未使用の TB5/PSK6/XH5/XH8 を削除)
XH2 = 'Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical'
XH3 = 'Connector_JST:JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical'
XH4 = 'Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical'
XH6 = 'Connector_JST:JST_XH_B6B-XH-A_1x06_P2.50mm_Vertical'
XH7 = 'Connector_JST:JST_XH_B7B-XH-A_1x07_P2.50mm_Vertical'
XH9 = 'Connector_JST:JST_XH_B9B-XH-A_1x09_P2.50mm_Vertical'
# v4.4: Celsius 用の GH4 定義は削除した(ユーザがケーブルを XH で自作しているため
#  基板側も XH4 に統一。GH 1.25mm ピッチでは XH ケーブルと嵌合しない)。
#  参考: SM04B-GHS-TB crtyd 9.46 x 6.40 / XH4 は 13.46 x 6.80
# v4.2: microSD を JLCPCB 実装可能な TF-01A (LCSC C91145, push-push/自動排出) へ変更。
#  自作FP。原点=パターン中心。rot0 で **接点列が -y 側 (y-6.35)、カード開口が +y 側 (y+6.79)**。
#  pads: 1(+2.15) 2(+1.05) 3(-0.05) 4(-1.15) 5(-2.25) 6(-3.35) 7(-4.45) 8(-5.55) 10=Cd(-6.65)
#  shell: SH(-7.75,-5.5) SH(+6.93,-5.5) 9(-7.75,+4.19) SH(+7.75,+4.19) / NPTH φ1.0 (∓, +4.49)
#  crtyd 17.20 x 15.60。Cd の相手側接点はシェルなので shell の1枚を pad"9"(=GND) にしてある。
USD = 'AquaBeacon:microSD_TF-01A'
W485 = 'AquaBeacon:Waveshare_TTL_RS485_C'   # 自作: TTL 1-4=VCC/GND/RXD/TXD, 485 5-8=PE/GND/A/B

# ===================== 回路図レイアウト (v4.6 で全面再配置) =====================
# A3(420x297)を 3列 x 3段のブロックグリッドに切り、**枠どうしは縦10mm・横12mm 以上**
# あける(見出しは枠の外側・上に size2.0 で出るので、詰めると必ず上の枠の中身を踏む)。
#   列: x 14-130 / 142-268(中列は段により幅可変) / 256-406
#   段: y 34-128 / 138-198 / 208-284
# **y<=32 は空ける**: PWR_FLAG は kicadgen が (20,20)+i*25.4 に固定配置し、下向きラベルが
# y=29 付近まで伸びる。取付穴 H1-H4 と TP_GND1 はこの帯の右側(x>=200)に並べてある。
# 注記は右下の DESIGN NOTES パネルへ集約した(v4.3 は各枠の内側に置いていて部品に乗っていた)。
# 検算は `python -X utf8 pcb\check_sch.py build_child_main`(build不要・数秒)。
parts = [
    # ================= MCU: Raspberry Pi Pico 2 W =================
    # 物理ピン->GP: 1=GP0 2=GP1 3=GND 4=GP2 5=GP3 6=GP4 7=GP5 8=GND 9=GP6 10=GP7
    #  11=GP8 12=GP9 13=GND 14=GP10 15=GP11 16=GP12 17=GP13 18=GND 19=GP14 20=GP15
    #  21=GP16 22=GP17 23=GND 24=GP18 25=GP19 26=GP20 27=GP21 28=GND 29=GP22 30=RUN
    #  31=GP26 32=GP27 33=AGND 34=GP28 35=ADC_VREF 36=3V3 37=3V3_EN 38=GND 39=VSYS 40=VBUS
    # パッド rot0: 左列 pin1..20 = (0, 2.54*(n-1)); 右列 pin21..40 = (17.78, 2.54*(40-n))
    # v3.2: LIGHT_PWM を GP7(物理10) → GP8(物理11) へ、旧LCD_CSを GP8 → GP7 へ交換。
    #  理由: RP2350 の PWM スライスは slice=(GP>>1)%12 なので **GP6 と GP7 は同一スライス3の
    #  A/B チャネル**。両者はカウンタ・wrap・分周を共有するため周波数を独立に設定できない。
    #  TH_PWM(GP6) は RX の平滑RC(τ=1ms)の都合で 125kHz/wrap>=1000 が必須 → 旧割当だと
    #  LIGHT_PWM も 125kHz に固定され、C-PWR の Q2(TO-220, Ciss数nF)を R_GL=100Ω で叩く
    #  構成ではゲート遷移が周期の1割を占めてスイッチング損と低duty側の非線形が出る。
    #  GP8=slice4A に移せば独立に設定できる(slice4B=GP9=LCD_DC は単なるGPIOでスライスを取らない)。
    #  交換相手を隣ピン(物理10↔11)にしてあるのは、Pico東列の脱出順・配線長をほぼ変えないため
    #  (GP15 など離れたピンと交換すると R列の脱出資源が枯れて I2C/INA_AL が配線不能になる)。
    Part('PICO1', 'MCU_Module', 'RaspberryPi_Pico', 'Pico 2 W',
         'Module:RaspberryPi_Pico_Common_THT',
         {'1': '485D_TXD', '2': '485D_RXD', '4': 'CMP_OUT', '5': 'INA_AL',
          '6': 'I2C_SDA', '7': 'I2C_SCL', '9': 'TH_PWM', '10': 'NC',
          '11': 'LIGHT_PWM', '12': 'NC', '14': 'SPI_SCK', '15': 'SPI_MOSI',
          '16': 'SPI_MISO', '17': 'SD_CS', '19': 'LED_STATUS', '20': 'SD_CD',
          '21': 'BNO_MISO', '22': 'BNO_CS', '24': 'BNO_SCK', '25': 'BNO_MOSI',
          '26': 'BNO_INT', '27': 'BNO_RST', '29': 'LEAK', '31': 'ENV_ADC',
          '32': 'BTN_ADC', '34': 'BL_PWM', '39': 'V5D',
          '3': 'GND', '8': 'GND', '13': 'GND', '18': 'GND', '23': 'GND',
          '28': 'GND', '33': 'GND', '38': 'GND',
          '36': 'NC', '30': 'NC', '35': 'NC', '37': 'NC', '40': 'NC'},
         # シンボル実寸: x±22.86 / y-38.1..+35.56。左右のラベルを入れて約 82 x 90mm。
         # Value は本体の左下へ逃がす(真下は GND シンボルが 8 個重なる場所)。
         at=(192, 86), ref_at=(192, 37), val_at=(162, 124)),

    # ================= 電源+I2C+制御 入力 (C-PWRから、v4.0で1本に統合) =================
    # ★v4.0(2026-08-01): ユーザ要求により **C-PWR との接続を XH9 1本に統合**。
    #  旧: J_PWR1(XH6 電源) + J_I2CP(XH5 I2C) + J_RXA1(XH3 V3A) + J_LIGHT1(XH2 ライトPWM)
    #      = 4コネクタ16ピン → **1コネクタ9ピン**。C-PWR の J_MAIN と完全同一ピン順=ストレート9芯。
    #  ピン割り: I2C対(5/6)を GND(4/7)で挟み、スイッチングする LIGHT_PWM(9) を電源から離す。
    #  SCL を SDA より先(北)にしてあるのは C-PWR 側 U_INA 東列の並びと揃えて交差を消すため。
    Part('J_PWR1', 'Connector_Generic', 'Conn_01x09', 'FROM_CPWR', XH9,   # ← C-PWR J_MAIN
         {'1': 'V5D', '2': 'V3D', '3': 'V3A', '4': 'GND', '5': 'I2C_SCL',
          '6': 'I2C_SDA', '7': 'GND', '8': 'INA_AL', '9': 'LIGHT_PWM'},
         at=(40, 62), gnd_style='label',
         ref_at=(40, 44), val_at=(40, 80)),
    # INA226 ALERT はオープンドレイン → 受け側(GP3)でプルアップする
    Part('R_AL', 'Device', 'R', '10k', RFP, {'1': 'V3D', '2': 'INA_AL'}, at=(100, 44), rot=90),
    Part('C_V5', 'Device', 'C', '10u', C0805, {'1': 'V5D', '2': 'GND'}, at=(78, 67.81)),
    Part('C_V5b', 'Device', 'C', '100n', CDISC, {'1': 'V5D', '2': 'GND'}, at=(100, 67.81)),
    Part('C_V3', 'Device', 'C_Polarized', '10u', CPRAD, {'1': 'V3D', '2': 'GND'}, at=(78, 85.81)),
    Part('C_V3b', 'Device', 'C', '100n', CDISC, {'1': 'V3D', '2': 'GND'}, at=(100, 85.81)),
    # 表示LED 横一列 (緑PWR=常時, 赤STATUS=GP14)。
    # v4.6: rot180 で A(pin2)を左、K(pin1)を右にして「左(電源側)→右(GND)」に電流が流れる図にした。
    # v4.2/v5.6: STATUS を橙→**赤**へ。JLCPCB の 0805 LED の Basic は赤(C84256)と緑(C2297)だけで、
    #  橙/黄は Extended になり装着費が発生するため(ユーザ要求: extended をできるだけ避ける)。
    Part('R_PWR', 'Device', 'R', '1k', RFP, {'1': 'V3D', '2': 'LEDP_A'}, at=(28, 96), rot=90),
    Part('LED_PWR', 'Device', 'LED', 'GREEN', XLED, {'2': 'LEDP_A', '1': 'GND'}, at=(54, 96), rot=180),
    Part('R_ST', 'Device', 'R', '1k', RFP, {'1': 'LED_STATUS', '2': 'LEDS_A'}, at=(38, 116), rot=90),
    Part('LED_ST', 'Device', 'LED', 'RED', XLED, {'2': 'LEDS_A', '1': 'GND'}, at=(64, 116), rot=180),

    # ================= microSD (TF-01A push-push, SPI1) =================
    Part('SD1', 'Connector', 'Micro_SD_Card_Det2', 'microSD', USD,
         {'1': 'NC', '2': 'SD_CS', '3': 'SPI_MOSI', '4': 'V3D', '5': 'SPI_SCK',
          '6': 'GND', '7': 'SPI_MISO', '8': 'NC', '9': 'GND', '10': 'SD_CD', 'SH': 'GND'},
         at=(320, 76), gnd_style='label',      # シンボル実寸 x±22.86 / 左列ピン y65.84..88.7
         ref_at=(320, 50), val_at=(320, 100)),
    Part('C_SD1', 'Device', 'C', '100n', CDISC, {'1': 'V3D', '2': 'GND'}, at=(368, 60)),
    Part('C_SD2', 'Device', 'C', '10u', C0805, {'1': 'V3D', '2': 'GND'}, at=(390, 60)),
    Part('R_CD', 'Device', 'R', '47k', RFP, {'1': 'V3D', '2': 'SD_CD'}, at=(372, 84), rot=90),
    # v4.3: CS プルアップ。Pico の GPIO は起動〜ファーム初期化まで Hi-Z なので、これが無いと
    #  CS がフロートしカードが未選択に落ち着かない(SPIモード microSD の間欠不良の定番要因)。
    Part('R_SDCS', 'Device', 'R', '10k', RFP, {'1': 'V3D', '2': 'SD_CS'}, at=(372, 100), rot=90),

    # ================= I2C (DS3231 / MS5837) =================
    Part('J_RTC1', 'Connector_Generic', 'Conn_01x06', 'DS3231_ZS042', 'AquaBeacon:DS3231_ZS042',
         {'1': 'NC', '2': 'NC', '3': 'I2C_SCL', '4': 'I2C_SDA', '5': 'V3D', '6': 'GND'},
         at=(172, 168), gnd_style='label',
         ref_at=(172, 152), val_at=(172, 182)),
    Part('J_PRS1', 'Connector_Generic', 'Conn_01x04', 'MS5837', XH4,
         {'1': 'V3D', '2': 'GND', '3': 'I2C_SDA', '4': 'I2C_SCL'},
         at=(212, 168), gnd_style='label',
         ref_at=(212, 156), val_at=(212, 178)),
    # I2Cプルアップはモジュール側との並列過多を避けるため既定DNP。
    # 無通電時のSDA/SCL-V3D間抵抗を測り、4.7k超なら必要に応じて実装する。
    Part('R_SDA', 'Device', 'R', '4.7k_DNP', RFP, {'1': 'V3D', '2': 'I2C_SDA'}, at=(170, 190), rot=90),
    Part('R_SCL', 'Device', 'R', '4.7k_DNP', RFP, {'1': 'V3D', '2': 'I2C_SCL'}, at=(212, 190), rot=90),

    # ================= BNO085 Adafruit 4754 (専用SPI0, 実物2列12ピン 25.4x22.86mm) =================
    # 実物FP=AquaBeacon:Adafruit_BNO085_4754。**2026-07-31 pad2/pad3 修正**:
    #  ベンダ提供のKiCad FP(pcb/datasheets/4754.zip の MODULE_4754.kicad_mod + 4754.kicad_sym)で実測した
    #  結果、実物の並びは 下列1-6=**VIN/3Vo/GND**/SCL/SDA/INT、上列7-12=BT/P0/P1/RST/DI/CS。
    #  旧版は pad2=GND / pad3=3Vo としており、**モジュール内蔵LDOの出力(3Vo)を基板GNDへ短絡し、
    #  かつ本当のGND(pad3)を未接続にする**という致命的な誤りだった。
    #  SPI: SCK=SCL(4) MISO=SDA(5) MOSI=DI(11) CS=CS(12) +INT(6)+RST(10)。
    #  SPIモード選択は PS1=P1(9)/PS0=P0(8) を共に High(CEVA 1000-3927 §1.2.4 note5, Adafruit公式配線も同じ)。
    #  ※データシートは「Pin6(PS0/WAKE)はGPIOへ繋げ」とするが Pico の26本に空きが無いため V3D 固定。
    #    ホスト起点の書込みは BNO 側 INT アサート時に相乗りする前提(Adafruit_BNO08x ライブラリと同じ方式)。
    #  VINはV3D(3.3V)給電で全ロジック3.3V。BT(7)/3Vo(2)=NC。
    Part('J_BNO1', 'Connector_Generic', 'Conn_01x12', 'BNO085_4754', 'AquaBeacon:Adafruit_BNO085_4754',
         {'1': 'V3D', '2': 'NC', '3': 'GND', '4': 'BNO_SCK', '5': 'BNO_MISO', '6': 'BNO_INT',
          '7': 'NC', '8': 'V3D', '9': 'V3D', '10': 'BNO_RST', '11': 'BNO_MOSI', '12': 'BNO_CS'},
         at=(348, 231), gnd_style='label',
         ref_at=(348, 212), val_at=(348, 250)),
    Part('C_BNO', 'Device', 'C', '100n', CDISC, {'1': 'V3D', '2': 'GND'}, at=(386, 231)),

    # ============ RS485通信: DATA=Waveshare(絶縁,双方向,自動方向) 1個のみ (トリガ廃止) ============
    # 実物7pad: TTL 1=GND 2=RXD 3=TXD 4=VCC / RS485 5=PE 6=B 7=A
    #  RXD<-PicoTX(485D_TXD), TXD->PicoRX(485D_RXD)。PE=絶縁側信号GND→テザーへ(単一絶縁リンクの基準)
    Part('U_485D1', 'Connector_Generic', 'Conn_01x07', 'W_RS485_DATA', W485,
         {'1': 'GND', '2': '485D_TXD', '3': '485D_RXD', '4': 'V3D',
          '5': '485D_PE', '6': '485D_B', '7': '485D_A'},
         at=(46, 166), gnd_style='label',      # ピン (40.92, 158.38..173.62)
         ref_at=(46, 150), val_at=(46, 180)),
    # 終端(120Ω, 既定DNP) + テザー(3ピンXH: A/B/PE)
    # ★v4.0: 旧 XH4 の pin4 は「予備」だった。ユーザ要求「予備のXHは全ていらない」により XH3 化。
    # v4.6: rot180(縦置き)にして pin1=485D_A が下・pin2=485D_B が上。x=90 の短い縦ジョグで
    #  U_485D1 の pin7/pin6 から直角に入れる(斜め線と交差を無くすため)。
    Part('R_TRMD1', 'Device', 'R', '120_DNP', RFP, {'1': '485D_A', '2': '485D_B'}, at=(100, 172), rot=180),
    Part('J_TETH1', 'Connector_Generic', 'Conn_01x03', 'TETHER', XH3,
         {'1': '485D_A', '2': '485D_B', '3': '485D_PE'},
         at=(108, 148),
         ref_at=(108, 140), val_at=(108, 156)),

    # ================= C-RX / 漏水 / ライト / UI =================
    # RX_improved_mini は製造済みで変更不可 → 本基板を RX の J2 に合わせる(v3.1)。
    #  J2(XH6) = 1:V3A 2:GND 3:TH_PWM 4:ENV_ADC 5:NC(旧SHDN) 6:CMP_OUT。
    #  ピン順を完全一致させてあるので RX との配線はストレート6芯1本で済む。
    #  RX には電源専用コネクタが無いため V3A も本コネクタ経由。
    #  v4.0: V3A は統合した J_PWR1(pin3) から直接受ける(旧 J_RXA1 は廃止)。
    #  (V3A の生成は C-PWR の REG3A。本基板には負荷を繋がない純パススルー)。
    Part('C_V3A', 'Device', 'C', '100n', CDISC, {'1': 'V3A', '2': 'GND'}, at=(276, 222)),
    Part('J_RX1', 'Connector_Generic', 'Conn_01x06', 'TO_CRX', XH6,
         {'1': 'V3A', '2': 'GND', '3': 'TH_PWM_F', '4': 'ENV_ADC', '5': 'NC', '6': 'CMP_OUT'},
         at=(240, 230), gnd_style='label',
         ref_at=(240, 214), val_at=(240, 244)),
    # ★v4.3: TH_PWM(125kHz PWM) のケーブル前段RC。J_RX1 では pin3(TH_PWM) と pin4(ENV_ADC=
    #  アナログ包絡線) が隣接ピンで、RX基板は製造済みのためピン順を変えられない。
    #  RX 側は R15(10k) -> C8(100n) で VTH を作り、その先は LM393 の高入力インピーダンス
    #  (Ib max 250nA)なので **DC電流が流れず、直列 R_THP による分圧誤差は 0.25uV = 実質ゼロ**。
    #  したがって duty -> VTH の関係もファームも変えずに、ケーブルへ出る dv/dt だけ落とせる。
    #  tau = 1k x 100n = 100us(RX側 tau=1ms の 1/10)なので応答も律速しない。
    Part('R_THP', 'Device', 'R', '1k', RFP, {'1': 'TH_PWM', '2': 'TH_PWM_F'}, at=(272, 240), rot=90),
    Part('C_THP', 'Device', 'C', '100n', CDISC, {'1': 'TH_PWM_F', '2': 'GND'},
         at=(272, 255.81), gnd_style='label'),
    Part('J_LEAK1', 'Connector_Generic', 'Conn_01x02', 'LEAK', XH2,
         {'1': 'LEAK', '2': 'GND'}, at=(240, 256), gnd_style='label',
         ref_at=(240, 250), val_at=(240, 264)),
    # ★v4.5: 1M -> 100k。RP2350 の入力リーク電流は最悪 ±1uA あり、1M だと **リーク単独で
    #  最大 1.0V も落ちる**(3.3-1.0=2.3V ≒ VIH 2.31V)。乾燥時の "High" が規格ぎりぎりで、
    #  漏水検知という「見逃したら機体を失う」機能にこの余裕は不適切。
    #  100k なら最悪 0.1V の低下で済む。漏水時の検出条件は Rwater < 0.32*R なので
    #  1M:320k / 100k:32k。海水は電極間が桁違いに低い(<1k)ので検出感度は実質変わらない。
    #  電極電流も 3.3V/100k = 33uA と微小で、電食は問題にならない。
    Part('R_LEAK', 'Device', 'R', '100k', RFP, {'1': 'V3D', '2': 'LEAK'}, at=(240, 274), rot=90),
    # v4.5: 電極線が拾うノイズの除去 (100k x 10n = tau 1ms)。漏水は秒オーダーの現象なので
    #  1ms の遅れは無害。誤検知(浮上・再ダイブのやり直し)を減らす方が価値が高い。
    Part('C_LEAK', 'Device', 'C', '10n', CDISC, {'1': 'LEAK', '2': 'GND'},
         at=(282, 268), gnd_style='label'),
    # v4.0: J_LIGHT1(XH2) 廃止 -> LIGHT_PWM は統合した J_PWR1(pin9) から C-PWR へ出す。
    # ================= 水温センサ Blue Robotics Celsius (TSYS01, I2C 0x77) =================
    # ★v4.0 新規: ユーザ指摘「子機に温度センサも積んでいるが基板に無い」への対応。
    # ★v4.4 (2026-08-03): **GH4 -> XH4 へ変更**。
    #  v4.0-v4.3 は「センサ付属ケーブルが 4極 JST-GH だから基板側も GH にすれば変換不要」
    #  という前提で SM04B-GHS-TB を載せ、ピン番号も Pixhawk/ArduPilot の JST-GH 標準
    #  (1=VCC 2=SCL 3=SDA 4=GND) に合わせていた。**この前提が誤りだった**:
    #  ユーザは Celsius のケーブルを **XH コネクタで自作**しており、GH の基板側コネクタとは
    #  ピッチが違う(GH 1.25mm / XH 2.5mm)ため**物理的に嵌合しない**。
    #  自作ケーブルなのでピン順は自由 -> **他の I2C センサと完全に同一の
    #  `1:V3D 2:GND 3:I2C_SDA 4:I2C_SCL`** に統一した。これで
    #   - C-MAIN `J_PRS1` / P-MAIN `J_PRS1` `J_MAG1` `J_TEMP1` と**ケーブルが全て共通**になる
    #   - 親子でコネクタ種別が食い違っていた問題(子=GH / 親=XH)も同時に解消する
    #  I2Cアドレス 0x77 = MS5837(0x76)/DS3231(0x68)/AT24C32(0x57)/INA226(0x40) と衝突しない。
    #  線色(赤=Vin 緑=SCL 白=SDA 黒=GND)はシルクに **R B W G** の順で刻む。
    Part('J_TEMP1', 'Connector_Generic', 'Conn_01x04', 'CELSIUS_TSYS01', XH4,
         {'1': 'V3D', '2': 'GND', '3': 'I2C_SDA', '4': 'I2C_SCL'},
         at=(250, 168), gnd_style='label',
         ref_at=(250, 156), val_at=(250, 178)),
    # ============ UI統合(LCD+3ボタン+バックライト)。LCDは親機と同じI2C品 ============
    # LCD側の昇圧C(VOUT-VDD / C1+-C1- 各1uF)はLCD至近のキャリア基板に置く。
    Part('J_LCD1', 'Connector_Generic', 'Conn_01x07', 'NHD_C0216CiZ', XH7,
         {'1': 'GND', '2': 'V3D', '3': 'I2C_SDA', '4': 'I2C_SCL', '5': 'LCD_RST',
          '6': 'LEDBL_A', '7': 'LEDBL_K'},
         at=(44, 232), gnd_style='label', ref_at=(44, 216), val_at=(44, 246)),
    Part('C_LCD', 'Device', 'C', '100n', CDISC, {'1': 'V3D', '2': 'GND'}, at=(76, 232)),
    # LCDリセット RC (電源投入リセット, GPIO消費せず)
    Part('R_RST', 'Device', 'R', '10k', RFP, {'1': 'V3D', '2': 'LCD_RST'}, at=(110, 216), rot=90),
    Part('C_RST', 'Device', 'C', '100n', CDISC, {'1': 'LCD_RST', '2': 'GND'}, at=(136, 219.81)),
    # バックライト: 親機と同じ V5D/100ohm。LED電流は公称約19mA。
    Part('R_BL', 'Device', 'R', '100', RFP, {'1': 'V5D', '2': 'LEDBL_A'}, at=(110, 232), rot=90),
    Part('Q_BL', 'Transistor_FET', '2N7002', '2N7002', FETSMD,   # G(152.92,250) S(160.54,255.08) D(160.54,244.92)
         {'1': 'BL_GATE', '2': 'GND', '3': 'LEDBL_K'}, at=(158, 250), gnd_style='label',
         ref_at=(146, 244), val_at=(146, 257)),
    Part('R_G', 'Device', 'R', '100', RFP, {'1': 'BL_PWM', '2': 'BL_GATE'}, at=(110, 250), rot=90),
    Part('R_GPD', 'Device', 'R', '100k', RFP, {'1': 'BL_GATE', '2': 'GND'}, at=(134, 253.81)),
    # 3ボタン ADC抵抗ラダー(BTN_ADC 1本判別): UP=0V/ENT=0.82V(3.3k/13.3k)/DN=1.65V/無=3.3V
    # v4.6: 横一列(y=272)に並べ替え。SW_Push は 1=(X-5.08,Y) 2=(X+5.08,Y)。
    Part('R_LAD', 'Device', 'R', '10k', RFP, {'1': 'V3D', '2': 'BTN_ADC'}, at=(32, 276), rot=90),
    Part('SW_UP', 'Switch', 'SW_Push', 'UP', SWP, {'1': 'BTN_ADC', '2': 'GND'}, at=(58, 276), gnd_style='label'),
    Part('SW_ENT', 'Switch', 'SW_Push', 'ENTER', SWP, {'1': 'BTN_ADC', '2': 'N_E'}, at=(96, 276)),
    # R_E/R_D の GND は**ラベル**にする(GNDシンボルだと隣のスイッチのラベルと当たる)
    Part('R_E', 'Device', 'R', '3.3k', RFP, {'1': 'N_E', '2': 'GND'}, at=(124, 276), rot=90,
         gnd_style='label'),
    Part('SW_DN', 'Switch', 'SW_Push', 'DOWN', SWP, {'1': 'BTN_ADC', '2': 'N_D'}, at=(158, 276)),
    Part('R_D', 'Device', 'R', '10k', RFP, {'1': 'N_D', '2': 'GND'}, at=(186, 276), rot=90),

    # ================= パスコン(Pico の V3D/V5D) =================
    Part('C_D1', 'Device', 'C', '100n', CDISC, {'1': 'V3D', '2': 'GND'}, at=(100, 112)),
    Part('C_D2', 'Device', 'C', '100n', CDISC, {'1': 'V5D', '2': 'GND'}, at=(78, 112)),

    # v4.5: スコープのグランドクリップ用 GND テストポイント(THT)。
    #  各レールは既に THT パッドで測れる(V5D/V3D/GND=J_PWR1, Pico 各ピン)ので電圧用TPは足さない。
    #  足りないのは「クリップを咬ませられる GND」の方。測定点の一覧は pcb/BRINGUP_BOARDS.md 参照。
    Part('TP_GND1', 'Connector', 'TestPoint', 'GND',
         'TestPoint:TestPoint_THTPad_D1.5mm_Drill0.7mm', {'1': 'GND'},
         at=(310, 22), gnd_style='label', ref_at=(318, 21), val_at=(318, 24.5)),

    # 取付穴は上端の帯(y=22)へ。どのブロック枠にも掛からない位置(PWR_FLAG は x<=110)。
    Part('H1', 'Mechanical', 'MountingHole', 'M3', 'MountingHole:MountingHole_3.2mm_M3', {}, at=(200, 22)),
    Part('H2', 'Mechanical', 'MountingHole', 'M3', 'MountingHole:MountingHole_3.2mm_M3', {}, at=(225, 22)),
    Part('H3', 'Mechanical', 'MountingHole', 'M3', 'MountingHole:MountingHole_3.2mm_M3', {}, at=(250, 22)),
    Part('H4', 'Mechanical', 'MountingHole', 'M3', 'MountingHole:MountingHole_3.2mm_M3', {}, at=(275, 22)),
]

# 隣接する部品どうしだけワイヤで結ぶ(38ネットのラベル主体図。全部を配線すると読めなくなる)。
sch_wires = [
    ('V5D', ['C_V5.1', 'C_V5b.1']),
    ('V3D', ['C_V3.1', 'C_V3b.1']),
    ('LEDP_A', ['R_PWR.2', 'LED_PWR.2']),
    ('LEDS_A', ['R_ST.2', 'LED_ST.2']),
    # x=90 で短く縦にジョグしてから R_TRMD1 の上下ピンへ入れる(A は y173.62、B は y171.08)
    ('485D_A', ['U_485D1.7', (90, 173.62), (90, 175.81), 'R_TRMD1.1']),
    ('485D_B', ['U_485D1.6', (90, 171.08), (90, 168.19), 'R_TRMD1.2']),
    ('TH_PWM_F', ['R_THP.2', (280, 240), (280, 252), 'C_THP.1']),
    ('LCD_RST', ['R_RST.2', 'C_RST.1']),
    ('BL_GATE', ['R_G.2', 'R_GPD.1', 'Q_BL.1']),
    ('BTN_ADC', ['R_LAD.2', 'SW_UP.1']),
    ('N_E', ['SW_ENT.2', 'R_E.1']),
    ('N_D', ['SW_DN.2', 'R_D.1']),
]
sch_junctions = [
    (134, 250),   # BL_GATE: R_GPD タップ
]
# ワイヤ化ネットのキーパーラベル位置(自動配置が部品に当たるものだけ明示)
sch_labels = {
    'V5D': (81, 64, 0),
    'V3D': (81, 82, 0),
    'LEDP_A': (34, 96, 0),
    'LEDS_A': (44, 116, 0),
    '485D_A': (52, 173.62, 0),
    '485D_B': (70, 171.08, 0),
    'TH_PWM_F': (280, 246, 0),
    'LCD_RST': (116, 216, 0),
    'BL_GATE': (116, 250, 0),
    'BTN_ADC': (37, 276, 0),
    'N_E': (103, 276, 0),
    'N_D': (165, 276, 0),
}

# ===== 回路図の機能ブロック枠と注記(v4.3 追加) =====
# どちらもグラフィックのみでネット・ERC・ネットリスト照合に影響しない。
# 本基板は38ネット超のラベル主体図なので、枠が無いと「どこからどこまでが1機能か」が読めない。
# 枠は互いに重ならない範囲に切ってある(散在しているRS485終端/プルアップは注記で補う)。
# 注記は各枠の**空いている下端**にまとめる(部品・Ref/Value テキストと重ならない位置)。
sch_blocks = [
    (14, 34, 130, 128, 'POWER IN from C-PWR (XH9) / BULK / LED'),
    (142, 34, 244, 128, 'MCU  Raspberry Pi Pico 2 W'),
    (256, 34, 406, 128, 'microSD  TF-01A  (SPI1)'),
    (14, 138, 130, 198, 'RS485 DATA  Waveshare SS-9778 (isolated)'),
    (142, 138, 268, 198, 'I2C  RTC DS3231(0x68) / PRS MS5837(0x76) / TEMP TSYS01(0x77)'),
    # DESIGN NOTES を中段右へ、IMU を下段右へ置く。**下段右は y<=254 まで**:
    #  シート右下 x296-412 / y257-290 は KiCad の A3 タイトルブロックが占有している。
    (280, 138, 406, 198, 'DESIGN NOTES'),
    (14, 208, 196, 284, 'UI  LCD NHD-C0216CiZ(I2C 0x3E) / BACKLIGHT / 3-BUTTON ADC'),
    (208, 208, 294, 284, 'TO C-RX (RX_improved_mini J2) / LEAK DETECT'),
    (312, 208, 406, 254, 'IMU  BNO085 Adafruit 4754  (SPI0)'),
]
# 注記は右下の DESIGN NOTES パネルへ集約する(枠の中に置くと必ず部品か Ref/Value に当たる)。
# 各ブロック内に残すのは「その場所でしか意味を持たない2件」だけ。
sch_texts = [
    (20, 192, 'RS485 側 GND/PE は基板 GND と分離 (絶縁を活かす)。PE はテザーへ', 1.27),
    (18, 258, 'LCD 昇圧C (VOUT-VDD / C1+-C1- 各1u) は LCD 至近の', 1.27),
    (18, 262, 'キャリア基板側に置く (充電ポンプノードなので XH で引き回さない)', 1.27),
    (18, 266, 'BTN_ADC: UP=0V / ENT=0.82V / DN=1.65V / 無押下=3.3V', 1.27),
    (284, 145, '[1] 基板間', 1.6),
    (284, 150, '  J_PWR1 = C-PWR J_MAIN と同一ピン順 (ストレート9芯1本)', 1.27),
    (284, 154, '  I2C対(5/6) を GND(4/7) で挟み、LIGHT_PWM(9) を電源ピンから離してある', 1.27),
    (284, 158, '  J_RX1 = 製造済み RX_improved_mini の J2 と同一ピン順 (pin5 は RX 側 NC)', 1.27),
    (284, 165, '[2] プルアップ / DNP', 1.6),
    (284, 170, '  R_SDA/R_SCL (4.7k) は既定 DNP。組立後に SDA/SCL-V3D 間を実測して要否を決める', 1.27),
    (284, 174, '  バスは 2 基板 + 4 ケーブルに跨るので、総容量が大きければ 2.2k も検討 (tr<1us)', 1.27),
    (284, 178, '  R_SDCS: 起動時 Pico GPIO は Hi-Z -> CS フロート防止 (v4.3)', 1.27),
    (284, 185, '[3] 信号', 1.6),
    (284, 190, '  R_THP+C_THP: 125kHz TH_PWM の dv/dt を落とし、隣接する ENV_ADC へのクロストークを抑える', 1.27),
    (284, 194, '  (RX 側 VTH は高インピーダンス = 直列 R_THP による DC 誤差はゼロ)', 1.27),
]

# --- PCB: 外形 112x88mm (v3.0 小型化: 150x105=15750 -> 9856mm2 = 63%) ---
# 下辺(y=88)を「USB/microSD 挿入辺」に統一(ユーザ要求)。両者を隣接させ書込み系を集約:
#   PICO1 rot180 = USB先端 y87.3(下端フラッシュ) / SD1(TF-01A) rot0 = slot開口 y85.79(端から2.21mm)
#   v4.2: SD が TF-01A になり接点列が**北向き**(y72.65)になったので、SPI は SD 直上の
#   B.Cu 縦バス(y71→y40.5)で Pico へ上げる。Pico crtyd 右端32.67 と SD crtyd 左端34.40。
#   SPIピン(14-17)はPico上端側(y44-52)にあるためSPI長は約35mm。これはPico自体のピン順
#   由来で、USB/SDを同一辺・隣接にする限り短縮不能(GPIO再割当をしない前提)。
# 列の向き: 信号列(pins1-20)=x30 を内側(右の広い領域)へ、電源/BNO列(21-40)=x12.22 を左stripへ。
# 主要ルーティング動線: 左strip(x1-9) / Pico-SD間チャネル(x33-37) / DS3231-Pico間の横レーン(y32-35)
#   / microSD・Waveshare・DS3231・BNO の本体下(パッド以外は銅箔無し=配線可)。
placements = {
    'PICO1': (30, 84.6, 180),      # crtyd x9.55-32.67 y33.9-87.79 / L列x12.22 R列x30
    # v4.2 TF-01A rot0 @(43,79): crtyd x34.40-51.60 y71.70-87.30 / 開口 y85.79(端から2.21mm)
    #  接点列 y72.65 が**北向き**になり Pico 側へ直接脱出できる(旧Molexは南向きで遠回りだった)。
    #  x=43 は Pico(東端x32.67)と Waveshare(西端x53)の中央。
    #  pads: 1(45.15) 2CS(44.05) 3MOSI(42.95) 4V3D(41.85) 5SCK(40.75) 6GND(39.65)
    #        7MISO(38.55) 8(37.45) 10CD(36.35) すべて y72.65
    'SD1': (43, 79, 0),
    # microSD支援(SD接点列の北の空き)。R_CD は Cd パッド(x36.35)の真上へ寄せた。
    'C_SD1': (40, 69, 0), 'C_SD2': (45, 69, 0), 'R_CD': (36, 64, 0),
    # v4.3: SD_CS プルアップ。**y62-65 は I2C の東進レーンなので置けない**(最初 (48,64) に
    #  置いて SDA/SCL が配線不能になった)。V3D 幹線(y67)と SPI ビア列(y71)の間、
    #  C_SD2(crtyd 東端 46.7)の東の空きへ。SD_CS は B.Cu 縦バス(x44.05)から拾う。
    #  さらに C_SD2 の GND 逃がし(y69, x45.95-47.5)と 0.125mm まで寄ったので y68 へ。
    #  pad1(V3D) が V3D 幹線(y67)の真南に来るので、同ネットで直に拾える。
    'R_SDCS': (50, 68, 0),         # crtyd x[48.52,51.48] y[67.27,68.73]
    # 左strip(x1-9): 電源入口 + 入力バルク + Pico用パスコン
    # XHのrot90は (dx,dy)->(dy,-dx) なのでpad列は -y 方向に並ぶ。
    #  rot90(SCLが最北)を選ぶと I2C 2本の幹線が左strip→DS3231間で交差せずに引ける
    #  (rot270だと J_PWR1側とDS3231側でSDA/SCLの上下関係が逆転し必ず1回交差する)。
    # ★v4.0: C-PWR との接続を XH9 1本に統合。rot90 なので pin1 が最南で 2.5mm ずつ北へ:
    #   1 V5D(5.5,32) 2 V3D(5.5,29.5) 3 V3A(5.5,27) 4 GND(5.5,24.5) 5 SCL(5.5,22)
    #   6 SDA(5.5,19.5) 7 GND(5.5,17) 8 INA_AL(5.5,14.5) 9 LIGHT_PWM(5.5,12)
    #   crtyd x[2.65,9.40] y[9.05,34.95]
    # **XH6+XH5 の2本(y14-30 と y35-48)から XH9 1本になり縦20mmの壁ができるので、
    #   左strip の y35 以南を完全に空けるため北へ寄せた。** ここを塞ぐと Pico 左列の
    #   LEAK/ENV_ADC/BTN_ADC/BL_PWM が西へ抜けられず配線不能になる(実際に起きた)。
    'J_PWR1': (5.5, 32, 90),
    'R_AL': (40, 32, 0),           # INA_AL プルアップ。BNO(crtyd x11-37)と V3A幹線(y30)と
                                   #  Pico(y>=33.9)の隙間 / crtyd x[38.52,41.48] y[31.27,32.73]
    # v4.0: H3 を (4.5,66) へ移した分、V5D/V3D バルクを北へ寄せ、C_V3b だけ穴の南へ逃がす
    'C_V5': (5, 54, 0), 'C_V5b': (5, 57, 0), 'C_V3': (5, 60, 0), 'C_V3b': (5, 73, 0),
    'C_D2': (5, 86, 0),            # V5D 100n: Pico pin39(12.22,82.06)近傍
    # 上帯 左: BNO085 (Pico L列上端 pins21-27 = y36-52 の真上)
    'J_BNO1': (24, 15, 0),         # crtyd x11-37 y3.17-26.83, 下列pads1-6 y23.9 / 上列7-12 y6.1
    'C_BNO': (38.8, 13, 90),       # BNO(x37)とDS3231(x41)の隙間。v4.0で V3D幹線が y9.5 に
                                   #  上がったので南へ退避 / pads V3D(38.8,13.79) GND(38.8,12.21)
    # 上帯 中: DS3231 (実測40x20 → 40mm軸がピン列と直交。rot270で本体を西へ寝かせる:
    #  body x41-81 / y9.5-29.5。北のタクトSW(crtyd 下端 y8.05)と南のPico(y>=33.9)の間に収まる)
    'J_RTC1': (80, 19.5, 270),     # pads x=80: 1=13.15 2=15.69 SCL=18.23 SDA=20.77 V3D=23.31 GND=25.85
    # 上辺: UI 3ボタン(USB辺の反対側=操作しやすい) + ラダー抵抗 + 表示LED
    # v4.0: 外形 112->104 に伴い LED/抵抗列と J_PRS1 を西へ 3-5mm 寄せた(H2 の逃げ確保)
    'SW_UP': (40, 2, 0), 'SW_ENT': (52, 2, 0), 'SW_DN': (64, 2, 0),
    # SW_PUSH_6mm の crtyd は x[-1.5,8.0] y[-1.5,6.0] = 9.5x7.5(思ったより東へ張り出す)
    'R_ST': (75, 2, 0), 'LED_ST': (80, 2, 0), 'R_PWR': (75, 6, 0), 'LED_PWR': (80, 6, 0),
    'J_PRS1': (85, 4, 0),          # MS5837/Bar30 I2C (pads V3D85/GND87.5/SDA90/SCL92.5)
    # 上帯 右: I2Cプルアップ + ADCラダー + V3Dパスコン
    'R_SDA': (84, 12, 0), 'R_SCL': (90, 12, 0), 'C_D1': (94, 12, 0),
    'R_LAD': (84, 17, 0), 'R_E': (90, 17, 0), 'R_D': (94, 17, 0),
    # 右中: センサ/UI系コネクタ 横一列 (y52)。v4.0 で J_RXA1/J_LIGHT1 が消えた枠に
    #  Celsius 温度センサ(J_TEMP1, JST-GH)を入れた。
    'C_V3A': (54, 43.21, 90),      # V3Aパススルーのデカップリング。pad1(V3A)=y44.0/pad2(GND)=y42.42
                                   #  pad1 を V3A 幹線(y=44)の真上に置いて分岐を作らない
    'J_RX1': (60, 52, 0),          # pads V3A60/GND62.5/TH_PWM_F65/ENV_ADC67.5/NC70/CMP_OUT72.5
                                   #  crtyd x[57.02,75.48] y[48.6,55.4]
    # v4.3 TH_PWM ケーブル前段RC。J_RX1 の北・V3A 縦幹線(x60)の東の空き帯(y45-47)。
    #  C_THP は「コネクタ側」に置くのが要点(RCの後段=ケーブルへ出る側で dv/dt を落とす)
    'R_THP': (63, 46, 0),          # crtyd x[61.52,64.48] y[45.27,46.73]
    'C_THP': (68, 46, 0),          # crtyd x[66.52,69.48] y[45.27,46.73]
    # v4.4: GH4 -> XH4 で crtyd が 9.46 -> 13.46mm に広がるので、この行の東側3点を
    #  まとめて東へずらす。J_RX1 crtyd 東端 75.48 / 基板端 104 の間に収める:
    #   J_TEMP1 [76.02,89.48] / J_LEAK1 [90.02,98.48] / R_LEAK [99.77,101.23]
    #  隙間は 0.54 / 1.29 / 2.77mm。R_LEAK は H4(99.5,66) とは y が違うので干渉しない。
    'J_TEMP1': (79, 52, 0),        # XH4 pads 1V3D(79,52) 2GND(81.5,52) 3SDA(84,52) 4SCL(86.5,52)
                                   #  crtyd x[76.02,89.48] y[48.6,55.4]
    'J_LEAK1': (93, 52, 0),        # XH2 pads LEAK(93,52) GND(95.5,52) / crtyd x[90.02,98.48]
    'R_LEAK': (100.5, 52, 90),     # crtyd x[99.77,101.23] y[50.52,53.48]
    'C_LEAK': (100.5, 47, 0),      # v4.5 LEAK ノイズ除去 / crtyd x[99.02,101.98] y[46.27,47.73]
    # v4.5: GND テストポイント。y30-46 / x82-104 は配置も配線も無い大きな空き(ASCIIマップ確認済)
    'TP_GND1': (96, 32, 0),
    # 右中下: LCD支援(y59) + LCDコネクタ(y65)
    # v4.0: J_TETH1 を東端から Waveshare の北へ移した分、y59 の列を西へ 3mm 寄せ、
    #  R_GPD だけ東端(x98)へ逃がした
    'C_LCD': (55, 59, 0), 'R_RST': (60, 59, 0), 'C_RST': (65, 59, 0), 'R_BL': (70, 59, 0),
    'Q_BL': (75, 59, 0), 'R_G': (81, 59, 0), 'R_GPD': (98, 59, 90),
    'J_LCD1': (60, 65, 0),         # XH7: GND60/V3D62.5/SDA65/SCL67.5/RST70/A72.5/K75
    # 右下: RS485 Waveshare。v4.0 で 2mm 西へ (TTL側x54.6→Pico pins1/2, 485側x97.4)
    'U_485D1': (76, 78, 0),        # crtyd x53-99 y70-86
    # テザーは XH3 化して Waveshare の**北**へ移した。旧位置(x107.5)は 104mm 幅に入らない。
    'J_TETH1': (87, 62, 0),        # pads A(87,62) B(89.5,62) PE(92,62) / crtyd x[84.02,94.98] y[59.12,65.92]
    'R_TRMD1': (101, 78, 90),      # 120ohm DNP (A-B間)。Waveshare の485パッド(x97.4)の東隣
                                   # crtyd x[100.27,101.73] y[76.52,79.48]
    # 取付穴: v4.0 で 112x88 -> 104x88。ピッチ 103x75.5 -> **95x61.5**。
    #  ★南辺を y=80 に置けない理由: Waveshare(crtyd x53-99 y70-86)が SE 隅を占有しており、
    #    M3 の逃げ(Ø6.9)が必ず重なる。y=66 へ上げてある。
    #    → 基板の南 22mm(Pico USB / microSD / Waveshare の帯)は片持ちになるので、
    #      機体側トレイに**支持パッド**を1つ足すこと(ボスではなく受けでよい)。
    #  ★機体側 child_vtray_deck.scad の main_hx/main_hu も直すこと。
    'H1': (4.5, 4.5, 0), 'H2': (99.5, 4.5, 0), 'H3': (4.5, 66, 0), 'H4': (99.5, 66, 0),
}

texts = [
    ('AquaBeacon C-MAIN v4.6', 34, 36, 'F.SilkS'),
    ('TO C-RX', 62, 47, 'F.SilkS'),
    # Celsius は 4極 JST-GH。線色を刻んで挿し違えを防ぐ(番号規約より色が確実)
    # v4.4: XH4 化に伴いピン順が 1V3D/2GND/3SDA/4SCL になったので線色表記も並べ替え
    #  (Celsius の線色 赤=Vin 緑=SCL 白=SDA 黒=GND)
    ('TEMP  R B W G', 78, 47, 'F.SilkS'),
    ('FROM C-PWR (XH9)', 11, 24, 'F.SilkS'),
    ('104x88', 34, 39, 'F.SilkS'),
    ('USB/SD ->', 34, 71, 'F.SilkS'),
    ('485 DATA Waveshare', 60, 87, 'F.SilkS'),
    ('UI SW', 46, 6, 'F.SilkS'),
    # v4.5: ブリングアップ用の測定点表示(詳細は pcb/BRINGUP_BOARDS.md)
    #  ※電源ピンの説明シルクは入れない。J_PWR1 の周りは既に 'FROM C-PWR (XH9)' と
    #    Ref/Value で埋まっており、長い文字列を足すと BNO/DS3231 の上まで伸びて重なる
    #    (実際に v4.5 の初回レンダーで重なった)。ピン割りは BRINGUP_BOARDS.md を見る。
    ('GND TP', 93, 29, 'F.SilkS'),
]

# ===== 配線: Dijkstra 2層オートルータ。microSD(TF-01A)は短スタブ+ビアでB.Cuへ =====
# SD1 (TF-01A) rot0 @ (43,79): 接点列は y72.65 で**北向き**。各パッドから北へ短スタブ→
# ビアで B.Cu に落とし、SD 本体下の空き B.Cu を縦バスにして Pico の SPI ピン高さへ上げる。
seed_tracks = [
    # BTN_ADC: LCDのI2C化後の再配線でオートルータがPico側1padを残すため、
    # 左端の空きB.Cuレーンから上辺のボタン共通線へ接続する。
    ('BTN_ADC', 'B.Cu', 0.3, ['PICO1.32', (9.5, 64.28), (9.5, 28.5)]),
    # y19.5/27のI2C B.Cu幹線だけF.Cuで跨ぐ。V3A(y30)より北で層を替える。
    ('BTN_ADC', 'F.Cu', 0.3, [(9.5, 28.5), (9.5, 16.5)]),
    ('BTN_ADC', 'B.Cu', 0.3, [(9.5, 16.5), (9.5, 1.2), (40.8, 1.2)]),
    ('SD_CS', 'F.Cu', 0.3, ['SD1.2', (44.05, 71.0)]),
    ('SPI_MOSI', 'F.Cu', 0.3, ['SD1.3', (42.95, 71.0)]),
    ('V3D', 'F.Cu', 0.3, ['SD1.4', (41.85, 71.0)]),
    ('SPI_SCK', 'F.Cu', 0.3, ['SD1.5', (40.75, 71.0)]),
    ('SPI_MISO', 'F.Cu', 0.3, ['SD1.7', (38.55, 71.0)]),
    # ビアから B.Cu で Pico の SPI ピン列の高さ(y40.5)まで一直線に北上させる。
    #  microSD本体下のB.Cuは完全に空き(Molexのパッドは全てF.Cu)。
    #  この4本を「B.Cu の縦バス」として固定するのが要点:
    #   - SD-Pico間を最短にできる(高頻度書込みの要求)
    #   - F.Cu の Pico 東側(x31-48)が空くので R列中段(I2C/LCD/TH_PWM/LIGHT_PWM)が東へ脱出できる
    #  (自動に任せると斜めに広がって東側を塞ぎ、6ネットが配線不能になる)
    ('SD_CS', 'B.Cu', 0.3, [(44.05, 71.0), (44.05, 40.5)]),
    ('SPI_MOSI', 'B.Cu', 0.3, [(42.95, 71.0), (42.95, 40.5)]),
    ('V3D', 'B.Cu', 0.3, [(41.85, 71.0), (41.85, 67.0)]),
    ('SPI_SCK', 'B.Cu', 0.3, [(40.75, 71.0), (40.75, 40.5)]),
    ('SPI_MISO', 'B.Cu', 0.3, [(38.55, 71.0), (38.55, 40.5)]),
    # --- V3D幹線(24ノード。自動任せだと最大bboxで最後に回され11パッド配線不能になる) ---
    # 左strip縦(x2.2) / 上帯を東進(y20: DS3231本体下の空き) / 右下横(y67) の3本の幹に
    # 分け、各ノードは短いタップで拾わせる。
    # 上帯の東進レーンは y20 → y15。v4.0 で V3D は統合コネクタの pin2(5.5,45.5) から取る。
    ('V3D', 'F.Cu', 0.3, ['J_PWR1.2', (2.2, 29.5), (2.2, 76)]),
    ('V3D', 'F.Cu', 0.3, ['C_V3.1', (2.2, 60)]),
    ('V3D', 'F.Cu', 0.3, ['C_V3b.1', (2.2, 73)]),
    # v4.0: 上帯の東進レーンを y15 -> **y9.5** へ。J_PWR1 が XH9 になって北へ寄った結果、
    #  そのパッド列(x5.5, y11.15-32.85, ピッチ2.5)を y15 では貫通できなくなったため、
    #  pin9(y12)の**北**を通す。DS3231 のパッド列(x80, y13.2-25.9)の北も同時に抜けられる。
    ('V3D', 'F.Cu', 0.3, [(2.2, 29.5), (2.2, 9.5), (93.5, 9.5)]),
    ('V3D', 'F.Cu', 0.3, [(39, 67), (90, 67)]),
    # v3.3: 上帯東端の V3D 枝。R_SDA(84,12)/R_LAD(84,17) の pad1 は共に x=83.175 の
    #  縦一列なので、y10 の幹線からそのまま真南に降ろせば他ネットのパッドを踏まない
    #  (ルータ任せだと R_SDA/R_SCL のパッド群に阻まれ R_LAD.1 が届かない)。
    ('V3D', 'F.Cu', 0.3, [(83.175, 9.5), 'R_SDA.1', 'R_LAD.1']),
    # BNO085 の V3D 3本 (pad1=VIN / pad8=P0 / pad9=P1) は上帯幹線(y9.5)から直接落とす。
    #  pad8/pad9 は上列(y6.1)なので北へ 3.4mm の短いスタブ、pad1(VIN)は下列(y23.9)なので
    #  本体下を南下する(BNO の2列間は銅箔が無いので通せる)。
    ('V3D', 'F.Cu', 0.3, [(22.73, 9.5), 'J_BNO1.9']),
    ('V3D', 'F.Cu', 0.3, [(20.19, 9.5), 'J_BNO1.8']),
    ('V3D', 'F.Cu', 0.3, [(17.65, 9.5), 'J_BNO1.1']),
    # --- I2C幹線(B.Cu) ---
    # 左strip縦 → BNO本体下〜DS3231本体下を東進(SDA y27 / SCL y25.5) → DS3231パッドへ北から接近。
    # 交差回避のため SCL=内側(x8.5/y25.5) / SDA=外側(x10.5/y27) の入れ子にする。
    # B.Cuに置くことで、L列→BNO の6本(F.Cuで北上)と交差せずに済む。
    # Pico pins6/7 と北東側(J_PRS1/プルアップ)への枝はルータに任せる(層をまたげるので交差可)。
    # J_I2CP は rot90 なので SCL(pin4,y19.5) が SDA(pin3,y22) より北。幹線は SCL が北(y25.5)
    #  なので、北のSCLを外側レーン(x10.5)・南のSDAを内側レーン(x8.5)に割り当てると交差ゼロ。
    #  (逆にすると SCL の東進スタブが SDA の縦線を必ず1回跨ぐ)
    # v3.3: DS3231 が rot270(pads は東端 x=80 の縦一列)になったので、幹線を本体下で東進
    #  させたあと**北へ立ち上げてから東へ差し込む**。SCL(北の幹線 y25.5)→SCL pad(y16.73=北)、
    #  SDA(南の幹線 y27)→SDA pad(y19.27=南)と南北の順序が保たれるので交差ゼロ。
    #  立ち上げは SCL=x76 / SDA=x78(SCLが先に内側で北上する)。逆にすると必ず1回交差する。
    # ★v4.0: I2C は統合コネクタの pin5(SCL, y38) / pin6(SDA, y35.5) から取る。
    #  SDA(pin6)が SCL(pin5)より**北**なので、上帯の幹線も **SDA を北(y25.5) / SCL を南(y27)**
    #  に入れ替えた。西端で交差しない条件は「南のピンほど外側(x大)のレーンを使う」なので
    #  SDA=内側(x8.5) / SCL=外側(x10.5)。
    #  一方 DS3231 のパッドは SCL(y18.23) が SDA(y20.77) より北なので**東端で1回だけ交差する**。
    #  その1回だけ SCL を F.Cu へ逃がして跨ぐ(B.Cu 幹線はそのまま)。
    #  J_PWR1 は SDA(pin6,y19.5) が SCL(pin5,y22) より北。両者とも南の幹線へ降りるので、
    #  西端で交差しない条件は「北のピンほど外側(x大)のレーン」= SDA x10.5 / SCL x8.5。
    ('I2C_SDA', 'B.Cu', 0.3, ['J_PWR1.6', (10.5, 19.5), (10.5, 25.5), (78, 25.5),
                              (78, 20.77), 'J_RTC1.4']),
    ('I2C_SCL', 'B.Cu', 0.3, ['J_PWR1.5', (8.5, 22), (8.5, 27), (74, 27)]),
    ('I2C_SCL', 'F.Cu', 0.3, [(74, 27), (74, 18.23), 'J_RTC1.3']),
    # ★v4.3: PICO1 の I2C 2本(pin7=SCL y69.36 / pin6=SDA y71.9)の**東側脱出を入れ子で固定**する。
    #  v4.2 まではルータ任せで通っていたが、R_SDCS を足して F.Cu の「R列東側脱出」動線が
    #  細った瞬間に SDA→SCL と順番に配線不能になった(2回とも実際に発生)。
    #  設計:
    #   - 縦は Pico crtyd 東端(32.67)と SD1 crtyd 西端(34.40)の間の 1.7mm チャネル。
    #     **北のピンほど内側(x小)**: SCL=x33.1 / SDA=x33.9(逆にすると必ず1回交差する)
    #   - 横は **F.Cu**。SPI 縦バス(x38.55-44.05)は B.Cu なので交差せず跨げる。
    #     **北の SCL ほど北のレーン**: SCL=y61.0 / SDA=y62.5
    #   - 終点の左右関係も SCL(J_LCD1.4 x67.5)が SDA(J_LCD1.3 x65)より東なので、
    #     始点の上下関係と矛盾せず交差ゼロで収まる
    #   - J_LCD1 は THT なのでビア無しでそのままパッドへ入れる
    #  ※ y60-62 の帯を空けるため、C_LCD.2 の GND 落とし(下の seed)を南→**北**へ変更した
    ('I2C_SCL', 'F.Cu', 0.3, ['PICO1.7', (33.1, 69.36), (33.1, 61.0), (67.5, 61.0),
                              'J_LCD1.4']),
    ('I2C_SDA', 'F.Cu', 0.3, ['PICO1.6', (33.9, 71.9), (33.9, 62.5), (65, 62.5),
                              'J_LCD1.3']),
    # V5D: 左strip東寄りのB.Cuレーン(x8.3)で入口→Pico VSYS(pin39)。
    #  F.Cu側はV3D幹線とバルクコンのパッドで埋まっており、H3の穴も避ける必要がある。
    ('V5D', 'B.Cu', 0.3, ['J_PWR1.1', (8.3, 32), (8.3, 82.06), 'PICO1.39']),
    # V3A: C-PWR(REG3A) → J_PWR1.3 → C_V3A → J_RX1.1 → RX基板 の純パススルー。
    #  v4.0: J_RXA1 廃止に伴い J_PWR1.3 から直接引く。Pico のパッド畑
    #  (x9.55-32.67 / y33.9-87.79, 2.54ピッチで隙間0.84mm)は貫通できないので**上帯を回る**。
    #  上帯の F.Cu は V3D 幹線が y15 を通るだけなので、その**南の y19 レーン**を素で使える。
    #  J_PWR1 のパッド列(x5.5)は東へ 2mm 逃げた x7.5 で北上して回避する。
    #  南下レーンは x48(SPI縦バス x40.5-46 の東隣)。C_V3A は pad1(V3A)が y=44.0 に来るよう
    #  rot90 @(54,43.21) に置き、y44 の幹線上で直に拾う。ビア0本・交差0で通る。
    ('V3A', 'F.Cu', 0.5, ['J_PWR1.3', (7.5, 27), (7.5, 30), (48, 30), (48, 44),
                          (60, 44), 'J_RX1.1']),
    # C_SD2 の GND パッドが F.Cu ベタの小島(44.2-48.5 / 67.4-70.1)に取り残される。
    #  島の中にビアを置く余地が無いので、東へ短スタブを出して島の外でビアを打つ。
    #  V3D の y67 幹線を跨がないよう**南**(y71)へ落とす(SD1 の crtyd は y73.42 から)。
    ('GND', 'F.Cu', 0.3, ['C_SD2.2', (47.5, 69), (47.5, 71)]),
    # C_LCD.2も信号線に囲まれるため短くビアで主GNDへ落とす。
    # v4.3: 落とす向きを南(y61.5)→**北(y57.5)** へ変更。南だと I2C の東進レーン
    #  (SCL y61.0 / SDA y62.5)を必ず跨いでしまう(実際に tracks_crossing が出た)。
    ('GND', 'F.Cu', 0.3, ['C_LCD.2', (55.775, 57.5)]),
    # BNO085とLCDコネクタ周囲のベタが信号線で分断されるため、F.Cu短線+ビアで主B.Cuへ落とす。
    # BNOのpad3から横へ出すと2.54mm隣のpad4を短絡するので、南へ直行する。
    ('GND', 'F.Cu', 0.3, ['J_BNO1.3', (22.73, 28.5)]),
    ('GND', 'F.Cu', 0.3, ['J_LCD1.1', (50.0, 65.0)]),
]
seed_vias = [
    ('BTN_ADC', 9.5, 28.5, 0.3, 0.6), ('BTN_ADC', 9.5, 16.5, 0.3, 0.6),
    ('BTN_ADC', 40.8, 1.2, 0.3, 0.6),
    ('SD_CS', 44.05, 71.0, 0.3, 0.6), ('SPI_MOSI', 42.95, 71.0, 0.3, 0.6),
    ('V3D', 41.85, 71.0, 0.3, 0.6), ('SPI_SCK', 40.75, 71.0, 0.3, 0.6),
    ('SPI_MISO', 38.55, 71.0, 0.3, 0.6),
    # GNDベタ F/B 橋渡し(空き領域スティッチング。孤立島はビルド後 probe_islands.py で追加)
    #  x31-48 は SPI縦バス + R列東側脱出の主要動線なのでビアを置かない
    ('I2C_SCL', 74, 27, 0.3, 0.6),   # v4.0: 東端で SDA を跨ぐための F.Cu ホップ
    ('GND', 52, 36), ('GND', 64, 36), ('GND', 78, 36), ('GND', 92, 36),
    ('GND', 52, 46), ('GND', 92, 46),
    ('GND', 96, 70), ('GND', 20, 45), ('GND', 20, 70),  # (14,30)はV3A経路と競合するため削除
    # F.Cu孤立島の解消。**v4.0 で再配置・再配線したため v3.x 実測の座標は全て破棄した**
    #  (旧座標は部品が動いた先で他ネットのビアと衝突する)。
    #  再実測(`probe_islands.py pcb\CHILD_MAIN\CHILD_MAIN.kicad_pcb`)で残った島は
    #  C_SD2 の GND パッド周り (44.2,67.4)-(48.5,70.1) の1個のみ。ただし島の中に
    #  ビアを置く余地が無い("NO SPOT")ので、下の seed_tracks で短スタブを出して落とす。
    ('GND', 47.5, 71.0),
    ('GND', 55.775, 57.5, 0.3, 0.6),   # v4.3: I2C東進レーンを避けて北へ移設
    ('GND', 22.73, 28.5, 0.3, 0.6), ('GND', 50.0, 65.0, 0.3, 0.6),
]
ok, rpt = build('CHILD_MAIN', parts, placements, (0, 0, 104, 88),
                tracks='auto', vias='auto', seed_tracks=seed_tracks, seed_vias=seed_vias,
                # SD/SPIは最重要(高頻度書込み)なので資源が空いているうちに最短で引かせる
                route_first=('SPI_SCK', 'SPI_MOSI', 'SPI_MISO', 'SD_CS', 'SD_CD',
                             'LIGHT_PWM', 'INA_AL'),
                # Pico GND/AGNDは生成時にpassiveへ補正するため、GNDへPWR_FLAGを付与できる。
                power_flag_nets=('GND', 'V5D', 'V3D', 'V3A'),
                texts=texts, sch_wires=sch_wires, sch_junctions=sch_junctions,
                sch_labels=sch_labels, sch_blocks=sch_blocks, sch_texts=sch_texts)
print('OK' if ok else 'DRC ISSUES')
