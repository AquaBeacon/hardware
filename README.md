# AquaBeacon TX/RX — 回路改良・シミュレーション検証・KiCad基板化

200kHz超音波トランスデューサ **TD04A** を用いた水中ビーコンの送信(TX)/受信(RX)/メイン基板一式。
LTspiceで定量検証した回路を、KiCad 10の回路図+2層PCBまで全自動生成パイプライン(`pcb/build_*.py`)で実装している。

## SPRESENSE SBL派生版の選定調査（2026-09-14）

SPRESENSE 1台、20m、最大基線1m、位置精度10cm以下を目標とする低コスト派生版は
[振動子選定資料](pcb/SPRESENSE_SBL/振動子選定.md) を参照。
SMC20D17H5を少数評価の第一候補とし、3受信＋送信監視1chの構成を検討中。
**最終採用・回路検証・基板生成・20m/10cmの実証は未完了**。
メーカー駆動定格と防水後の実負荷・帯域が必要。合成データの検証を実回路のPASSとは扱わない。

## システム全体像

- **目的**: 光(角度)+音(距離)+テザー(時刻同期)で藻場のマッピング/位置推定。**親機(水上)** と **子機(水中ドローン)** の2ユニット構成。
- **測距方式**: 親機が音を出した瞬間にテザー経由で電気トリガを送り、子機は「トリガ到達→音響受信」のΔtだけを測る(距離=Δt×音速)。両機の時計合わせは不要。
- **テザーは信号のみ**(電源は流さない): 1ペア=有線トリガ(MAX3485)、1ペア=デバッグRS-485(Waveshare TTL-RS485(C))。両端に120Ω終端、SHLDは1点接地。
- **給電**: 子機は自前LiPo 3S(44–55Wh)。共通電源チェーンは LiPo3S → 3Aヒューズ → 電源SW → BUCK 5V → NJU7223F33 LDO(3.3V)。
- **50kHz将来対応**: 振動子コネクタ化+RXのBPF段ソケット化で、基板改版なしに差し替え可能とする方針。

## 基板一覧と設計方針

