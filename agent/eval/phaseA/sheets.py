"""육안 검증용 컨택트시트 — 클립 전체 스팬 + rotation peak 후보 주변."""
import sys, json
from pathlib import Path
import numpy as np, cv2

sys.path.insert(0, "/home/ho/projects/super-sub.cloud/agent/src")
ROOT = Path("/mnt/d/supersub-phaseA")
FRAMES, OUT = ROOT/"frames", ROOT/"sheets"
OUT.mkdir(exist_ok=True)
TILE = 260

def tile(cid, t, label, mark=None):
    p = FRAMES/cid/f"{t:03d}.jpg"
    img = cv2.imread(str(p)) if p.exists() else None
    if img is None:
        img = np.zeros((int(TILE*0.6), TILE, 3), np.uint8)
    h, w = img.shape[:2]
    img = cv2.resize(img, (TILE, int(h*TILE/w)), interpolation=cv2.INTER_AREA)
    bar = np.zeros((26, TILE, 3), np.uint8)
    col = (0,0,255) if mark == "peak" else ((0,200,255) if mark else (235,235,235))
    cv2.putText(bar, label, (5, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 1, cv2.LINE_AA)
    if mark == "peak":
        cv2.rectangle(img, (0,0), (TILE-1, img.shape[0]-1), (0,0,255), 4)
    return np.vstack([bar, img])

def row(tiles):
    h = max(t.shape[0] for t in tiles)
    return np.hstack([np.vstack([t, np.zeros((h-t.shape[0], TILE, 3), np.uint8)]) for t in tiles])

def sheet(cid, T, peak, extras=None):
    span = [int(round(i*(T-1)/9)) for i in range(10)]
    r1 = row([tile(cid, t, f"{t} ({t/(T-1):.0%})", "peak" if t == peak else None) for t in span])
    rows = [r1]
    if peak is not None:
        near = [t for t in range(peak-4, peak+5) if 0 <= t < T]
        r2 = row([tile(cid, t, f"{t}{' <PEAK' if t==peak else ''}",
                       "peak" if t == peak else "near") for t in near])
        if r2.shape[1] < r1.shape[1]:
            r2 = np.hstack([r2, np.zeros((r2.shape[0], r1.shape[1]-r2.shape[1], 3), np.uint8)])
        rows.append(r2[:, :r1.shape[1]])
    hdr = np.zeros((30, r1.shape[1], 3), np.uint8)
    txt = f"{cid}  T={T}  rotation_peak={peak}" + (f"  {extras}" if extras else "")
    cv2.putText(hdr, txt, (6, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 1, cv2.LINE_AA)
    img = np.vstack([hdr] + rows)
    cv2.imwrite(str(OUT/f"{cid}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 82])

def main():
    import csv
    rows = list(csv.DictReader(open(ROOT/"phaseA_pose.csv")))
    for r in rows:
        cid = r["clip_id"]; T = int(r["frames"])
        pk = r.get("rp_peak_frame")
        peak = int(pk) if pk not in ("", "None", None) else None
        sheet(cid, T, peak, f"pos={r.get('rp_peak_pos')} npeaks={r.get('rp_n_peaks')} "
                            f"bat={r.get('obj_baseball_bat')}")
    print(f"{len(rows)} sheets -> {OUT}")

if __name__ == "__main__":
    main()
