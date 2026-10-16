# P-MAIN / C-MAIN / P-PWR / C-PWR 設計仕様 (2026-07-19 コネクタ確定版準拠)

../docs/AquaBeacon_詳細設計書.md の実装仕様。
本ファイルが4基板の **確定ネット表**。build_*.py はこの表に一致させること。

## 共通方針

- センサ・低電流信号 = JST XH (`Connector_JST:JST_XH_B{n}B-XH-A_1x0{n}_P2.50mm_Vertical`,
  パッドピッチ2.5mm, pin1=(0,0), +x方向)。電源系 = XT30
  (`Connector_AMASS:AMASS_XT30U-M_1x02_P5.0mm_Vertical`, pin1=(0,0), pin2=(+5,0))。
  シンボルはどちらも `Connector_Generic:Conn_01x0N`。
  **XT30の極性(2026-07-19確定・FP実測)**: KiCadのAMASS_XT30U-Mは **pad1=「−」pad2=「+」**
  (FP内蔵シルクで確認済み)。全XT30は **1=GND(または低電位側), 2=+レール** に割当てること。
  → J_BAT: 1=GND 2=VBAT / J_TX・J_RXP: 1=GND 2=VBAT_M / J_LED: 1=LED_N 2=VBAT_M。
  (下表の旧記載「1=VBAT 2=GND」等はこの規則を優先して読み替える)
- microSD = `Connector:Micro_SD_Card_Det2` + `Connector_Card:microSD_HC_Molex_104031-0811`。
  シンボルピン(sch座標, 配置(X,Y)基準): 1 DAT2=(X-22.86,Y-10.16), 2 DAT3/CD=(Y-7.62),
  3 CMD=(Y-5.08), 4 VDD=(Y-2.54), 5 CLK=(Y), 6 VSS=(Y+2.54), 7 DAT0=(Y+5.08),
  8 DAT1=(Y+7.62), 10 DET_A=(Y+10.16), 9 DET_B=(Y+12.7), SH=(X+20.32,Y+12.7)。
  FPパッド(rot0): 1..8 SMD上列 (-3.105..+4.545, -5.45), 9=(-5.74,0.7), 10=(-5.74,4.4),
  SH=(5.755,-5.1)。SMDパッドなので配線はF.Cuから直接。コートヤード25.7x18.0。
- SDロードスイッチ = IRLML6402 (SOT-23, `Transistor_FET:IRLML6402` 1=G,2=S,3=D /
  `Package_TO_SOT_SMD:SOT-23` pads 1=(-0.938,-0.95),2=(-0.938,0.95),3=(0.938,0))。
  ハイサイドPMOS: S=3.3Vレール, D=SD_VDD, G=SD_PWR_EN(GPIO直駆動+100kプルアップでデフォルトOFF)。
- 逆接保護 = `Transistor_FET:IRF9540N`(TO-220, 1=G,2=D,3=S,
  `Package_TO_SOT_THT:TO-220-3_Vertical`)。D=ヒューズ後, S=負荷側, G→100k→GND。
  Vgs max±20V > 12.6V なのでツェナー不要。
- 入力TVS = SMBJ15A (`Diode_SMD:D_SMB`) K=ヒューズ後レール, A=GND(build_tx_improved.pyのD1参照)。
- 3.3V LDO = NJU7223F33 購入済み (Conn_01x03表現, TO-220F, **1=VOUT 2=VIN 3=GND**,
  build_child_main.py旧版のREG33参照)。入出力に10u(CP)+100n。
- Fuse/TB/PSK/PH/R/C のFPエイリアスは旧 build_child_main.py と同じものを使う。
- 電池電流経路(VBAT*, LED_N, V5系幹線)はトラック幅1.5〜2.0mm。信号0.5〜0.6mm。
- モジュール類(BUCK/INA226/DS3231/RS485)はピンソケット実装(従来通り)。
- INA226 = CJMCU-226系モジュール想定(未購入)。1x06ソケット(電源/I2C/ALERT/VBS) +
  1x02ソケット(IN+/IN-, 電池電流をモジュール内シャント経由で通す)。
  ※3A対応にはモジュールのシャントをR010へ換装(シルクに注記不要、docs側に記載済み)。
