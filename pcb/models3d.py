"""3Dモデルが手に入らない部品に、簡易STEPソリッド(mkmodel3d.py 生成)を割り当てる表。

なぜ必要か: KiCad標準ライブラリに .step 実体が無い部品(XT30PW/ヒューズクリップ/半固定VR)と、
自作フットプリント(トグルSW/MYMGK)は 3D出力で**無言で消える**ため、筐体設計で高さが読めない。
表を1か所に集約し、`pcbgen.build_board()` が全基板の生成時に自動で流し込む
(→ 基板を再生成すれば .kicad_pcb に (model) が入る)。

寸法の出典は mkmodel3d.py の PARTS コメント(全てデータシート実値)。
位置合わせは **フットプリント自身のジオメトリ基準**なので、FPを直しても追従する:
  align='F.Fab'  … F.Fab(部品ボディ外形)bboxの中心に載せる
  align='pads'   … パッドbboxの中心に載せる(F.Fabが無いFP用)
dx/dy は上記中心からのオフセット(mm, KiCad基板座標=Y下向き)。dz は基板上面からの高さ。

使い方: 単体では何もしない。`import models3d` して `models3d.apply(fp)`(pcbgen が呼ぶ)。
モデル未生成のときは警告を出してスキップするだけなので、ビルドは止まらない。
"""
import os
from pathlib import Path

import pcbnew

HERE = Path(__file__).parent
MODELDIR = HERE / 'footprints' / '3dmodels'
# 基板は pcb/<BOARD>/ にあるので KIPRJMOD からの相対で書く(リポジトリを移動しても動く)
PREFIX = '${KIPRJMOD}/../footprints/3dmodels/'

# KiCad標準3Dライブラリ(未解決モデルの検出用)
STDDIR = os.environ.get('KICAD10_3DMODEL_DIR',
                        r'C:\Program Files\KiCad\10.0\share\kicad\3dmodels')


def M(file, align='F.Fab', dx=0.0, dy=0.0, dz=0.0, rot=(0.0, 0.0, 0.0)):
    return dict(file=file, align=align, dx=dx, dy=dy, dz=dz, rot=rot)


# フットプリント名 (ライブラリ名は無視) -> 割り当てるモデル群
MODELS = {
    # 基板端コネクタ XT30PW-M/-F: DS高さ5.20、XYはF.Fab(ハウジング13.40×11.00)
    'AMASS_XT30PW-M_1x02_P2.50mm_Horizontal': [M('XT30PW_body')],
    'AMASS_XT30PW-F_1x02_P2.50mm_Horizontal': [M('XT30PW_body')],

    # 半固定VR
    'Potentiometer_Bourns_3386P_Vertical': [M('POT_3386P_body')],
    'Potentiometer_Bourns_TC33X_Vertical': [M('POT_TC33X_body')],

    # トグルSW(自作FP・F.Fab無し → パッド3×2グリッドの中心基準)。
    # ケース8.94 → ブッシング5.59 → レバー9.00 と積み上げ、総高23.53mm。
    'SW_Toggle_2MD1_6P': [
        M('SW_2MD1_case', align='pads'),
        M('SW_2MD1_bushing', align='pads', dz=8.94),
        M('SW_2MD1_lever', align='pads', dz=8.94 + 5.59),
    ],

    # 秋月MYMGK降圧モジュール(ピンヘッダ2.5+基板1.6+モジュール5.0=9.1mm)
    'MYMGK00506ERSR_AE': [M('MYMGK_AE_stack')],

    # 1x03 ピンソケット = C/P-PWR の **AE-LXDC55 降圧モジュール**の土台(他用途では未使用)。
    #  ソケット(8.5) + モジュール本体 11×25 を縦挿し(25 が高さ) = **総高 33.5mm**。
    #  ソケット単体だと 8.5mm しか出ず、筐体の高さ検討を 10mm 過小評価する。
    'PinSocket_1x03_P2.54mm_Vertical': [
        M('PINSOCK_1x03_FH', align='pads'),
        M('LXDC55_AE_body', align='pads', dz=8.50),
    ],

    # ヒューズホルダ: クリップ2個(パッド列 x=0 / x=23.11)+ 5×20ガラス管(軸=X, 軸高5.5)
    'Fuseholder_Clip-5x20mm_Keystone_3517_Inline_P23.11x6.76mm_D1.70mm_Horizontal': [
        M('FUSE_CLIP_FUC03A', align='pads', dx=-11.555),
        M('FUSE_CLIP_FUC03A', align='pads', dx=+11.555),
        # 円柱は+Z押し出しなのでY軸90度回転でX軸方向に倒す。KiCadのY回転は原点から
        # **-X側**に伸びる向きなので(レンダで確認済)、中心を合わせるため dx=+10。
        M('FUSE_5x20_glass', align='pads', dx=+10.0, dz=5.5, rot=(0.0, 90.0, 0.0)),
    ],

    # ===== C/P-MAIN 用 (2026-07-31 追加) =====
    # microSD Molex 104031-0811: KiCad同梱FPは (model) 行を持つが実体 .step が
    # 同梱されない(= "Could not add 3D model")ので、ここで上書きする。
    # F.Fab bbox 中心は (0.02, -2.00) = カード挿入ガイドを含む位置なので、
    # 本体矩形の中心(0.02, 0.00)へ戻すため dy=+2.0。
    'microSD_HC_Molex_104031-0811': [M('MICROSD_MOLEX_104031', dy=+2.0)],

    # microSD TF-01A (自作FP, 2026-08-03 で Molex から差し替え)。F.Fab が本体外形そのものなので
    # オフセット不要。カード開口は +Y 側。
    'microSD_TF-01A': [M('MICROSD_TF01A')],

    # BNO085 Adafruit 4754: F.Fab(25.90×23.36 ベンダFP実測)中心=FP原点。1x6ソケット2列が y=±8.89、
    # その上(z=8.5)にモジュール(ヘッダ樹脂+本体)が載る。総高 15.60mm。
    'Adafruit_BNO085_4754': [
        M('HDR_SOCKET_1x6_FH', dy=+8.89),
        M('HDR_SOCKET_1x6_FH', dy=-8.89),
        M('BNO085_4754_STACK', dz=8.5),
    ],

    # DS3231 ZS-042 (実測40×20×10): F.Fab(20×40)中心=(0,19)、パッド列は y=0 なので
    # ソケットは dy=-19。モジュールは F.Fab 中心のまま z=8.5 から。総高 18.50mm。
    'DS3231_ZS042': [
        M('HDR_SOCKET_1x6_FH', dy=-19.0),
        M('DS3231_ZS042_STACK', dz=8.5),
    ],

    # Waveshare TTL TO RS485 (C): キャステレーション直付け(基板上面に密着)。
    'Waveshare_TTL_RS485_C': [M('WAVESHARE_RS485_C')],
}

