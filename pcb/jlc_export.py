"""JLCPCB発注用ファイル一式を生成する。
- gerbers/ (ガーバー+ドリル) -> <board>_gerbers.zip
- <board>_bom_jlc.csv  (Comment,Designator,Footprint,LCSC Part #,MFR Part #)
- <board>_cpl_jlc.csv  (Designator,Mid X,Mid Y,Layer,Rotation)
使い方: & "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" -u pcb\\jlc_export.py RX_improved_mini
"""
import csv
import subprocess
import sys
import zipfile
from pathlib import Path

KICAD_CLI = r'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe'
HERE = Path(__file__).parent

# ref -> (LCSC番号, MFR型番, 備考)。LCSC空欄はJLCPCBのBOMツールでMFR型番から自動マッチさせる。
# JLC_PARTS[board][value+footprintキー] ではなく ref単位で明示する(確実性優先)。
JLC_PARTS = {
    # 2026-07-19 更新: RX_improved_mini は v1.1 (NJM2137/LM393) のミニ版に変更。
    # SMT実装は抵抗・コンデンサ(0805)のみ。IC(DIP-8)/ダイオード(DO-35)/トリマ(3362P)は
    # 購入済み部品を手はんだ (BOARD_EXCLUDE で除外)。
    'RX_improved_mini': {
        # 抵抗 0805 (UNI-ROYAL 1%)
        'R1':  ('C17408', '0805W8F1000T5E', '100Ω basic'),
        'R2':  ('C149504', '0805W8F1003T5E', '100kΩ basic (C17407在庫切れの代替, 同型番)'),
        'R3':  ('C17513', '0805W8F1001T5E', '1kΩ basic'),
        'R4':  ('C27834', '0805W8F5101T5E', '5.1kΩ basic (ゲイン固定分 G>=6.1)'),
        'R5':  ('C17513', '0805W8F1001T5E', '1kΩ basic (MFB)'),
        'R6':  ('C25270', '0805W8F1800T5E', '180Ω extended (MFB, f0=206.3kHz用)'),
        'R7':  ('C17614', '0805W8F3901T5E', '3.9kΩ basic (MFB帰還)'),
        'R8':  ('C17513', '0805W8F1001T5E', '1kΩ basic'),
        'R9':  ('C27834', '0805W8F5101T5E', '5.1kΩ basic (ゲイン固定分 G>=6.1)'),
        'R10': ('C17414', '0805W8F1002T5E', '10kΩ basic'),
        'R11': ('C17414', '0805W8F1002T5E', '10kΩ basic (包絡線 tau=20us: 2n×10k)'),
        'R12': ('C17414', '0805W8F1002T5E', '10kΩ basic'),
        'R13': ('C17414', '0805W8F1002T5E', '10kΩ basic'),
        'R14': ('C17514', '0805W8F1004T5E', '1MΩ basic'),
        'R15': ('C17414', '0805W8F1002T5E', '10kΩ basic'),
        'R16': ('C149504', '0805W8F1003T5E', '100kΩ basic (C17407在庫切れの代替, 同型番)'),
        'R17': ('C149504', '0805W8F1003T5E', '100kΩ basic (C17407在庫切れの代替, 同型番)'),
        'R18': ('C17414', '0805W8F1002T5E', '10kΩ basic (LM393 OCプルアップ)'),
        # コンデンサ 0805
        'C1':  ('C49678', 'CC0805KRX7R9BB104', '100nF X7R basic'),
        'C2':  ('C28323', 'CL21B105KBFNNNE', '1uF X7R basic'),
        'C3':  ('C1791', 'CL21C102JBCNNNC', '1nF C0G extended (MFB周波数決定用)'),
        'C4':  ('C1791', 'CL21C102JBCNNNC', '1nF C0G extended (MFB周波数決定用)'),
        'C5':  ('C28323', 'CL21B105KBFNNNE', '1uF X7R basic'),
        'C6':  ('C49678', 'CC0805KRX7R9BB104', '100nF X7R basic'),
        'C7':  ('C46653', 'CL21B102KBCNNNC', '1nF X7R basic (包絡線 2n並列の片方)'),
        'C8':  ('C49678', 'CC0805KRX7R9BB104', '100nF X7R basic'),
        'C9':  ('C15850', 'CL21A106KAYNNNE', '10uF 25V basic'),
        'C10': ('C49678', 'CC0805KRX7R9BB104', '100nF X7R basic'),
        'C11': ('C49678', 'CC0805KRX7R9BB104', '100nF X7R basic'),
        'C12': ('C49678', 'CC0805KRX7R9BB104', '100nF X7R basic'),
        'C13': ('C46653', 'CL21B102KBCNNNC', '1nF X7R basic (包絡線 2n並列の片方)'),
    },
    # 2026-07-19 更新: build_rx_advanced_mini.py の現行値 (470pF/Basic再設計 + ゲイントリマ) に同期
    'RX_advanced_mini': {
        'R1':  ('C17408', '0805W8F1000T5E', '100Ω basic'),
        'R2':  ('C149504', '0805W8F1003T5E', '100kΩ basic (C17407在庫切れの代替, 同型番)'),
        'R3':  ('C17513', '0805W8F1001T5E', '1kΩ basic'),
        'R4':  ('C27834', '0805W8F5101T5E', '5.1kΩ basic (ゲイン固定分 G>=6.1)'),
        'RV1': ('C720648', 'TC33X-2-203E', 'SMDトリマ20k (初段ゲイン 6.1..26.1)'),
        'R5':  ('C17614', '0805W8F3901T5E', '3.9kΩ basic (MFB1)'),
        'R6':  ('C17630', '0805W8F3300T5E', '330Ω basic (MFB1)'),
        'R7':  ('C17444', '0805W8F1202T5E', '12kΩ basic (MFB1帰還)'),
        'R8':  ('C17513', '0805W8F1001T5E', '1kΩ basic'),
        'R9':  ('C27834', '0805W8F5101T5E', '5.1kΩ basic (ゲイン固定分 G>=6.1)'),
        'RV2': ('C720648', 'TC33X-2-203E', 'SMDトリマ20k (後段ゲイン 6.1..26.1)'),
        'R10': ('C17414', '0805W8F1002T5E', '10kΩ basic'),
        'R11': ('C17475', '0805W8F1502T5E', '15kΩ basic (包絡線 tau=15us)'),
        'R12': ('C17414', '0805W8F1002T5E', '10kΩ basic'),
        'R13': ('C17414', '0805W8F1002T5E', '10kΩ basic'),
        'R14': ('C17514', '0805W8F1004T5E', '1MΩ basic'),
        'R15': ('C17414', '0805W8F1002T5E', '10kΩ basic'),
        'R16': ('C149504', '0805W8F1003T5E', '100kΩ basic (C17407在庫切れの代替, 同型番)'),
        'R17': ('C149504', '0805W8F1003T5E', '100kΩ basic (C17407在庫切れの代替, 同型番)'),
        'R18': ('C17513', '0805W8F1001T5E', '1kΩ basic'),
        'R19': ('C17604', '0805W8F2001T5E', '2kΩ basic (MFB2)'),
        'R20': ('C17617', '0805W8F3000T5E', '300Ω basic (MFB2)'),
        'R21': ('C17828', '0805W8F8201T5E', '8.2kΩ basic (MFB2帰還)'),
        'C1':  ('C49678', 'CC0805KRX7R9BB104', '100nF X7R basic'),
        'C2':  ('C28323', 'CL21B105KBFNNNE', '1uF X7R basic'),
        'C3':  ('C1743', 'CC0805JRNPO9BN471', '470pF C0G basic (MFB周波数決定用)'),
        'C4':  ('C1743', 'CC0805JRNPO9BN471', '470pF C0G basic (MFB周波数決定用)'),
        'C5':  ('C28323', 'CL21B105KBFNNNE', '1uF X7R basic'),
        'C6':  ('C49678', 'CC0805KRX7R9BB104', '100nF X7R basic'),
        'C7':  ('C46653', 'CC0805KRX7R9BB102', '1nF X7R basic (包絡線)'),
        'C8':  ('C49678', 'CC0805KRX7R9BB104', '100nF X7R basic'),
        'C9':  ('C15850', 'CL21A106KAYNNNE', '10uF 25V basic'),
        'C10': ('C49678', 'CC0805KRX7R9BB104', '100nF X7R basic'),
        'C11': ('C49678', 'CC0805KRX7R9BB104', '100nF X7R basic'),
        'C12': ('C49678', 'CC0805KRX7R9BB104', '100nF X7R basic'),
        'C13': ('C1743', 'CC0805JRNPO9BN471', '470pF C0G basic (MFB周波数決定用)'),
        'C14': ('C1743', 'CC0805JRNPO9BN471', '470pF C0G basic (MFB周波数決定用)'),
        'D1': ('C81598', '1N4148W', 'basic'),
        'D2': ('C81598', '1N4148W', 'basic'),
        'D3': ('C8598', 'B5819W', 'Schottky basic'),
        'U1': ('C1518676', 'OPA2607IDR', 'SOIC-8 extended'),
        'U2': ('C1518676', 'OPA2607IDR', 'SOIC-8 extended'),
        'U3': ('C193413', 'TLV3501AIDBVR', 'SOT-23-6 extended'),
    },
    # 2026-07-19 追加: TX_advanced SMD版 (Q/T/L/J/HはTHT手はんだで除外)
    'TX_advanced': {
        'R1':  ('C17408', '0805W8F1000T5E', '100Ω basic'),
        'R2':  ('C17408', '0805W8F1000T5E', '100Ω basic'),
        'R3':  ('C17415', '0805W8F100JT5E', '10Ω basic (ゲート)'),
        'R4':  ('C17415', '0805W8F100JT5E', '10Ω basic (ゲート)'),
        'R5':  ('C17414', '0805W8F1002T5E', '10kΩ basic'),
        'R6':  ('C17414', '0805W8F1002T5E', '10kΩ basic'),
        'R7':  ('C17901', '1206W4F1000T5E', '100Ω 1206 0.25W basic (スナバ)'),
        'R8':  ('C17901', '1206W4F1000T5E', '100Ω 1206 0.25W basic (スナバ)'),
        'R9':  ('C38808', '25121WJ0221T4E', '220Ω 2512 1W extended (二次ダンピング)'),
        'R10': ('C17900', '1206W4F1003T5E', '100kΩ 1206 200V basic (ブリーダ)'),
        'C1':  ('C72477', 'RVT1E101M0607', '100uF 25V SMD電解 extended'),
        'C2':  ('C49678', 'CC0805KRX7R9BB104', '100nF X7R basic'),
        'C5':  ('C49678', 'CC0805KRX7R9BB104', '100nF X7R basic'),
        'C3':  ('C9196', '1206B102K202NT', '1nF 2kV X7R 1206 basic (スナバ)'),
        'C4':  ('C9196', '1206B102K202NT', '1nF 2kV X7R 1206 basic (スナバ)'),
        'D1':  ('C19077448', 'BZT52C15S', '15VツェナーSOD-323 preferred(装着費無料)'),
        'D2':  ('C19077448', 'BZT52C15S', '15VツェナーSOD-323 preferred(装着費無料)'),
        'D3':  ('C5331120', 'SMBJ40A', 'TVS SMB extended'),
        'D4':  ('C5331120', 'SMBJ40A', 'TVS SMB extended'),
        'D9':  ('C726824', 'SMBJ15A', 'TVS SMB extended'),
        'U1':  ('C20551', 'TC4427AEOA713', 'SOIC-8 1.5Aゲートドライバ (MIC4427ピン互換)'),
    },
    # 2026-08-03 全面改訂: **基板上のSMD部品は全てJLCPCBのSMT実装に出す**(ユーザ方針)。
    #  旧版は INA226 まわり3点だけを実装対象にし、他のSMD(0603/0805のR/C, 0805 LED, SMB TVS)を
    #  手はんだ扱いにしていた = BOM/CPL 不足。C-PWR は 16点 / P-PWR は 4点が正しい数。
    # 手はんだのまま残るもの(すべてTHTまたはモジュール):
    #  XT30PW(J_BAT/J_LED/J_TX) / ヒューズクリップF1 / TO-220(Q1,Q2,REG3D,REG3A,REG3S) /
    #  トグルSW(SW_PWR,SW_TX) / 電解C_BLK / ディスクC / ピンソケット(PS1,PS_A,PS_B) / JST XH / M3穴。
    # ※ P-PWR は受動部品がまだTHT(軸抵抗・ディスクC・砲弾LED)なので実装点数が少ない。
    #    C-PWR と同じくSMD化すれば手はんだはさらに減る(要 再配置・再配線)。
    # LCSC 照会(2026-08-03): SMBJ15A は **C19077569 が Preferred = 装着費無料**(在庫13,053)。
    #  旧メモの C726824 は通常のExtendedなので置き換えた。
    #  ※ SMBJ15A は単方向TVS = **向きあり**。JLCのプレビューでカソード帯の向きを必ず確認する。
    'CHILD_PWR': {
        # --- INA226 電流検出 ---
        'U_INA': ('C49851', 'INA226AIDGSR', 'MSOP-10 extended (電流電圧監視, addr0x40)'),
        'R_SH':  ('C728347', 'PA2512FKF7W0R02E', '20mΩ 1% 2W 2512 extended (YAGEO電流検出用, FS≈4A)'),
        'C_VS':  ('C14663', 'CC0603KRX7R9BB104', '100nF X7R 0603 basic (INA226 VSパスコン)'),
        # --- 保護 (単方向TVS, SMB/DO-214AA。DigiKey購入済10個は予備に回る) ---
        'D1':    ('C19077569', 'SMBJ15A', 'TVS 15V SMB preferred=装着費無料 (入力サージ/逆接クランプ)'),
        'D_LED': ('C19077569', 'SMBJ15A', 'TVS 15V SMB preferred=装着費無料 (ライト誘導性スパイク)'),
        # --- 抵抗 ---
        'R_G':   ('C25803', '0603WAF1003T5E', '100kΩ 0603 basic (Q1 Pchゲートプルダウン)'),
        'R_PDL': ('C25803', '0603WAF1003T5E', '100kΩ 0603 basic (Q2 ゲートプルダウン)'),
        'R_LED': ('C21190', '0603WAF1001T5E', '1kΩ 0603 basic (電源表示LED直列)'),
        'R_GL':  ('C17408', '0805W8F1000T5E', '100Ω 0805 basic (Q2ゲート直列。過渡電力で0805)'),
        # --- コンデンサ ---
        'C_BK2': ('C15850', 'CL21A106KAYNNNE', '10uF 25V 0805 basic (V5D 出力側)'),
        'C_D5':  ('C14663', 'CC0603KRX7R9BB104', '100nF X7R 0603 basic (V5D)'),
        'C_3D1': ('C15850', 'CL21A106KAYNNNE', '10uF 25V 0805 basic (V3D 出力側)'),
        'C_3D2': ('C14663', 'CC0603KRX7R9BB104', '100nF X7R 0603 basic (V3D)'),
        'C_3A1': ('C15850', 'CL21A106KAYNNNE', '10uF 25V 0805 basic (V3A 出力側)'),
        'C_3A2': ('C14663', 'CC0603KRX7R9BB104', '100nF X7R 0603 basic (V3A)'),
        # --- 表示 ---
        'LED1':  ('C2297', 'KT-0805G', '緑LED 0805 basic (電源表示)'),
    },
    'PARENT_PWR': {
        'U_INA': ('C49851', 'INA226AIDGSR', 'MSOP-10 extended (電流電圧監視, addr0x40)'),
        'R_SH':  ('C728347', 'PA2512FKF7W0R02E', '20mΩ 1% 2W 2512 extended (YAGEO電流検出用, FS≈4A)'),
        'C_VS':  ('C14663', 'CC0603KRX7R9BB104', '100nF X7R 0603 basic (INA226 VSパスコン)'),
        'D1':    ('C19077569', 'SMBJ15A', 'TVS 15V SMB preferred=装着費無料 (入力サージ/逆接クランプ)'),
        # 注: R_G/R_LED は軸抵抗、C_5L*/C_3S*/C_5C*/C_BK1 はディスク/電解、LED1 は砲弾 = すべてTHT。
        #     C-PWR と同様にSMD化すればここも実装対象にできる(未実施)。
    },
    # 2026-08-02 追加: メイン基板のSMT実装対象は R(0603) / C(0603,0805) / LED(0805) / 2N7002(SOT-23) のみ。
    # 手はんだ(=BOM/CPL対象外): Pico 2 W, microSD Molex 104031-0811, DS3231 ZS-042ソケット,
    #  BNO085(2x05ソケット), Waveshare RS485(キャステレーション), JST XH/GH 各種, タクトSW(THT), M3穴。
    # DNP(未実装)なので意図的に載せない: R_SDA / R_SCL (I2Cプルアップ4.7k) / R_TRMD1 (RS485終端120Ω)。
    # LCSC番号は jlcsearch で照会済(2026-08-02, 在庫は全て100万個超)。
    #  0603抵抗はUNI-ROYAL 0603WAF系がすべてBasic / 100n=C14663 / 10n=C57112 / 10u 0805=C15850。
    #  LED 0805のBasicは赤(C84256)と緑(C2297)のみ → **STATUSは赤 C84256**
    #  (2026-08-03 ユーザ要求で Extended を排除。旧: 黄 C84261 = Extended)。
    # **メイン基板で Extended が残るのは microSD ソケット SD1 のみ**。JLCPCB の Basic ライブラリに
    #  コネクタ類は1点も無いため代替不能。TF-01A = LCSC C91145 は JLC で最も流通している
    #  push-push(押してロック/自動排出)品(在庫17万個超・$0.12)。
    #  FP は AquaBeacon:microSD_TF-01A(公式図面のベクタ実寸から起こした自作)。
    'CHILD_MAIN': {
        # --- 電源デカップリング/表示 ---
        'C_V5':  ('C15850', 'CL21A106KAYNNNE', '10uF 25V X5R 0805 basic (V5D バルク)'),
        'C_V5b': ('C14663', 'CC0603KRX7R9BB104', '100nF X7R 0603 basic (V5D)'),
        'C_V3':  ('C15850', 'CL21A106KAYNNNE', '10uF 25V X5R 0805 basic (V3D バルク, 旧電解を積セラ化)'),
        'C_V3b': ('C14663', 'CC0603KRX7R9BB104', '100nF X7R 0603 basic (V3D)'),
        'C_D1':  ('C14663', 'CC0603KRX7R9BB104', '100nF X7R 0603 basic (V3D 分散デカップリング)'),
        'C_D2':  ('C14663', 'CC0603KRX7R9BB104', '100nF X7R 0603 basic (V5D 分散デカップリング)'),
        'R_PWR': ('C21190', '0603WAF1001T5E', '1kΩ 0603 basic (PWR LED電流制限)'),
        'LED_PWR': ('C2297', 'KT-0805G', '緑LED 0805 basic (電源表示)'),
        'R_ST':  ('C21190', '0603WAF1001T5E', '1kΩ 0603 basic (STATUS LED電流制限)'),
        'LED_ST': ('C84256', 'NCD0805R1', '赤LED 0805 basic (STATUS表示。0805のBasic LEDは赤/緑のみ)'),
        # --- INA226アラート/センサ ---
        'R_AL':  ('C25804', '0603WAF1002T5E', '10kΩ 0603 basic (INA_AL プルアップ)'),
        'C_V3A': ('C14663', 'CC0603KRX7R9BB104', '100nF X7R 0603 basic (V3A RXアナログ)'),
        # v4.5: 1M -> 100k へ変更(RP2350の入力リーク±1uAで1M だと最大1.0V落ちるため)。
        #  **LCSC番号も 1M(C22935) から 100k(C25803) へ差し替え済み**
        'R_LEAK': ('C25803', '0603WAF1003T5E', '100kΩ 0603 basic (漏水検知プルアップ。v4.5で1Mから変更)'),
        'C_LEAK': ('C57112', '0603B103K500NT', '10nF X7R 0603 basic (漏水電極のノイズ除去。v4.5 新規)'),
        # --- microSD (SMT実装。**唯一の Extended**: コネクタに Basic 品は存在しない) ---
        'SD1':   ('C91145', 'TF-01A', 'microSD/TFソケット push-push extended (Korean Hroparts, JLC最流通品)'),
        'C_SD1': ('C14663', 'CC0603KRX7R9BB104', '100nF X7R 0603 basic (SD電源)'),
        'C_SD2': ('C15850', 'CL21A106KAYNNNE', '10uF 25V X5R 0805 basic (SD電源バルク)'),
        'R_CD':  ('C25819', '0603WAF4702T5E', '47kΩ 0603 basic (SD_CD プルアップ)'),
        'R_SDCS': ('C25804', '0603WAF1002T5E', '10kΩ 0603 basic (SD_CS プルアップ。v4.3 新規)'),
        # --- TH_PWM ケーブル前段RC (v4.3 新規) ---
        'R_THP': ('C21190', '0603WAF1001T5E', '1kΩ 0603 basic (TH_PWM 直列)'),
        'C_THP': ('C14663', 'CC0603KRX7R9BB104', '100nF X7R 0603 basic (TH_PWM 平滑)'),
        # --- LCD (NHD-C0216CiZ I2C) ---
        'C_LCD': ('C14663', 'CC0603KRX7R9BB104', '100nF X7R 0603 basic (LCD電源)'),
        'R_RST': ('C25804', '0603WAF1002T5E', '10kΩ 0603 basic (LCD_RST プルアップ)'),
        'C_RST': ('C14663', 'CC0603KRX7R9BB104', '100nF X7R 0603 basic (LCD_RST リセットRC)'),
        # --- バックライト (V5D / 2N7002ローサイド) ---
        'R_BL':  ('C22775', '0603WAF1000T5E', '100Ω 0603 basic (バックライト電流制限)'),
        'Q_BL':  ('C8545', '2N7002', 'Nch MOSFET SOT-23 basic (G1/S2/D3, バックライト駆動)'),
        'R_G':   ('C22775', '0603WAF1000T5E', '100Ω 0603 basic (ゲート直列)'),
        'R_GPD': ('C25803', '0603WAF1003T5E', '100kΩ 0603 basic (ゲートプルダウン)'),
        # --- 3ボタン ADCラダー ---
        'R_LAD': ('C25804', '0603WAF1002T5E', '10kΩ 0603 basic (ラダー上側)'),
        'R_E':   ('C22978', '0603WAF3301T5E', '3.3kΩ 0603 basic (ENTER)'),
        'R_D':   ('C25804', '0603WAF1002T5E', '10kΩ 0603 basic (DOWN)'),
        # --- BNO085 ---
        'C_BNO': ('C14663', 'CC0603KRX7R9BB104', '100nF X7R 0603 basic (BNO085電源)'),
        # ★2026-08-03 (v4.4): `J_TEMP1` を SMT 実装対象から**削除**した。
        #  旧: JST-GH SM04B-GHS-TB(C189895, SMD横入れ, 在庫591個の Extended)。
        #  ユーザが Celsius のケーブルを **XH で自作**しているため基板側も XH4(B4B-XH-A)へ
        #  変更した。XH は THT なので他の JST XH と同じく**手はんだ**扱いになる。
        #  副次効果: これで**メイン基板の Extended は microSD の SD1 だけ**になった。
    },
    'PARENT_MAIN': {
        # --- 電源デカップリング/表示 ---
        'C_V5':  ('C15850', 'CL21A106KAYNNNE', '10uF 25V X5R 0805 basic (V5D バルク)'),
        'C_V5b': ('C14663', 'CC0603KRX7R9BB104', '100nF X7R 0603 basic (V5D)'),
        'C_V3':  ('C15850', 'CL21A106KAYNNNE', '10uF 25V X5R 0805 basic (V3D バルク, 旧電解を積セラ化)'),
        'C_V3b': ('C14663', 'CC0603KRX7R9BB104', '100nF X7R 0603 basic (V3D)'),
        'C_D1':  ('C14663', 'CC0603KRX7R9BB104', '100nF X7R 0603 basic (V3D 分散デカップリング)'),
        'C_D2':  ('C14663', 'CC0603KRX7R9BB104', '100nF X7R 0603 basic (V5D 分散デカップリング)'),
        'R_PWR': ('C21190', '0603WAF1001T5E', '1kΩ 0603 basic (PWR LED電流制限)'),
        'LED_PWR': ('C2297', 'KT-0805G', '緑LED 0805 basic (電源表示)'),
        'R_ST':  ('C21190', '0603WAF1001T5E', '1kΩ 0603 basic (STATUS LED電流制限)'),
        'LED_ST': ('C84256', 'NCD0805R1', '赤LED 0805 basic (STATUS表示。0805のBasic LEDは赤/緑のみ)'),
        # --- INA226アラート ---
        'R_AL':  ('C25804', '0603WAF1002T5E', '10kΩ 0603 basic (INA_AL プルアップ)'),
        # --- microSD (SMT実装。**唯一の Extended**: コネクタに Basic 品は存在しない) ---
        'SD1':   ('C91145', 'TF-01A', 'microSD/TFソケット push-push extended (Korean Hroparts, JLC最流通品)'),
        'C_SD1': ('C14663', 'CC0603KRX7R9BB104', '100nF X7R 0603 basic (SD電源)'),
        'C_SD2': ('C15850', 'CL21A106KAYNNNE', '10uF 25V X5R 0805 basic (SD電源バルク)'),
        'R_CD':  ('C25819', '0603WAF4702T5E', '47kΩ 0603 basic (SD_CD プルアップ)'),
        'R_SDCS': ('C25804', '0603WAF1002T5E', '10kΩ 0603 basic (SD_CS プルアップ。v5.7 新規)'),
        # --- P-TX 制御 / サーミスタ読み(分圧+平滑) ---
        'R_TXP': ('C22775', '0603WAF1000T5E', '100Ω 0603 basic (TX_PWM 直列ダンピング。v5.7 新規)'),
        'R_TT':  ('C21190', '0603WAF1001T5E', '1kΩ 0603 basic (TX_TEMP 直列)'),
        # v5.7: 10n -> 100n へ変更(tau 10us -> 100us)。**LCSC番号も 10n(C57112) から
        #  100n(C14663) へ差し替え済み**
        'C_TT':  ('C14663', 'CC0603KRX7R9BB104', '100nF X7R 0603 basic (TX_TEMP 平滑。v5.7で10nから変更)'),
        'R_TTD': ('C25803', '0603WAF1003T5E', '100kΩ 0603 basic (TX_TEMP 分圧下側)'),
        # --- SPRESENSE 拡張ボード I/F ---
        'R_PPS': ('C22775', '0603WAF1000T5E', '100Ω 0603 basic (PPS 直列)'),
        'R_EVT': ('C22775', '0603WAF1000T5E', '100Ω 0603 basic (EVENT 直列)'),
        # --- LCD (NHD-C0216CiZ I2C) ---
        'C_LCD': ('C14663', 'CC0603KRX7R9BB104', '100nF X7R 0603 basic (LCD電源)'),
        'R_RST': ('C25804', '0603WAF1002T5E', '10kΩ 0603 basic (LCD_RST プルアップ)'),
        'C_RST': ('C14663', 'CC0603KRX7R9BB104', '100nF X7R 0603 basic (LCD_RST リセットRC)'),
        # --- バックライト (V5D / 2N7002ローサイド) ---
        'R_BL':  ('C22775', '0603WAF1000T5E', '100Ω 0603 basic (バックライト電流制限)'),
        'Q_BL':  ('C8545', '2N7002', 'Nch MOSFET SOT-23 basic (G1/S2/D3, バックライト駆動)'),
        'R_G':   ('C22775', '0603WAF1000T5E', '100Ω 0603 basic (ゲート直列)'),
        'R_GPD': ('C25803', '0603WAF1003T5E', '100kΩ 0603 basic (ゲートプルダウン)'),
        # --- 3ボタン ADCラダー ---
        'R_LAD': ('C25804', '0603WAF1002T5E', '10kΩ 0603 basic (ラダー上側)'),
        'R_E':   ('C22978', '0603WAF3301T5E', '3.3kΩ 0603 basic (ENTER)'),
        'R_D':   ('C25804', '0603WAF1002T5E', '10kΩ 0603 basic (DOWN)'),
    },
}