| 基板 | 役割 | サイズ | 状態 |
|---|---|---|---|
| `pcb/TX_improved/` | 送信・標準版(TC4427+1石) | 70×50mm | ERC/DRC合格(v1.1、ガーバー要再出力) |
| `pcb/TX_advanced/` | 送信・高出力版(プッシュプル+トランス) | 85×60mm | ERC/DRC合格・ガーバー済 |
| `pcb/RX_improved/` | 受信・標準版(THTフルサイズ) | 130×80mm | ERC/DRC合格(v1.1、ガーバー要再出力) |
| `pcb/RX_advanced/` | 受信・高性能版(THTフルサイズ) | 140×80mm | ERC/DRC合格・ガーバー済 |
| `pcb/RX_improved_mini/` | 受信・標準版v1.1のミニ版(R/CのみSMD, IC=DIP手はんだ) | 68×46mm | 配線済・DRC 0 |
| `pcb/RX_advanced_mini/` | 受信・高性能版のSMD最小化 | 60×36mm | 配線済(JLCPCB向け) |
| `pcb/CHILD_MAIN/` | 子機メイン(**Pico 2 W**, BNO085/microSD/RS485/I²C LCD) **v4.5** | **104×88mm** | **ERC合格・netlist一致(40ネット)・DRC 0・未接続0**。**2026-08-03 (v4.5): `R_LEAK` 1M→100k + `C_LEAK` 10n**(1MだとRP2350の入力リーク±1µAだけで最大1.0V落ち、乾燥時Highの余裕がVIHぎりぎりだった)、**`TP_GND1`(THT)追加**。**(v4.4): `J_TEMP1`(Celsius)を JST-GH→XH4 へ変更**(ユーザがケーブルをXHで自作しており GH では嵌合しなかった)。ピン順も `1:V3D 2:GND 3:SDA 4:SCL` に統一し **I²Cセンサ用ケーブルが親子・センサ間で完全共通**に。y52行(J_TEMP1/J_LEAK1/R_LEAK)を東へ再配置。**2026-08-03 レビュー反映(v4.3): `R_THP`1k+`C_THP`100n で TH_PWM のケーブル前段を鈍らせ隣接 ENV_ADC へのクロストークを低減(RX側VTHは高Z → DC誤差ゼロ・ファーム不変)、`R_SDCS`10k で SD_CS プルアップ、PICO1 の I2C 東側脱出を入れ子レーンで手seed、回路図に機能ブロック枠+注記**。2026-08-03: microSDを**TF-01A(LCSC C91145, push-push)**へ変更しJLCPCBでSMT実装可に(接点列が北向きになりSPIはSD直上のB.Cu縦バスで脱出)。STATUS LEDを黄(Extended)→赤(Basic)。2026-08-02: LCDをNHD-C0216CiZへ統一、J_LCD1 XH9→XH7、GP7/GP9解放、R_BL=100Ω/V5D。I²Cプルアップは4.7k DNP選択 |
| `pcb/PARENT_MAIN/` | 親機メイン(**Pico 2 W**, GNSS/P-TX/SPRESENSE連携/I²C LCD) **v5.8** | **112×88mm** | **ERC合格・netlist一致(37ネット)・DRC 0・未接続0**。**2026-08-03 (v5.8): `TP_GND1`(THT GNDテストポイント)追加**。**レビュー反映(v5.7): `J_TETH1`/`J_SPR1` を XH4→XH3(予備ピン削除。子機にしか適用されていなかった)、`R_TXP`100Ω を 200kHz TX_PWM に直列追加、`C_TT` 10n→100n(τ=100µs, DC分圧比不変)、`R_SDCS`10k で SD_CS プルアップ、回路図に機能ブロック枠+注記**。2026-08-03: microSDを**TF-01A(LCSC C91145, push-push)**へ変更しJLCPCBでSMT実装可に。STATUS LEDを黄(Extended)→赤(Basic)。2026-08-02: SPRESENSE拡張ボード使用・JP1=3.3Vを反映し、同期2信号を100Ω直列で接続。J_SPR pin4はNC。I²Cプルアップは4.7k DNP選択 |
| `pcb/CHILD_PWR/` | 子機電源・ライト基板(3Aヒューズ/2SJ349/INA226/BUCK5V/LDO×2) **v2.3** | **62×70mm** | **ERC合格・netlist一致(17ネット)・DRC 0・未接続0**。M3穴をinset 4.0mmへ移動（ピッチ54×62mm）。**2026-08-03 (v2.3): `TP_GND1`+測定点シルク追加(各レールは既存THTパッドで測れるので電圧用TPは不要)**。**(v2.2): 回路図に機能ブロック枠+DESIGN NOTES パネルを追加(ネット不変)。NJU7223F33 のピン順(1=VOUT/2=VIN/3=GND)を一次資料で再照合し `pcb/datasheets/` へ保管** |
| `pcb/PARENT_PWR/` | 親機電源基板(同構成+**カメラ用BUCK** AE-MYMGK00506ERSR-5V0/TX給電VBAT_S) **v1.4** | 100×84mm | **完成: ERC合格・netlist一致(15ネット)・DRC 0・LTspice全項目PASS**。C-PWR `J_I2C` と完全同一ピン順で P-MAIN `J_I2CP` とストレート5芯。**2026-08-03 (v1.4): `TP_GND1`+測定点シルク。`SW_TX` の活線投入を新規LTspice検証**(`PARENT_PWR_SWTX.cir`)→ **突入はR制限なのでTX側C1を減らしても効かず、真の問題は電池終止時にVBAT_Mが5.13Vまで落ちLXDC55のVin下限6.0Vを74µs割ること。対策は「SW_TXをSW_PWRより先に入れる」運用で部品追加ゼロ**(送信停止はTX_PWM Lo固定)。**(v1.3): 回路図に機能ブロック枠+DESIGN NOTES** |
| ~~`pcb/UI_BOARD/`~~ | **廃止(2026-07-23)**: スイッチ/バックライト/リセットRCをC-MAIN/P-MAINへ統合。コネクタはLCD専用J_LCD(9P)に集約 | — | 旧v1.0(参考保管) |
| `onlyTX/` | 手作業のTX回路図(パイプライン外) | — | 回路図作業中・PCB空(`onlyTX/REVIEW.md`参照) |