- I2Cプルアップは基板側に置かない(DS3231/INA226等モジュール内蔵品を使用)。
- XT30間の誤挿抜は全てVBATレベルなので破損しない。シルクに用途名と+/-を明記。
- 基板名/スクリプト: PARENT_MAIN=build_parent_main.py, CHILD_MAIN=build_child_main.py,
  PARENT_PWR=build_parent_pwr.py, CHILD_PWR=build_child_pwr.py (全て作り直し/新規)。

## CHILD_PWR (C-PWR) 100x70mm

電流経路: J_BAT(XT30) → F1(3A) → Q1(逆接PFET) → J_SW(外部スイッチTB2) →
J_INAS(INA226シャント) → VBAT_M → 各系統。

| Ref | シンボル | 値 | FP | ピン→ネット |
|---|---|---|---|---|
| J_BAT | Conn_01x02 | LiPo3S_XT30 | XT30U-M | 1=VBAT 2=GND |
| F1 | Device:Fuse | 3A | FUSEクリップ | 1=VBAT 2=VBAT_F |
| D1 | (SMBJ) | SMBJ15A | D_SMB | K=VBAT_F A=GND |
| Q1 | IRF9540N | IRF9540N | TO-220-3_V | 1(G)=QG 2(D)=VBAT_F 3(S)=VBAT_P |
| R_G | R | 100k | RFP | 1=QG 2=GND |
| J_SW | Conn_01x02 | PWR_SW | TB2 | 1=VBAT_P 2=VBAT_SW |
| J_INA | Conn_01x06 | INA226_MOD | PSK6 | 1=V3D 2=GND 3=INA_AL 4=I2C_SCL 5=I2C_SDA 6=VBAT_SW(VBSセンス) |
| J_INAS | Conn_01x02 | INA226_SHUNT | PSK2(PinSocket_1x02) | 1=VBAT_SW 2=VBAT_M |
| C_BLK | C_Polarized | 470u/25V | CP_Radial_D8.0mm_P3.50mm | 1=VBAT_M 2=GND |
| C_BK1 | C | 10u/25V | CDISC | 1=VBAT_M 2=GND |
| PS1 | Conn_01x04 | BUCK_5V_MOD | PSK4 | 1=VBAT_M 2=GND 3=V5D 4=GND |
| C_BK2 | C | 10u | CDISC | V5D/GND |
| C_D5 | C | 100n | CDISC | V5D/GND |
| REG3D | Conn_01x03 | NJU7223F33 | TO-220F | 1=V3D 2=V5D 3=GND |
| C_3D1 | C_Polarized | 10u | CPRAD | V3D/GND |
| C_3D2 | C | 100n | CDISC | V3D/GND |
| REG3A | Conn_01x03 | NJU7223F33 | TO-220F | 1=V3A 2=V5D 3=GND |
| C_3A1 | C_Polarized | 10u | CPRAD | V3A/GND |
| C_3A2 | C | 100n | CDISC | V3A/GND |
| Q2 | IRLZ44Nシンボル | TK7R4A10PL | TO-220-3_V | 1(G)=QG_LED 2(D)=LED_N 3(S)=GND |
| R_GL | R | 100 | RFP | 1=LED_PWM 2=QG_LED |
| R_PDL | R | 100k | RFP | 1=QG_LED 2=GND |
| D_LED | (SMBJ) | SMBJ15A | D_SMB | K=LED_N A=GND (誘導クランプ) |
| J_LED | Conn_01x02 | LED_XT30 | XT30U-M | 1=VBAT_M 2=LED_N |
| J_RXP | Conn_01x02 | RX_XT30 | XT30U-M | 1=VBAT_M 2=GND (現行RX_improved電源) |
| J_RXA | Conn_01x03 | RX_3V3A | XH3 | 1=V3A 2=GND 3=GND (将来RXクリーン給電) |
| J_MAIN | Conn_01x06 | TO_CMAIN_PWR | XH6 | 1=V5D 2=V5D 3=GND 4=GND 5=V3D 6=V3D |
| J_CTL | Conn_01x02 | LED_PWM_IN | XH2 | 1=LED_PWM 2=GND |
| LED1+R_LED | LED+R 1k | PWR_LED | LED_D3.0mm+RFP | V5D→R→LED→GND |
| H1-H4 | MountingHole M3 | | | |

## PARENT_PWR (P-PWR) 100x70mm

C-PWRと同じ保護チェーン(J_BAT/F1/D1/Q1/R_G/J_SW/J_INA/J_INAS/C_BLK/C_BK1)。
INA226のVCCはV3S。相違点:

