# 完了記録: LCD を I²C 品へ変更（C-MAIN v4.1）

**完了: 2026-08-02**。`build_child_main.py`へXH7/I²C LCD、GP7/GP9解放、V5D/100Ωバックライトを反映。
ERC合格、netlist一致(39ネット)、DRC違反0、未接続0。以下は実施時の引継ぎ原文として残す。

**作成: 2026-08-01 / 対象: `pcb/CHILD_MAIN/` を担当するエージェント**

> C-MAIN の作業中は本件に着手しないこと。**現在のタスクが完了してから**着手してください。
> P-MAIN 側（`pcb/PARENT_MAIN/部品一覧.md`）は 2026-08-01 に更新済みです。同じ内容を C-MAIN にも反映してください。
> 調査は完了しています。データシートの再取得・再調査は不要です。

---

## 1. 何が決まったか

親機・子機共通のLCDを **ユーザー判断で下記へ変更**（2026-08-01）。理由は**配線の簡素化**。

| | 変更前（不採用） | **変更後（採用）** |
|---|---|---|
| 型番 | NHD-C12864WO-B1TFH#-M | **NHD-C0216CiZ-FSW-FBW-3V3** |
| 表示 | 128×64 グラフィック | 2×16 キャラクタ |
| I/F | 4線SPI（CS/DC/SCK/MOSI） | **I²C（既存バスに相乗り）** |
| 引き出し | 30ピン 0.5mm FFC ＋ バックライト別線 | 8ピン 1.5mm THT ＋ A/K 2ピン THT |
| 価格(DigiKey JP) | ¥4,244 | **¥2,248** |

データシートは取得済み: `pcb/datasheets/NHD-C0216CiZ-FSW-FBW-3V3_Newhaven_datasheet.pdf`
コントローラIC: `pcb/datasheets/AiP31032_controller_datasheet.pdf`（Wuxi I-CORE rev B3, 57p）
（旧候補の `NHD-C12864WO-B1TFH-M_Newhaven_datasheet.pdf` / `ST7567_Sitronix_controller_datasheet.pdf` /
`Molex_52892-3095_FFC_30p_0.5mm.pdf` は**不採用品の資料**。参考保管）

## 2. 新LCDの確定仕様（データシート実値。推測ではない）

- コントローラ **AiP31032**、**I²C スレーブアドレス 0x7C（8bit書込形式）= 7bit 0x3E**
- VDD **2.7 / 3.0 / 3.3(max) V**、IDD **0.1 / 0.3 / 0.5 mA**
- VLCD（コントラスト）4.8/5.0/5.2V は**内蔵昇圧**
- バックライト **VLED 2.88 / 2.96 / 3.12 V @ ILED=20mA**、ILED **10 / 20 / 30(max) mA**
- 外形 **56.80 × 26.20 × 5.50 mm**（±0.5）、表示 V.A 45.70×14.30 / A.A 42.86×11.32
- ⚠ **取付穴なし**（旧候補は 4×φ3.2 あり）→ 筐体設計に影響。ベゼル押さえ等が必要
- 信号8ピン **1.5mmピッチ THT**（P1.5×7=10.50, ピン長8.0±0.5, **pin8が左・pin1が右**）
- 推奨PCBフットプリント: 信号=穴φ0.80/ランドφ1.20、バックライトA/K=穴φ1.00/ランドφ1.80（A-K間2.50mm）

**ピン配置**:

| ピン | 記号 | 結線 |
|---|---|---|
| 1 | RST | `LCD_RST`（Lowアクティブ。既存 `R_RST`+`C_RST` のRCをそのまま流用可） |
| 2 | SCL | `I2C_SCL`（プルアップ4.7k–10k指定 → 既存 `R_SCL` 4.7k で充足） |
| 3 | SDA | `I2C_SDA`（同上 → `R_SDA` 4.7k） |
| 4 | VSS | `GND` |
| 5 | VDD | `V3D` |
| 6 | VOUT | **VOUT–VDD 間に 0.47–2.2µF**（推奨1µF） |
| 7 | C1+ | **C1+–C1− 間に 0.1–1µF**（推奨1µF） |
| 8 | C1− | 同上 |
| A | LED+ | `LEDBL_A` |
| K | LED− | `LEDBL_K`（`Q_BL` 経由でGND） |

