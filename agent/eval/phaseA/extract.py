"""Phase A — production pose pipeline을 READ-ONLY로 39클립에 실행하고 캐시한다.

production code는 import만 한다. 수정하지 않는다.
캐시: keypoints/objects(npz) + 샘플링 프레임(JPEG 480px, 육안 검증용).
"""
import sys, time, json, os
from pathlib import Path
import numpy as np, cv2

sys.path.insert(0, "/home/ho/projects/super-sub.cloud/agent/src")
from supersub_agent import pose

ROOT = Path("/mnt/d/supersub-phaseA")
CLIPS, CACHE, FRAMES = ROOT/"clips", ROOT/"cache", ROOT/"frames"
CACHE.mkdir(exist_ok=True); FRAMES.mkdir(exist_ok=True)

clips = sorted(CLIPS.glob("*.mp4"))
print(f"{len(clips)} clips", flush=True)
for i, p in enumerate(clips, 1):
    cid = p.stem
    npz = CACHE/f"{cid}.npz"
    if npz.exists():
        print(f"[{i}/{len(clips)}] skip {cid}", flush=True); continue
    t0 = time.time()
    try:
        # observe=False — 오프라인 평가는 서비스 입력이 아니다. 기본값이 True라
        # 그냥 두면 39클립이 서비스 입력 관측 sink에 쌓여 다중인원 노출·fps
        # 분포를 오염시킨다. 추출 결과(keypoints·objects·fps)에는 영향이 없다.
        r = pose.extract_keypoints(str(p), target_fps=pose.DEFAULT_TARGET_FPS, observe=False)
    except Exception as e:
        print(f"[{i}/{len(clips)}] FAIL {cid}: {type(e).__name__}: {e}", flush=True)
        np.savez_compressed(CACHE/f"{cid}.ERROR.npz", err=str(e)); continue
    np.savez_compressed(
        npz, keypoints=r.keypoints, source_fps=r.source_fps, sampled_fps=r.sampled_fps,
        **{f"obj_{k}": v for k, v in r.objects.items()},
    )
    fd = FRAMES/cid; fd.mkdir(exist_ok=True)
    # PoseResult는 프레임을 들고 있지 않다 — 저장 직전에 다시 디코딩한다.
    # read_frames가 결정적이라 추출 때 본 것과 같은 프레임·같은 순서다.
    for t, fr in enumerate(r.load_frames()):
        h, w = fr.shape[:2]
        if w > 480:
            fr = cv2.resize(fr, (480, int(h*480/w)), interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(fd/f"{t:03d}.jpg"), fr, [cv2.IMWRITE_JPEG_QUALITY, 80])
    print(f"[{i}/{len(clips)}] {cid} {r.keypoints.shape[0]}f {time.time()-t0:.0f}s "
          f"objs={sorted(r.objects)}", flush=True)
print("EXTRACT DONE", flush=True)