| Ref | シンボル | 値 | FP | ピン→ネット |
|---|---|---|---|---|
| PS_A | Conn_01x04 | BUCK_5V_LOGIC | PSK4 | 1=VBAT_M 2=GND 3=V5L 4=GND |
| PS_B | Conn_01x04 | BUCK_5V_CAM | PSK4 | 1=VBAT_M 2=GND 3=V5C 4=GND |
| C_5L1/C_5L2 | 10u/100n | | CDISC | V5L/GND |
| C_5C1/C_5C2 | 10u/100n | | CDISC | V5C/GND |
| REG3S | Conn_01x03 | NJU7223F33 | TO-220F | 1=V3S 2=V5L 3=GND |
| C_3S1/C_3S2 | 10u(CP)/100n | | | V3S/GND |
| J_TX | Conn_01x02 | TX_XT30 | XT30U-M | 1=VBAT_M 2=GND (P-TXのV12入力へ) |
| J_MAIN | Conn_01x06 | TO_PMAIN_PWR | XH6 | 1=V5L 2=V5L 3=GND 4=GND 5=V3S 6=V3S |
| J_POD | Conn_01x02 | POD_5V | XH2 | 1=V5C 2=GND (Pi Zero 2W, XH接点3A以内) |
| J_I2C | Conn_01x04 | I2C_PMAIN | XH4 | 1=V3S 2=GND 3=I2C_SDA 4=I2C_SCL |
| J_ALT | Conn_01x02 | INA_ALERT | PH2 | 1=INA_AL 2=GND (予備) |
| LED1+R_LED | V5L系 | | | |
| H1-H4 | | | | |

J_INA: 1=V3S 2=GND 3=INA_AL 4=I2C_SCL 5=I2C_SDA 6=VBAT_SW。

## CHILD_MAIN (C-MAIN) 130x95mm — 全面作り直し

Picoキャリア。電源はC-PWRから受電(基板上にヒューズ/BUCK/LDO無し)。
BNO085はSPI0+INT+RST。microSDオンボード(Molex)。

Picoピン割当(モジュールピン番号: GPn):
1:GP0=DBG_TX 2:GP1=DBG_RX 4:GP2=CMP_OUT 5:GP3=LEAK_DET 6:GP4=I2C_SDA 7:GP5=I2C_SCL
9:GP6=TRG_RO 10:GP7=INA_AL 11:GP8=U1TX 12:GP9=U1RX 14:GP10=SD_SCK 15:GP11=SD_MOSI
16:GP12=SD_MISO 17:GP13=SD_CS 19:GP14=SD_CD 20:GP15=SD_PWR_EN 21:GP16=IMU_MISO
22:GP17=IMU_CS 24:GP18=IMU_SCK 25:GP19=IMU_MOSI 26:GP20=IMU_INT 27:GP21=IMU_RST
29:GP22=TH_PWM 30:RUN=RUN_N 31:GP26=ENV_ADC 32:GP27=RX_EN 34:GP28=LED_PWM
39:VSYS=VSYS_D 36:3V3=NC(**V3Dと接続しない** — レール競合回避) 40:VBUS=NC
GND: 3,8,13,18,23,28,33,38。35,37=NC。