### TX_improved — 送信・標準版 (v1.1: TC4427ゲートドライバ化 2026-07-19)

- **構成**: TC4427CPA(DIP-8, ch.Aのみ使用) + 2SK4017(TO-251) 1石 + 直列同調L1(470µH, 購入済品) + 保護一式(SMBJ48A/15A TVS、G-S GDZJ15Cクランプ)。C1=470µF/25V(購入済ルビコンPX)。
- **方針**: 購入済み部品優先。MCU 3.3V PWM → TC4427(VIH max2.4Vで直結可)→ 12Vスイングでゲート駆動し、実デバイスのVthばらつきでも確実にフルエンハンス。
- **検証(v1.1)**: 12V通常 Vds=45.1V(<48V derate)/Vgs=12.1V/XD=45.7Vpp、故障(振動子外れ)でもTVSクランプ53.4V<60V。旧版の「5Vパルス必要・9V推奨」制約は解消。
- **コネクタ(2026-07-19統一)**: J1電源=**XT30**(基板用横型**XT30PW-M**、基板端から開口が突き出す実装。KiCadパッド1='-'=GND/パッド2='+'=V12なのでピンマップ注意)、J2 PWM=**JST XH 2P**、J3 TD04A=端子台(従来通り)。
- **MOSFET温度監視(2026-07-20追加)**: 外付けNTC(Vishay `NTCLE100E3103GB0`, 10k/B=3977K)を **Q1の樹脂モールド面**に絶縁性熱伝導接着剤で貼付し、2芯線で J4(XH 2P)へ戻す。基板上は R6=10k 1%(3V3基準の分圧)+C5=100n平滑+R7=1k(ADC保護)+C6=1n(DNP)。J5(XH 3P: 3V3/TEMP_ADC/GND)でメイン基板と接続する。**温度上昇でTEMP_ADCは低下**(25℃≈1.65V、85℃≈0.33V @3.3V基準)。断線≈3.3V/短絡≈0Vで異常判定できるので、ファーム側で 過熱・断線・短絡いずれでも送信停止すること。金属タブへの貼付は厳禁。
- **基板サイズ変更**: 温度ブロック追加に伴い 70×50mm → **74×50mm**(アウトラインは `(-4,0,70,50)`。左へ4mm延長し、縦は元のまま)。取付穴H1/H3を (0,4)/(0,46) へ移動(筐体設計は要追従)。J4(NTC引き出し)は**Q1の真上**でTH1までの2芯線が約4mm、J5と分圧回路(C5/R6/R7/C6)は左端に縦一列。R6/R7は縦立て実装(P2.54)で省スペース化。
- **未確定**: TEMP_ADCの受け側(メイン基板のADC)は未実装。メイン基板は3.3Vフルスケールでない**SPRESENSE**なので、接続時に分圧比の再設計かレベル調整が必要。R7(直列1k)・C6は指示書ではPico直近配置だが、ADC側未定のため暫定でTX基板側に実装している。

### TX_advanced — 送信・高出力版

