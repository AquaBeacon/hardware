# AGENTS.md — AquaBeacon (未踏ジュニア) KiCadプロジェクト

200kHz水中音響ビーコン(TD04A)のTX/RX/電源/メイン基板一式(全11基板)。システム全体像・
各基板の設計方針は `README.md`、回路の根拠は `sim/notes.md` を参照。
上位仕様は `../docs/AquaBeacon_詳細設計書.md`
(同じ場所に 確定仕様メモ / 実験検証仕様書 / 基板センサ電源アーキテクチャ決定書 もある。
仕様書はワークスペース共通の `Mitou26/AquaBeacon-OSS/docs/` に一元管理。パスはプロジェクトルート起点)。
メイン基板のネット定義の正は `../docs/AquaBeacon_MAIN_UI_GPIO_コネクタ表.md`。
ユーザーへの回答は日本語で。

## 最重要ルール

- **`pcb/<BOARD>/` 内の .kicad_sch / .kicad_pcb を直接編集しない。**
  各基板は `pcb/build_<name>.py`(部品表・回路図座標・PCB配置・配線を全部記述)から
  全自動生成する。修正は必ず build スクリプト側に入れて再生成する:
  ```powershell
  & "C:\Program Files\KiCad\10.0\bin\python.exe" -u pcb\build_tx_improved.py
  ```
  (ERC → ネットリスト意図照合 → DRC → render まで自動。KiCad同梱pythonが必須 = pcbnew依存)
- **回路はLTspiceで検証してから設計・KiCad化する。順序は「検証 → build_*.py」。**
  検証を省いてbuildスクリプトを書き始めない。各基板は `LTspice/<name>.asc` または `.cir` と
  1対1対応。検証スクリプトは `sim/*_verify.py`(アサート付き)。実行は普通のpythonでよい:
  ```powershell
  python sim\tx_improved_verify.py    # 他: rx_improved / tx_advanced / rx_advanced
  python sim\child_pwr_verify.py      # 電源基板(突入/逆接/負荷ステップ)
  python sim\parent_pwr_verify.py
  ```
  - **検証が要る**: 新規トポロジ、定数変更、特性の変わる部品置換、保護回路(TVS/ヒューズ/
    逆接/突入)、電源レール成立性と熱、負荷変動・バースト、ゲート駆動の成立性(Vth最悪値)。
  - **要らない**: コネクタ/ピン配置・フットプリント・シルク・配置配線の変更、純デジタルの
    I2C/SPI/UART結線、既に検証済みで定数が変わらないもの。迷ったら先に検証する。
  - **形式**: 回路図として目視レビューしたいものは `.asc`。電源経路のように
    「突入/逆接/負荷ステップ」でトポロジと `.param` を切り替える検証が主体のものは
    `.cir` ネットリストでよい(前例: `LTspice/{CHILD,PARENT}_PWR{,_rev}.cir`。
    座標付き .asc は転記ミス由来の偽の結果を生みやすい)。
  - **デバイス定数は推測せずデータシート実値を使う**(Vth/RDS(on)/Vin窓/IFSM/定格電流)。
    最悪値(Vth上限など)で成立するかを見る。共通ヘルパと定格定数は `sim/pwr_common.py`。
  - **結果・設計判断・モデル化の前提(想定値の一覧)を `sim/notes.md` に追記して残す。**
    実測待ちの想定値は「実測後に .param を書き換えて再実行」と明記する。
  - LTspiceはパース失敗しても rc=0 で古い `.raw` を残す → 実行後に `.raw` の mtime 更新を
    必ず確認する(`sim/pwr_common.py` の `run()` が assert 済み)。
- **購入済み部品を優先する。** 部品の追加・変更時は `../docs/未踏ジュニア購入物品.xlsx` を確認
  (openpyxlで読める。シート下部に基板別BOM追記欄あり。`.bak_*.xlsx` は履歴なので開かない)。
  Excel自体は無断で書き換えない。**未反映の既知差分: INA226行が旧モジュール品のまま**
  (基板側はMSOP-10のSMD直載せに変更済み) → ユーザーの更新待ち。
