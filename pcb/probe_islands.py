# -*- coding: ascii -*-
"""GND zone island prober: locate isolated GND fill islands and propose safe
GND stitch-via spots inside them.

Usage (KiCad python required):
  & "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" -u pcb\\probe_islands.py pcb\\CHILD_MAIN\\CHILD_MAIN.kicad_pcb

Background: kicad-cli DRC reports "zone unconnected" at (0,0) so the island
location is unknown. This walks zone.GetFilledPolysList() outlines and counts
contained GND vias / THT pads; outlines containing none are isolated islands
(an SMD-pad-only island is still isolated: pad+island form a floating cluster).
For each island it then proposes via spots: candidates are ranked by distance
to non-GND copper FIRST (cheap), and the expensive SHAPE_POLY_SET.Contains is
only called on the best few (full-grid Contains takes >10min on dense boards).
Add the printed spots to build_*.py seed_vias as ('GND', x, y).
"""
import math
import sys

import pcbnew

MM = pcbnew.FromMM


def main(path):
    b = pcbnew.LoadBoard(path)

    gnd_vias, tht, smd = [], [], {pcbnew.F_Cu: [], pcbnew.B_Cu: []}
    segs, pts = [], []          # obstacles: (x1,y1,x2,y2,halfw,is_gnd) / (x,y,r,is_gnd)
    for t in b.GetTracks():
        g = (t.GetNetname() == 'GND')
        if t.Type() == pcbnew.PCB_VIA_T:
            p = t.GetPosition()
            if g:
                gnd_vias.append((p.x, p.y))
            pts.append((p.x, p.y, MM(0.4), g))
        elif t.Type() == pcbnew.PCB_TRACE_T:
            a, e = t.GetStart(), t.GetEnd()
            segs.append((a.x, a.y, e.x, e.y, t.GetWidth() / 2, g))
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            p = pad.GetPosition()
            bb = pad.GetBoundingBox()
            g = (pad.GetNetname() == 'GND')
            pts.append((p.x, p.y, max(bb.GetWidth(), bb.GetHeight()) / 2, g))
            if not g:
                continue
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                tht.append((p.x, p.y))
            else:
                for l in (pcbnew.F_Cu, pcbnew.B_Cu):
                    if pad.IsOnLayer(l):
                        smd[l].append((p.x, p.y))

    def clearance(x, y):
        """distance from (x,y) to nearest non-GND copper edge (through-via view)."""
        dmin = 10 ** 12
        for (a1, b1, a2, b2, hw, g) in segs:
            if g:
                continue
            dx, dy = a2 - a1, b2 - b1
            L2 = dx * dx + dy * dy
            if L2 == 0:
                d = math.hypot(x - a1, y - b1) - hw
            else:
                t = max(0.0, min(1.0, ((x - a1) * dx + (y - b1) * dy) / L2))
                d = math.hypot(x - (a1 + t * dx), y - (b1 + t * dy)) - hw
            if d < dmin:
                dmin = d
        for (px, py, r, g) in pts:
            if g:
                continue
            d = math.hypot(x - px, y - py) - r
            if d < dmin:
                dmin = d
        return dmin

    zones = [z for z in b.Zones() if z.GetNetname() == 'GND']
    n_island = 0
    for z in zones:
        for lname, l in (('F.Cu', pcbnew.F_Cu), ('B.Cu', pcbnew.B_Cu)):
            if not z.IsOnLayer(l):
                continue
            poly = z.GetFilledPolysList(l)
            for i in range(poly.OutlineCount()):
                bb = poly.Outline(i).BBox()

                def cnt(lst):
                    return sum(1 for (x, y) in lst
                               if poly.Contains(pcbnew.VECTOR2I(int(x), int(y)), i))
                nv, nt = cnt(gnd_vias), cnt(tht)
                x0, y0 = pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop())
                x1, y1 = pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom())
                if nv + nt > 0:
                    print('%s out%d ok: bbox=(%.1f,%.1f)-(%.1f,%.1f) vias=%d tht=%d'
                          % (lname, i, x0, y0, x1, y1, nv, nt))
                    continue
                n_island += 1
                print('%s out%d ISLAND: bbox=(%.1f,%.1f)-(%.1f,%.1f) smd=%d'
                      % (lname, i, x0, y0, x1, y1, cnt(smd[l])))
                # propose stitch-via spots
                cands = []
                step = MM(0.5)
                y = bb.GetTop() + step
                while y < bb.GetBottom():
                    x = bb.GetLeft() + step
                    while x < bb.GetRight():
                        d = clearance(x, y)
                        if d > MM(0.75):
                            cands.append((d, x, y))
                        x += step
                    y += step
                cands.sort(reverse=True)
                n = 0
                for (d, x, y) in cands:
                    if poly.Contains(pcbnew.VECTOR2I(x, y), i):
                        print("  via spot: ('GND', %.2f, %.2f)  # clr=%.2fmm"
                              % (pcbnew.ToMM(x), pcbnew.ToMM(y), pcbnew.ToMM(int(d))))
                        n += 1
                        if n >= 3:
                            break
                if n == 0:
                    print('  NO SPOT (%d candidates failed Contains; relax clearance?)'
                          % len(cands))
    print('islands: %d' % n_island)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else
         r'pcb\CHILD_MAIN\CHILD_MAIN.kicad_pcb')