# THT混在基板: JLC_PARTS表に載っているrefだけをSMT実装(CPL/BOM)対象とし、
# それ以外のrefは手はんだ扱いでWARNINGも出さない(prefix除外では R_SH と R_G を区別できないため)。
# **whitelist基板では EXCLUDE_PREFIX を適用しない**: メイン基板の Q_BL(SOT-23) や
# LED_PWR/LED_ST は SMT対象なのに prefix 'Q'/'L' で先に落ちてしまうため。
WHITELIST_BOARDS = ('CHILD_PWR', 'PARENT_PWR', 'CHILD_MAIN', 'PARENT_MAIN')

# SMT実装から除外する部品 (THT: コネクタ/取付穴/MOSFET/トランス/インダクタは手はんだ)
EXCLUDE_PREFIX = ('J', 'H', 'Q', 'T', 'L')
# 基板ごとの追加除外 (購入済みTHT部品を手はんだする基板)
BOARD_EXCLUDE = {
    'RX_improved_mini': ('U', 'D', 'RV'),   # NJM2137/LM393(DIP), 1N4148/BAT43(DO-35), 3362P
}


def _refkey(ref):
    import re
    m = re.match(r'([A-Za-z]+)(\d+)', ref)
    return (m.group(1), int(m.group(2))) if m else (ref, 0)