- **各基板の `pcb/<BOARD>/部品一覧.md` が使用部品の一次台帳。回路設計・配置・定数決めの前に、
  必ずここのリンク先(データシート/CAD図/寸法図)でピン配置・外形・電気特性を確認してから設計する。**
  推測でピン番号や寸法を決めない。部品を追加・変更したら同ファイルにも追記し、1部品につき
  仕様リンクを最低1つ(できればデータシート+CAD/3Dモデル+購入ページの3種)貼る。
  メーカー公式など CAD図・機械寸法のある一次資料を優先。
  **現状ある台帳は CHILD_MAIN / PARENT_MAIN / CHILD_PWR / PARENT_PWR の4基板のみ。
  TX/RX系(6基板)は未作成なので、その基板を触るときはまず作る**(雛形: `pcb/CHILD_MAIN/部品一覧.md`)。
- **部品のデータシートPDFは `pcb/datasheets/` に保存し、そこを一次参照して設計する。**
  ピン配置・ピッチ・寸法・電気特性を決める前に:
  1. **まず `pcb/datasheets/` に該当PDFが既にあるか確認する**(重複DL・二度手間を防ぐ)。
  2. 無ければ公式/秋月/TI等から `curl -sL -A "Mozilla/5.0" -o pcb/datasheets/<名前>.pdf <URL>` でDLして同フォルダへ保存
     (命名例: `INA226_TI_datasheet.pdf`, `LXDC55_akizuki_AE-LXDC55-5V0.pdf`, `SW_Toggle_Cosland_2MD1_g104028.pdf`)。
     秋月商品ページの「データシート」リンクは `https://akizukidenshi.com/goodsaffix/<name>.pdf`。
  3. 読解は **PyMuPDF(fitz)でページをPNG化して行う**(Read用のpoppler不要)。テキスト抽出できない図はページ画像を描画して目視:
     `python -c "import fitz; d=fitz.open('pcb/datasheets/x.pdf'); p=d[N]; p.get_pixmap(matrix=fitz.Matrix(3,3)).save('OUT.png')"`
     (保存先はWindowsパス表記で。fitzは `/c/...` 形式のsave不可)。
  - **推測でピン番号・ピッチ・G/D/S順を決めない。KiCad標準シンボル/FPが実物と食い違うことがある**ので
    (例: 秋月トグルg104028はKiCad JS202011と配置が別 → 自作FP必要)、必ずデータシートで裏取りしてから配置・配線する。

## 省トークン運用ルール(どのモデルでも守る)

- **生成物(.kicad_sch/.kicad_pcb/.net/レポート全文)は読まない。** 真実は build_*.py と
  build() の標準出力のみ。エラー時はエラー行だけ読む。
- **新規基板はゼロから書かず、最も近い既存 build_*.py をコピーして差分編集**:

  | 用途 | テンプレ |
  |---|---|
  | 最小構成のTHTドライバ/パワー系 | `build_tx_improved.py`(170行・全パターン網羅) |
  | SMD混在の小型アナログ(JLC発注向け) | `build_rx_improved_mini.py` |
  | 電源基板(ヒューズ/SW/Pch逆接保護/INA226 SMD/LED) | `build_child_pwr.py` |
  | Pico搭載の密なSMDメイン基板(オートルータ/UI統合) | `build_parent_main.py` |

- 使用実績のある部品のピン/パッド座標は既存スクリプトのコメントに全部ある →
  **probe_pins.py / probe_fp.py の再実行は不要**(新規シンボルのみ実行し、結果をコメントに残す)。
- **密な基板は手配線しない。`tracks='auto'`(下記)で回し、失敗ネットだけ手当てする。**
- **手seedは「太い幅が要る経路(電池・大電流)」に絞る。** ルータ既定 0.5mm 幅は 1oz で約1.3A
  流せるので、0.5A 級の 5V/3.3V レールまで手で引くと B.Cu レーンが枯れて逆に交差・短絡を作る
  (2026-08-01 C-PWR で実害)。**SMD 部品の下の B.Cu は完全に空いている**ので、THT パッド列に
  阻まれた電源経路はそこを通すと抜けることが多い。
