"""CHILD_PWR / PARENT_PWR 検証スクリプト共通ヘルパ。

LTspiceの.raw読み出し + 時間窓つき測定 + PASS/FAIL集計。
定格値は各データシート実値(sim/notes.md「2026-07-23 PWR基板」節に出典を記載)。
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import ltspice_sim as lt  # noqa: E402

EXE = r'C:\Users\ryupc\AppData\Local\Programs\ADI\LTspice\LTspice.exe'
ROOT = Path(__file__).resolve().parents[1]

# --- 部品定格 (データシート実値) ---------------------------------------
Q1_VDSS, Q1_VGSS, Q1_ID = 60.0, 20.0, 20.0     # 2SJ349 (Toshiba)
Q1_RDSON_MAX = 0.045                            # @|VGS|=10V
Q2_VDSS, Q2_VGSS, Q2_ID = 100.0, 20.0, 50.0    # TK7R4A10PL (Toshiba)
TVS_VRWM, TVS_VBR_MIN, TVS_IFSM = 15.0, 16.7, 100.0   # SMBJ15A
LXDC55_VIN_MIN, LXDC55_VIN_MAX, LXDC55_IOUT = 6.0, 14.0, 1.5
NJU7223_IOUT, NJU7223_VIN_MAX, NJU7223_DROP = 0.5, 18.0, 0.4
NJU7223_RTH_JA = 65.0                           # TO-220F 放熱器なし実力値[degC/W]
FUSE_I2T_FAST, FUSE_I2T_NORM, FUSE_I2T_SLOW = 5.0, 15.0, 40.0   # 5x20 3A 概算
SW_TOGGLE_I = 3.0                               # 秋月g104028 トグル 28VDC/3A


def run(cir_name: str) -> str:
    """バッチ実行。.rawのmtimeが更新されたことを必ず確認する。

    LTspiceはネットリストのパースに失敗しても rc=0 で返し、古い .raw が
    残ったままになる(sim/notes.md「ハマりどころ」)。ここで検出する。
    """
    cir = ROOT / 'LTspice' / cir_name
    raw_path = cir.with_suffix('.raw')
    before = raw_path.stat().st_mtime_ns if raw_path.exists() else -1
    out = str(lt.run_batch(str(cir), ltspice_path=EXE))
    after = Path(out).stat().st_mtime_ns
    assert after != before, f'{raw_path.name} が更新されていない(LTspiceのパース失敗の可能性)'
    return out


def load(raw_path: str):
    raw = lt.read_raw(raw_path)
    t = np.abs(np.asarray(raw.get_trace('time').get_wave(0), dtype=float))
    return raw, t


def wv(raw, name: str) -> np.ndarray:
    return np.asarray(raw.get_trace(name).get_wave(0)).real


def wmax(raw, t, name, t0=None, t1=None) -> float:
    return float(_slice(wv(raw, name), t, t0, t1).max())


def wmin(raw, t, name, t0=None, t1=None) -> float:
    return float(_slice(wv(raw, name), t, t0, t1).min())


def wavg(raw, t, name, t0, t1) -> float:
    return float(_slice(wv(raw, name), t, t0, t1).mean())


def _slice(y, t, t0, t1):
    m = np.ones_like(t, dtype=bool)
    if t0 is not None:
        m &= (t >= t0)
    if t1 is not None:
        m &= (t <= t1)
    if not m.any():
        raise ValueError(f'時間窓に点がない: {t0}..{t1}')
    return y[m]


def tcross(raw, t, name, level) -> float:
    """traceが初めてlevel以上になる時刻。到達しなければ nan。"""
    y = wv(raw, name)
    idx = np.nonzero(y >= level)[0]
    return float(t[idx[0]]) if len(idx) else float('nan')


class Checks:
    """PASS/FAILを集計して最後にまとめて落とす(1件ずつ止めない)。"""

    def __init__(self, title):
        self.title = title
        self.rows = []

    def add(self, name, ok, detail):
        self.rows.append((name, bool(ok), detail))

    def le(self, name, value, limit, unit='', note=''):
        self.add(name, value <= limit, f'{value:.4g}{unit} <= {limit:.4g}{unit} {note}'.rstrip())
        return value

    def ge(self, name, value, limit, unit='', note=''):
        self.add(name, value >= limit, f'{value:.4g}{unit} >= {limit:.4g}{unit} {note}'.rstrip())
        return value

    def between(self, name, value, lo, hi, unit='', note=''):
        self.add(name, lo <= value <= hi,
                 f'{lo:.4g} <= {value:.4g}{unit} <= {hi:.4g} {note}'.rstrip())
        return value

    def info(self, name, detail):
        self.rows.append((name, None, detail))

    def report(self) -> bool:
        print(f'\n--- {self.title} ---')
        for name, ok, detail in self.rows:
            mark = 'INFO' if ok is None else ('PASS' if ok else 'FAIL')
            print(f'  [{mark}] {name:34s} {detail}')
        return all(ok for _, ok, _ in self.rows if ok is not None)