- **構成**: TC4427Aゲートドライバ(SOIC-8, MIC4427ピン互換) + 2SK4017×2プッシュプル + センタータップ1:5トランス(手巻きEEコア、2.54mm 5ピンヘッダ実装)。12V対応、±150V級駆動。
- **JLCPCB表面実装対応(2026-07-19)**: R/C/ツェナーを0805/1206/2512/SOD-323にSMD化(ほぼBasic部品)。MOSFET(TO-251)・トランス・L1(470µH, Bourns RLB0912-471KL)・端子台はTHT手はんだ。
- **方針**: 詳細設計書の「MIC4427直結プッシュプル」は**動作しない**(トーテムポール出力がハイZにならず巻線スイングを阻止、アイドル時に巻線へDC印加)ことをLTspiceで確認 → MIC4427をゲートドライバ専任とし2SK4017×2で駆動する方式に修正。
- **制約**: J2は3.3V PWM入力可(MIC4427が12Vへレベル変換)。A/B同時High禁止・デッドタイム≥100nsは**駆動側ファームウェアで担保**(SPRESENSEのPWMにデッドタイム機能が無いため)。
- **コネクタ(2026-07-19統一)**: J1電源=**XT30**(**XT30PW-M**横型。パッド1='-'=GND/パッド2='+'=V12)、J2 PWM=**JST XH 3P**(A/B/G)、J3 TD04A=端子台(従来通り)。T1はコネクタではなくトランス実装穴なのでピンヘッダのまま。

### RX_improved / RX_improved_mini — 受信・標準版

- **構成**: クランプ → 初段×21 → MFB 2次BPF → 後段×25 → 包絡線検波 → コンパレータ。計60dB。3.3V単電源、VMID=1.65Vバイアス。
- **フルサイズ版 v1.1 (購入済み部品優先化 2026-07-19)**: NJM2137D×2(DIP-8, GBW200MHz) + LM393GN(DIP-8, OC出力→R18=10kプルアップ追加)。MFBは購入済1000pF C0Gで再設計(C=1n, 1k/180/3.9k → f0=206.3kHz=TX共振と整合, Q=2.53)。検波はBAT43、C7=1n×2(τ=20µs)。SHDN廃止のためJ2ピン5は**NC**(ピン順は従来互換)。NJM2137は非RRO(ENV最大~0.5V)・CM=1.3〜2.0V@3.3Vに注意。
- **mini版(2026-07-19全面改版)**: **RX_improved v1.1 のミニ版**(68×46mm、元130×80mm)。回路トポロジ・ネットはv1.1と完全同一(NJM2137D×2 + LM393 + R18プルアップ、MFB=1k/180/3.9k C=1n C0G → f0=206.3kHz、包絡線2nF、J2.5=NC)。
- **mini版の実装方針**: SMD化は**抵抗・コンデンサ(0805)のみ**。IC(DIP-8)・ダイオード(DO-35)・トリマ・コネクタは購入済み部品を手はんだ(jlc_exportのBOARD_EXCLUDEで自動除外)。
- **mini版コネクタ(2026-07-19統一)**: J1 TD04A=**端子台**(5.08mm MKDS互換、ピンヘッダから変更)、J2 TO_PICO=**JST XH 6P**(ピン順は従来のピンヘッダと同一)。advanced_miniも同様。
- **ゲイン半固定化(improved_mini)**: 固定5.1k + **購入済み3362P 100k半固定**(秋月103283)の直列でG=6.1〜106を実装後調整可(NJM2137はユニティゲイン安定なので下限制約なし)。3362PはKiCad標準の**3386P縦型パターン**を使用(1-3間5.08mm+ピン2オフセット2.54mmで互換、Bournsデータシート確認済)。

### RX_advanced / RX_advanced_mini — 受信・高性能版