- **DRC/ERC違反はまとめて直して再ビルド**(1違反ずつ回さない)。配置前にスキルの
  クリアランス表に従えば反復自体がほぼ消える。
- render PNG / 回路図PNG を読むのは全チェック合格後に各1回、crop してから。
- エラーはまずスキル `kicad-pcb-gen` の `references/traps.md` 冒頭「エラー即引き表」を引く。

## パイプラインの構成 (pcb/)

- `kicadgen.py` 回路図S式生成 / `pcbgen.py` pcbnew操作+オートルータ / `buildlib.py` build()一式
- `probe_pins.py <Lib> <Symbol>` シンボルのピン座標プローブ、`probe_fp.py` フットプリント調査
  (**`probe_fp.py` の "courtyard" は Ref/Value テキスト込みの bbox なので配置設計に使わない**。
  実 F.CrtYd は `probe_crtyd.py <Lib:FP>` で出す。普通のpythonで動く。GH4 で 43.5mm vs 9.46mm と
  4倍以上ずれる)
- `check_sch.py <build_module|--all>` **回路図の衝突検査**(build不要・数秒。普通のpythonで動く)。
  build_*.py を import して回路図だけ生成し、生成S式の実ジオメトリ(シンボル本体/Ref/Value/
  自動スタブラベル/GNDシンボル/PWR_FLAG/枠/見出し/注記)を突き合わせる。**テキスト幅は近似**
  なので0件になった後に必ず1回だけ目視する。
- `render_sch.py <BOARD|--all>` 回路図PNG(kicad-cli sch export svg → headless Chrome)
- `probe_islands.py <board.kicad_pcb>` GNDベタの孤立島特定+スティッチビア候補出力
- `jlc_export.py <board>` JLCPCB発注用ガーバー/BOM/CPL出力
- `export_3d.py [board...]` 3Dモデル出力 → `pcb/3d/<board>.step`(機械CAD) / `.glb`(ビューア) /
  `<board>_mech.stl`(筐体干渉チェック・OpenSCAD import)。`--gaps` でモデル欠落だけ確認。
  モデルが無い部品は **無言で消える** ので、実行後に必ず gap 一覧を見る
  (`MountingHole_*` だけなら正常)。**基板を再生成せずにここだけ回すと部品が反映されない**
  (モデル割当は build 時に `.kicad_pcb` へ焼かれる)。詳細・実装高さ表は `pcb/3d/README.md`。
- `mkmodel3d.py` / `models3d.py` 3Dモデルが手に入らない部品の簡易STEPソリッド生成と
  FP名→モデルの割当表(`pcbgen.build_board()` が自動適用)。**寸法はデータシート実値のみ**。
- `footprints/AquaBeacon.pretty/` 自作フットプリント(標準ライブラリに無い/実物と違う部品)。
  現在: Waveshare RS485・BNO085(Adafruit 4754)・DS3231(ZS-042)・秋月トグル2MD1・MYMGK降圧
- 汎用版スキル(設計品質ルール・レシピ・罠一覧付き)が `~/.Codex/skills/kicad-pcb-gen/` にある。
  新規基板・レビューはそちらを起点に(SKILL.md=手順と禁止事項、references/=回路図レビュー/
  フットプリント管理/PCB配置配線/電源アナログ/チェックリスト/罠/AquaBeacon固有)。
  **スキルの `scripts/` はこの `pcb/` と同一内容に同期済み(2026-08-03)。パイプライン本体を
  直したら両方を更新する。**

## 配線: オートルータ (`tracks='auto'`)

C-MAIN / P-MAIN は**どちらも112×88mm**(2026-07-25小型化。旧150×105 / 182×116)で
全ネット配線済み(未接続0・DRC exit=0)。手順と既知の逆効果パターン:

0. **配置を変えたら先に `check_placement.py` で確認する**(build不要・数秒):
   `python.exe pcb\check_placement.py build_child_main --map`
   → コートヤード重なり / 盤外 / パッド-基板端0.5mm を検査し、空き領域のASCIIマップを出す。
   DRCを回して配置ミスを見つけるのは高コスト。