def run(args):
    r = subprocess.run(args, capture_output=True, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        print(r.stdout)
        print(r.stderr)
        raise SystemExit(f'command failed: {args}')
    return r.stdout


def main(board):
    bdir = HERE / board
    pcb = bdir / f'{board}.kicad_pcb'
    sch = bdir / f'{board}.kicad_sch'
    parts = JLC_PARTS.get(board)  # None = THT基板: ガーバーのみ出力(BOM/CPL不要)
    whitelist = board in WHITELIST_BOARDS
    exclude = () if whitelist else EXCLUDE_PREFIX + BOARD_EXCLUDE.get(board, ())

    # --- gerbers + drill ---
    gdir = bdir / 'gerbers'
    gdir.mkdir(exist_ok=True)
    for f in gdir.iterdir():
        f.unlink()
    run([KICAD_CLI, 'pcb', 'export', 'gerbers', '-o', str(gdir) + '\\', str(pcb)])
    run([KICAD_CLI, 'pcb', 'export', 'drill', '-o', str(gdir) + '\\', str(pcb)])
    zpath = bdir / f'{board}_gerbers.zip'
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(gdir.iterdir()):
            z.write(f, f.name)
    print(f'gerbers -> {zpath.name} ({len(list(gdir.iterdir()))} files)')

    if parts is None:
        print(f'{board}: JLC_PARTS未登録のためBOM/CPLはスキップ (ガーバーのみ)')
        return

    # --- 位置ファイル (CPL) ---
    pos = bdir / f'{board}_pos.csv'
    run([KICAD_CLI, 'pcb', 'export', 'pos', '--format', 'csv', '--units', 'mm',
         '--side', 'front', '-o', str(pos), str(pcb)])
    cpl = bdir / f'{board}_cpl_jlc.csv'
    n = 0
    with open(pos, encoding='utf-8') as fi, open(cpl, 'w', newline='', encoding='utf-8') as fo:
        rd = csv.DictReader(fi)
        w = csv.writer(fo)
        w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
        for row in rd:
            ref = row['Ref']
            if exclude and ref.startswith(exclude):
                continue
            if whitelist and ref not in parts:
                continue
            w.writerow([ref, f"{float(row['PosX']):.4f}mm", f"{float(row['PosY']):.4f}mm",
                        'Top' if row['Side'] == 'top' else 'Bottom', row['Rot']])
            n += 1
    print(f'cpl -> {cpl.name} ({n} parts)')

    # --- BOM (value/footprint は基板から, LCSCは表から) ---
    bom_src = bdir / f'{board}_bom_src.csv'
    run([KICAD_CLI, 'sch', 'export', 'bom', '--fields', 'Reference,Value,Footprint',
         '--output', str(bom_src), str(sch)])
    rows = {}
    with open(bom_src, encoding='utf-8-sig') as fi:
        for row in csv.DictReader(fi):
            for ref in row['Reference'].replace(' ', '').split(','):
                # 末尾数字なしref(R_SH等)はKiCadが未アノテーション扱いで'?'を付ける -> 除去
                ref = ref.rstrip('?')
                if not ref or (exclude and ref.startswith(exclude)):
                    continue
                if ref not in parts:
                    if not whitelist:
                        print(f'WARNING: {ref} にLCSC割当がありません')
                    continue
                lcsc, mfr, note = parts[ref]
                fp = row['Footprint'].split(':')[-1]
                key = (row['Value'], fp, lcsc, mfr)
                rows.setdefault(key, []).append(ref)
    bom = bdir / f'{board}_bom_jlc.csv'
    with open(bom, 'w', newline='', encoding='utf-8') as fo:
        w = csv.writer(fo)
        w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC Part #', 'MFR Part #'])
        for (val, fp, lcsc, mfr), refs in sorted(rows.items(), key=lambda x: x[1][0]):
            w.writerow([val, ','.join(sorted(refs, key=_refkey)), fp, lcsc, mfr])
    print(f'bom -> {bom.name} ({len(rows)} lines)')
    # 未割当チェック
    assigned = {r for refs in rows.values() for r in refs}
    missing = set(parts) - assigned
    if missing:
        print(f'WARNING: BOMに現れなかった割当: {sorted(missing)}')


if __name__ == '__main__':
    main(sys.argv[1])