- **構成**: BPFを**4次スタガードMFB**(2段をf01=177kHz/f02=232kHzにずらして合成)化し帯域外抑圧+12dB。入力保護強化(R_IN+R_IN2)。
- **部品**: OPA2607×2(デュアル×2で3ユニット使用、mini版はOPA607不使用) + TLV3501。
- **方針**: improved=簡素・低コスト、advanced=選択度優先という位置づけ。**両者のPico側コネクタJ2はピン順統一**(1=V3A, 2=GND, 3=TH_PWM, 4=ENV_ADC, 5=SHDN, 6=CMP_OUT)で、差し替え運用が可能(RX_improved v1.1はLM393化でピン5がNCになったが位置互換は維持)。
- **ゲイン半固定化(2026-07-19, advanced_mini)**: 初段/後段のゲイン設定を「固定5.1k+SMDトリマ20k(TC33X-2-203E)」に変更し、実装後にG=6.1〜26.1で調整可能(固定分がOPA2607の最小安定ゲインG≥6を担保)。
- **advanced_miniコネクタ(2026-07-19統一)**: J1 TD04A=**端子台**(ピンヘッダから変更)、J2 TO_PICO=**JST XH 6P**(ピン順不変)。

### CHILD_MAIN — 子機メイン基板

> **⚠ 2026-07-28 改訂(v3.1) — 基板間コネクタの整合**: **`RX_improved_mini` は製造済み(基板到着済み)で
> 変更不可**のため、本基板を RX の `J2` に合わせた。`J_RX1` を **XH4→XH6 / ピン順 V3A・GND・TH_PWM・
> ENV_ADC・NC・CMP_OUT**（RX `J2` と完全同一＝ストレート6芯1本）。RX に受け口の無い `RX_EN` を廃止し
> **GP6 を `TH_PWM`(PWM3A)へ転用**。RX には電源専用コネクタが無いので **V3A は C-PWR `J_RXA` →
> 新設 `J_RXA1`(XH3) → 本基板を純パススルー → `J_RX1` pin1** で渡す（本基板側に V3A 負荷は付けない）。
> 併せて **C-PWR との電源/I2C コネクタ不整合も解消**: `J_PWR1` を C-PWR `J_MAIN` と同じ
> V5D/V5D/GND/GND/V3D/V3D へ、`J_I2CP`(XH5, C-PWR `J_I2C` と1:1)を新設し **INA226 の ALERT を GP3** で受ける
> (`R_AL` 10k プルアップ)。詳細は `pcb/RX_improved_mini/基板仕様書.md` §5。

> **⚠ 2026-07-21 全面改訂(v2.0)**: 主制御を**Raspberry Pi Pico 2 W**へ統一。IMUを**BNO085(SPI0専用バス)**へ、microSDを**Molex 104031-0811 表面実装**へ、RS485を**Waveshare×2(DATA+TRIGGER、MAX3485直載せ廃止)**へ、電源は**C-PWRからV5D/V3D受電(オンボードレギュレータ廃止)**へ変更。LCD/3ボタンは**UI基板**へ分離(J_UI)。**確定ネット定義=`../docs/AquaBeacon_MAIN_UI_GPIO_コネクタ表.md`**。以下の旧記述(BMI270/MAX3485/オンボード電源)は破棄。

- **役割(旧)**: 詳細設計書§2.2のデジタル/電源部。アナログ受信は別基板(RX)に分離し、J_RXで接続するキャリア基板。全部品THT/モジュール実装方針。
- **構成**: Raspberry Pi Pico(ピンソケット) + BUCK 5V + NJU7223F33 LDO、microSD SPIモジュール(V5)、DS3231 RTC、SparkFun Micro BMI270(Qwiic)、Waveshare TTL-RS485(C)、MAX3485(トリガ**受信固定**)+120Ω終端、テザー端子台。
- **電源レール**: V5 / V3A(LDO由来クリーンアナログ、RX基板へ給電) / V3D(Pico内蔵SMPS)を分離。
- **主要な設計判断**:
  - LDOはAP2112→**NJU7223F33**に変更。TO-220Fで**ピン順1=VOUT, 2=VIN, 3=GND(78xx系と逆)**。
  - **MAX3485のVCCはV3D(3.3V)**。設計書のV5指定はIC仕様(3.0–3.6V専用)違反のため修正(設計書側は未修正)。
  - **RS-485モジュールも3.3V給電**(5VだとRXDが5VスイングしPicoが非トレラント)。自動方向切替品のため設計書のGP14方向制御は廃止。
  - `R_SDA/R_SCL` 4.7kは両MAIN基板に実装場所を残すが、モジュール側プルアップとの並列過多を避けるため**既定DNP**。
    組立後、無通電でSDA/SCL–V3D間抵抗を測り、4.7kΩ超の場合だけ必要に応じて実装する。