1. まず素で `tracks='auto', vias='auto'` を回す(bbox昇順=局所ネット優先で引かれる)。
2. `[autoroute] FAILED net X` のネットだけ手当て:
   - **脱出不可**(微細ピッチ/コネクタの隣接パッドに挟まれる) → `seed_tracks` でパッド外側へ
     短スタブ + `seed_vias` でB.Cuへ落とす。**seedは短く**(長いseedは大動脈を塞ぐ)。
   - **資源枯渇** → `route_first` に入れる。**ただし bbox最大のマルチドロップネットに
     `route_first` を使うのは逆効果**(中央貫通で他ネットを潰す。実例: I2C_SDAで他5ネット死)。
   - **充填率40%超の密基板(112×88のC/P-MAINが該当)は、素通しでは V3D(24ノード)が
     「11パッド配線不能」になる。幹線(トランク)を手seedして枝だけルータに拾わせるのが定石**:
     ① V3D = 左strip縦(x2.2) + 上帯横(y20: モジュール本体下の空き) + 右下横(y67) の3幹線。
     ② I2C = 2本を**入れ子**にしてB.Cuに寝かせる(内側SCL y25.5 / 外側SDA y27)。
     ③ SPI/SD = microSD本体下のB.Cu(Molexのパッドは全てF.Cuなので完全に空き)を
        縦バスにしてPicoのSPIピン高さへ直行させる。**これでF.CuのPico東側が空き、
        R列中段(I2C/LCD/RX_EN等)が東へ脱出できるようになる**(やらないと6ネット死)。
   - **手seedの幹線は「交差ゼロ」を紙上で確認してから書く**(ルータと違いDRCで
     tracks_crossing=ショートになる)。2本を並走させるときは
     **始点側の上下関係と終点側の左右関係を突き合わせ、逆転していたら平面配線は不可能** →
     片方をF.Cu/もう片方をB.Cuに分ける、または片方の幹線終端をもう片方の縦線より手前で止める。
     コネクタの回転で解ける場合もある(下記XHのrot90/rot270)。
3. `zone unconnected`(座標が(0,0)で場所不明) → `probe_islands.py` で島を特定し
   出力された `('GND', x, y)` を `seed_vias` に追加。**配線を変えると島も変わるので再実行**。
4. 微細ピッチSMD(MSOP-10等)を載せる基板は `min_clearance=0.13` を渡す(JLC 5mil可)。
5. **seed_vias は `0.3, 0.6`**(環状幅0.15mm ≥ JLC下限0.13mm)。既定値も0.3/0.6に修正済み
   (2026-07-25)。ルータ自動生成ビアは0.4/0.8でOK。`pcbgen.build_board()` が
   `m_ViasMinAnnularWidth=0.13` / `m_MinThroughDrill=0.2` を基板に書き込むので、
   以後は規格外ビアをDRCが検出する(KiCad既定の環状幅下限0.10mmでは素通りしていた)。
   → C-MAIN/P-MAIN は0.3/0.6で再生成済み(DRC exit=0 / 未接続0 / 全ビア環状幅0.15mm)。
6. **ルータの盤外マージンは `m=4`(端から1.2mm)**(2026-07-25修正)。m=2(0.6mm)だと
   トラックで端まで0.45mm・自動ビアで0.2mmしか空かず、小型基板で端レーンを使い出した瞬間に
   `copper_edge_clearance`(既定0.5mm)違反が出る。**手seedはこの制限を受けない**ので、
   端から1.2mm以内を通したいときだけ自分で座標を書く(DRCは0.5mm以上を確認)。
7. GNDスティッチビアは**主要動線(SPI縦バスやピン列の脱出経路)に置かない**。置くと
   0.05mm級のclearance違反やB.Cu側の孤立(`zone unconnected`)を生む。

## 回路図の書き方(基板の性格で変える)

- **配置を変えたら `check_sch.py` で衝突を検算する**(build不要・数秒。2026-08-04 追加):
  `python -X utf8 pcb\check_sch.py --all`
  → 枠どうしの交差/近すぎ、見出しが上の枠の中身を踏む、シンボル重なり、Ref/Value/ラベルが
  他部品に乗る、注記が枠線をまたぐ、**シート右下タイトルブロックとの重なり**、用紙外を検出する。
  目視用PNGは `python -X utf8 pcb\render_sch.py --all`(全チェック合格後に1回だけ見る)。
