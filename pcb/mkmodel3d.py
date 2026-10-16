"""3Dモデル(STEP)が存在しない部品用の簡易ソリッドを生成する。

FreeCAD/OCC が無い環境なので、**KiCad自身をSTEPライタとして使う**:
  外形(Edge.Cuts)= 部品の水平断面 / 板厚 = 部品高さ のダミー基板を作り、
  `kicad-cli pcb export step --board-only` で押し出しソリッドを書き出す。
STLは KiCad の STEPエクスポータが読まない ("No model for filename") ため使えない。

生成物は `footprints/3dmodels/*.step`。部品への割り当ては `models3d.py` の表で行う。
座標系: 断面は原点中心(x右/y上)、Zは 0(上面)〜 -h。models3d 側で offset z=+h して
基板上面に載せる(KiCad 3Dの +Z は基板上面から上向き)。

使い方(KiCad同梱pythonが必須 = pcbnew依存):
  & "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" -u pcb\\mkmodel3d.py
"""
import math
import re
import subprocess
import sys
from pathlib import Path

import pcbnew

KICAD_CLI = r'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe'
HERE = Path(__file__).parent
OUT = HERE / 'footprints' / '3dmodels'
TMP = HERE / '_3dtmp'


def _outline(board, shape):
    """shape: ('rect', w, d) 原点中心 / ('circle', dia) / ('poly', [(x,y),...])"""
    kind = shape[0]
    if kind == 'rect':
        w, d = shape[1], shape[2]
        pts = [(-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)]
    elif kind == 'poly':
        pts = list(shape[1])
    elif kind == 'circle':
        # 円は多角形近似せず gr_circle で出す(OCCが真円のシリンダにしてくれる)
        c = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_CIRCLE)
        c.SetCenter(pcbnew.VECTOR2I(0, 0))
        c.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(shape[1] / 2.0), 0))
        c.SetLayer(pcbnew.Edge_Cuts)
        c.SetWidth(pcbnew.FromMM(0.05))
        board.Add(c)
        return
    else:
        raise ValueError(kind)
    for i in range(len(pts)):
        ax, ay = pts[i]
        bx, by = pts[(i + 1) % len(pts)]
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(ax), pcbnew.FromMM(ay)))
        s.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(bx), pcbnew.FromMM(by)))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(pcbnew.FromMM(0.05))
        board.Add(s)


# KiCadは板厚から銅箔ぶん(実測0.09mm)を差し引いた誘電体だけをボディとして出すので、
# 指定高さちょうどのソリッドにするには板厚を+0.09mmしておく(生成後にassertで確認)。
Z_COMP = 0.09


def solid(name, shape, height):
    """押し出しソリッドを footprints/3dmodels/<name>.step に生成し、実測bboxを返す。"""
    OUT.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(exist_ok=True)
    tmp_pcb = TMP / (name + '.kicad_pcb')
    board = pcbnew.CreateEmptyBoard()
    board.GetDesignSettings().SetBoardThickness(pcbnew.FromMM(height + Z_COMP))
    _outline(board, shape)
    pcbnew.SaveBoard(str(tmp_pcb), board)

    step = OUT / (name + '.step')
    p = subprocess.run([KICAD_CLI, 'pcb', 'export', 'step', '--board-only', '--no-optimize-step',
                        '-f', '-o', str(step), str(tmp_pcb)],
                       capture_output=True, text=True, errors='replace')
    log = (p.stdout or '') + (p.stderr or '')
    if not step.exists():
        print('  [FAIL] %s: %s' % (name, log.strip()))
        return None
    bb = bbox(step)
    zh = bb[5] - bb[2]
    assert abs(zh - height) < 0.03, '%s: z=%.3f want %.3f (Z_COMP要調整)' % (name, zh, height)
    assert abs(bb[2]) < 0.03, '%s: 下面がz=0でない (z0=%.3f)' % (name, bb[2])
    print('  [ OK ] %-28s h=%5.2f  bbox x[%.2f %.2f] y[%.2f %.2f] z[%.2f %.2f]  %6.1f KB'
          % (name, height, bb[0], bb[3], bb[1], bb[4], bb[2], bb[5], step.stat().st_size / 1024))
    return bb