> 昇圧C×2（VOUT–VDD / C1+–C1−）は**充電ポンプのノード**なので、XHケーブルで引き回さずLCD至近に置くこと。

## 3. C-MAIN に入れる変更（`build_child_main.py`）

現状の該当箇所は `build_child_main.py` の **L180–L192**（`J_LCD1` / `C_LCD` / `R_RST` / `C_RST` / `R_BL` / `Q_BL` / `R_G`）
と、配置表 **L266–L268**。P-MAIN の L164–L176 / L250–L252 と構造は同一。

1. **`J_LCD1` を XH9 → XH7 に縮小**
   現状: `Conn_01x09` / `XH9` / `{1:GND, 2:V3D, 3:SPI_SCK, 4:SPI_MOSI, 5:LCD_CS, 6:LCD_DC, 7:LCD_RST, 8:LEDBL_A, 9:LEDBL_K}`
   変更後（案）: `Conn_01x07` / `XH7` / `{1:GND, 2:V3D, 3:I2C_SDA, 4:I2C_SCL, 5:LCD_RST, 6:LEDBL_A, 7:LEDBL_K}`
   value も `NHD_C12864WO` → `NHD_C0216CiZ` に。**配置表 L268 のパッド座標コメントも更新すること**
   （昇圧C×2とRCをキャリア基板側に持たせるなら `LCD_RST` を省いて XH6 も可）
2. **`LCD_CS` / `LCD_DC` の Pico ピン割当を削除**（`build_child_main.py` L64–L65 の `'10': 'LCD_CS'` と `'12': 'LCD_DC'`）
   → **GP7 と GP9 が解放される**。空きピンは `'NC'` にする（CLAUDE.md「未使用ピンは `{'30': 'NC'}`」）
3. **SPI1 は microSD 専用になる**。「microSD と LCD で SPI1 共有」の制約が消えるので、コメント類も更新
4. **`R_BL` を 33Ω → 100Ω、上流を `V3D` → `V5D` へ**
   現状 `Part('R_BL', 'Device', 'R', '33', RFP, {'1': 'V3D', '2': 'LEDBL_A'}, ...)`
   → `'100'` / `{'1': 'V5D', '2': 'LEDBL_A'}`
   **根拠**: VLED typ 2.96V に対し 3.3V レールでは余裕 0.34V しかなく、VLED公差 2.88–3.12V で電流が 2.3倍ばらつく。
   5V なら (5−2.96)/(100+RDS(on)≈7) ≈ **19.1mA**、公差込みでも 18.4–20.8mA に収まる。
   ※C-MAIN に `V5D` が来ているかを先に確認すること（P-MAIN は `J_PWR1` 経由で来ている）。無ければ 3.3V のまま
   `R_BL`≈10Ω とし、明るさばらつきを許容する旨をコメントに残す
5. **I²Cアドレス衝突なし**を確認済み（DS3231=0x68 / AT24C32=0x57 / BNO085はSPI0 / MS5837=0x76 / TSYS01=0x77 / LCD=0x3E）
6. **LCD直近に昇圧C×2を載せる小型キャリア基板が必要**（LCDは1.5mmピッチTHT直付け前提でコネクタが無いため）。
   Newhaven純正 `NHD-PCB0216CZ`(¥2,259) は **CZシリーズ用でCiZ非対応**。自前で小基板を起こすのが安価。
   ※これは親機・子機で**共通の基板**にできる。着手前にユーザーへ確認すること

## 4. C-MAIN の `部品一覧.md` に入れる変更

**`pcb/CHILD_MAIN/部品一覧.md` には LCD 本体の記載がそもそも無い**（`J_LCD1` コネクタの行だけ）。
`pcb/PARENT_MAIN/部品一覧.md` の **「## 5. 表示（LCD）」節をそのまま複製**して追加してください（内容は親子共通）。
併せて `J_LCD1` の行（現 L127）を XH9→XH7 予定に更新。