- **A3 レイアウトの固定ルール(2026-08-04 に4基板を全面再配置。この寸法を守れば衝突は出ない)**
  - 用紙は **A3(420x297)固定**。使えるのは概ね x14-406 / y34-284。
  - **枠どうしは縦10mm・横12mm 以上あける。** 見出しは `_sch_text(title, x1, y1-1.27, 2.0)` =
    枠上辺の **-3.27〜-1.27mm** に出て、1文字あたり約1.9mm 横に伸びる。旧版の4mm間隔では
    見出しが必ず上のブロックの中身を踏んでいた。長い見出しは**右隣のブロック**にも当たる。
  - **y<=32 は空ける。** PWR_FLAG は kicadgen が `(20,20)+i*25.4` に固定配置し、下向きラベルが
    ネット名の長さぶん(最大 y=33 付近まで)伸びる。取付穴 H1-H4 と TP_GND1 はこの帯の
    右側(x>=200)に並べる。
  - **右下 x296-412 / y257-290 は KiCad の A3 タイトルブロックが占有**している(シート枠と一緒に
    描かれるので .kicad_sch のジオメトリには現れない)。下段右のブロックは **y<=254** で切る。
  - MAIN 系(38ネット超)は **3列 x 3段のグリッド**: x 14-130 / 142-268 / 280-406、
    y 34-128 / 138-198 / 208-284。注記は右列の DESIGN NOTES パネルに集約する。
  - **C-MAIN と P-MAIN は同一回路の部分(電源入力/Pico/microSD/RS485/UI)を同じ座標**にしてある。
    2枚を並べて差分だけ追えるので、片方を動かしたらもう片方も動かす。
- **機能ブロックの破線枠+見出しは `sch_blocks=[(x1,y1,x2,y2,'TITLE')]`、部品の役割・定数根拠・
  変更理由の注記は `sch_texts=[(x,y,'注記',size)]`**(2026-08-03 追加)。どちらもグラフィックのみで
  ネット・ERC・ネットリスト照合に影響しない → 接続を変えずに可読性だけ上げられる。
  見出しは枠の外側・左上の上に出る。
- **注記(`sch_texts`)は枠の中に置かない。** ワイヤ・Ref/Value のどれかに必ず当たる。
  右側/右下に `DESIGN NOTES` パネルを作ってそこへ集約する(4基板とも同じ構成にしてある)。
- **`sch_labels` のアンカーはワイヤ上の点でなければならない。** 縦セグメントに置くときも
  x はワイヤの x に合わせる(ずらすと ERC `label_dangling`)。
- **同じネットのワイヤ群を2箇所に分けて書かない。** `net_segs` はネット単位なのでキーパーラベルが
  1つしか置かれず、もう一方が名無しの浮きワイヤになる。離れた場所はスタブ+ラベルで繋ぐ。
- アナログ/電源基板: `sch_wires` で結線してレビュー可能な図にする(信号は左→右)。
- **多ピンモジュール主体のデジタル基板(30ネット超)はラベル主体**。C-MAIN(38ネット)は
  `sch_wires` が5本だけ。全部ワイヤ化すると座標衝突の泥沼になる。
- **未使用ピンは `{'30': 'NC'}`**。`NC`は予約名でネットにならず no_connect マーカーになる。
- **Picoから給電されるGND/3V3に PWR_FLAG を付けない**(power_output同士で pin_to_pin になる)。
  `power_flag_nets` はC/P-MAINでは `('V5D','V3D')` のみ。
- 同じxに部品を縦積みするとスタブ端が上下のピンと同座標になり短絡(netlist mismatch)。

## ハマりどころ(実績あり)

- LTspice: `C:\Users\ryupc\AppData\Local\Programs\ADI\LTspice\LTspice.exe`(自動探索に無いので明示指定)。
  `.asc` はASCIIのみで書く(µ→u)。TEXT行を壊すと **rc=0のまま古い.rawを読み続ける** ので、
  編集後は .raw のタイムスタンプ更新を確認すること。