### PARENT_MAIN — 親機メイン基板

> **⚠ 2026-08-01 v5.3: LCD を I²C 品へ変更**(ユーザ判断=配線簡素化)。Newhaven **NHD-C12864WO-B1TFH#-M**
> (128×64 グラフィック / 4線SPI / 30pin 0.5mm FFC) → **NHD-C0216CiZ-FSW-FBW-3V3**
> (2×16 キャラクタ / **I²C** / AiP31032 / 8pin 1.5mm THT / I²C 0x3E(7bit))。
> 旧LCDは 30pin FFC + バックライト別線(PHR-2)で `J_LCD1`(XH9) と物理的に直結できなかった。
> **`J_LCD1`: XH9→XH7**(GND/V3D/SDA/SCL/RST/LED_A/LED_K)、**GP14(`LCD_CS`)/GP19(`LCD_DC`)を解放**、
> **SPI1 は microSD 専用**に。**`R_BL`: 33Ω/V3D → 100Ω/V5D**(新LCDの VLED=2.96V typ に対し
> 3.3Vでは余裕0.34Vしか無く電流が公差で2.3倍ばらつくため)。昇圧C(VOUT–VDD / C1+–C1− 各1µF)は
> **LCD至近のキャリア基板側**に置く。再ビルド結果: ERC合格 / netlist一致(34ネット) / **DRC違反0・未接続0・孤立島0**。
> **C-MAINも2026-08-02 v4.1で反映済み**。親子で同じXH7ピン順・LCD・バックライト回路を使用する。

> **2026-08-02 v5.5: SPRESENSE拡張ボード対応**。CXD5602PWBEXT1のJP1を必ず3.3V側に設定し、
> J_SPRのPPS/Eventは各100Ω直列でArduino互換デジタル端子へ接続する。pin4はNCとし、SPRESENSEはUSB等の正規電源から給電する。

> **⚠ 2026-07-21 全面改訂(v3.0)**: 主制御を**SPRESENSE→Raspberry Pi Pico 2 W**へ変更。SPRESENSEは**独立IMUロガー**として J_SPR(PPS+EVENT_MARK)接続のみ。GNSS(NEO-M9N UART1+PPS)、P-TX制御(PWM_A/B+TX_EN+TRG_TX)、TX温度ADC入口(直列R+RCフィルタ+未接続検出)、microSD Molex、RS485×2(Waveshare)、I2C(DS3231/MS5837/LIS3MDL/Celsius/INA226)。電源はP-PWRからV5D/V3D受電。LCD/3ボタンはUI基板へ。**確定ネット定義=`../docs/AquaBeacon_MAIN_UI_GPIO_コネクタ表.md`**。以下の旧SPRESENSEキャリア記述は破棄。

### CHILD_PWR / PARENT_PWR — 電源基板(2026-07-23新設・2026-07-24完成)

