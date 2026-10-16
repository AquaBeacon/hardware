# 発注用ガーバー一式 (2026-07-12 出力)

各ZIPをそのままJLCPCB/PCBWay等のアップローダに投入可能(ガーバーRS-274X+Excellonドリル同梱)。

| ZIP | 基板サイズ | 層数 | 備考 |
|---|---|---|---|
| TX_improved_gerbers_20260712.zip | 60×45mm | 2層 | 2SK4017 1石TX(9V推奨) |
| TX_advanced_gerbers_20260712.zip | 85×60mm | 2層 | MIC4427+プッシュプル+1:5トランス(12V) |
| RX_improved_gerbers_20260712.zip | 130×80mm | 2層 | 受信60dB 2次MFB |
| RX_advanced_gerbers_20260712.zip | 140×80mm | 2層 | 受信60dB 4次スタガードMFB。**J2ピン順統一版(4=ADC,5=SHDN,6=CMP)** — 2026-07-12再配線・DRC 0違反 |

- 全基板: 1.6mm FR-4 / 1oz銅 / HASL可 / 最小トラック0.5mm・最小クリアランス0.5mm級
  (製造難度は低い。DRCはKiCad標準ルールでエラー0、残る警告はシルク見た目のみ)
- 発注前チェックリストは `../ORDERING.md` を参照
  (TD04AのC0実測とR_DMP最終値はL1/R9の**実装部品**側の話でありガーバーには影響しない)
- RX基板の-20dB入力減衰ジャンパは本版には未実装(外付けパッドで代替、`../BRINGUP.md` §6)
