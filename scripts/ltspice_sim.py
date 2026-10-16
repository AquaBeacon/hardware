#!/usr/bin/env python3
"""
LTspiceをバッチモードで実行し、.rawの波形から数値指標を取り出すための薄いラッパー。

依存: PyLTSpice (`pip install PyLTSpice --break-system-packages`)
      内部で LTspice本体(GUIアプリ)を subprocess 実行する。LTspiceそのものは
      このスクリプトに同梱されていないので、事前にインストールしておくこと。

想定ワークフロー:
    1. .asc (回路図) をClaudeがテキストとして直接編集する(SYMATTR Valueの書き換え等)
       -> references/ltspice-format.md を参照。
    2. 本スクリプトで `run_batch()` を呼び、GUIを開かずに1回シミュレーションする。
    3. `read_raw()` で結果を取り、`measure_*` 系の関数で数値指標を出す。
    4. 指標がassertを満たさなければ1へ戻って定数を調整。

CLIとしても使える:
    python ltspice_sim.py run circuit.asc
    python ltspice_sim.py measure circuit.raw --trace "V(out)" --metric vpp
    python ltspice_sim.py list circuit.raw          # トレース名一覧
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# LTspice実行ファイルの探索
# ---------------------------------------------------------------------------

_CANDIDATE_PATHS = [
    # Windows
    r"C:\Program Files\ADI\LTspice\LTspice.exe",
    r"C:\Program Files\LTC\LTspiceXVII\XVIIx64.exe",
    r"C:\Program Files (x86)\LTC\LTspiceXVII\XVIIx64.exe",
    # macOS
    "/Applications/LTspice.app/Contents/MacOS/LTspice",
]


def find_ltspice_exe(explicit_path: Optional[str] = None) -> str:
    """LTspice本体のパスを決める。見つからなければ例外を投げる。

    優先順位: 明示指定 > PATH上の`ltspice`/`XVIIx64` > 既知のインストール先。
    """
    if explicit_path:
        p = Path(explicit_path)
        if p.exists():
            return str(p)
        raise FileNotFoundError(f"指定されたLTspiceパスが存在しません: {explicit_path}")

    for name in ("ltspice", "LTspice", "XVIIx64.exe"):
        found = shutil.which(name)
        if found:
            return found

    for cand in _CANDIDATE_PATHS:
        if Path(cand).exists():
            return cand

    raise FileNotFoundError(
        "LTspiceの実行ファイルが見つかりません。--ltspice-path で明示指定するか、"
        "PATHに通してください(参考: references/ltspice-workflow.md)。"
    )


# ---------------------------------------------------------------------------
# バッチ実行
# ---------------------------------------------------------------------------

def run_batch(
    circuit_path: str,
    ltspice_path: Optional[str] = None,
    timeout: float = 120.0,
) -> Path:
    """.asc または .net / .cir をバッチモードで1回シミュレーションし、.rawのパスを返す。

    LTspiceのGUIウィンドウは開かない(-b オプション相当)。既に同名の.rawがあれば
    上書きされる。
    """
    try:
        from PyLTSpice import LTspice
    except ImportError as e:
        raise ImportError(
            "PyLTSpiceが見つかりません。`pip install PyLTSpice --break-system-packages` "
            "を実行してください。"
        ) from e

    circuit = Path(circuit_path)
    if not circuit.exists():
        raise FileNotFoundError(f"回路ファイルが見つかりません: {circuit_path}")

    if ltspice_path:
        LTspice.spice_exe = [ltspice_path]

    rc = LTspice.run(circuit, timeout=timeout)
    if rc != 0:
        log = circuit.with_suffix(".log")
        hint = f"詳細は {log} を確認してください。" if log.exists() else ""
        raise RuntimeError(f"LTspiceの実行が失敗しました(exit={rc})。{hint}")

    raw_path = circuit.with_suffix(".raw")
    if not raw_path.exists():
        raise RuntimeError(f".rawが生成されませんでした: {raw_path}")
    return raw_path


# ---------------------------------------------------------------------------
# 結果読み取り・測定
# ---------------------------------------------------------------------------

def read_raw(raw_path: str):
    """RawReadオブジェクトを返す(PyLTSpice)。トレース名一覧は .get_trace_names()。"""
    from PyLTSpice import RawRead

    return RawRead(raw_path)


def list_traces(raw_path: str) -> list[str]:
    raw = read_raw(raw_path)
    return list(raw.get_trace_names())


def _trace_values(raw_path: str, trace_name: str):
    import numpy as np

    raw = read_raw(raw_path)
    names = raw.get_trace_names()
    if trace_name not in names:
        raise KeyError(
            f"トレース '{trace_name}' が見つかりません。利用可能: {names}"
        )
    trace = raw.get_trace(trace_name)
    data = np.array(trace.get_wave())
    if np.iscomplexobj(data):
        data = np.abs(data)  # AC解析結果は複素数 -> 振幅を使う
    return data


def measure_vpp(raw_path: str, trace_name: str) -> float:
    """Peak-to-peak電圧/電流を返す。"""
    data = _trace_values(raw_path, trace_name)
    return float(data.max() - data.min())


def measure_avg(raw_path: str, trace_name: str) -> float:
    data = _trace_values(raw_path, trace_name)
    return float(data.mean())


def measure_rms(raw_path: str, trace_name: str) -> float:
    import numpy as np

    data = _trace_values(raw_path, trace_name)
    return float(np.sqrt(np.mean(np.square(data))))


def measure_max(raw_path: str, trace_name: str) -> float:
    return float(_trace_values(raw_path, trace_name).max())


def measure_min(raw_path: str, trace_name: str) -> float:
    return float(_trace_values(raw_path, trace_name).min())


def measure_settling_time(
    raw_path: str,
    trace_name: str,
    target: float,
    tolerance: float,
    time_trace: str = "time",
) -> Optional[float]:
    """targetに対してtolerance(絶対値)以内に入り、以後外れなくなる最初の時刻を返す。
    トランジェント解析専用。整定しなければNoneを返す。
    """
    import numpy as np

    raw = read_raw(raw_path)
    t = np.array(raw.get_trace(time_trace).get_wave()).real
    y = _trace_values(raw_path, trace_name)

    inside = np.abs(y - target) <= tolerance
    # 末尾から見て、連続してinsideな区間の開始点を探す
    idx = len(inside) - 1
    if not inside[idx]:
        return None
    while idx > 0 and inside[idx - 1]:
        idx -= 1
    return float(t[idx])


def measure_bandwidth_hz(
    raw_path: str,
    trace_name: str,
    drop_db: float = 3.0,
    freq_trace: str = "frequency",
) -> Optional[float]:
    """AC解析結果からピークゲインより drop_db [dB] 下がる最初の周波数(-3dB帯域端)を返す。"""
    import numpy as np

    raw = read_raw(raw_path)
    f = np.array(raw.get_trace(freq_trace).get_wave()).real
    y = _trace_values(raw_path, trace_name)
    mag_db = 20 * np.log10(np.maximum(y, 1e-30))
    peak_db = mag_db.max()
    below = np.where(mag_db <= peak_db - drop_db)[0]
    if len(below) == 0:
        return None
    return float(f[below[0]])


MEASURES = {
    "vpp": measure_vpp,
    "avg": measure_avg,
    "rms": measure_rms,
    "max": measure_max,
    "min": measure_min,
}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="バッチシミュレーションを1回実行する")
    p_run.add_argument("circuit", help=".asc / .net / .cir ファイル")
    p_run.add_argument("--ltspice-path", default=None)
    p_run.add_argument("--timeout", type=float, default=120.0)

    p_list = sub.add_parser("list", help="トレース名一覧を表示する")
    p_list.add_argument("raw", help=".rawファイル")

    p_measure = sub.add_parser("measure", help="トレースから指標を計算する")
    p_measure.add_argument("raw", help=".rawファイル")
    p_measure.add_argument("--trace", required=True)
    p_measure.add_argument("--metric", choices=list(MEASURES.keys()), required=True)

    args = parser.parse_args(argv)

    if args.cmd == "run":
        raw_path = run_batch(args.circuit, args.ltspice_path, args.timeout)
        print(f"OK: {raw_path}")
    elif args.cmd == "list":
        for name in list_traces(args.raw):
            print(name)
    elif args.cmd == "measure":
        fn = MEASURES[args.metric]
        value = fn(args.raw, args.trace)
        print(value)

    return 0


if __name__ == "__main__":
    sys.exit(main())
