"""KiCad 10 PCB generator (KiCad同梱pythonのpcbnew APIで実行すること).

入力: kicad-cliで出力したネットリスト(.net) + 配置/配線記述
出力: .kicad_pcb (基板外形、部品配置、配線、GNDベタ、シルク)

ネット割当はネットリスト由来なので回路図と常に一致する。
検証は kicad-cli pcb drc で行う。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pcbnew

import models3d  # 3Dモデルが無い部品への簡易ソリッド割り当て表(3D出力用。電気的影響なし)

FPDIR = Path(r"C:\Program Files\KiCad\10.0\share\kicad\footprints")
# プロジェクト内カスタムフットプリント(*.pretty)。標準ライブラリに無いものはここから読む。
LOCAL_FPDIR = Path(__file__).parent / 'footprints'


def load_footprint(fpid):
    """LibName:FpName を標準ライブラリ→プロジェクトlocalの順で探して返す。
    存在しない.pretty へ FootprintLoad するとplug=Noneで例外になるため、先にディレクトリ存在確認。"""
    libname, fpname = fpid.split(':', 1)
    for base in (FPDIR, LOCAL_FPDIR):
        libdir = base / f'{libname}.pretty'
        if libdir.is_dir():
            fp = pcbnew.FootprintLoad(str(libdir), fpname)
            if fp is not None:
                return fp
    return None


def _auto_route(board, board_rect, netmap, track_width,
                grid=0.3, tw=0.3, skip=("GND",), H=0.72, route_first=()):
    """Dijkstra 2層迷路オートルータ。GND以外の全ネットをF.Cu/B.Cu+ビアで配線。
    障害物=全パッド/配線済みトラックをクリアランス込みでグリッドへ焼き込み。"""
    import heapq
    import array as _array
    x0, y0, x1, y1 = board_rect
    nx = int((x1 - x0) / grid) + 1
    ny = int((y1 - y0) / grid) + 1
    NL = 2  # 0=F.Cu 1=B.Cu
    layer_of = {0: pcbnew.F_Cu, 1: pcbnew.B_Cu}
    size = NL * nx * ny

    def ci(x):  # mm -> cell (clamped)
        return x
    def cx(x):
        return min(nx - 1, max(0, int(round((x - x0) / grid))))
    def cy(y):
        return min(ny - 1, max(0, int(round((y - y0) / grid))))
    def idx(l, ix, iy):
        return (l * ny + iy) * nx + ix
    def cxmm(ix):
        return x0 + ix * grid
    def cymm(iy):
        return y0 + iy * grid

    core = _array.array('h', bytes(2 * size))   # ネットid(1..) / 0空 / -1盤外
    halo = _array.array('h', bytes(2 * size))
    # ネットid割付
    netid = {}
    for name in netmap:
        if name and name != 'GND' and not name.startswith('unconnected'):
            netid.setdefault(name, len(netid) + 1)
    netid.setdefault('GND', len(netid) + 1)   # GNDも障害物として焼く
    id2name = {v: k for k, v in netid.items()}

    def stamp(cxc, cyc, netv, rx, ry, layers, margin=H):
        """矩形ハロー: core=|dx|<=rx,|dy|<=ry(実銅), halo=+margin(クリアランス確保)。"""
        icx, icy = cx(cxc), cy(cyc)
        hrx, hry = rx + margin, ry + margin
        rrx, rry = int(hrx / grid) + 1, int(hry / grid) + 1
        crx, cry = rx / grid, ry / grid
        chx, chy = hrx / grid, hry / grid
        for l in layers:
            base = l * ny
            for dy in range(-rry, rry + 1):
                iy = icy + dy
                if iy < 0 or iy >= ny:
                    continue
                ady = abs(dy)
                for dx in range(-rrx, rrx + 1):
                    ix = icx + dx
                    if ix < 0 or ix >= nx:
                        continue
                    adx = abs(dx)
                    i = (base + iy) * nx + ix
                    if adx <= crx and ady <= cry:
                        core[i] = netv
                    if adx <= chx and ady <= chy:
                        h = halo[i]
                        if h == 0:
                            halo[i] = netv
                        elif h != netv:
                            halo[i] = -2

    # 盤外マージン。KiCad既定の基板端クリアランス0.5mmを満たす必要がある:
    #  m=2(0.6mm)だとトラック(0.3幅)で端まで0.45mm、自動ビア(0.8径)で0.2mmしか空かず
    #  copper_edge_clearance違反になる(小型基板で端レーンを使い始めると必ず出る)。
    #  m=4(1.2mm)ならトラック1.05mm/ビア0.8mm確保できる。
    m = 4
    for l in range(NL):
        for iy in range(ny):
            for ix in range(nx):
                if ix < m or ix >= nx - m or iy < m or iy >= ny - m:
                    core[idx(l, ix, iy)] = -1
                    halo[idx(l, ix, iy)] = -1

    # 全パッドを焼き込み + ネット別パッドセル収集
    net_pads = {}   # name -> list of (mmx, mmy, layers-tuple, cellset)。配線の連結単位
    net_snap = {}   # name -> 実パッドのみ。_emit_path のパッド中心スタブ用(併合しない)
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            nm = pad.GetNetname()
            pos = pad.GetPosition()
            px, py = pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)
            bb = pad.GetBoundingBox()   # 回転考慮の軸並行bbox
            rx = pcbnew.ToMM(bb.GetWidth()) / 2.0
            ry = pcbnew.ToMM(bb.GetHeight()) / 2.0
            tht = pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH
            layers = (0, 1) if (tht or (pad.IsOnLayer(pcbnew.F_Cu) and pad.IsOnLayer(pcbnew.B_Cu))) \
                else (0,) if pad.IsOnLayer(pcbnew.F_Cu) else (1,)
            nv = netid.get(nm) if nm else None
            if nv is None:   # NC/未知ネットのパッドも物理銅なので純障害物(-1)として焼く
                stamp(px, py, -1, rx, ry, layers)
                continue
            stamp(px, py, nv, rx, ry, layers)
            # ターゲットセル(coreと同じ矩形領域)
            cells = set()
            icx, icy = cx(px), cy(py)
            rcx, rcy = int(rx / grid), int(ry / grid)
            for l in layers:
                for dy in range(-rcy, rcy + 1):
                    for dx in range(-rcx, rcx + 1):
                        ix, iy = icx + dx, icy + dy
                        if 0 <= ix < nx and 0 <= iy < ny:
                            cells.add((l, ix, iy))
            if not cells:
                cells.add((layers[0], icx, icy))
            net_pads.setdefault(nm, []).append((px, py, layers, cells))
            # _emit_path の snap_stub 用。**実パッドだけ**の表を別に持つ。
            #  併合後の net_pads を渡すと「セルは長いシードトラック / 座標は先頭要素」に
            #  なり、経路端から遠くのパッド中心へ 20mm 級の斜めスタブが引かれて
            #  他ネットを横断する(2026-08-01 CHILD_MAIN で tracks_crossing 37件)。
            net_snap.setdefault(nm, []).append((px, py, layers, set(cells)))

    # 既存(シード)トラックを各ネットの連結起点として取り込む + 障害物化
    for t in board.GetTracks():
        nm = t.GetNetname()
        nv = netid.get(nm)
        if nv is None:
            continue
        if t.Type() == pcbnew.PCB_VIA_T:   # シードビア: 両層connected
            p = t.GetPosition()
            vx, vy = pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)
            # 実際のビア外径で焼く(0.4固定だと 1.1mm 径のシードビアの脇を通されて短絡する)
            # KiCad 10 の PCB_VIA::GetWidth() は layer 引数必須(無いと assert 警告)
            vr = max(0.4, pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)) / 2.0)
            stamp(vx, vy, nv, vr, vr, (0, 1))
            net_pads.setdefault(nm, []).append((vx, vy, (0, 1),
                                                {(0, cx(vx), cy(vy)), (1, cx(vx), cy(vy))}))
            continue
        if t.Type() != pcbnew.PCB_TRACE_T:
            continue
        a, b = t.GetStart(), t.GetEnd()
        ax, ay = pcbnew.ToMM(a.x), pcbnew.ToMM(a.y)
        bx, by = pcbnew.ToMM(b.x), pcbnew.ToMM(b.y)
        l = 0 if t.GetLayer() == pcbnew.F_Cu else 1
        # **実際のトラック幅で焼く。** tw/2(=0.15mm)固定だと電源基板の 2.0mm 幅シードの
        # 脇 0.9mm にルータが線を通してしまい shorting_items になる(2026-08-01 CHILD_PWR で実害)。
        hw = max(tw, pcbnew.ToMM(t.GetWidth())) / 2.0
        cells = set()
        n = max(1, int(((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5 / grid) + 1)
        for s in range(n + 1):
            mx = ax + (bx - ax) * s / n
            my = ay + (by - ay) * s / n
            stamp(mx, my, nv, hw, hw, (l,))
            cells.add((l, cx(mx), cy(my)))
        net_pads.setdefault(nm, []).append((ax, ay, (l,), cells))

    # **既に物理的に繋がっている要素(パッドと、その上から出ているシードトラック等)を併合する。**
    # これをしないとルータが「同じ場所」同士を結ぶ 0.1mm 級の斜め線をパッド脇に足してしまい、
    # 0.5mmピッチIC(MSOP-10等)の隣ピンとクリアランス違反になる
    # (2026-08-01 CHILD_PWR の INA_AL/U_INA で実害。全ネットをseedしても消えなかった)。
    for nm, pads_l in list(net_pads.items()):
        merged = []
        for entry in pads_l:
            e = (entry[0], entry[1], entry[2], set(entry[3]))
            hits = [m for m in merged if e[3] & m[3]]
            if not hits:
                merged.append(e)
                continue
            # 複数に跨って重なることがあるので全部まとめて1つにする
            keep = hits[0]
            keep[3].update(e[3])
            for other in hits[1:]:
                keep[3].update(other[3])
                merged.remove(other)
        net_pads[nm] = merged

    added_t, added_v = 0, 0

    def passable(nv, l, ix, iy):
        i = idx(l, ix, iy)
        c = core[i]
        h = halo[i]
        return (c == 0 or c == nv) and (h == 0 or h == nv)

    # 配線対象ネット(パッド2個以上, GND除外) を bbox 昇順で
    todo = []
    for nm, pads_l in net_pads.items():
        if nm in skip or len(pads_l) < 2:
            continue
        xs = [p[0] for p in pads_l]; ys = [p[1] for p in pads_l]
        bbox = (max(xs) - min(xs)) + (max(ys) - min(ys))
        todo.append((bbox, len(pads_l), nm))
    # bbox昇順(小さい/局所ネット先)。route_first指定ネットは資源枯渇前に最優先で配線
    todo.sort(key=lambda e: (e[2] not in route_first, e[0], e[1], e[2]))

    for _, _, nm in todo:
        nv = netid[nm]
        pads_l = net_pads[nm]
        # 連結集合(pad0のセル) から各padへ順次
        connected = set(pads_l[0][3])
        remaining = list(range(1, len(pads_l)))
        # 各padのターゲットセル集合(高速判定用)
        while remaining:
            target_cells = {}
            for pi in remaining:
                for c in pads_l[pi][3]:
                    target_cells[c] = pi
            # Dijkstra: 複数始点(connected) -> 最寄りtarget
            dist = {}
            pq = []
            for (l, ix, iy) in connected:
                dist[(l, ix, iy)] = 0
                heapq.heappush(pq, (0, l, ix, iy))
            prev = {}
            found = None
            while pq:
                d, l, ix, iy = heapq.heappop(pq)
                if dist.get((l, ix, iy), 1 << 30) < d:
                    continue
                if (l, ix, iy) in target_cells:
                    found = (l, ix, iy)
                    break
                # 同層4近傍
                for dx, dy, in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    jx, jy = ix + dx, iy + dy
                    if 0 <= jx < nx and 0 <= jy < ny and passable(nv, l, jx, jy):
                        nd = d + 1
                        k = (l, jx, jy)
                        if nd < dist.get(k, 1 << 30):
                            dist[k] = nd
                            prev[k] = (l, ix, iy)
                            heapq.heappush(pq, (nd, l, jx, jy))
                # 層変更(ビア)
                ol = 1 - l
                if passable(nv, ol, ix, iy) and passable(nv, l, ix, iy):
                    nd = d + 8
                    k = (ol, ix, iy)
                    if nd < dist.get(k, 1 << 30):
                        dist[k] = nd
                        prev[k] = (l, ix, iy)
                        heapq.heappush(pq, (nd, ol, ix, iy))
            if found is None:
                print(f'  [autoroute] FAILED net {nm} ({len(remaining)} pad remain)')
                break
            # backtrace
            path = [found]
            cur = found
            while cur in prev:
                cur = prev[cur]
                path.append(cur)
            path.reverse()
            # トラック/ビア生成 + 焼き込み
            _emit_path(board, path, nv, id2name[nv], netmap, tw, layer_of,
                       cxmm, cymm, stamp, grid, net_snap.get(nm, ()))
            for c in path:
                connected.add(c)
            hit = target_cells[found]
            for c in pads_l[hit][3]:
                connected.add(c)
            remaining.remove(hit)

    # GNDスティッチングビア: 両層GND可の空きセルに粗いグリッドで配置(ベタ島の橋渡し)
    # スティッチングは孤立ビアを生むため無効(THT GNDパッドがF/B橋渡し、孤立断片は島除去ALWAYSで消える)
    gnv = netid.get('GND')
    if gnv is not None and False:
        def vec2(x, y):
            return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))
        step = max(1, int(6.0 / grid))   # 約6mm間隔
        for iy in range(m + 2, ny - m - 2, step):
            for ix in range(m + 2, nx - m - 2, step):
                ok2 = True
                for l in (0, 1):
                    i = idx(l, ix, iy)
                    if not (core[i] in (0, gnv) and halo[i] in (0, gnv)):
                        ok2 = False
                        break
                if ok2:
                    v = pcbnew.PCB_VIA(board)
                    v.SetPosition(vec2(cxmm(ix), cymm(iy)))
                    v.SetDrill(pcbnew.FromMM(0.4))
                    v.SetWidth(pcbnew.FromMM(0.8))
                    v.SetNet(netmap['GND'])
                    board.Add(v)
                    stamp(cxmm(ix), cymm(iy), gnv, 0.4, 0.4, (0, 1))

    # 統計
    nt = sum(1 for t in board.GetTracks() if t.Type() == pcbnew.PCB_TRACE_T)
    nv2 = sum(1 for t in board.GetTracks() if t.Type() == pcbnew.PCB_VIA_T)
    print(f'  [autoroute] tracks={nt} vias={nv2} nets={len(todo)}')


def _emit_path(board, path, nv, netname, netmap, tw, layer_of,
               cxmm, cymm, stamp, grid, pads_l=()):
    """セル列 path -> PCB_TRACK(直線マージ) + PCB_VIA を追加し、焼き込む。
    始点/終点セルがパッド領域内なら実パッド中心へスタブを追加(丸パッドの非接続対策)。"""
    def vec(x, y):
        return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))

    def snap_stub(cell):
        l, ix, iy = cell
        for (px, py, plys, cells) in pads_l:
            if cell in cells:
                sl = l if l in plys else plys[0]
                t = pcbnew.PCB_TRACK(board)
                t.SetStart(vec(cxmm(ix), cymm(iy)))
                t.SetEnd(vec(px, py))
                t.SetWidth(pcbnew.FromMM(tw))
                t.SetLayer(layer_of[sl])
                t.SetNet(netmap[netname])
                board.Add(t)
                return
    snap_stub(path[0])
    snap_stub(path[-1])
    # セグメント分割: 同層かつ同方向でまとめる
    segs = []   # (layer, (ix0,iy0),(ix1,iy1))
    vias_here = []
    i = 0
    while i < len(path) - 1:
        l, ix, iy = path[i]
        l2, jx, jy = path[i + 1]
        if l2 != l:
            vias_here.append((ix, iy))
            i += 1
            continue
        dx, dy = jx - ix, jy - iy
        # 同方向に伸ばす
        k = i + 1
        while k < len(path):
            lk, kx, ky = path[k]
            if lk != l:
                break
            px, py = path[k - 1][1], path[k - 1][2]
            if (kx - px, ky - py) != (dx, dy):
                break
            k += 1
        end = path[k - 1]
        segs.append((l, (ix, iy), (end[1], end[2])))
        i = k - 1
    for (l, a, b) in segs:
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(vec(cxmm(a[0]), cymm(a[1])))
        t.SetEnd(vec(cxmm(b[0]), cymm(b[1])))
        t.SetWidth(pcbnew.FromMM(tw))
        t.SetLayer(layer_of[l])
        t.SetNet(netmap[netname])
        board.Add(t)
        # 焼き込み(トラック沿い)
        n = max(abs(b[0] - a[0]), abs(b[1] - a[1]))
        for s in range(n + 1):
            ix = a[0] + (b[0] - a[0]) * s // n if n else a[0]
            iy = a[1] + (b[1] - a[1]) * s // n if n else a[1]
            stamp(cxmm(ix), cymm(iy), nv, tw / 2, tw / 2, (l,))
    for (ix, iy) in vias_here:
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(vec(cxmm(ix), cymm(iy)))
        v.SetDrill(pcbnew.FromMM(0.4))
        v.SetWidth(pcbnew.FromMM(0.8))
        v.SetNet(netmap[netname])
        board.Add(v)
        stamp(cxmm(ix), cymm(iy), nv, 0.4, 0.4, (0, 1))


# --- ネットリスト読み込み (最小S式パーサ; kicadgenと同等) ---

def tokenize(text):
    token = re.compile(r'"(?:[^"\\]|\\.)*"|[()]|[^\s()"]+')
    for m in token.finditer(text):
        yield m.group(0)


def parse(tokens):
    stack = [[]]
    for t in tokens:
        if t == '(':
            new = []
            stack[-1].append(new)
            stack.append(new)
        elif t == ')':
            stack.pop()
        else:
            stack[-1].append(t)
    return stack[0]


def load_netlist(path):
    """(components: ref->footprint, nets: netname -> [(ref,pin)]) を返す。"""
    root = parse(tokenize(Path(path).read_text(encoding='utf-8')))[0]
    comps = {}
    nets = {}
    for node in root:
        if not isinstance(node, list) or not node:
            continue
        if node[0] == 'components':
            for c in node[1:]:
                ref = fp = None
                for e in c:
                    if isinstance(e, list) and e:
                        if e[0] == 'ref':
                            ref = e[1].strip('"')
                        elif e[0] == 'footprint':
                            fp = e[1].strip('"')
                comps[ref] = fp
        elif node[0] == 'nets':
            for n in node[1:]:
                name = None
                nodes = []
                for e in n:
                    if isinstance(e, list) and e:
                        if e[0] == 'name':
                            name = e[1].strip('"').lstrip('/')
                        elif e[0] == 'node':
                            ref = pin = None
                            for f in e:
                                if isinstance(f, list) and f:
                                    if f[0] == 'ref':
                                        ref = f[1].strip('"')
                                    elif f[0] == 'pin':
                                        pin = f[1].strip('"')
                            nodes.append((ref, pin))
                nets[name] = nodes
    return comps, nets


def mm(v):
    return pcbnew.FromMM(float(v))


def vec(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


def build_board(out_path, netlist_path, placements, board_rect, tracks=(), vias=(),
                zones=('F.Cu', 'B.Cu'), track_width=0.5, values=None, texts=(),
                seed_tracks=(), seed_vias=(), min_clearance=0.2, route_first=()):
    """
    placements: ref -> (x, y, rot_deg[, 'bottom'])
    board_rect: (x0, y0, x1, y1)
    tracks: (net, layer, width_mm, [(x,y), ...])
    vias:   (net, x, y)
    zones:  GNDベタを張る層のリスト
    values: ref -> value文字列 (シルク用; netlistにValueが無い場合の補完)
    texts:  (text, x, y, layer)
    """
    comps, nets = load_netlist(netlist_path)

    board = pcbnew.CreateEmptyBoard()

    # 銅クリアランス(既定0.2mm)。微細ピッチSMD(0.5mm MSOP等)を載せる基板だけ
    # build()側からmin_clearanceを下げる(JLC最小0.127mm。緩めるだけなので他基板に影響なし)。
    ds = board.GetDesignSettings()
    if min_clearance and abs(min_clearance - 0.2) > 1e-9:
        ds.m_MinClearance = pcbnew.FromMM(min_clearance)
        try:
            board.GetAllNetClasses()['Default'].SetClearance(pcbnew.FromMM(min_clearance))
        except Exception as e:
            print('WARN set clearance:', e)

    # JLCPCB 2層の下限をDRCにも効かせる(環状幅0.13mm / 貫通穴0.2mm)。
    # KiCad既定の環状幅下限は0.10mmなので 0.3/0.5 ビア(環状幅0.10mm)が素通りしていた。
    try:
        ds.m_ViasMinAnnularWidth = pcbnew.FromMM(0.13)
        ds.m_MinThroughDrill = pcbnew.FromMM(0.2)
    except Exception as e:
        print('WARN set via constraints:', e)

    netmap = {}
    for name in nets:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netmap[name] = ni

    padnet = {}
    for name, nodes in nets.items():
        for ref, pin in nodes:
            padnet[(ref, pin)] = name

    # 部品
    for ref, fpid in comps.items():
        if ref.startswith('#'):
            continue
        assert ref in placements, f'placement missing for {ref}'
        assert fpid, f'footprint missing for {ref}'
        fp = load_footprint(fpid)
        assert fp is not None, f'footprint not found: {fpid}'
        # 3Dモデル差し替えは配置/回転より前に行う(bboxをローカル座標として使うため)
        models3d.apply(fp)
        fp.SetReference(ref)
        if values and ref in values:
            fp.SetValue(values[ref])
        pl = placements[ref]
        x, y, rot = pl[0], pl[1], pl[2]
        board.Add(fp)
        if len(pl) > 3 and pl[3] == 'bottom':
            fp.Flip(vec(x, y), False)
        fp.SetPosition(vec(x, y))
        fp.SetOrientationDegrees(rot)
        for pad in fp.Pads():
            key = (ref, pad.GetPadName())
            if key in padnet:
                pad.SetNet(netmap[padnet[key]])
    # 外形
    x0, y0, x1, y1 = board_rect
    for (ax, ay, bx, by) in [(x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)]:
        seg = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(vec(ax, ay))
        seg.SetEnd(vec(bx, by))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(mm(0.1))
        board.Add(seg)

    layer_id = {'F.Cu': pcbnew.F_Cu, 'B.Cu': pcbnew.B_Cu}

    # パッド位置解決ヘルパ: 'REF.PAD' -> (x, y) [mm]
    pads = {}
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            p = pad.GetPosition()
            pads[f'{fp.GetReference()}.{pad.GetPadName()}'] = (
                pcbnew.ToMM(p.x), pcbnew.ToMM(p.y))

    def resolve(pt):
        if isinstance(pt, str):
            return pads[pt]
        return pt

    # オートルータ (tracks=='auto'): Dijkstra 2層迷路配線。GNDはベタなので配線しない。
    if tracks == 'auto':
        # シード配線/ビア(微細ピッチのエスケープ等)を先に敷いてから自動配線に引き継ぐ
        for (netname, layer, width, pts) in (seed_tracks or []):
            pts = [resolve(p) for p in pts]
            for (a, b) in zip(pts, pts[1:]):
                t = pcbnew.PCB_TRACK(board)
                t.SetStart(vec(*a)); t.SetEnd(vec(*b))
                t.SetWidth(mm(width or track_width))
                t.SetLayer(layer_id[layer]); t.SetNet(netmap[netname])
                board.Add(t)
        for sv in (seed_vias or []):
            netname, sx, sy = sv[0], sv[1], sv[2]
            # 既定 0.3/0.6 = 環状幅0.15mm。JLCPCB下限0.13mmを満たす最小サイズ。
            # (0.3/0.5だと環状幅0.10mmで規格外。KiCad DRCは既定で環状幅を見ないので通ってしまう)
            drill, w = (sv[3], sv[4]) if len(sv) > 3 else (0.3, 0.6)
            (sx, sy) = resolve((sx, sy)) if isinstance(sx, str) else (sx, sy)
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(vec(sx, sy)); v.SetDrill(mm(drill)); v.SetWidth(mm(w))
            v.SetNet(netmap[netname]); board.Add(v)
        _auto_route(board, board_rect, netmap, track_width, route_first=route_first)
        tracks = []
        vias = () if vias == 'auto' else vias

    # 配線
    for (netname, layer, width, pts) in tracks:
        pts = [resolve(p) for p in pts]
        for (a, b) in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(vec(*a))
            t.SetEnd(vec(*b))
            t.SetWidth(mm(width or track_width))
            t.SetLayer(layer_id[layer])
            t.SetNet(netmap[netname])
            board.Add(t)
    for (netname, x, y) in vias:
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(vec(x, y))
        v.SetDrill(mm(0.4))
        v.SetWidth(mm(0.8))
        v.SetNet(netmap[netname])
        board.Add(v)

    # GNDベタ
    for lname in zones:
        z = pcbnew.ZONE(board)
        z.SetLayer(layer_id[lname])
        if 'GND' in netmap:
            z.SetNet(netmap['GND'])
        chain = pcbnew.SHAPE_LINE_CHAIN()
        for (px, py) in [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]:
            chain.Append(mm(px), mm(py))
        chain.SetClosed(True)
        z.Outline().AddOutline(chain)
        z.SetLocalClearance(mm(0.25))
        z.SetMinThickness(mm(0.13))   # 細い接続ネックを残しGND孤立島を主ベタへ繋ぐ(5mil, 製造可)
        z.SetThermalReliefGap(mm(0.4))
        z.SetThermalReliefSpokeWidth(mm(0.5))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)   # ソリッド接続(starved_thermal回避)
        try:   # 主GNDから切り離された孤立ベタ断片(パッド無しスリバ)を除去
            z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        except Exception:
            pass
        board.Add(z)

    for (txt, x, y, layer) in texts:
        t = pcbnew.PCB_TEXT(board)
        t.SetText(txt)
        t.SetPosition(vec(x, y))
        t.SetLayer(layer_id.get(layer, pcbnew.F_SilkS) if isinstance(layer, str) else layer)
        if layer == 'F.SilkS' or layer is None:
            t.SetLayer(pcbnew.F_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(mm(1.2), mm(1.2)))
        board.Add(t)

    pcbnew.SaveBoard(str(out_path), board)

    # ZONE_FILLERはCreateEmptyBoardで作った直後のボードでクラッシュすることがあるため
    # 保存->再読込->フィル->再保存の順で行う
    board2 = pcbnew.LoadBoard(str(out_path))
    filler = pcbnew.ZONE_FILLER(board2)
    filler.Fill(board2.Zones())
    pcbnew.SaveBoard(str(out_path), board2)
    return board2


if __name__ == '__main__':
    # スモークテスト: pcb/_test/test.net の R1,R2 のみ配置した小基板
    here = Path(__file__).parent
    outdir = here / '_test'
    placements = {
        'R1': (10, 10, 0), 'R2': (10, 20, 0), 'R3': (10, 30, 0), 'R4': (10, 40, 0),
        'D1': (30, 10, 0), 'U1': (30, 25, 0),
    }
    build_board(outdir / 'testgen.kicad_pcb', outdir / 'test.net', placements,
                (0, 0, 55, 50))
    print('board written')