| Ref | シンボル | 値 | FP | ピン→ネット |
|---|---|---|---|---|
| PICO1 | RaspberryPi_Pico | Pico | RaspberryPi_Pico_Common_THT | 上記 |
| D_VS | D_Schottky | 1N5819 | D_DO-41_SOD81_P10.16mm_H | K=VSYS_D A=V5 (USB併用時の逆流防止) |
| J_PWR | Conn_01x06 | FROM_CPWR | XH6 | 1=V5 2=V5 3=GND 4=GND 5=V3D 6=V3D |
| J_IMU | Conn_01x08 | BNO085_SPI | XH8 | 1=V3D 2=GND 3=IMU_SCK 4=IMU_MOSI 5=IMU_MISO 6=IMU_CS 7=IMU_INT 8=IMU_RST |
| J_RX | Conn_01x07 | TO_RX_J2 | XH7 | 1=GND 2=TH_PWM 3=ENV_ADC 4=RX_EN 5=CMP_OUT 6=GND 7=GND |
| J_I2CS | Conn_01x04 | I2C_BAR30 | XH4 | 1=V3D 2=GND 3=I2C_SDA 4=I2C_SCL |
| J_I2CP | Conn_01x05 | I2C_CPWR | XH5 | 1=V3D 2=GND 3=I2C_SDA 4=I2C_SCL 5=INA_AL |
| J_LEAK | Conn_01x02 | LEAK | XH2 | 1=LEAK_S 2=GND |
| R_LK | R | 1M | RFP | 1=V3D 2=LEAK_S (プルアップ; 漏水で電極間導通→Low) |
| C_LK | C | 100n | CDISC | 1=LEAK_S 2=GND |
| ※LEAK_DETはLEAK_Sと同ネットにする(=ネット名LEAK_Sに統一, GP3へ) |
| J_CTL | Conn_01x02 | LED_PWM_OUT | XH2※ | 1=LED_PWM 2=GND (→C-PWR J_CTL) ※J_LEAKとXH2重複はシルクで区別 |
| SD1 | Micro_SD_Card_Det2 | microSD | Molex 104031-0811 | 1=NC 2=SD_CS_C 3=SD_MOSI_C 4=SD_VDD 5=SD_SCK_C 6=GND 7=SD_MISO 8=NC 9=GND 10=SD_CD SH=GND |
| Q_SD | IRLML6402 | IRLML6402 | SOT-23 | 1(G)=SD_PWR_EN 2(S)=V3D 3(D)=SD_VDD |
| R_PU | R | 100k | RFP | 1=V3D 2=SD_PWR_EN |
| R_SC/R_SM/R_SS | R | 22 | RFP | SD_SCK→SD_SCK_C / SD_MOSI→SD_MOSI_C / SD_CS→SD_CS_C |
| R_CSU | R | 100k | RFP | 1=SD_VDD 2=SD_CS_C (CSプルアップ) |
| R_CD | R | 100k | RFP | 1=V3D 2=SD_CD |
| C_SD1 | C | 100n | CDISC | SD_VDD/GND |
| C_SD2 | C | 10u | CDISC | SD_VDD/GND |
| TRIG1 | MAX3485 | MAX3485CPA | DIP-8 | 1=TRG_RO 2=GND 3=GND 4=GND 5=GND 6=TRG_A 7=TRG_B 8=V3D (受信固定) |
| R_TRM | R | 120 | RFP | TRG_A/TRG_B |
| J_TETH | Conn_01x05 | TETHER | TB5 | 1=TRG_A 2=TRG_B 3=485D_A 4=485D_B 5=GND |
| J_485AB | Conn_01x03 | RS485_AB | TB3 | 1=485D_A 2=485D_B 3=GND |
| J_485 | Conn_01x04 | TTL_RS485_C | PSK4 | 1=GND 2=U1RX 3=U1TX 4=V3D (旧版どおり; モジュール表記GND/RXD/TXD/VCC) |
| J_RTC | Conn_01x06 | DS3231_MOD | PSK6 | 1=NC 2=NC 3=I2C_SCL 4=I2C_SDA 5=V3D 6=GND |
| J_DBG | Conn_01x03 | UART0_DBG | PH3 | 1=GND 2=DBG_TX 3=DBG_RX |
| SW_RST | Switch:SW_Push | RESET | SW_PUSH_6mm | 1=RUN_N 2=GND |
| C_TR | C | 100n | CDISC | V3D/GND (MAX3485近傍) |
| C_D1..C_D3 | C | 100n | CDISC | V3D/GND (Pico/RTC/IMUコネクタ近傍) |
| C_BK | C | 10u | CDISC | V5/GND |
| LED1+R_LED | LED+R 1k | PWR | | V3D→R→LED→GND |
| H1-H4 | M3 | | | |

## PARENT_MAIN (P-MAIN) 130x95mm — 全面作り直し

SPRESENSE拡張ボード(CXD5602PWBEXT1, JP1=3.3V)とケーブル接続するキャリア。
電源はP-PWRから受電。GNSS UART+PPS、microSDオンボード、1-Wire、I2C×3ポート。
SPRESENSEのUARTはUART2(D00/D01)のみ→GNSSに割当。RS485データはD03/D07のGPIO
(SW-UART/デバッグ用途, 確定仕様メモ§4「必要ならデバッグ用RS485」)。TX_ENは廃止
(TX基板J2にTX_ENは存在しない)。

