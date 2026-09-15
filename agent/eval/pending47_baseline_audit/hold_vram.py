"""VRAM 을 GiB 단위로 잡고 잔다 (미결 ho 47번 3회차 · 점유 프로세스).

🔴 **계산을 하지 않는다** — 메모리 말고 다른 변수를 섞지 않으려는 것이다.
"""
import sys
import time

import torch

gib = float(sys.argv[1])
n = int(gib * (1024 ** 3) / 4)          # float32
x = torch.empty(n, dtype=torch.float32, device="cuda")
free, total = torch.cuda.mem_get_info(0)
print(f"{gib} GiB 점유 · 남은 여유 {free} / {total}", flush=True)
time.sleep(float(sys.argv[2]) if len(sys.argv) > 2 else 600)