## 4.5 P-MAIN で実際に踏んだ罠（同じことが C-MAIN でも起きる可能性が高い）

P-MAIN v5.3 は上記1〜5をそのまま入れて **ERC合格 / netlist一致(34ネット) / DRC違反0 / 未接続0 / 孤立島0** で完了したが、
途中で1点ハマったので先に共有する。

- **`R_BL` の V3D→V5D 変更で全ネットが再配線され、`C_SD2`(10µF **0805 SMD**)の GNDパッドが
  `I2C_SCL`(北) / `I2C_SDA`(南・東) / `V3D`(西) に四方を囲まれて F.Cu 上で孤立した。**
  （`C_SD1` は THT なのでリードが B.Cu 主ベタへ素通しになり無事。**SMDのGNDパッドだけが危ない**）
- DRC は `zone unconnected` を座標(0,0)で報告するので、`probe_islands.py` で島を特定する。
- ただし P-MAIN では **`probe_islands.py` が "NO SPOT" を返した**（島が狭くて候補を出せなかった）。
  さらに、**目視で選んだ「パッド列の北」は島ではなく主ベタ側**だったため、そこにビアを置いても島は繋がらない
  （DRCは通るが未接続が残る、という紛らわしい状態になる）。
- 最終的に **島ポリゴンへの内包判定(`SHAPE_POLY_SET.Contains`)＋両層クリアランス実測**を
  スクリプトで総当たりして唯一の実用解を求めた。C-MAIN でも同じ手を使うこと（下記そのまま流用可）:

```python
# KiCad同梱python で実行。zone.GetFilledPolysList(F_Cu) の島 outline を特定し、
# その内部かつ F.Cu/B.Cu 双方で非GND銅から (via_r + clearance) 離れる格子点を総当たりする。
# 出てきた座標を build_*.py の seed_vias に ('GND', x, y) で追加 → 再ビルド。
```

- **B.Cu 側も必ず見る**。P-MAIN では島の直下を `SD_CS`(x≈45.95) と `SD_CD`(x=47.10) の縦線が走り、
  間が 0.85mm しか無く 0.6mm ビア＋クリアランスが物理的に入らなかった。
  最初に選んだ (46.1, 69.0) は **B.Cu の SD_CS と短絡**して DRC で弾かれた。
- 採用値（P-MAIN）: `('GND', 46.70, 69.30)`。**C-MAIN は配置も配線も違うので、この座標は流用不可。必ず再測定すること。**

## 5. 他に追従が必要なドキュメント

- `../docs/AquaBeacon_MAIN_UI_GPIO_コネクタ表.md` … **ネット定義の正**。
  **P-MAIN 分・共通分は 2026-08-01 に更新済み**（P-MAIN GPIO表 / P-MAIN コネクタ表 `J_LCD` /
  オンボードUI表（LCD型番・`Q_BL` の V5D+100Ω）/ BOM追加必要品 / 冒頭の「microSDバスはLCDと共有」）。
  **残るのは「## C-MAIN（子機メイン）Pico 2 W GPIO割当」節と「### C-MAIN」コネクタ表の2箇所だけ**:
  GP7=`LCD_CS` と GP9=`LCD_DC` を予備・未実装に、GP10/GP11 を microSD 専用に、
  `J_LCD` を XH9→XH7（GND/V3D/SDA/SCL/RST/LED_A/LED_K）へ。GP4/GP5 の接続先に LCD(0x3E) を追記。
- `hardware/README.md` L104 … LCD型番と `J_MAIN(XH8: ...)` の記述
- `docs/AquaBeacon_詳細設計書.md` L34 ほか（確定仕様メモ/実験検証仕様書/電源アーキ決定書の同一記述, 各L35–L38付近）

## 6. 未確定（ユーザー判断待ち）

- キャリア基板を起こすか、LCDピンへ直付けで済ませるか
- 2×16キャラクタで必要な情報が表示しきれるか（旧候補は128×64グラフィックだった）→ ファーム側のUI設計に影響
- LCD未購入（`../docs/未踏ジュニア購入物品.xlsx` に行が無い）