SPRESENSE拡張ピン割当:
D00=GNS_TX(モジュール→SPR RX) D01=GNS_RX(SPR TX→モジュール) D02=TRG_TX D03=485_TXD
D04=GNSS_PPS D05=PWM_B D06=PWM_A D07=485_RXD D08=SD_PWR_EN D09=OW_DQ D10=SD_CS
D11=SD_MOSI D12=SD_MISO D13=SD_SCK D14=I2C_SDA D15=I2C_SCL A0=SD_CD

| Ref | シンボル | 値 | FP | ピン→ネット |
|---|---|---|---|---|
| J_SPR1 | Conn_01x08 | SPR_D00-D07 | PH8 | 1=GNS_TX 2=GNS_RX 3=TRG_TX 4=485_TXD 5=GNSS_PPS 6=PWM_B 7=PWM_A 8=485_RXD |
| J_SPR2 | Conn_01x08 | SPR_D08-D15 | PH8 | 1=SD_PWR_EN 2=OW_DQ 3=SD_CS 4=SD_MOSI 5=SD_MISO 6=SD_SCK 7=I2C_SDA 8=I2C_SCL |
| J_SPR3 | Conn_01x04 | SPR_A0_GND | PH4(PinHeader_1x04) | 1=SD_CD 2=NC 3=GND 4=GND |
| J_PWRIN | Conn_01x06 | FROM_PPWR | XH6 | 1=V5L 2=V5L 3=GND 4=GND 5=V3S 6=V3S |
| J_SPRPWR | Conn_01x02 | TO_EXT_JP3_5VIN | PH2 | 1=V5L 2=GND |
| J_GNSS | Conn_01x05 | NEO-M9N | XH5 | 1=V3S 2=GND 3=GNS_TX 4=GNS_RX 5=GNSS_PPS |
| J_MAG | Conn_01x04 | LIS3MDL_I2C | XH4 | 1=V3S 2=GND 3=I2C_SDA 4=I2C_SCL |
| J_PRS | Conn_01x04 | BAR30_I2C | XH4 | 同上 |
| J_I2CP | Conn_01x04 | I2C_PPWR | XH4 | 同上 (→P-PWR J_I2C) |
| J_TEMP | Conn_01x03 | DS18B20 | XH3 | 1=V3S 2=GND 3=OW_DQ |
| R_OW | R | 4.7k | RFP | 1=V3S 2=OW_DQ |
| J_TXSIG | Conn_01x03 | TO_TX_J2 | XH3 | 1=PWM_A 2=PWM_B 3=GND (TEMPとXH3重複、シルク区別) |
| SD1回路一式 | C-MAINと同一構成 | | | レール=V3S, SD_PWR_EN/SD_CD/R_PU/R_CD/R_SC/R_SM/R_SS/R_CSU/C_SD1/C_SD2/Q_SD |
| TRIG1 | MAX3485 | MAX3485CPA | DIP-8 | 1=NC 2=GND 3=V3S(DE=H常時送信) 4=TRG_TX 5=GND 6=TRG_A 7=TRG_B 8=V3S |
| R_TRM | R | 120 | RFP | TRG_A/TRG_B |
| J_TETH | Conn_01x05 | TETHER | TB5 | 1=TRG_A 2=TRG_B 3=485D_A 4=485D_B 5=GND |
| J_485AB | Conn_01x03 | RS485_AB | TB3 | 1=485D_A 2=485D_B 3=GND |
| J_485 | Conn_01x04 | TTL_RS485_C | PSK4 | 1=GND 2=485_RXD 3=485_TXD 4=V3S |
| J_RTC | Conn_01x06 | DS3231_MOD | PSK6 | 1=NC 2=NC 3=I2C_SCL 4=I2C_SDA 5=V3S 6=GND |
| C_TR/C_D1..C_D3 | C 100n | | CDISC | V3S/GND 分散 |
| C_BK | C | 10u | CDISC | V5L/GND (J_SPRPWR近傍) |
| LED1+R_LED | LED+R 1k | PWR | | V3S→R→LED→GND |
| H1-H4 | M3 | | | |

## 検証・出荷条件(各基板共通)

1. build() で ERC=0 / netlist mismatch=0 / DRC=0 まで反復。
2. tracks を全ネットに張る(GNDはゾーン任せ)。未配線を残さない。
3. `kicad-cli pcb render` PNG と 回路図SVG→PNG(headless Chrome)で目視確認、
   テキスト重なりを修正。
4. シルク: 基板名+版数、XH/XT30コネクタごとに用途名とpin1/極性を texts で入れる。