# 3Dモデルが無いままの部品(高さの一次資料が未取得。推測でモデル化しない)。
# 実測またはデータシート入手後に mkmodel3d.PARTS と MODELS へ追加する。
# 2026-07-31: C/P-MAIN の4部品(microSD/BNO085/DS3231/RS485)はモデル化済みで解消。
# MountingHole_* は穴なのでボディ不要(export_3d の gap 一覧には出るが正常)。
PENDING = {}


def _bbox(fp, layer):
    """フットプリント原点基準のbbox中心(mm)。layer='pads' でパッド、他はグラフィック層名。"""
    lo = [1e18, 1e18]
    hi = [-1e18, -1e18]
    if layer == 'pads':
        items = list(fp.Pads())
    else:
        items = [it for it in fp.GraphicalItems()
                 if getattr(it, 'GetLayerName', None) and it.GetLayerName() == layer]
    for it in items:
        bb = it.GetBoundingBox()
        lo[0] = min(lo[0], bb.GetLeft()); hi[0] = max(hi[0], bb.GetRight())
        lo[1] = min(lo[1], bb.GetTop()); hi[1] = max(hi[1], bb.GetBottom())
    if lo[0] > 1e17:
        return None
    return (pcbnew.ToMM((lo[0] + hi[0]) // 2), pcbnew.ToMM((lo[1] + hi[1]) // 2))


def apply(fp, verbose=True):
    """fp に割り当て定義があればモデルを差し替える。差し替えた数を返す。
    **位置決め前(load直後)に呼ぶこと**(GetBoundingBoxをローカル座標として使う)。
    3Dモデルは電気的検証(ERC/netlist/DRC)に一切関与しないので、
    ここで何が起きてもビルドは止めない(例外は警告にして続行する)。"""
    try:
        return _apply(fp)
    except Exception as e:  # noqa: BLE001 - 3D装飾のためにビルドを落とさない
        print('WARN models3d: %s で例外 -> モデル割り当てをスキップ: %s'
              % (fp.GetFPIDAsString(), e))
        return 0


def _apply(fp, verbose=True):
    name = fp.GetFPIDAsString().split(':')[-1]
    spec = MODELS.get(name)
    if not spec:
        if verbose:
            _warn_unresolved(fp, name)
        return 0
    models = fp.Models()
    models.clear()
    n = 0
    for s in spec:
        path = MODELDIR / (s['file'] + '.step')
        if not path.exists():
            print('WARN models3d: %s が無い (mkmodel3d.py を実行) -> %s はモデル無し'
                  % (path.name, name))
            continue
        c = _bbox(fp, s['align'])
        if c is None:
            print('WARN models3d: %s に %s が無い -> パッド基準にフォールバック' % (name, s['align']))
            c = _bbox(fp, 'pads') or (0.0, 0.0)
        m = pcbnew.FP_3DMODEL()
        m.m_Filename = PREFIX + s['file'] + '.step'
        # KiCadの3D座標系はY反転(基板のY下向き -> 3DのY上向き)
        m.m_Offset = pcbnew.VECTOR3D(c[0] + s['dx'], -(c[1] + s['dy']), s['dz'])
        m.m_Rotation = pcbnew.VECTOR3D(*s['rot'])
        m.m_Scale = pcbnew.VECTOR3D(1.0, 1.0, 1.0)
        m.m_Show = True
        models.push_back(m)
        n += 1
    return n


def _warn_unresolved(fp, name):
    """割り当て定義が無く、かつ参照先モデルも実在しない部品を1行で報告する。"""
    if name in PENDING:
        return  # 既知(高さ資料待ち)なので毎回の警告は出さない
    for m in fp.Models():
        f = m.m_Filename.replace('${KICAD10_3DMODEL_DIR}', STDDIR).replace('${KIPRJMOD}', str(HERE))
        if not Path(f.replace('/', os.sep)).exists():
            print('WARN models3d: %s のモデルが見つからない: %s' % (name, Path(f).name))