- **電流経路**: `J_BAT(XT30PW-M) → F1(3A速断) → Q1(2SJ349 Pch逆接保護) → SW_PWR(トグル 28VDC/3A) → R_SH(20mΩ/2512) → VBAT_M` → 各系統。
- **電流検出**: `U_INA(INA226AIDGSR, MSOP-10 SMD直載せ, addr 0x40)` を R_SH でKelvin検出。I2C/ALERTは J_I2C(XH5) でメイン基板へ。0.5mmピッチのため **`min_clearance=0.13mm`(JLC 5mil)で発注**。
- **レール**: BUCK 5V(LXDC55) → NJU7223F33 ×2 で V3D(デジタル)/V3A(アナログ)を分離。親機のみカメラポッド用に2系統目のBUCK(秋月 **AE-MYMGK00506ERSR-5V0**、自作FP `AquaBeacon:MYMGK00506ERSR_AE`)を搭載し、TX駆動基板へは VBAT_S を直結。
- **主要な設計判断(LTspice検証済み)**: **C_BLK を 470µF→100µF に低減**し突入電流を 31/40A まで下げた(トグルSWの3A接点保護)。**F1は速断品が必須**(標準品ではI²Tが足りない)。検証は座標ミスを避けるため `.cir` ネットリスト形式(`LTspice/{CHILD,PARENT}_PWR{,_rev}.cir`)。数値は `sim/notes.md` 2026-07-23節。
- **未反映**: 購入リストExcelのINA226行が旧モジュール品のまま(基板はSMD直載せに変更済み)。

### UI_BOARD — 共通表示操作基板(2026-07-21新設 → 2026-07-23廃止)

- **役割**: 親機・子機共通。Newhaven **NHD-C12864WO-B1TFH#-M**(ST7567系128×64, 4線SPI)+ UP/ENTER/DOWN 3ボタン + バックライトPWM。メイン基板と J_MAIN(XH8: V3D/GND/SCK/MOSI/LCD_CS/LCD_DC/BL_PWM/BTN_ADC)で接続。
  - ※**この節はUI基板廃止(2026-07-23)時点の記録**。LCDは 2026-08-01 に **NHD-C0216CiZ-FSW-FBW-3V3**(I²C) へ変更済み。現行仕様は PARENT_MAIN 節と `pcb/PARENT_MAIN/部品一覧.md` §5 を参照。
- **設計判断**: 3ボタンは**ADC抵抗ラダーで BTN_ADC 1本に集約**(Pico GPIO節約)。LCD_RSTは**RC電源投入リセット**。BLは**2SK4017**でPWM調光。**FFCピン順・LCD外形・取付穴はメーカー機械図で要確定**(暫定9ピン表現)。

- **役割(旧)**: 設計書§2.3+§2.5。SPRESENSE拡張ボードとケーブル接続するキャリア/配電基板。
- **構成**: J_SPR(拡張ボードArduinoヘッダへ: UART2/TRG_TX/PWM0・1/I2C0)、MAX3485(トリガ**送信**、DE=H固定)+120Ω終端、Waveshare TTL-RS485(C)、DS3231、予備I2C(将来の磁気センサ)。
- **電源系統**: **BUCKを2系統に分割**(突入/ノイズ分離) — BUCK_A→拡張ボードJP3(5V_IN)+NJU7223F33でV3T生成、BUCK_B→カメラポッド(Pi Zero 2W)。TX駆動基板へはVBAT_S(≈11.1V)直結。V3Tは拡張ボードの3.3Vレールと**接続しない**(レール競合回避)。
- **主要な設計判断**(SPRESENSE公式ドキュメント調査に基づく):
  - **SPRESENSEメインボード単体はIO=1.8V(超過厳禁)・PWM非搭載** → **拡張ボードCXD5602PWBEXT1必須、JP1=3.3V設定**。
  - SDログは拡張ボードのSDIOスロットを使用(子機と異なり基板上にSD無し)。
  - PWMはD06=PWM0/D05=PWM1。ハード相補・デッドタイム機能なし → FWで担保。

### onlyTX — 手作業プロジェクト(パイプライン外)