- PowerShell 5.1: BOM無しUTF-8日本語スクリプトはパースエラー。ツール類はASCIIで書く。
  `kicad-cli sch export bom` の `${QUANTITY}` はシングルクォートで渡す。
- Python標準出力はcp932で化けやすい → `python -X utf8` を使う。
- **回転時のパッド並び方向を思い込みで決めない**(2026-07-25に実害)。KiCadは
  rot90で `(dx,dy)→(dy,-dx)`、rot270で `(dx,dy)→(-dy,dx)`。JST XHの1x06を
  `rot90` で置くと**pin1→pin6が -y 方向**(rot270なら +y)。座標を間違えると
  seedがパッド間を斜めに突っ切ってtracks_crossing/shortになる。`probe_fp.py <Lib:FP>` が
  rot0/90/180/270の全パッド座標を出すので、seedを書く前に必ず引く。
- 主要部品の実測値(rot180 / 原点=pin1): **Pico** body 21.1×51.1、pads列間17.78・2.54ピッチ、
  **USB先端は原点+2.72(pin1側)**、crtyd x[-20.45,+2.67] y[-50.70,+3.19]。
  **microSD TF-01A**(自作FP `AquaBeacon:microSD_TF-01A`、2026-08-03に Molex から差替)
  rot0で**接点列が -y 側(y-6.35)・カード開口が +y 側(y+6.79)**、pads 1(+2.15)〜8(-5.55)/10=Cd(-6.65)、
  crtyd 17.20×15.60、実装高さ1.85mm。パッドは全てF.Cu(=本体下のB.Cuは配線に使える)だが
  **φ1.0 NPTH位置決め穴が2つ(原点±, +4.49)あり両層を塞ぐ**ので縦バスはその外を通す。
- DRCクリアランス目安: track-track中心≥0.7 / THTパッド-track≥1.4 / THTパッド-via≥1.55 / パッド間≥2.1mm。
  DIP-8の同一列ピン間(2.54mmピッチ)にF.Cuトラックは通せない → B.Cu回廊+ビアで跨ぐ。
- 回路図の目視確認: `kicad-cli sch export svg` → headless Chrome `--screenshot` でPNG化。
- `jlc_export.py`: THT混在基板は prefix 除外では `R_SH`(SMD)と `R_G`(THT)を区別できない →
  `WHITELIST_BOARDS` でLCSC表に載ったrefのみSMT対象にする。BOMのrefは末尾数字が無いと
  KiCadが `?` を付ける(`rstrip('?')` 済み)→ **新規部品のrefは必ず数字で終える**。
- JLCPCB 2層の下限: トラック/間隔 0.127mm、ビア環状幅 **0.13mm**、ビア穴 0.2〜0.3mm。

## 設計上の確定事実(変更時は要再検証)

- TD04A は **C0=1260pF仮定**。LCR実測後に L1 同調と駆動振幅を再確定する約束。
- L1=470µH(購入済) → TX共振 206.8kHz。RXのMFB BPFは f0=206.3kHz(C=1n, 1k/180/3.9k, Q=2.53)で整合。
- TX_improved v1.1: TC4427(3.3Vロジック直結可)で12Vゲート駆動。2SK4017は G/D/S=1/2/3(東芝PDF確認済)。
- RX_improved v1.1: NJM2137×2 + LM393(OC出力・R18プルアップ、J2ピン5はNC)。
  NJM2137は非RRO・CM=1.3〜2.0V@3.3V。NJM2737はGBW不足で不採用。
