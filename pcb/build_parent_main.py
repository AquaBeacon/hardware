"""PARENT_MAIN (P-MAIN) v5.9: 親機メイン基板。2026-07-21統合仕様。主制御 Raspberry Pi Pico 2 W。

v5.9 変更点 (2026-08-04 可読性): **回路図を A3 全面へ再配置した(電気的変更ゼロ)**。
 触ったのは `at` / `rot` / `sch_wires` / `sch_labels` / `sch_junctions` / `sch_blocks` /
 `sch_texts` / `ref_at` / `val_at` / `gnd_style` だけで、`{pin: net}` / `placements` /
 `seed_*` は不変。ネットリスト意図照合 37ネット一致 + DRC 0違反/未接続0 で
 「読みやすくしただけ」を担保している。主な内容: **3列 x 3段のブロックグリッド**へ全面再配置(C-MAIN v4.6 と同一の座標体系。
 共通回路は同じ位置に置いてあるので2枚を並べて差分だけ追える)。
 旧版は枠が互いに交差し、注記が部品の上に乗っていた。注記は DESIGN NOTES パネルへ集約。
 GNSS と SPRESENSE 同期を1ブロックに統合、取付穴と TP は上端の帯(x>=200)へ。
 検算は `python -X utf8 pcb\\check_sch.py build_parent_main` (build不要・数秒)。
**銅箔は完全同一ではない**: `placements` / `seed_*` / `tracks` は不変だがオートルータが
 再実行され、0.3mm 級のトラックが数セグメント別経路になった(ネット番号の並びが変わるため)。
 ドリル/マスク/ペースト/外形/BOM/CPL はバイト一致、DRC 0違反・未接続0 も維持している。
 → **シルクの版数も v5.9 へ上げた**(基板が入れ替わったことを実物で識別できるようにするため)。

v5.8変更(2026-08-03 レビュー残件): **`TP_GND1`(THT GND テストポイント)追加**とブリングアップ用
 シルク。各レールは既存 THT パッド(J_PWR1 / Pico ピン)で測れるので電圧用TPは足していない。
 手順書は `pcb/BRINGUP_BOARDS.md`。

v5.7変更(2026-08-03 レビュー反映。子機に入れた改善を親機にも揃える):
 1. **`J_TETH1` XH4 -> XH3 / `J_SPR1` XH4 -> XH3**。どちらも pin4 が「予備」「NC」で、
    ユーザ要求「予備のXHは全ていらない」は C-MAIN(v4.0 で XH4->XH3)にしか適用されていなかった。
 2. **`R_TXP` 100ohm を TX_PWM に直列追加**。200kHz の TX_PWM が XH ケーブルへ裸で出ていた
    一方、1Hz の PPS/EVENT には 100ohm が入っており優先順位が逆だった。TC4427 の入力容量は
    小さい(数pF)ので 100ohm でもエッジ鈍化は無視でき、リンギングと放射だけが下がる。
    ネット名: Pico 側 `TX_PWM` / コネクタ側 `TX_PWM_O`。
 3. **`C_TT` 10n -> 100n**。TX 温度の RC を tau=10us -> 100us へ。TX 基板は 200kHz で
    スイッチングしており 10us(-3dB 16kHz)では帰還線としてのフィルタが弱い。温度は低速なので
    副作用なし。**R_TTD による分圧比は不変**(Cのみ変更)なのでファームの補正値も不変。
 4. **`R_SDCS` 10k(V3D -> SD_CS) を追加**(C-MAIN v4.3 と同一の理由: 起動時 CS フロート防止)。
 5. 回路図に機能ブロック枠(`sch_blocks`)と注記(`sch_texts`)を追加。あわせて図面上で
    位置が機能とちぐはぐだった `R_SDA`/`R_SCL`(I2C プルアップ)と `J_SPR1` を、それぞれ
    I2C センサ群 / SPRESENSE 同期ブロックの中へ移した(**PCB配置とネットは不変**)。
 6. シルクの版数を実体に合わせた(v5.5 表記のままだった)。

v5.6変更(2026-08-03): microSD を **TF-01A (LCSC C91145, push-push/自動排出)** へ変更し
 JLCPCB の SMT 実装対象にした。自作FP AquaBeacon:microSD_TF-01A。**接点列が北向き(y72.65)**に
 なったので SPI は SD 直上の B.Cu 縦バス(y71 -> y40.5)で Pico へ上げる。R_CD を (37,64) へ移動。
 STATUS LED を黄(JLC Extended)→**赤 C84256(Basic)**へ。

v5.5変更(2026-08-02): SPRESENSE拡張ボード(CXD5602PWBEXT1)使用を反映。
 - 拡張ボードJP1を3.3V側に設定し、Arduino互換デジタル端子へ接続する。
 - v5.4の10k/12k分圧は撤去。PPS/EVENTにはケーブル保護・リンギング抑制用100ohm直列抵抗を入れる。
 - J_SPR1 pin4はNCのまま。SPRESENSE拡張ボードはUSB等の正規電源から給電する。
 - J_SPR1 = SPR_PPS_3V3 / SPR_EVENT_3V3 / GND / NC。

v5.3変更(2026-08-01): **LCD を I2C 品へ変更**(ユーザ判断: 配線簡素化)。
 Newhaven **NHD-C12864WO-B1TFH#-M**(128x64 グラフィック / 4線SPI / 30pin 0.5mm FFC) から
 **NHD-C0216CiZ-FSW-FBW-3V3**(2x16 キャラクタ / I2C / AiP31032 / 8pin 1.5mm THT) へ。
 - 旧LCDは 30pin FFC + バックライト別線(PHR-2)で **J_LCD1(XH9) と物理的に直結できなかった**。
   新LCDは I2C 2本で済むため既存 I2C0 バス(GP4/GP5)へ相乗りする(アドレス 0x7C/8bit = 0x3E/7bit。
   DS3231=0x68 / AT24C32=0x57 / LIS3MDL=0x1C,0x1E / MS5837=0x76 / TSYS01=0x77 / INA226=0x40台 と衝突なし)。
 - **J_LCD1: XH9 -> XH7**(GND/V3D/SDA/SCL/RST/LED_A/LED_K)。
 - **GP14(物理19)=LCD_CS / GP19(物理25)=LCD_DC を解放(NC)**。SPI1 は microSD 専用になり
   「microSD と LCD で SPI1 共有」の制約が消えた。
 - **R_BL: 33ohm/V3D -> 100ohm/V5D**。新LCDの VLED=2.96V typ に対し 3.3V では余裕 0.34V しか
   無く電流が公差で 2.3倍ばらつくため(旧LCDは VLED 3.5V typ で 3.3V では原理的に点灯しなかった)。
 - 昇圧C(VOUT-VDD / C1+-C1- 各1uF)は充電ポンプノードなので **LCD至近のキャリア基板側**に置く。
   本基板には載せない(XHケーブルで引き回さないこと)。
 - Pico 2 W のピン配置は公式データシート/ピンアウト図で照合済み
   (pcb/datasheets/RaspberryPi_Pico2W_datasheet.pdf / _pinout.pdf)。
   KiCad シンボル MCU_Module:RaspberryPi_Pico のピン番号は実機の物理ピン番号と一致(probe_pins 実測)。

v5.2変更(2026-07-31): DS3231(ZS-042)の実測 **40x20x10mm** を反映。40mm軸がピン列と直交する
 ことが判明したため FP を 38x22 -> 20x40 に作り直し、J_RTC1 を rot270 @(80,18.7) へ移設。
 子機と違い I2C 幹線が東のセンサ3連まで貫通するので、幹線レーンを y25.5/27 -> y26.5/28 へ
 下げてパッド列(x=80, y11.3-26.1)の南を通した。実装高さ 18.49mm(ソケット8.5+本体10)。

v5.1(2026-07-31 基板間コネクタ整合。C-MAIN v3.1 と同じ趣旨の修正を親機側にも適用):
 - **P-PWR との電源/I2C**: 旧 J_PWR1(XH6) に電源とI2Cを混載していたが、P-PWR 側は
   J_MAIN(XH6 V5L/V5L/GND/GND/V3S/V3S) + J_I2C(XH5 V3S/GND/SDA/SCL/INA_AL) の2本立てで
   本数もピン順も噛み合っていなかった。J_PWR1 を P-PWR J_MAIN と同順に直し、
   J_I2CP(XH5) を新設して INA226 の ALERT を **GP3** で受ける(R_AL 10k プルアップ)。
   ※P-PWR も v1.2 で J_I2C を XH4→XH5 化し J_ALT(PH2) を廃止した(C-PWR と完全同一)。
 - **P-TX との接続**: 旧 J_TX1(XH6 PWM_A/PWM_B/TX_EN/TX_TEMP_RAW/GND/GND) に対応する
   TX基板が存在しなかった(TX_advanced=XH3 PWM_A/B/GND のみ・TX_EN も温度回路も無し)。
   親機TXを **TX_improved(TC4427+2SK4017 1石)** に確定し、
   J_TX1 を **XH2(TX_PWM/GND) = TX_improved J2 と同順**、
   J_TXT1 を **XH3(V3D/GND/TX_TEMP_RAW) = TX_improved J5(V3S/GND/TEMP_ADC) と同順** に分割。
   PWM は単相 1本(GP16)になり **PWM_B(GP17)/TX_EN(GP18) は廃止=NC**。
   送信停止は TX_PWM を Low 固定(TC4427出力Low → 2SK4017 OFF)で行う。

v4.0(ユーザ指摘反映): 受動部品をSMD化(JLCPCB Basic志向 0603/0805)。UI基板を廃止しスイッチを
本基板へ統合(3ボタンADCラダー+バックライト2N7002+リセットRC)、コネクタはLCD専用(J_LCD1)に変更。
J_UI1廃止。RS485(Waveshare)キャステレーション直付け。SPRESENSEは独立IMUロガー(PPS+EVENT_MARK)。
GNSS=UART1+PPS。P-TX制御=PWM_A/B+TX_EN。TX温度=直列R+RCフィルタ→ADC1。

ネット定義の正: ../docs/AquaBeacon_MAIN_UI_GPIO_コネクタ表.md
実行: & "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" -u pcb\\build_parent_main.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from kicadgen import Part
from buildlib import build

# SMD受動部品(JLCPCB Basic志向)。名称は既存流用のままSMDへ差し替え
RFP = 'Resistor_SMD:R_0603_1608Metric'      # 全抵抗 0603
CDISC = 'Capacitor_SMD:C_0603_1608Metric'   # 100n等 0603
C0805 = 'Capacitor_SMD:C_0805_2012Metric'   # 10uF積セラ 0805
CPRAD = C0805                                # 旧電解10uF→積セラ0805
XLED = 'LED_SMD:LED_0805_2012Metric'         # 表示LED 0805
SWP = 'Button_Switch_THT:SW_PUSH_6mm'        # タクトSW THT 6mm(押しやすさ優先)
FETSMD = 'Package_TO_SOT_SMD:SOT-23'         # 2N7002(G1/S2/D3)
XH2 = 'Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical'
XH3 = 'Connector_JST:JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical'
XH4 = 'Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical'
XH5 = 'Connector_JST:JST_XH_B5B-XH-A_1x05_P2.50mm_Vertical'
XH6 = 'Connector_JST:JST_XH_B6B-XH-A_1x06_P2.50mm_Vertical'
XH7 = 'Connector_JST:JST_XH_B7B-XH-A_1x07_P2.50mm_Vertical'
# (v5.7: 未使用の XH9 定義を削除)
# v5.6: microSD を JLCPCB 実装可能な TF-01A (LCSC C91145, push-push/自動排出) へ変更。
#  自作FP。原点=パターン中心。rot0 で **接点列が -y 側 (y-6.35)、カード開口が +y 側 (y+6.79)**。
#  pads: 1(+2.15) 2(+1.05) 3(-0.05) 4(-1.15) 5(-2.25) 6(-3.35) 7(-4.45) 8(-5.55) 10=Cd(-6.65)
#  shell: SH(-7.75,-5.5) SH(+6.93,-5.5) 9(-7.75,+4.19) SH(+7.75,+4.19) / NPTH φ1.0 (∓, +4.49)
#  crtyd 17.20 x 15.60。Cd の相手側接点はシェルなので shell の1枚を pad"9"(=GND) にしてある。
USD = 'AquaBeacon:microSD_TF-01A'
W485 = 'AquaBeacon:Waveshare_TTL_RS485_C'   # TTL 1-4=VCC/GND/RXD/TXD, 485 5-8=PE/GND/A/B

parts = [
    # ================= MCU: Raspberry Pi Pico 2 W (物理ピン->GPはC-MAINと同一) =================
    # v5.1: pin5(GP3)=INA_AL を追加 / pin21(GP16)=TX_PWM(単相) / pin22(GP17)・pin24(GP18)は解放。
    #  GP16 は RP2350 の PWM slice8A。他に PWM を使うのは BL_PWM(GP28=slice2A) だけなので
    #  200kHz の TX_PWM とバックライト調光は独立に周波数設定できる(スライス衝突なし)。
    #  GP17 は slice8B なので、将来 TX_advanced(相補PWM)へ戻す場合の PWM_B 予約枠として空けてある。
    Part('PICO1', 'MCU_Module', 'RaspberryPi_Pico', 'Pico 2 W',
         'Module:RaspberryPi_Pico_Common_THT',
         {'1': '485D_TXD', '2': '485D_RXD', '4': 'LED_STATUS', '5': 'INA_AL',
          '6': 'I2C_SDA', '7': 'I2C_SCL', '9': 'GNSS_PPS', '10': 'EVENT_MARK',
          '11': 'GNSS_TX', '12': 'GNSS_RX', '14': 'SPI_SCK', '15': 'SPI_MOSI',
          '16': 'SPI_MISO', '17': 'SD_CS', '19': 'NC', '20': 'SD_CD',
          '21': 'TX_PWM', '22': 'NC', '24': 'NC', '25': 'NC',
          '31': 'BTN_ADC', '32': 'TX_TEMP_ADC', '34': 'BL_PWM', '39': 'V5D',
          '3': 'GND', '8': 'GND', '13': 'GND', '18': 'GND', '23': 'GND',
          '28': 'GND', '33': 'GND', '38': 'GND',
          '26': 'NC', '27': 'NC', '29': 'NC',
          '36': 'NC', '30': 'NC', '35': 'NC', '37': 'NC', '40': 'NC'},
         # シンボル実寸: x±22.86 / y-38.1..+35.56。左右のラベルを入れて約 82 x 90mm。
         # Value は本体の左下へ逃がす(真下は GND シンボルが 8 個重なる場所)。
         at=(192, 86), ref_at=(192, 37), val_at=(162, 124)),

    # ================= 電源入力 / I2C+ALERT (P-PWRから) =================
    # v5.1: P-PWR の出力コネクタと1:1で噛み合うよう2本に分割(C-MAIN v3.1 と同一方式)。
    #  旧版は電源+I2Cを1本のXH6に混載していたが、P-PWR 側は J_MAIN(XH6)/J_I2C(XH5) の2本で
    #  ピン順も違い、ストレートケーブルでは繋がらなかった。
    Part('J_PWR1', 'Connector_Generic', 'Conn_01x06', 'PWR_FROM_PPWR', XH6,   # ← P-PWR J_MAIN
         {'1': 'V5D', '2': 'V5D', '3': 'GND', '4': 'GND', '5': 'V3D', '6': 'V3D'},
         at=(40, 50), gnd_style='label', ref_at=(40, 36), val_at=(40, 62)),
    Part('J_I2CP', 'Connector_Generic', 'Conn_01x05', 'I2C_FROM_PPWR', XH5,   # ← P-PWR J_I2C
         {'1': 'V3D', '2': 'GND', '3': 'I2C_SDA', '4': 'I2C_SCL', '5': 'INA_AL'},
         at=(40, 82), gnd_style='label', ref_at=(40, 68), val_at=(40, 94)),
    # INA226 ALERT はオープンドレイン → 受け側(GP3)でプルアップする
    Part('R_AL', 'Device', 'R', '10k', RFP, {'1': 'V3D', '2': 'INA_AL'}, at=(100, 44), rot=90),
    Part('C_V5', 'Device', 'C', '10u', C0805, {'1': 'V5D', '2': 'GND'}, at=(78, 67.81)),
    Part('C_V5b', 'Device', 'C', '100n', CDISC, {'1': 'V5D', '2': 'GND'}, at=(100, 67.81)),
    Part('C_V3', 'Device', 'C_Polarized', '10u', CPRAD, {'1': 'V3D', '2': 'GND'}, at=(78, 85.81)),
    Part('C_V3b', 'Device', 'C', '100n', CDISC, {'1': 'V3D', '2': 'GND'}, at=(100, 85.81)),
    Part('R_PWR', 'Device', 'R', '1k', RFP, {'1': 'V3D', '2': 'LEDP_A'}, at=(28, 96), rot=90),
    Part('LED_PWR', 'Device', 'LED', 'GREEN', XLED, {'2': 'LEDP_A', '1': 'GND'}, at=(54, 96), rot=180),
    Part('R_ST', 'Device', 'R', '1k', RFP, {'1': 'LED_STATUS', '2': 'LEDS_A'}, at=(38, 116), rot=90),
    Part('LED_ST', 'Device', 'LED', 'RED', XLED, {'2': 'LEDS_A', '1': 'GND'}, at=(64, 116), rot=180),

    # ================= microSD (TF-01A push-push, SPI1) =================
    Part('SD1', 'Connector', 'Micro_SD_Card_Det2', 'microSD', USD,
         {'1': 'NC', '2': 'SD_CS', '3': 'SPI_MOSI', '4': 'V3D', '5': 'SPI_SCK',
          '6': 'GND', '7': 'SPI_MISO', '8': 'NC', '9': 'GND', '10': 'SD_CD', 'SH': 'GND'},
         at=(320, 76), gnd_style='label', ref_at=(320, 50), val_at=(320, 100)),
    Part('C_SD1', 'Device', 'C', '100n', CDISC, {'1': 'V3D', '2': 'GND'}, at=(368, 60)),
    Part('C_SD2', 'Device', 'C', '10u', C0805, {'1': 'V3D', '2': 'GND'}, at=(390, 60)),
    Part('R_CD', 'Device', 'R', '47k', RFP, {'1': 'V3D', '2': 'SD_CD'}, at=(372, 84), rot=90),
    # v5.7: CS プルアップ。Pico の GPIO は起動〜ファーム初期化まで Hi-Z なので、これが無いと
    #  CS がフロートしカードが未選択に落ち着かない(SPIモード microSD の間欠不良の定番要因)。
    Part('R_SDCS', 'Device', 'R', '10k', RFP, {'1': 'V3D', '2': 'SD_CS'}, at=(372, 100), rot=90),

    # ================= I2C センサ群 (DS3231/MS5837/LIS3MDL/Celsius) =================
    Part('J_RTC1', 'Connector_Generic', 'Conn_01x06', 'DS3231_ZS042', 'AquaBeacon:DS3231_ZS042',
         {'1': 'NC', '2': 'NC', '3': 'I2C_SCL', '4': 'I2C_SDA', '5': 'V3D', '6': 'GND'},
         at=(172, 164), gnd_style='label', ref_at=(172, 150), val_at=(172, 176)),
    Part('J_PRS1', 'Connector_Generic', 'Conn_01x04', 'MS5837', XH4,
         {'1': 'V3D', '2': 'GND', '3': 'I2C_SDA', '4': 'I2C_SCL'},
         at=(212, 164), gnd_style='label', ref_at=(212, 152), val_at=(212, 176)),
    Part('J_MAG1', 'Connector_Generic', 'Conn_01x04', 'LIS3MDL', XH4,
         {'1': 'V3D', '2': 'GND', '3': 'I2C_SDA', '4': 'I2C_SCL'},
         at=(248, 164), gnd_style='label', ref_at=(248, 152), val_at=(248, 176)),
    Part('J_TEMP1', 'Connector_Generic', 'Conn_01x04', 'CELSIUS_TEMP', XH4,
         {'1': 'V3D', '2': 'GND', '3': 'I2C_SDA', '4': 'I2C_SCL'},
         at=(284, 164), gnd_style='label', ref_at=(280, 152), val_at=(280, 176)),
    # I2Cプルアップはモジュール側との並列過多を避けるため既定DNP。
    # 無通電時のSDA/SCL-V3D間抵抗を測り、4.7k超なら必要に応じて実装する。
    # v5.7: 図面上の位置だけ I2C センサ群の中へ移した(PCB配置・ネットは不変)
    Part('R_SDA', 'Device', 'R', '4.7k_DNP', RFP, {'1': 'V3D', '2': 'I2C_SDA'}, at=(172, 188), rot=90),
    Part('R_SCL', 'Device', 'R', '4.7k_DNP', RFP, {'1': 'V3D', '2': 'I2C_SCL'}, at=(216, 188), rot=90),

    # ================= GNSS (NEO-M9N: UART1 + PPS) =================
    Part('J_GNSS1', 'Connector_Generic', 'Conn_01x05', 'NEO_M9N', XH5,
         {'1': 'V3D', '2': 'GND', '3': 'GNSS_TX', '4': 'GNSS_RX', '5': 'GNSS_PPS'},
         at=(338, 226), gnd_style='label', ref_at=(338, 214), val_at=(338, 238)),

    # ============ RS485通信: DATA=Waveshare(絶縁,双方向,自動方向) 1個のみ (トリガ廃止) ============
    # 実物7pad: TTL 1=GND 2=RXD 3=TXD 4=VCC / RS485 5=PE 6=B 7=A。PE→テザー(単一絶縁リンクの基準)
    Part('U_485D1', 'Connector_Generic', 'Conn_01x07', 'W_RS485_DATA', W485,
         {'1': 'GND', '2': '485D_TXD', '3': '485D_RXD', '4': 'V3D',
          '5': '485D_PE', '6': '485D_B', '7': '485D_A'},
         at=(46, 166), gnd_style='label', ref_at=(46, 150), val_at=(46, 180)),   # ピン (40.92, 158.38..173.62)
    # 終端(120Ω,既定DNP) + テザー(4ピンXH: A/B/PE + 予備)
    Part('R_TRMD1', 'Device', 'R', '120_DNP', RFP, {'1': '485D_A', '2': '485D_B'}, at=(100, 172), rot=180),   # 1=(100,175.81) 2=(100,168.19)
    # v5.7: XH4 -> XH3。pin4 は「予備」だったのでユーザ要求(予備のXHは全ていらない)に従い削除。
    #  C-MAIN は v4.0 で既に XH3 化済みで、親機だけ取り残されていた。
    Part('J_TETH1', 'Connector_Generic', 'Conn_01x03', 'TETHER', XH3,
         {'1': '485D_A', '2': '485D_B', '3': '485D_PE'},
         at=(108, 148), ref_at=(108, 140), val_at=(108, 156)),

    # ================= P-TX (TX_improved) 制御 + TX温度ADC入口 =================
    # TX_improved v1.1 のコネクタと1:1(ストレート)で噛み合わせる:
    #   J_TX1 (XH2) → TX_improved J2 : 1=PWM_IN 2=GND
    #   J_TXT1(XH3) → TX_improved J5 : 1=V3S(=本基板のV3D) 2=GND 3=TEMP_ADC
    # TX側は V3S→R6 10k 1%→TEMP_RAW→NTC(10k B=3977)→GND の分圧を R7 1k で送出する。
    # 本基板側は R_TT 1k + C_TT 10n でフィルタし、R_TTD 100k で **ケーブル断線時に 0V へ落とす**
    # (NTC断線は TX 側 R6 が 3.3V へ持ち上げるので、両方向の故障が識別できる)。
    # ※R_TTD 100k はTX側テブナン(5k)+直列2kに並列に効くので読み値が約 -5.7% ずれる。
    #   分圧比は既知なのでファーム側で補正すること(未補正なら 25℃付近で約 +2.9℃ の誤差)。
    Part('J_TX1', 'Connector_Generic', 'Conn_01x02', 'TO_PTX_PWM', XH2,
         {'1': 'TX_PWM_O', '2': 'GND'},
         at=(240, 222), gnd_style='label', ref_at=(240, 214), val_at=(240, 230)),
    # ★v5.7: 200kHz TX_PWM のケーブル直列ダンピング。TC4427 の入力容量は数pF なので
    #  100ohm でも時定数は 1ns 未満(周期 5us の 0.02%)= 波形は事実上変わらず、
    #  ケーブルのリンギングと放射だけが下がる。PPS/EVENT(1Hz)には既に 100ohm が入っており、
    #  より高速な TX_PWM だけ素通しだったのを揃えた。
    Part('R_TXP', 'Device', 'R', '100', RFP,
         {'1': 'TX_PWM', '2': 'TX_PWM_O'}, at=(272, 222), rot=90),
    Part('J_TXT1', 'Connector_Generic', 'Conn_01x03', 'TO_PTX_TEMP', XH3,
         {'1': 'V3D', '2': 'GND', '3': 'TX_TEMP_RAW'},
         at=(240, 246), gnd_style='label', ref_at=(240, 236), val_at=(240, 254)),
    Part('R_TT', 'Device', 'R', '1k', RFP, {'1': 'TX_TEMP_RAW', '2': 'TX_TEMP_ADC'}, at=(240, 268), rot=90),
    # v5.7: 10n -> 100n (tau 10us -> 100us)。TX 基板は 200kHz でスイッチングしており
    #  tau=10us(-3dB 16kHz)ではフィルタが弱い。温度は低速なので副作用なし。
    #  **R_TT/R_TTD は不変 = DC 分圧比も不変**なので、ファーム側の -5.7% 補正値は変えなくてよい。
    Part('C_TT', 'Device', 'C', '100n', CDISC, {'1': 'TX_TEMP_ADC', '2': 'GND'}, at=(270, 271.81)),
    Part('R_TTD', 'Device', 'R', '100k', RFP, {'1': 'TX_TEMP_ADC', '2': 'GND'}, at=(284, 271.81)),

    # ================= SPRESENSE拡張ボード IMUロガー同期 =================
    # CXD5602PWBEXT1のArduino互換デジタル端子を使用し、JP1は必ず3.3V側へ設定する。
    # PPS/EventはいずれもP-MAIN→SPRESENSEの低速・単方向信号。100ohm直列抵抗で
    # ケーブルのリンギングと誤設定時の瞬間的な競合電流を緩和する。
    Part('R_PPS', 'Device', 'R', '100', RFP,
         {'1': 'GNSS_PPS', '2': 'SPR_PPS_3V3'}, at=(376, 216), rot=90),
    Part('R_EVT', 'Device', 'R', '100', RFP,
         {'1': 'EVENT_MARK', '2': 'SPR_EVENT_3V3'}, at=(376, 228), rot=90),
    # v5.7: XH4 -> XH3。pin4 は v5.5 で V3D 給電を廃止して以来 NC のままだった
    #  (SPRESENSE 拡張ボードは USB 等の正規電源から給電する)。図面位置も本ブロック内へ移動。
    Part('J_SPR1', 'Connector_Generic', 'Conn_01x03', 'TO_SPRESENSE_EXT_3V3', XH3,
         {'1': 'SPR_PPS_3V3', '2': 'SPR_EVENT_3V3', '3': 'GND'},
         at=(380, 246), gnd_style='label', ref_at=(380, 238), val_at=(380, 252)),

    # ============ UI統合(LCD+3ボタン+バックライト)。旧J_UI1(UI基板)廃止, コネクタはLCD専用 ============
    # v5.3: LCD を Newhaven NHD-C0216CiZ-FSW-FBW-3V3 (2x16キャラクタ / I2C / AiP31032) に変更。
    #  旧 NHD-C12864WO(128x64, 4線SPI, 30pin FFC) から乗り換え、配線を簡素化した:
    #   - SPI(SCK/MOSI/CS/DC) 4本 -> I2C(SDA/SCL) 2本。既存 I2C0 バスへ相乗り(アドレス 0x3E/7bit)
    #   - J_LCD1 は XH9 -> XH7 に縮小、Pico の GP14(物理19)/GP19(物理25) が解放される
    #   - LCD側の昇圧C(VOUT-VDD 1u / C1+-C1- 1u)は LCD至近のキャリア基板に置く(充電ポンプノードのため
    #     XHケーブルで引き回さない)。本基板には載せない
    #  データシート: pcb/datasheets/NHD-C0216CiZ-FSW-FBW-3V3_Newhaven_datasheet.pdf (ピン配置 p.5)
    # LCDコネクタ(7ピン): GND/V3D/SDA/SCL/RST/LED_A/LED_K
    Part('J_LCD1', 'Connector_Generic', 'Conn_01x07', 'NHD_C0216CiZ', XH7,
         {'1': 'GND', '2': 'V3D', '3': 'I2C_SDA', '4': 'I2C_SCL', '5': 'LCD_RST',
          '6': 'LEDBL_A', '7': 'LEDBL_K'},
         at=(44, 232), gnd_style='label', ref_at=(44, 216), val_at=(44, 246)),
    Part('C_LCD', 'Device', 'C', '100n', CDISC, {'1': 'V3D', '2': 'GND'}, at=(76, 232)),
    # LCDリセット RC (電源投入リセット, GPIO消費せず)
    Part('R_RST', 'Device', 'R', '10k', RFP, {'1': 'V3D', '2': 'LCD_RST'}, at=(110, 216), rot=90),
    Part('C_RST', 'Device', 'C', '100n', CDISC, {'1': 'LCD_RST', '2': 'GND'}, at=(136, 219.81)),
    # バックライト: BL_PWM->R_G->gate, Q_BL(2N7002:1=G,2=S,3=D) D=LEDBL_K S=GND, V5D->R_BL->LEDBL_A
    # v5.3: 33ohm/V3D -> 100ohm/V5D。NHD-C0216CiZ の VLED=2.88/2.96/3.12V @ILED=20mA に対し
    #  3.3Vレールでは余裕が 0.34V しかなく、VLED公差だけで電流が 2.3倍ばらつく(0.18-0.42V)。
    #  V5D なら (5-2.96)/(100+RDS(on)~7) = 19.1mA、公差込みでも 18.4-20.8mA に収まる。
    #  V5D は J_PWR1(pin1,2) で本基板に来ている。ILED max は 30mA なので上限側も安全。
    Part('R_BL', 'Device', 'R', '100', RFP, {'1': 'V5D', '2': 'LEDBL_A'}, at=(110, 232), rot=90),
    Part('Q_BL', 'Transistor_FET', '2N7002', '2N7002', FETSMD,
         {'1': 'BL_GATE', '2': 'GND', '3': 'LEDBL_K'}, at=(158, 250), gnd_style='label',
         ref_at=(146, 244), val_at=(146, 257)),   # G(152.92,250) S(160.54,255.08) D(160.54,244.92)
    Part('R_G', 'Device', 'R', '100', RFP, {'1': 'BL_PWM', '2': 'BL_GATE'}, at=(110, 250), rot=90),
    Part('R_GPD', 'Device', 'R', '100k', RFP, {'1': 'BL_GATE', '2': 'GND'}, at=(134, 253.81)),
    # 3ボタン ADC抵抗ラダー(BTN_ADC 1本判別): UP=0V/ENT=0.82V(3.3k/13.3k)/DN=1.65V/無=3.3V
    Part('R_LAD', 'Device', 'R', '10k', RFP, {'1': 'V3D', '2': 'BTN_ADC'}, at=(32, 276), rot=90),
    Part('SW_UP', 'Switch', 'SW_Push', 'UP', SWP, {'1': 'BTN_ADC', '2': 'GND'}, at=(58, 276), gnd_style='label'),
    Part('SW_ENT', 'Switch', 'SW_Push', 'ENTER', SWP, {'1': 'BTN_ADC', '2': 'N_E'}, at=(96, 276)),
    Part('R_E', 'Device', 'R', '3.3k', RFP, {'1': 'N_E', '2': 'GND'}, at=(124, 276), rot=90, gnd_style='label'),
    Part('SW_DN', 'Switch', 'SW_Push', 'DOWN', SWP, {'1': 'BTN_ADC', '2': 'N_D'}, at=(158, 276)),
    Part('R_D', 'Device', 'R', '10k', RFP, {'1': 'N_D', '2': 'GND'}, at=(186, 276), rot=90),

    # ================= パスコン =================
    Part('C_D1', 'Device', 'C', '100n', CDISC, {'1': 'V3D', '2': 'GND'}, at=(100, 112)),
    Part('C_D2', 'Device', 'C', '100n', CDISC, {'1': 'V5D', '2': 'GND'}, at=(78, 112)),

    # v5.8: スコープのグランドクリップ用 GND テストポイント(THT)。
    #  各レールは既に THT パッドで測れる(V5D/V3D/GND=J_PWR1, Pico 各ピン)ので電圧用TPは足さない。
    #  測定点の一覧は pcb/BRINGUP_BOARDS.md 参照。
    Part('TP_GND1', 'Connector', 'TestPoint', 'GND',
         'TestPoint:TestPoint_THTPad_D1.5mm_Drill0.7mm', {'1': 'GND'},
         at=(310, 22), gnd_style='label', ref_at=(318, 21), val_at=(318, 24.5)),

    Part('H1', 'Mechanical', 'MountingHole', 'M3', 'MountingHole:MountingHole_3.2mm_M3', {}, at=(200, 22)),
    Part('H2', 'Mechanical', 'MountingHole', 'M3', 'MountingHole:MountingHole_3.2mm_M3', {}, at=(225, 22)),
    # v5.0: 外形をC-MAINと同一(112x88)にしたので取付穴も4隅共通(筐体を共用できる)
    Part('H3', 'Mechanical', 'MountingHole', 'M3', 'MountingHole:MountingHole_3.2mm_M3', {}, at=(250, 22)),
    Part('H4', 'Mechanical', 'MountingHole', 'M3', 'MountingHole:MountingHole_3.2mm_M3', {}, at=(275, 22)),
]

# 隣接する部品どうしだけワイヤで結ぶ(40ネット超のラベル主体図。全部を配線すると読めなくなる)。
sch_wires = [
    ('V5D', ['C_V5.1', 'C_V5b.1']),
    ('V3D', ['C_V3.1', 'C_V3b.1']),
    ('LEDP_A', ['R_PWR.2', 'LED_PWR.2']),
    ('LEDS_A', ['R_ST.2', 'LED_ST.2']),
    # x=90 で短く縦にジョグしてから R_TRMD1 の上下ピンへ入れる(A は y173.62、B は y171.08)
    ('485D_A', ['U_485D1.7', (90, 173.62), (90, 175.81), 'R_TRMD1.1']),
    ('485D_B', ['U_485D1.6', (90, 171.08), (90, 168.19), 'R_TRMD1.2']),
    ('TX_TEMP_ADC', ['R_TT.2', 'C_TT.1', 'R_TTD.1']),
    ('LCD_RST', ['R_RST.2', 'C_RST.1']),
    ('BL_GATE', ['R_G.2', 'R_GPD.1', 'Q_BL.1']),
    ('BTN_ADC', ['R_LAD.2', 'SW_UP.1']),
    ('N_E', ['SW_ENT.2', 'R_E.1']),
    ('N_D', ['SW_DN.2', 'R_D.1']),
]
sch_junctions = [
    (270, 268),   # TX_TEMP_ADC: C_TT タップ
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
    'TX_TEMP_ADC': (246, 268, 0),
    'LCD_RST': (116, 216, 0),
    'BL_GATE': (116, 250, 0),
    'BTN_ADC': (37, 276, 0),
    'N_E': (103, 276, 0),
    'N_D': (165, 276, 0),
}

# ===== 回路図の機能ブロック枠と注記(v5.9 で全面再配置) =====
# グラフィックのみでネット・ERC・ネットリスト照合に影響しない。
# A3(420x297)を 3列 x 3段に切り、**枠どうしは縦10mm・横12mm 以上**あける。
# 見出しは枠の外側・上に size2.0 で出る(枠上辺 -3.27..-1.27)ので、詰めると上の枠を踏む。
# **y<=32 は空ける**: PWR_FLAG が (20,20)+i*25.4 固定で、下向きラベルが y=29 付近まで伸びる。
# C-MAIN と同一回路の部分(電源入力/Pico/microSD/RS485/UI)は **C-MAIN v4.6 と同じ座標**に
# してあるので、2枚を並べて差分だけ追える。
sch_blocks = [
    (14, 34, 130, 128, 'POWER + I2C IN from P-PWR / BULK / LED'),
    (142, 34, 244, 128, 'MCU  Raspberry Pi Pico 2 W'),
    (256, 34, 406, 128, 'microSD  TF-01A  (SPI1)'),
    (14, 138, 130, 198, 'RS485 DATA  Waveshare SS-9778 (isolated)'),
    (142, 138, 288, 198, 'I2C SENSORS  RTC(0x68) / PRS(0x76) / MAG(0x1C) / TEMP(0x77)'),
    # DESIGN NOTES を中段右へ、GNSS/SPRESENSE を下段右へ置く。**下段右は y<=254 まで**:
    #  シート右下 x296-412 / y257-290 は KiCad の A3 タイトルブロックが占有している。
    (300, 138, 406, 198, 'DESIGN NOTES'),
    (14, 208, 196, 284, 'UI  LCD NHD-C0216CiZ(I2C 0x3E) / BACKLIGHT / 3-BUTTON ADC'),
    (208, 208, 294, 284, 'TO P-TX  (TX_improved: PWM / NTC -> ADC1)'),
    (312, 208, 406, 254, 'GNSS NEO-M9N / SPRESENSE EXT SYNC (JP1=3V3)'),
]
# 注記は右下の DESIGN NOTES パネルへ集約する(枠の中に置くと必ず部品か Ref/Value に当たる)。
# 各ブロック内に残すのは「その場所でしか意味を持たない3行」だけ。
sch_texts = [
    (20, 192, 'RS485 側 GND/PE は基板 GND と分離 (絶縁を活かす)。PE はテザーへ', 1.27),
    (18, 258, 'LCD 昇圧C (VOUT-VDD / C1+-C1- 各1u) は LCD 至近の', 1.27),
    (18, 262, 'キャリア基板側に置く (充電ポンプノードなので XH で引き回さない)', 1.27),
    (18, 266, 'BTN_ADC: UP=0V / ENT=0.82V / DN=1.65V / 無押下=3.3V', 1.27),
    (304, 145, '[1] 基板間', 1.6),
    (304, 150, '  J_PWR1 = P-PWR J_MAIN / J_I2CP = P-PWR J_I2C (ストレート)', 1.27),
    (304, 154, '  J_TX1 / J_TXT1 = TX_improved の J2 / J5 とストレート', 1.27),
    (304, 158, '  J_SPR1: PPS/EVENT とも P-MAIN -> SPRESENSE の単方向 (各 100 直列)', 1.27),
    (304, 162, '  拡張ボードの JP1 は必ず 3.3V 側へ (電源は拡張ボード側から)', 1.27),
    (304, 169, '[2] プルアップ / DNP', 1.6),
    (304, 174, '  R_SDA/R_SCL (4.7k) は既定 DNP。組立後に実測して要否を決める', 1.27),
    (304, 178, '  (2 基板 + 4 ケーブルで総容量が大きい -> 2.2k も検討, tr<1us)', 1.27),
    (304, 182, '  R_SDCS: 起動時 Pico GPIO は Hi-Z -> CS フロート防止 (v5.7)', 1.27),
    (304, 189, '[3] TX 温度 / PWM', 1.6),
    (304, 194, '  R_TTD 100k = 断線時に 0V へ落とす (読み値 -5.7%) / R_TXP = ダンピング', 1.27),
]

# --- PCB: 外形 112x88mm (v5.0 小型化: 182x116=21112 -> 9856mm2 = 47%) ---
# 下辺(y=88)を「USB/microSD 挿入辺」に統一(ユーザ要求)。C-MAIN v3.0 と同一外形・同一取付穴・
# 同一の Pico/SD/電源/LCD/485 配置(検証済みの動線をそのまま流用)。C-MAINのBNO085の場所に
# 親機固有の J_TX1(P-TX制御)+TX温度RC を置き、右側にI2Cセンサ3個を縦積みしている。
#   PICO1 rot180 = USB先端 y87.3(下端フラッシュ) / SD1(TF-01A) rot0 = slot開口 y85.79(端から2.21mm)
#   Pico crtyd 右端32.67 と SD crtyd 左端35.40。SPIはSD直上のB.Cu縦バス(y71→y40.5)で直結。
# 主要動線: 左strip(x1-9) / Picoのピン列間チャネル(x12-30, 北向き) / DS3231・Waveshare本体下
placements = {
    'PICO1': (30, 84.6, 180),      # crtyd x9.55-32.67 y33.9-87.79 / L列x12.22 R列x30
    # v5.6 TF-01A rot0 @(44,79): crtyd x35.40-52.60 y71.70-87.30 / 開口 y85.79(端から2.21mm)
    #  接点列 y72.65 が**北向き**になり Pico 側へ直接脱出できる(旧Molexは南向きで遠回りだった)。
    #  pads: 1(46.15) 2CS(45.05) 3MOSI(43.95) 4V3D(42.85) 5SCK(41.75) 6GND(40.65)
    #        7MISO(39.55) 8(38.45) 10CD(37.35) すべて y72.65
    'SD1': (44, 79, 0),
    'C_SD1': (41, 69, 0), 'C_SD2': (46, 69, 0), 'R_CD': (37, 64, 0),
    # v5.7: SD_CS プルアップ。SD crtyd(y71.70から)の北・V3D 幹線(y67)の北の空き。
    #  SD_CS は B.Cu 縦バス(x45.05)にあるので東から短く拾える / crtyd x[47.52,50.48] y[63.27,64.73]
    'R_SDCS': (49, 64, 0),
    # 左strip(x1-9): 電源入口 + I2C入口 + 入力バルク + Pico用パスコン
    # XHのrot90は (dx,dy)->(dy,-dx) なのでpad列は -y 方向(pin1が最北)。この順だと
    #  左strip→DS3231 の I2C 2本が交差せずに引ける(rot270だと必ず1回交差する)。
    'J_PWR1': (5.5, 48, 90),       # pads V5D48/V5D45.5/GND43/GND40.5/V3D38/V3D35.5
    # I2C+ALERT入口は左strip北端(C-MAIN v3.1と同座標。I2C幹線 y25.5/27 に最短で乗る)
    'J_I2CP': (5.5, 27, 90),       # pads V3D27/GND24.5/SDA22/SCL19.5/AL17, crtyd y14.0-30.0
    'R_AL': (6, 11, 0),            # INA_AL プルアップ(J_I2CPの北・J_TX1の西の空き)
    'C_V5': (5, 66, 0), 'C_V5b': (5, 69, 0), 'C_V3': (5, 72, 0), 'C_V3b': (5, 75, 0),
    'C_D2': (5, 86, 0),            # V5D 100n: Pico pin39(12.22,82.06)近傍
    # 上帯 左: P-TX制御(単相PWM)+ TX温度コネクタ + 温度RC。
    #  Pico L列上端 pin21(GP16=TX_PWM)=(12.22,36.34) / pin32(GP27=TX_TEMP_ADC)=(12.22,64.28)
    'J_TX1': (13.5, 12, 0),        # XH2: pads TX_PWM_O(13.5,12) GND(16,12), crtyd x11.05-18.45
    'J_TXT1': (23, 12, 0),         # XH3: pads V3D(23,12) GND(25.5,12) TX_TEMP_RAW(28,12)
    # v5.7: TX_PWM 直列 100ohm。J_TX1 の南・温度RC列(y24)の北の空き帯。
    #  Pico pin21(GP16)=(12.22,36.34) から北上して R_TXP -> J_TX1.1 の順に通る
    'R_TXP': (14, 18, 0),          # crtyd x[12.52,15.48] y[17.27,18.73]
    'R_TT': (14, 24, 0), 'C_TT': (19, 24, 0), 'R_TTD': (24, 24, 90),
    # 上帯 中: DS3231 (実測40x20 → 40mm軸がピン列と直交。rot270で本体を西へ寝かせる:
    #  body x41-81 / y8.7-28.7。北のタクトSW(crtyd 下端 y8.05)との隙間0.25mm、南はPico(y>=33.9)。
    #  子機と違い I2C 幹線が東へ貫通するので、パッド列(y11.3-26.1)より南に幹線を通す必要があり
    #  レーンを y25.5/27 → **y26.5/28** へ下げてある(子機は幹線がここで終端するので不要)
    'J_RTC1': (80, 18.7, 270),     # pads x=80: 1=12.35 2=14.89 SCL=17.43 SDA=19.97 V3D=22.51 GND=25.05
    # 上辺: UI 3ボタン(USB辺の反対側=操作しやすい) + 表示LED
    'SW_UP': (40, 2, 0), 'SW_ENT': (52, 2, 0), 'SW_DN': (64, 2, 0),
    'R_ST': (76, 2, 0), 'LED_ST': (81, 2, 0), 'R_PWR': (76, 6, 0), 'LED_PWR': (81, 6, 0),
    # 上帯 右: I2Cプルアップ + ADCラダー + V3Dパスコン
    'R_SDA': (84, 12, 0), 'R_SCL': (90, 12, 0), 'C_D1': (96, 12, 0),
    'R_LAD': (84, 17, 0), 'R_E': (90, 17, 0), 'R_D': (96, 17, 0),
    # 右: I2Cセンサ3個を縦積み。rot0なので同じネットのパッドがx一定の縦一列に並び、
    #  SDA(x98)/SCL(x100.5) を1本の縦線でデイジーチェーンできる(他ネットのパッドを踏まない)。
    'J_PRS1': (93, 32, 0), 'J_MAG1': (93, 42, 0), 'J_TEMP1': (93, 52, 0),
    # 右中: GNSS(pins9/11/12) / SPRESENSE拡張ボード同期(JP1=3.3V、100ohm直列)
    'J_GNSS1': (58, 52, 0), 'J_SPR1': (74.5, 52, 0),
    'R_PPS': (72, 46, 0), 'R_EVT': (82, 46, 0),
    # 右中下: LCD支援(y59) + LCDコネクタ(y65)
    'C_LCD': (58, 59, 0), 'R_RST': (63, 59, 0), 'C_RST': (68, 59, 0), 'R_BL': (73, 59, 0),
    'Q_BL': (78, 59, 0), 'R_G': (84, 59, 0), 'R_GPD': (89, 59, 90),
    'J_LCD1': (60, 65, 0),         # v5.3: XH7 pads GND60/V3D62.5/SDA65/SCL67.5/RST70/A72.5/K75 (旧XH9は x80まで)
    # 右下: RS485 Waveshare (TTL側x56.6→Pico pins1/2, 485側x99.4→右端テザー)
    'U_485D1': (78, 78, 0),        # crtyd x55-101 y70-86
    'R_TRMD1': (102.5, 75, 90), 'J_TETH1': (107.5, 60, 90),
    # v5.8: GND テストポイント。y30-42 / x50-88 の空き(GNDスティッチビアから7mm以上離す)
    'TP_GND1': (58, 38, 0),
    'H1': (4.5, 4.5, 0), 'H2': (107.5, 4.5, 0), 'H3': (4.5, 80, 0), 'H4': (107.5, 80, 0),
}

texts = [
    ('AquaBeacon P-MAIN v5.9', 34, 36, 'F.SilkS'),
    ('112x88', 34, 39, 'F.SilkS'),
    ('USB/SD ->', 34, 71, 'F.SilkS'),
    ('485 DATA Waveshare', 60, 87, 'F.SilkS'),
    ('PWM', 12, 8, 'F.SilkS'),
    ('TX TEMP', 22, 8, 'F.SilkS'),
    ('UI SW', 46, 6, 'F.SilkS'),
    ('PRS/MAG/TEMP', 86, 30, 'F.SilkS'),
    ('SPRESENSE EXT', 70, 42, 'F.SilkS'),
    ('JP1=3V3!', 63, 45, 'F.SilkS'),
    # v5.8: ブリングアップ用の測定点表示(詳細は pcb/BRINGUP_BOARDS.md)
    #  ※電源ピンの説明シルクは入れない(C-MAIN と同じ理由: 左strip は Ref/Value で埋まっている)
    ('GND TP', 55, 35, 'F.SilkS'),
]

# ===== 配線: C-MAIN v3.0 と同一の手seed戦略(同一配置なのでSD/SPI/V5Dはそのまま流用) =====
seed_tracks = [
    # microSD: パッド→内側スタブ→段違いビア
    ('SD_CS', 'F.Cu', 0.3, ['SD1.2', (45.05, 71.0)]),
    ('SPI_MOSI', 'F.Cu', 0.3, ['SD1.3', (43.95, 71.0)]),
    ('V3D', 'F.Cu', 0.3, ['SD1.4', (42.85, 71.0)]),
    ('SPI_SCK', 'F.Cu', 0.3, ['SD1.5', (41.75, 71.0)]),
    ('SPI_MISO', 'F.Cu', 0.3, ['SD1.7', (39.55, 71.0)]),
    # B.Cu 縦バス: SD本体下(TF-01Aのパッドは全てF.Cuなので空き)を通りPicoのSPIピン高さへ。
    #  SD-Pico間を最短にし、かつ F.Cu の Pico 東側を空けてR列中段の東進を通す。
    ('SD_CS', 'B.Cu', 0.3, [(45.05, 71.0), (45.05, 40.5)]),
    ('SPI_MOSI', 'B.Cu', 0.3, [(43.95, 71.0), (43.95, 40.5)]),
    ('SPI_SCK', 'B.Cu', 0.3, [(41.75, 71.0), (41.75, 40.5)]),
    ('SPI_MISO', 'B.Cu', 0.3, [(39.55, 71.0), (39.55, 40.5)]),
    ('V3D', 'B.Cu', 0.3, [(42.85, 71.0), (42.85, 67.0)]),
    # --- V3D幹線 --- 左strip縦(x2.2) → 上辺(y7.5: コネクタ列の北) → x36縦 →
    #  上帯を東進(y20: DS3231本体下) / 右下横(y67)。各ノードは短いタップで拾わせる。
    #  v5.1: 給電元が J_PWR1.5/.6(倍ピン)に変わり、J_I2CP.1 も同じ幹線から拾う。
    ('V3D', 'F.Cu', 0.3, ['J_PWR1.5', (2.2, 38), (2.2, 76)]),
    ('V3D', 'F.Cu', 0.3, ['J_PWR1.6', (2.2, 35.5)]),   # 倍ピンの片割れ
    ('V3D', 'F.Cu', 0.3, ['J_I2CP.1', (2.2, 27)]),
    ('V3D', 'F.Cu', 0.3, ['C_V3.1', (2.2, 72)]),
    ('V3D', 'F.Cu', 0.3, ['C_V3b.1', (2.2, 75)]),
    # v5.2: 東端は y20 のままだと DS3231 のパッド列(x=80, y13.2-25.9)に突き当たる。
    #  x74 で y10 へ上がってからパッド列の北を east へ抜ける。
    ('V3D', 'F.Cu', 0.3, [(2.2, 38), (2.2, 7.5), (36, 7.5), (36, 20), (74, 20),
                          (74, 10), (95.5, 10)]),
    ('V3D', 'F.Cu', 0.3, [(39, 67), (95, 67)]),
    # v5.2: 上帯東端の V3D 枝。R_SDA(84,12)/R_LAD(84,17) の pad1 は共に x=83.175 の
    #  縦一列なので、y10 の幹線からそのまま真南に降ろせば他ネットのパッドを踏まない
    #  (ルータ任せだと R_SDA/R_SCL のパッド群に阻まれ R_LAD.1 が届かない)。
    ('V3D', 'F.Cu', 0.3, [(83.175, 10), 'R_SDA.1', 'R_LAD.1']),
    # --- I2C幹線(B.Cu, 入れ子: SCL=内側y25.5 / SDA=外側y27) ---
    # 右のセンサ3連は縦一直線でデイジーチェーン。SCLの縦線(x100.5)はSDA横線の終点(x98)より
    #  東、SDAの縦線(x98)はSCL横線(y25.5)より南に置くことで交差ゼロにしている。
    # v5.1: 入口が J_I2CP(x5.5, SCL=y19.5 / SDA=y22) に変わった。C-MAIN と同じく
    #  北のSCLを外側レーン(x10.5)・南のSDAを内側レーン(x8.5)に割り当てると交差ゼロになる。
    ('I2C_SCL', 'B.Cu', 0.3, ['J_I2CP.4', (10.5, 19.5), (10.5, 26.5), (100.5, 26.5),
                              'J_PRS1.4', 'J_MAG1.4', 'J_TEMP1.4']),
    # v5.2: DS3231 が rot270(pads は東端 x=80 の縦一列。SCL=y16.73 / SDA=y19.27 で
    #  どちらも幹線より**北**)になった。SCLは幹線(y25.5)から x76 で北上すればSDA幹線(y27)を
    #  跨がずに届く。SDAは y27 から北上すると**SCL幹線(y25.5)を必ず1回跨ぐ**
    #  (親機はSCL幹線がx100.5まで東進するので西へ逃げても回避不能) → ビアでF.Cuに乗り換える。
    ('I2C_SCL', 'B.Cu', 0.3, [(76, 26.5), (76, 17.43), 'J_RTC1.3']),
    ('I2C_SDA', 'B.Cu', 0.3, ['J_I2CP.3', (8.5, 22), (8.5, 28), (98, 28),
                              'J_PRS1.3', 'J_MAG1.3', 'J_TEMP1.3']),
    ('I2C_SDA', 'F.Cu', 0.3, [(78, 28), (78, 19.97), 'J_RTC1.4']),
    # V5D: 左strip東寄りのB.Cuレーン(x8.3)で入口→Pico VSYS(pin39)。H3の穴(x2.9-6.1)を避ける。
    ('V5D', 'B.Cu', 0.3, ['J_PWR1.1', (8.3, 48), (8.3, 82.06), 'PICO1.39']),
    ('V5D', 'F.Cu', 0.3, ['J_PWR1.1', 'J_PWR1.2']),   # 倍ピンの片割れ
]
seed_vias = [
    ('SD_CS', 45.05, 71.0, 0.3, 0.6), ('SPI_MOSI', 43.95, 71.0, 0.3, 0.6),
    ('V3D', 42.85, 71.0, 0.3, 0.6), ('SPI_SCK', 41.75, 71.0, 0.3, 0.6),
    ('SPI_MISO', 39.55, 71.0, 0.3, 0.6),
    ('V3D', 42.85, 67.0, 0.3, 0.6),   # B.Cu縦バス→F.Cu右下幹線(y67)の乗り換え
    ('I2C_SDA', 78, 28, 0.3, 0.6),        # v5.2: SDA幹線(B.Cu)→F.Cuへ乗り換えてSCL幹線を跨ぐ
    # GNDベタ F/B 橋渡し。x31-48 は SPI縦バス+R列東側脱出の主要動線なのでビアを置かない
    ('GND', 52, 36), ('GND', 64, 36), ('GND', 78, 36), ('GND', 52, 46), ('GND', 78, 46),
    ('GND', 52, 62), ('GND', 96, 64), ('GND', 14, 30), ('GND', 20, 45), ('GND', 20, 70),
    ('GND', 86, 22),
    ('GND', 88.40, 18.60),   # F.Cu孤立島(R_E/R_DのGNDパッド。probe_islands.pyで実測)
    # v5.3: R_BL の V3D->V5D 変更で再配線され、C_SD2(0805, SMD なので F.Cu のみ)の
    #  GNDパッド(45.95,69)が I2C_SCL(北 y66) / I2C_SDA(南 y70.5・東 x47.4) / V3D(西) に
    #  囲まれて F.Cu 上で孤立した(C_SD1 は THT なので B.Cu 主ベタへ素通し=孤立しない)。
    #  島ポリゴンへの内包判定(SHAPE_POLY_SET.Contains)と両層クリアランス実測で選んだ唯一の
    #  実用解が (46.70,69.30)。F.Cu/B.Cu とも非GND銅から 0.55mm 空く(DRC下限 0.5mm)。
    #  ※パッド列の北(y67.7付近)は島ではなく主ベタ側なので、そこに置いても島は繋がらない。
    ('GND', 46.70, 69.30),
]

ok, rpt = build('PARENT_MAIN', parts, placements, (0, 0, 112, 88),
                tracks='auto', vias='auto', seed_tracks=seed_tracks, seed_vias=seed_vias,
                # SD/SPIは最重要(高頻度書込み)なので資源が空いているうちに最短で引かせる
                route_first=('SPI_SCK', 'SPI_MOSI', 'SPI_MISO', 'SD_CS', 'SD_CD'),
                # Pico GND/AGNDは生成時にpassiveへ補正するため、GNDへPWR_FLAGを付与できる。
                power_flag_nets=('GND', 'V5D', 'V3D'),
                texts=texts, sch_wires=sch_wires, sch_junctions=sch_junctions,
                sch_labels=sch_labels, sch_blocks=sch_blocks, sch_texts=sch_texts)
print('OK' if ok else 'DRC ISSUES')
