"""UI (共通表示操作基板) v1.0: 親機・子機共通のLCD+3ボタン+バックライト基板。
2026-07-21統合仕様。メイン基板(C-MAIN/P-MAIN)と J_MAIN(XH8)で接続。

上位仕様: ../docs/AquaBeacon_確定仕様メモ.md §表示・操作UI
GPIO/コネクタ: ../docs/AquaBeacon_MAIN_UI_GPIO_コネクタ表.md

構成:
 - LCD: Newhaven NHD-C12864WO-B1TFH#-M (ST7567系 128x64, 4線SPI)。
   J_LCD で接続。※FFCピン順・外形・取付穴はメーカー機械図で要確定(暫定9ピン表現)。
 - 3ボタン UP/ENTER/DOWN: ADC抵抗ラダーで BTN_ADC 1本に集約(メイン基板ADC1本で判別)。
   V3D--10k--BTN_ADC、UP=直結GND(0V)/ENT=3.3k(0.66V)/DOWN=10k(1.65V)/無押下=3.3V。
 - バックライト: BL_PWM -> R_G -> 2SK4017ゲート、ドレイン=LED_K、V3D--R_BL--LED_A。日中消灯/PWM調光。
 - LCD_RST: RC電源投入リセット(GPIO消費せず)。
実行: & "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" -u pcb\\build_ui_board.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from kicadgen import Part
from buildlib import build

RFP = 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal'
CDISC = 'Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm'
XH8 = 'Connector_JST:JST_XH_B8B-XH-A_1x08_P2.50mm_Vertical'
PH9 = 'Connector_PinHeader_2.54mm:PinHeader_1x09_P2.54mm_Vertical'
SWP = 'Button_Switch_THT:SW_PUSH_6mm'
TO92 = 'Package_TO_SOT_THT:TO-92_Inline'

parts = [
    # メイン基板へ (XH8): V3D/GND/SCK/MOSI/LCD_CS/LCD_DC/BL_PWM/BTN_ADC
    Part('J_MAIN1', 'Connector_Generic', 'Conn_01x08', 'TO_MAIN', XH8,
         {'1': 'V3D', '2': 'GND', '3': 'SPI_SCK', '4': 'SPI_MOSI', '5': 'LCD_CS',
          '6': 'LCD_DC', '7': 'BL_PWM', '8': 'BTN_ADC'},
         at=(30.48, 55.88), gnd_style='label',
         ref_at=(30.48, 45.72), val_at=(30.48, 71.12)),

    # LCD (NHD-C12864WO-B1TFH#-M) 暫定9ピン: FFC順はデータシート機械図で要確定
    Part('J_LCD1', 'Connector_Generic', 'Conn_01x09', 'NHD_C12864WO', PH9,
         {'1': 'GND', '2': 'V3D', '3': 'SPI_SCK', '4': 'SPI_MOSI', '5': 'LCD_CS',
          '6': 'LCD_DC', '7': 'LCD_RST', '8': 'LEDBL_A', '9': 'LEDBL_K'},
         at=(30.48, 20.32), gnd_style='label',
         ref_at=(30.48, 5.08), val_at=(30.48, 45.72)),
    Part('C_LCD', 'Device', 'C', '100n', CDISC, {'1': 'V3D', '2': 'GND'}, at=(53.34, 20.32)),

    # LCD_RST: RC電源投入リセット (同一x縦積みはラベル短絡を招くため各部品を別x・別yに散らす)
    Part('R_RST', 'Device', 'R', '10k', RFP, {'1': 'V3D', '2': 'LCD_RST'}, at=(64.0, 12.0)),
    Part('C_RST', 'Device', 'C', '100n', CDISC, {'1': 'LCD_RST', '2': 'GND'}, at=(80.0, 16.0)),

    # バックライト: V3D -> R_BL -> LED_A ... LED_K -> Q_BL(D) -> GND, gate=BL_PWM
    Part('R_BL', 'Device', 'R', '33', RFP, {'1': 'V3D', '2': 'LEDBL_A'}, at=(100.0, 24.0)),
    # 2SK4017 (TO-92, G/D/S=1/2/3): Transistor_FET:IRLZ44N シンボル流用
    Part('Q_BL', 'Transistor_FET', 'IRLZ44N', '2SK4017', TO92,
         {'1': 'BL_GATE', '2': 'LEDBL_K', '3': 'GND'}, at=(120.0, 30.0), gnd_style='label',
         ref_at=(127.6, 27.46), val_at=(127.6, 30.0)),
    Part('R_G', 'Device', 'R', '100', RFP, {'1': 'BL_PWM', '2': 'BL_GATE'}, at=(64.0, 30.0)),
    Part('R_GPD', 'Device', 'R', '100k', RFP, {'1': 'BL_GATE', '2': 'GND'}, at=(90.0, 34.0), rot=90),

    # 3ボタン ADC抵抗ラダー
    Part('R_LAD', 'Device', 'R', '10k', RFP, {'1': 'V3D', '2': 'BTN_ADC'}, at=(14.0, 88.0)),
    Part('SW_UP', 'Switch', 'SW_Push', 'UP', SWP, {'1': 'BTN_ADC', '2': 'GND'},
         at=(40.0, 88.0), gnd_style='label', ref_at=(40.0, 82.92), val_at=(40.0, 93.08)),
    Part('SW_ENT', 'Switch', 'SW_Push', 'ENTER', SWP, {'1': 'BTN_ADC', '2': 'N_E'},
         at=(60.0, 88.0), ref_at=(60.0, 82.92), val_at=(60.0, 93.08)),
    Part('R_E', 'Device', 'R', '3.3k', RFP, {'1': 'N_E', '2': 'GND'}, at=(52.0, 99.0), rot=90),
    Part('SW_DN', 'Switch', 'SW_Push', 'DOWN', SWP, {'1': 'BTN_ADC', '2': 'N_D'},
         at=(80.0, 88.0), ref_at=(80.0, 82.92), val_at=(80.0, 93.08)),
    Part('R_D', 'Device', 'R', '10k', RFP, {'1': 'N_D', '2': 'GND'}, at=(72.0, 99.0), rot=90),

    Part('H1', 'Mechanical', 'MountingHole', 'M3', 'MountingHole:MountingHole_3.2mm_M3', {}, at=(120, 15)),
    Part('H2', 'Mechanical', 'MountingHole', 'M3', 'MountingHole:MountingHole_3.2mm_M3', {}, at=(120, 30)),
]

sch_wires = [
    ('BTN_ADC', ['R_LAD.2', 'SW_UP.1']),
]
sch_junctions = []
sch_labels = {}

# --- PCB: 配置のみ。外形 100x65mm (LCD active~42x27はJ_LCD上方に実装、要機械図確定) ---
# 座標規則: XH +x / PinHeader +y / R rot0横 rot90縦 / TO-92 3リード / SW 6mm角
placements = {
    # LCD (上辺、FFC/フレーム実装領域は上方へ張り出し)
    'J_LCD1': (12, 10, 0),        # PH9 縦 x10..14 y7..30
    'C_LCD': (24, 10, 0),
    'R_RST': (40, 10, 0), 'C_RST': (55, 10, 0),
    'R_BL': (40, 18, 0),
    'R_G': (40, 26, 0), 'R_GPD': (60, 24, 90),
    'Q_BL': (72, 22, 0),
    # 3ボタン (中央、操作面)
    'SW_UP': (35, 42, 0), 'SW_ENT': (55, 42, 0), 'SW_DN': (75, 42, 0),
    'R_LAD': (20, 42, 0),
    'R_E': (48, 54, 90), 'R_D': (68, 54, 90),
    # メインコネクタ (下辺)
    'J_MAIN1': (30, 58, 0),
    'H1': (92, 8, 0), 'H2': (92, 58, 0),
}

texts = [
    ('AquaBeacon UI v1.0 (LCD+3btn+BL, placement)', 8, 62, 'F.SilkS'),
    ('LCD NHD-C12864WO-B1TFH#-M (FFC pinout TBD/datasheet)', 8, 3, 'F.SilkS'),
    ('UP', 33, 48, 'F.SilkS'), ('ENTER', 51, 48, 'F.SilkS'), ('DOWN', 73, 48, 'F.SilkS'),
    ('TO MAIN (XH8)', 30, 65, 'F.SilkS'),
]

# 配線: pcbgen Dijkstraオートルータに委譲 (GNDは両面ベタ)
seed_tracks = [
    # V3D: J_MAIN/R_LADの分岐を橋渡し
    ('V3D', 'B.Cu', 0.3, ['J_MAIN1.1', (30, 48), (20, 48), 'R_LAD.1']),
    # バックライト LEDBL_K: LCD LED- -> MOSFETドレイン (LCDピン列x12を避けy33で横断)
    ('LEDBL_K', 'B.Cu', 0.3, ['J_LCD1.9', (12, 34), (73.27, 34), 'Q_BL.2']),
]
seed_vias = [
    ('GND', 15.0, 55.0), ('GND', 50.0, 55.0), ('GND', 85.0, 55.0),
    ('GND', 15.0, 35.0), ('GND', 90.0, 35.0), ('GND', 50.0, 12.0),
]
ok, rpt = build('UI_BOARD', parts, placements, (0, 0, 100, 65),
                tracks='auto', vias='auto', seed_tracks=seed_tracks, seed_vias=seed_vias,
                power_flag_nets=('V3D', 'GND'),
                texts=texts, sch_wires=sch_wires, sch_junctions=sch_junctions,
                sch_labels=sch_labels)
print('OK' if ok else 'DRC ISSUES')