- TX_improvedと同一トポロジ(TC4427→2SK4017 1石)を手作業でKiCad化中。PCBは未着手(空)。
- `onlyTX/REVIEW.md` の机上レビューで判明した要修正点:
  - **Q3のフットプリントがSOT-523(2SK3019用, 30V/0.1A)になっている** → 実部品2SK4017はTO-251 THT(60V/5A)。動作時ドレインピーク33V(9V)/44V(12V)がSOT-523品の定格を即超過するため必ず修正。
  - ドレインTVS(SMBJ48A)と電源保護(SMBJ15A+バルク100µF)が未実装 → 振動子外れ時フライバック(53V@12V)対策に必須。
  - フットプリント未割当部品多数。検証済みの `pcb/TX_improved/` の流用を推奨。

## 横断的な設計方針

1. **単一ソースからの全自動生成**: 各基板は `pcb/build_*.py` の回路記述から sch/ERC/netlist照合/pcb/DRC/ガーバー/BOM/3Dレンダまで一括生成。不整合が構造的に起きない。座標・定数変更後も該当スクリプト再実行のみ。
2. **GNDは両面ベタ**(サーマルリリーフ)、給電・信号交差はB.Cu回廊。200kHzアナログは2層+ベタで十分。
3. **JLCPCB発注方針**(mini系): 受動・ダイオードはBasic品限定、ICのみ拡張部品。LCSC番号を回路定義に埋め込み。Basic化での定数変更は必ず原設計と周波数特性を数値比較。BPFコンデンサはC0G/NP0必須、フルサイズTHT版の抵抗はE96 1%金属皮膜。
4. **TD04A C0=1260pF は仮定値**: LCR実測後にTX両基板のL1とTX_advancedのR_DMPを再確定(`pcb/TODO.md`)。
5. **リファレンスは必ず数字で終える**(J_BAT1等)。でないとBOM/アノテーションで「?」になる。

## ディレクトリ構成

- `docs/` — 元仕様書(AquaBeacon 確定仕様/実験検証仕様/詳細設計)
- `LTspice/` — 回路シミュレーション(TX_improved/TX_advanced/RX_improved/RX_advanced は `.asc`、電源基板 CHILD_PWR/PARENT_PWR は `.cir` ネットリスト)
- `sim/` — 検証スクリプトと **`notes.md`(設計判断の全記録)**
- `scripts/ltspice_sim.py` — LTspiceバッチ実行ラッパー(PyLTSpice)
- `pcb/` — KiCad生成パイプラインと10基板+廃止1(詳細は `pcb/README.md`、発注は `ORDERING.md`、組立は **`BRINGUP_BOARDS.md`(電源/メイン4基板)** と `BRINGUP.md`(TX/RX)、システム統合は `SYSTEM_INTEGRATION.md`)。`footprints/AquaBeacon.pretty/` は自作フットプリント、`datasheets/` は部品データシートPDFの保管先
- `onlyTX/` — 手作業KiCadプロジェクト(独立、`REVIEW.md` 参照)
- `tools/auto_continue.ps1` — Claude Code 5時間制限の自動再開スクリプト

## 再現方法

```powershell
# LTspice検証(要: LTspice + pip install PyLTSpice)
python sim\tx_improved_verify.py
python sim\child_pwr_verify.py     # 電源基板: 突入 / 逆接 / 負荷ステップ
python sim\parent_pwr_verify.py

# KiCad基板の再生成(sch/ERC/netlist/pcb/DRC/renderまで一括)
& "C:\Program Files\KiCad\10.0\bin\python.exe" -u pcb\build_tx_improved.py

# GNDベタの孤立島を探す(密なSMD基板でDRC zone unconnectedが出たとき)
& "C:\Program Files\KiCad\10.0\bin\python.exe" -u pcb\probe_islands.py pcb\CHILD_MAIN\CHILD_MAIN.kicad_pcb

# JLCPCB発注用(ガーバーzip + BOM + CPL)
python pcb\jlc_export.py CHILD_PWR
```

## 開発とライセンス

[開発ガイド](DEVELOPMENT.md)にセットアップ・入口・確認方法をまとめています。自作部分は [Apache License 2.0](LICENSE)。[第三者素材・依存の扱い](THIRD_PARTY.md)も参照してください。
