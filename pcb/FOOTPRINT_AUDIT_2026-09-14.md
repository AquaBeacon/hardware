# AquaBeacon フットプリント監査（2026-09-14）

## 結論

- **確定した誤りは 1 件**: `TX_improved:L1`。
  購入済み `TCV-471M-2.5A-5026`（外径 16.0 mm max、リード間隔 10.0 ±2.0 mm）に対し、
  現在は `L_Radial_D10.0mm_P5.00mm_Fastron_07M`（胴体 D10、ピッチ 5 mm）を使用している。
  リードを曲げれば穴には入る可能性があるが、実物胴体が `J4` と干渉するため製造前に修正必須。
- **条件付きで未確定が 2 件**:
  1. `TX_advanced:T1` は、手巻きトランスを「2.54 mm 1列5ピンヘッダへ終端する」という実装方法なら正しい。
     巻線部品そのもののボビン／端子図がないため、別形状のトランスを直接載せる場合は未検証。
  2. C/P-MAIN の `SW_UP/SW_ENT/SW_DN` は、購入品の本体 6.2 mm と端子間ピッチ 4.5 mm は一致する。
     一方、もう一方のリード列間隔 6.5 mm の一次図面がなく、現物確認が残る。
- 上記以外は、現在指定している実装部品に対して **FP名・パッド番号・ピン数・主要寸法／ピッチに矛盾なし**。

## 対象と機械検査

`pcb/audit_footprints.py` で build スクリプトを読み取り専用インポートし、生成物を変更せずに
次を検査した。

1. 指定フットプリントが KiCad 標準ライブラリまたは `pcb/footprints/` に存在すること。
2. 回路で使用する全ピン番号に対応するパッドが存在すること。
3. 同一 Ref の複数ユニットが同じフットプリントを使うこと。

| 基板 | Ref数 | 機械検査 | 実物照合 |
|---|---:|---|---|
| CHILD_MAIN | 54 | PASS | PASS（タクトSWのみ現物確認残り） |
| PARENT_MAIN | 57 | PASS | PASS（タクトSWのみ現物確認残り） |
| CHILD_PWR | 33 | PASS | PASS |
| PARENT_PWR | 32 | PASS | PASS |
| TX_improved | 28 | PASS | **FAIL: L1** |
| TX_advanced | 32 | PASS | PASS（T1は5ピンヘッダ終端を条件） |
| RX_improved | 43 | PASS | PASS |
| RX_improved_mini | 45 | PASS | PASS |
| RX_advanced | 47 | PASS | PASS |
| RX_advanced_mini | 49 | PASS | PASS |

## 重点照合結果

### メイン基板

- Pico 2 W: `RaspberryPi_Pico_Common_THT` の40ピン配置と一致。
- microSD TF-01A: 自作FPの信号8 + Cd + シェル／位置決め穴は保存済みメーカー図面と一致。
- DS3231 ZS-042: ユーザー実測 40 × 20 × 10 mm、6ピン列の向きを自作FPへ反映済み。
- Adafruit BNO085 4754: ベンダ提供 KiCadデータの2列×6、列間17.78 mm、2.54 mmピッチ、
  pad 1～12の並びと一致。
- Waveshare TTL-RS485(C): 実物7パッドの配置へ修正済み。
- JST XH 2/3/4/5/6/7/9極: 品番・2.50 mmピッチ・極数が一致。
- 2N7002: SOT-23、1=G/2=S/3=Dで一致。
- 6 mmタクトSW: 4.5 mm方向は購入ページと一致。6.5 mm方向だけ一次図面／現物確認待ち。

### 電源基板

- XT30PW-M: KiCad標準FPと購入品の横型基板実装、極性（pad1=-、pad2=+）が一致。
- FUC-03A: 穴間隔6.7 mm、穴径1.7 mmが Keystone 3517 Inline FPと一致。
- Cosland 2MD1: KiCad標準 `JS202011` は使わず、保存済み寸法図準拠の自作6P FPを使用している。
- 2SJ349 / TK7R4A10PL / NJU7223F33: いずれも1列3ピン、2.54 mmピッチ。ピン順は各データシートと一致。
  `TO-220-3_Vertical` は穴位置上互換。
- INA226AIDGSR: DGS（VSSOP/MSOP-10）、3 × 3 mm、0.5 mmピッチ、pin 1～10が一致。
- AE-LXDC55: 1×3、2.54 mm、1=VIN/2=GND/3=VOUTで一致。
- AE-MYMGK00506ERSR: 自作FP 2×6、列間25.4 mm、列内2.54 mm、pin 1～12が一致。
- 100 µF/25 V、10 µF/50 V電解、2512シャント、SMB TVS、0603/0805部品は購入／JLC品の
  パッケージ指定と一致。

### TX基板

- `TX_improved:L1`: **不一致**。専用 `D16/P10（公差を考慮した長穴推奨）` 相当FPと周辺再配置が必要。
- `TX_improved:J1`: 指定部品は XT30PW-F で、KiCad FPも-F。FP選択自体は正しい。
  購入表の該当行も XT30PW-F だが、ローカル保存PDFは-Mだけなので、組立前に現物性別を確認する。
- `TX_advanced:L1`: Bourns RLB0912-471KL（D9 × 12 mm、P5 mm）を使う前提なら現FPは適合。
  `TX_improved` の購入済みトロイダルを流用してはいけない。
- `TX_advanced:T1`: 1列5ピンヘッダ終端という設計意図には一致。専用トランス部品としての外形は未定義。
- TC4427（DIP-8 / SOIC-8）、2SK4017（TO-251、1=G/2=D/3=S）、SMB/SOD-323、
  1206/2512、端子台/XHは一致。

### RX基板

- NJM2137D / LM393GN: DIP-8、ピン配置互換を確認。
- OPA2350/OPA2607系: SOIC-8標準デュアルOPAMP配置と一致。
- TLV3501AIDBVR: SOT-23-6と一致。
- RX_improved_mini の購入済み3362Pに3386P FPを使う点は、pad 1–3間5.08 mm、pad 2の
  2.54 mmオフセットが一致するためPCB穴配置は互換。3386Pの大きいコートヤード／3D表示は安全側。
- RX_advanced_mini のTC33X-2はKiCad標準TC33Xランドと一致。
- 1N4148/BAT43（DO-35）、1N4148W/B5819W（SOD-123）、JST XH6、2.54 mm 1×6ヘッダ、
  Phoenix互換5.08 mm端子台は一致。

## 修正優先順位

1. **TX_improved L1 の専用FP化と再配置**（製造ブロッカー）。
2. C/P-MAIN タクトSWの現物穴間隔をノギスで確認（6.5 mmなら変更不要）。
3. TX_advanced T1の最終的な機械実装方法を図面化し、5ピンヘッダ終端を確定する。

電気定数は変更していないため、この監査ではLTspice再実行は不要。