def bbox(step_path):
    """STEPのCARTESIAN_POINTからbboxを出す(円は制御点しか見ないので円弧分は概算)。"""
    txt = step_path.read_text(encoding='utf-8', errors='replace')
    lo = [1e9] * 3
    hi = [-1e9] * 3
    for m in re.finditer(r'CARTESIAN_POINT\(\s*\'[^\']*\',\s*\(([^)]*)\)\s*\)', txt):
        v = [float(x) for x in m.group(1).split(',')]
        if len(v) != 3:
            continue
        for i in range(3):
            lo[i] = min(lo[i], v[i])
            hi[i] = max(hi[i], v[i])
    return tuple(lo) + tuple(hi)


# ---------------------------------------------------------------------------
# 部品ごとの簡易ソリッド定義。**寸法は全てデータシート実値**(出典は下記コメント/models3d.py)。
# (name, shape, height)   shape: ('rect', X, Y) / ('circle', dia)
# X/Y は「フットプリントのローカル座標系での向き」。押し出しは常に +Z。
PARTS = [
    # --- Cosland 2MD1 トグルSW (datasheets/SW_Toggle_Cosland_2MD1_g104028.pdf, DWG 2MD1T1B4VS2QES)
    #     ケース 8.94(H) / 正面9.14 × 側面10.16、ブッシング ø4.95×5.59、レバー ø2.54×9.00。
    #     X=10.16 をパッド2列(5.08間隔)方向に取る。総高 8.94+5.59+9.00 = 23.53mm。
    ('SW_2MD1_case',      ('rect', 10.16, 9.14), 8.94),
    ('SW_2MD1_bushing',   ('circle', 4.95), 5.59),
    ('SW_2MD1_lever',     ('circle', 2.54), 9.00),
    # --- AMASS XT30PW-M/-F (datasheets/XT30PW-M_akizuki_117949.pdf)
    #     DS外形 14.00×13.30(バレル/取付タブ含む)、高さ 5.20。XYはKiCad FPのF.Fab
    #     (13.40×11.00 = ハウジング)を使い、FP原点との相対位置を崩さない。
    ('XT30PW_body',       ('rect', 13.40, 11.00), 5.20),
    # --- 秋月 AE-MYMGK00506ERSR-5V0 (datasheets/MYMGK_akizuki_AE-manual.pdf 基板28.5×16mm)
    #     高さ = ピンヘッダ2.5 + 基板1.6 + Murata MYMGK00506ERSR 5.0max
    #     (datasheets/MYMGK00506ERSR_datasheet.pdf: 9.0×7.5×5.0max) = 9.1mm。
    ('MYMGK_AE_stack',    ('rect', 28.50, 16.00), 9.10),
    # --- 秋月 AE-LXDC55-5V0 (datasheets/LXDC55_akizuki_AE-LXDC55-5V0.pdf)
    #     **モジュール基板 11 × 25mm を SIP3 で「縦挿し」する**部品。
    #     25mm が高さ方向、11mm がピン列(2.54×3)方向。厚みは実装部品込みで 5mm 見込み。
    #     1x03 ピンソケット(8.5)の上に載るので **総高 8.5 + 25 = 33.5mm**。
    #     ★これを入れるまで C-PWR の 3D 出力にはソケット(8.5)しか出ておらず、
    #       mech.stl の最大高さ 23.52mm が実物より 10mm 低く出ていた(2026-08-01 発見)。
    ('PINSOCK_1x03_FH',   ('rect', 2.50, 7.62), 8.50),
    ('LXDC55_AE_body',    ('rect', 5.00, 11.00), 25.00),
    # --- FUC-03A ヒューズクリップ + 5×20ガラス管 (datasheets/FuseHolder_FUC-03A_akizuki.pdf)
    #     FUC-03A: A=6.4(ヒューズ軸と直交) E=6.3(軸方向) B=8.8(高さ) C=5.5REF(ヒューズ軸高さ)
    ('FUSE_CLIP_FUC03A',  ('rect', 6.30, 6.40), 8.80),
    ('FUSE_5x20_glass',   ('circle', 5.00), 20.00),
    # --- Bourns 3386P 半固定VR (datasheets/Bourns_3386_trimmer.pdf: 9.53×9.53×4.83)
    ('POT_3386P_body',    ('rect', 9.53, 9.53), 4.83),
    # --- Bourns TC33X SMD半固定VR (datasheets/Bourns_TC33X_trimmer.pdf: 3.8×3.0, H=1.2)
    ('POT_TC33X_body',    ('rect', 3.80, 3.00), 1.20),

    # ===== C/P-MAIN 用 (2026-07-31 追加) =====
    # --- microSD Molex 104031-0811 (KiCad同梱FPの descr が Molex Sales Drawing
    #     1040310811_sd.pdf を引いて "1.42mm Height" と明記。Newark/Farnell/RS の
    #     製品スペックも 1.42mm で一致)。XYはFPのF.Fab本体矩形 11.95×11.40
    #     (F.Fabのy<-5.7 はカード挿入ガイドの作図なので本体には含めない)。
    ('MICROSD_MOLEX_104031', ('rect', 11.95, 11.40), 1.42),
    # --- microSD TF-01A (push-push, LCSC C91145)。datasheets/microSD_TF-01A_...pdf の
    #     PCB Layout と側面図から: 本体 14.85 x 13.42、基板上面からの高さ **1.85mm**
    #     (JLCPCB 部品ページの "1.85mm height above board" と一致)。
    ('MICROSD_TF01A', ('rect', 14.85, 13.42), 1.85),
    # --- 2.54mm メスピンソケット 1x6 (datasheets/PinSocket_FH_1x00SG_akizuki.pdf)
    #     "Insulator 8.5mm, Contacts 3.0mm (PCB Dip)" / 1x6 の全長 Dim.B = 15.74mm、
    #     ハウジング厚み 2.5mm(秋月 g103077 商品仕様)。DS3231・BNO085 の土台。
    ('HDR_SOCKET_1x6_FH', ('rect', 15.74, 2.50), 8.50),
    # --- Adafruit BNO085 4754 モジュール本体。
    #     **2026-07-31: XY をベンダ提供 KiCad FP(pcb/datasheets/4754.zip の MODULE_4754)の
    #     実アウトライン 25.90 × 23.36mm に更新**(旧 25.4×22.86 は 1.0×0.9inch の丸め値)。
    #     高さ = オスピンヘッダ樹脂 2.5(2.54mmヘッダ標準値) + モジュール4.6
    #     (Adafruit公式 Product Dimensions 25.6×22.7×4.6 の Z) = 7.10。
    #     ソケット上面(z=8.5)から生やすので総高 8.5+7.1 = 15.60mm。
    #     ※zip 同梱の 4754.step を使えばより正確だが、原点/向きの整合が必要なため簡易ソリッドのまま。
    ('BNO085_4754_STACK', ('rect', 25.90, 23.36), 7.10),
    # --- DS3231 ZS-042 モジュール本体 (**2026-07-31 実測: 40 × 20 × 10mm**)。
    #     向き: **40mm 軸はピン列と直交**(スルーホール列から 40mm 伸びる)、
    #     ピン列方向が 20mm。FPローカルでは X=ピン列方向=20 / Y=伸びる方向=40。
    #     高さ 10mm は**ピン先端まで含む実測値**。ソケット(8.5)の上面から丸ごと積んで
    #     総高 18.50mm としている(ピンがソケットに刺さる分だけ実物は下がるので安全側。
    #     オスヘッダの挿入量が決まれば最大 6mm 下げられる)。
    ('DS3231_ZS042_STACK', ('rect', 20.00, 40.00), 10.00),
    # --- Waveshare TTL TO RS485 (C) (Waveshare wiki 機械図: 42.8×15.2×**4.75**mm。
    #     FPの descr に 2025-07 照合済みと記録あり)。キャステレーション直付け = dz 0。
    ('WAVESHARE_RS485_C', ('rect', 42.80, 15.20), 4.75),
]


def main():
    only = set(sys.argv[1:])
    print('== simple STEP solids -> %s' % OUT)
    n = 0
    for name, shape, h in PARTS:
        if only and name not in only:
            continue
        if solid(name, shape, h):
            n += 1
    for f in TMP.glob('*'):
        f.unlink()
    if TMP.exists():
        TMP.rmdir()
    print('%d model(s) written' % n)


if __name__ == '__main__':
    main()