- 詳細設計書の「MIC4427直結プッシュプル」は動作しない(TX_advancedはドライバ+FETプッシュプルに修正済み)。
- **⚠ 2026-08-02 で子機だけ寸法が分岐した**: **C-MAIN = 104×88 (v4.1) / C-PWR = 62×70 (v2.1)**。
  P-MAIN(112×88) / P-PWR(100×84) は未変更なので**筐体はもう共用できない**。
  子機は C-PWR との接続を **XH9 1本**に統合(旧 XH6+XH5+XH3+XH2 の4本)、`J_RXP`(死にコネクタ)を削除、
  Celsius 水温センサ(TSYS01/0x77, **JST-GH 4極** `J_TEMP1`)を新設、`J_TETH1` を XH4→XH3。
  取付穴ピッチ C-MAIN **95×61.5** / C-PWR **54×62**。C-PWRはM3穴をinset 4.0mmへ移動したため、
  機体 `child_vtray_deck.scad` のボス位置も **v2.1へ追従済み**。
  **AE-LXDC55 は 11×25mm を縦挿しするので実高 33.5mm**(旧3D出力はソケット8.5しか出ておらず10mm過小。
  `mkmodel3d.py`/`models3d.py` に追加済み)。**P-PWR も同じ部品なので再生成すると高さが上がる。**
- **P-MAIN は 112×88mm**(2026-07-25小型化。C v3.0 / P v5.0。機能・ネットは不変)。
  取付穴M3×4も同座標 (4.5,4.5)/(107.5,4.5)/(4.5,80)/(107.5,80) → **筐体を共用できる**。
  実装高さ(2026-07-31 `_mech.stl` 実測): **上面18.49mm**(律速=DS3231 ZS-042スタック=
  ピンソケット8.5+モジュール実測10)/下面リード4.75mm。C/P-PWRは上面23.52mm(2MD1トグル)、
  TX/RX_miniは上面13.79mm。**PWRの旧表記25.12mmは基板裏面からの値**なので混同しないこと。
- **DS3231 ZS-042 は実測 40×20×10mm で、40mm軸がピン列と直交する**(2026-07-31ユーザー実測。
  旧FPの38×22は向きごと誤り)。C-MAIN v3.3 / P-MAIN v5.2 で FP を 20×40 に作り直し
  J_RTC1 を rot270 で上帯(body x41-81)へ移設。**親機はI2C幹線が東のセンサ3連まで貫通するので
  幹線レーンを y25.5/27→26.5/28 へ下げてパッド列の南を通す必要がある**(子機は幹線が終端するので不要)。
  **下辺(y=88)が「Pico USB + microSD 挿入辺」**: Pico rot180 @(30,84.6) でUSB先端y87.3、
  SD1 rot180 @(44,80) で開口y85.75(端から2.25mm)、両者は4.46mmだけ離した隣接配置。
  **SPI配線長が約35mmあるのはPico自体のピン順(SPI1=GP10-13=物理14-17がUSBと逆端)由来で、
  「USBとSDを同一辺・基板端」に置く限り短縮できない**。これ以上詰めるならGPIO再割当
  (=`../docs/AquaBeacon_MAIN_UI_GPIO_コネクタ表.md` とファームの変更)が必要。
- **メイン基板は Pico 2 W 統一**。SPRESENSEは親機の独立IMUロガーで、拡張ボード
  **CXD5602PWBEXT1**を使用する。P-MAIN v5.5ではJP1=3.3Vを前提にJ_SPRのPPS/EVENTを
  各100Ω直列で接続し、pin4のV3D給電は廃止(NC)した。
  UI基板は**廃止**(2026-07-23)しスイッチ/バックライト/リセットRCをC/P-MAINへ統合、
  コネクタはLCD専用 `J_LCD1`(XH9)に集約。3ボタンはADCラダーで `BTN_ADC` 1本。
- **I2CプルアップR_SDA/R_SCL 4.7kはC/P-MAIN両基板で既定DNP**(2026-08-02)。
  組立後の合成抵抗を測り、4.7kΩ超なら必要に応じて実装する。
- 電源基板(C-PWR/P-PWR): Q1=**2SJ349**(Pch逆接保護)、INA226は**MSOP-10のSMD直載せ**
  (`min_clearance=0.13`)、**C_BLK 470u→100u**(トグルSW 3A接点保護のため突入31/40Aへ低減)、
  F1は**速断ヒューズ必須**。P-PWRのカメラBUCKは秋月AE-MYMGK00506ERSR-5V0(自作FP)。
  検証は全項目PASS(`sim/notes.md` 2026-07-23節)。
- 過去の検証値・置換理由は `sim/notes.md` が一次記録。README の個別基板欄は改版に追従遅れがあり得る
  (基板を変えたら README の該当行も更新すること)。
