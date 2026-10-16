# AquaBeacon TX/RX 基板 (KiCad 10) — 2026-07-11

LTspiceで検証済みの4回路(`LTspice/` `sim/notes.md` 参照)をKiCadの回路図+PCBに実装したもの。
すべて **ERC合格・意図ネットリスト照合合格・DRC 0違反/未配線0**。

| 基板 | 内容 | サイズ | 主要部品 |
|---|---|---|---|
| `TX_improved/` | 2SK4017 1石 + 保護一式 | 60×45mm | 2SK4017(TO-251), SMBJ48A/15A, 500µH |
| `TX_advanced/` | ゲートドライバ + 2SK4017×2プッシュプル + CT1:5トランス (**SMD化済 2026-07-19**) | 85×60mm | TC4427A(SOIC-8), 2SK4017×2(THT), SMBJ40A×2, L1=470uH RLB0912(THT), 手巻きトランス(5ピンヘッダ実装) |
| `RX_improved/` | 受信チェーン(×20→MFB BPF→×25→BAT85検波→TLV3501) | 130×80mm | OPA2607(SOIC-8), OPA607(SOT-23-5), TLV3501(SOT-23-6) |
| `RX_advanced/` | 4次スタガードMFB版 + 入力保護強化(R_IN+R_IN2) | 140×80mm | OPA2607×2(SOIC-8), TLV3501 |

各フォルダの内容: `.kicad_sch` / `.kicad_pcb` / `.kicad_pro`、`*_schematic.pdf`、
`*_render.png`(3Dレンダ)、`gerbers/`(ガーバー+ドリル)、`erc.rpt` / `drc.rpt`、`*.net`、
`*_bom.csv`(部品表: Value/Footprintでグループ化)。
`datasheets/` に発注前確認で参照した一次資料(2SK4017東芝純正データシート)を同梱。

発注・組立時は **[ORDERING.md](ORDERING.md)**(4基板統合発注リスト+代替品情報)と
**[BRINGUP.md](BRINGUP.md)**(組立順序・通電手順・シミュ由来の期待測定値)を参照。
全体システム(Pico/SPRESENSE/テザー)への組み込みは **[SYSTEM_INTEGRATION.md](SYSTEM_INTEGRATION.md)**
(設計書とのギャップ分析・J2↔GPIO対応表)を参照。

## 生成・検証ツールチェーン(再現方法)

回路図・基板ともPythonで生成している(単一の回路記述からsch/netlist/pcbを導出するので不整合が起きない):

```
& "C:\Program Files\KiCad\10.0\bin\python.exe" pcb\build_tx_improved.py   # 各基板
```

フロー: `kicadgen.py`(回路図S式生成: 標準ライブラリからシンボル抽出、ピン座標変換、
グローバルラベル結線) → `kicad-cli sch erc` → `netlist出力+意図と照合` →
`pcbgen.py`(pcbnew APIで配置・配線・GNDベタ) → `kicad-cli pcb drc`。
座標を変更したら該当 build_*.py を再実行するだけで全ファイルが再生成される。

3Dモデル出力(部品込み)は `python -X utf8 pcb\export_3d.py [board]` → `pcb/3d/` に
`<board>.step`(機械CAD) / `.glb`(ビューア) / `_mech.stl`(筐体干渉チェック)。
基板ディレクトリには書き込まない。3Dモデル未割当の部品は `--gaps` で一覧できる。
標準ライブラリに3Dモデルが無い部品は `mkmodel3d.py`(KiCad自身をSTEPライタにして
データシート寸法の簡易ソリッドを生成)+ `models3d.py`(FPへの割り当て表、`pcbgen` が自動適用)
で埋める。詳細は `pcb/3d/README.md`。

## 設計メモ

- GNDは両面ベタ(サーマルリリーフ)。給電・信号交差はB.Cu回廊(THT穴を避けたx/y)を使用。
- RXのアナログ信号帯(200kHz)は距離が短く2層+ベタで十分。
- TX_advanced はアイドル時PWM=Lowで両FETオフ(設計書のMIC4427直結案の飽和問題を回避、sim/notes.md参照)。
- トランスT1は手巻きEEコア想定で2.54mm 5ピンヘッダ穴に実装(1=P1, 2=CT, 3=P2, 4=S1, 5=S2)。

## JLCPCB表面実装 (2026-07-19)

- **TX_advanced**: R/C/ツェナーを0805/1206/2512/SOD-323のJLC部品にSMD化
  (抵抗・スナバC=Basic、R9=2512 1W、C1=SMD電解、D1/D2=BZT52C15S Preferred、
  U1=TC4427A SOIC-8 C20551)。**MOSFET(TO-251)・トランス・L1・端子台はTHT手はんだ**。
- **RX_improved_mini (2026-07-19全面改版)**: RX_improved **v1.1**(NJM2137/LM393 購入部品優先版)の
  ミニ版に変更(68×46mm)。SMD化は抵抗・コンデンサ0805のみで、IC(DIP-8)・DO-35ダイオード・
  トリマは購入済み部品を手はんだ。ゲインは固定5.1k+**3362P 100k**(購入済)でG=6.1〜106。
  3362PはKiCad標準の3386P縦型パターン(ピン互換)で実装。MFBの1nFはC0G(C1791)を指定。
- **RX_advanced_mini**: ゲイン設定抵抗を「固定5.1k + SMDトリマ20k(TC33X-2-203E)」に変更。
  G=1+(5.1k+0..20k)/1k=**6.1〜26.1** を実装後に調整可(固定5.1kがOPA2607の最小安定
  ゲインG≥6を担保)。トリマは1-2ピンショートのレオスタット接続。
- 発注ファイル: `pcb/jlc_export.py <board>` で `*_gerbers.zip` / `*_bom_jlc.csv` /
  `*_cpl_jlc.csv` を生成 (J/H/Q/T/L リファレンスはSMT除外)。
- TX_advanced L1 は Bourns RLB0912-471KL (470uH/0.48A, D9×12 P5mm, DigiKey) —
  `../docs/未踏ジュニア購入物品.xlsx` に追記済み。C0実測後にL値再確定。

## 発注/組立前の要確認事項

1. **2SK4017 ピン配置**: ~~要確認~~ → **確認済み**。東芝純正データシート
   (2009-09-29版, `datasheets/2SK4017_toshiba.pdf`, JEITA 2-7J2B)にて
   **1=ゲート, 2=ドレイン(放熱タブ), 3=ソース** を確認。設計どおり。
2. **OPA2607 / OPA607 のパッケージとピン配置**: **確認済み**。TIデータシートにて
   OPA2607=SOIC-8(TL072互換配置)、OPA607=SOT-23-5(標準DBV配置)を確認。
   単電源3.3V動作・入力コモンモード範囲はデータシートで最終確認を推奨。
3. **TD04A C0=1260pF 仮定**: LCR実測後、TX両基板のL1(500µH/480µH)とTX_advancedの
   R_DMP(=R9 220Ω)を再確定。
4. **BZX79-C15(THT) / BAT85(THT)**: LTspiceシムのBZX84C15L/BAT54のTHT等価品として選定。
5. ゲート駆動: TX_improvedのJ2には5Vパルス(3.3V GPIO直結不可)。TX_advancedのJ2は
   3.3V PWM入力可(MIC4427が12Vへレベル変換)。
