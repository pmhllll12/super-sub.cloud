/**
 * 사람 하나의 **생김새**를 색으로 요약한다.
 *
 * ## 🔴 회색조 무늬 비교를 버린 이유
 *
 * 처음에는 상자 안 무늬를 회색조로 떠서 정규화 상호상관으로 비교했다. 그런데
 * **이 영상에서 사람을 가르는 것은 유니폼 색**이다 — 흰 조끼 · 검은 유니폼 ·
 * 파란 셔츠. 회색으로 바꾸는 순간 그 정보가 통째로 사라지고, 남은 것은 "밝은
 * 세로 덩어리" 뿐이라 누구든 서로 닮아 보인다. 실제로 박스가 지나가던 다른
 * 사람에게 옮겨 붙었다.
 *
 * 게다가 무늬 비교는 **자리가 어긋나면 무너진다.** 사람은 팔다리를 움직이고
 * 돌아서고 흐려지는데, 그때마다 같은 사람인데도 점수가 떨어져 "놓쳤다" 가 됐다.
 *
 * ## 그래서 색 히스토그램이다
 *
 * 몸통 부분의 색 분포만 센다. **어디에 무엇이 있는지는 안 본다** — 그래서
 * 팔을 들든 돌아서든 흐리든 같은 사람이면 비슷하게 나온다. 추적기에서 쓰는
 * 생김새는 딱 이 성질이어야 한다.
 *
 * 🔴 색은 **RGB 가 아니라 색도(chromaticity)** 로 센다. `r/(r+g+b)` 처럼
 * 밝기로 나누면 그늘에 들어가도 같은 색으로 읽힌다 — 코트에는 그늘과 역광이
 * 섞여 있어서 RGB 그대로 세면 같은 사람이 구름 한 번에 남이 된다.
 * 밝기는 따로 아주 성기게(4칸)만 넣는다 — 흰 조끼와 검은 유니폼을 가르려면
 * 밝기가 있어야 하기 때문이다.
 */

import type { Box } from './box'

/**
 * 색도 칸 수(가로·세로)와 밝기 칸 수.
 *
 * 🔴 밝기를 4 → 6 으로 늘렸다. **흰 조끼와 검은 유니폼은 색도가 같아서**
 * (둘 다 r=g=b) 오직 밝기 칸만이 둘을 가른다 — 칸이 성기면 배경 잡음에
 * 묻힌다. 실제로 그 둘 사이에서 박스가 넘어갔다.
 */
const C = 6
const V = 6
const PART_N = C * C * V
export const HIST_N = PART_N * 2

/**
 * 🔴 **상의와 하의를 따로 센다.**
 *
 * 하나로 뭉쳐 세다가 박스가 검은 유니폼에 붙어 안 떨어졌다. 원인은 색도가
 * 밝기를 나눠 버린다는 것이다 — **흰 조끼와 검은 유니폼은 색도가 똑같다**
 * (둘 다 r=g=b). 밝기 칸이 그걸 갈라야 하는데, 한 덩어리로 세면 배경(코트 ·
 * 펜스)이 표의 절반을 차지해 그 차이를 묻어 버린다.
 *
 * 위아래를 나누면 **"흰 상의 + 무늬 있는 반바지" 와 "검은 상의 + 검은 반바지"**
 * 가 각각의 표에서 갈린다. 한쪽이 배경에 먹혀도 다른 쪽이 남는다.
 *
 * 자리도 좁혔다 — 가운데 기둥만 본다. 사람 상자의 좌우 끝은 거의 배경이다.
 */
const TOP = { x0: 0.3, x1: 0.7, y0: 0.14, y1: 0.48 }
const BOTTOM = { x0: 0.32, x1: 0.68, y0: 0.5, y1: 0.78 }

/** 한 자리에서 뽑는 표본 격자. */
const GX = 12
const GY = 16

/**
 * 상자 안 몸통의 색 분포를 센다. 합이 1 인 히스토그램이 나온다.
 *
 * `img` 는 프레임 한 장의 RGBA 다(축소본이면 충분하다).
 */
export function colorHist(
  img: { data: Uint8ClampedArray; width: number; height: number },
  box: Box,
  out = new Float32Array(HIST_N),
): Float32Array {
  out.fill(0)
  const parts = [TOP, BOTTOM]
  for (let k = 0; k < parts.length; k += 1) {
    const r0 = parts[k]
    const base = k * PART_N
    const x0 = box.x + box.w * r0.x0
    const y0 = box.y + box.h * r0.y0
    const bw = box.w * (r0.x1 - r0.x0)
    const bh = box.h * (r0.y1 - r0.y0)

    let n = 0
    for (let j = 0; j < GY; j += 1) {
      const fy = Math.round((y0 + ((j + 0.5) / GY) * bh) * img.height)
      if (fy < 0 || fy >= img.height) continue
      for (let i = 0; i < GX; i += 1) {
        const fx = Math.round((x0 + ((i + 0.5) / GX) * bw) * img.width)
        if (fx < 0 || fx >= img.width) continue
        const p = (fy * img.width + fx) * 4
        const r = img.data[p]
        const g = img.data[p + 1]
        const b = img.data[p + 2]
        const sum = r + g + b
        // 아주 어두운 점은 색이라는 게 없다 — 색도는 가운데로 몰아 넣고
        // 밝기 칸이 그것을 가른다.
        const cr = sum > 24 ? r / sum : 1 / 3
        const cg = sum > 24 ? g / sum : 1 / 3
        const bi = Math.min(C - 1, Math.floor(cr * C))
        const bj = Math.min(C - 1, Math.floor(cg * C))
        /**
         * 🔴 밝기는 **로그**로 잰다. 그늘에 들어가는 것은 밝기를 절반쯤으로
         * **곱하는** 일이고, 흰 조끼와 검은 유니폼의 차이는 예닐곱 배다 —
         * 선형으로 재면 그 둘이 같은 폭으로 보인다. 로그로 재면 그늘은 한
         * 칸 안쪽, 옷 차이는 두 칸 넘게 벌어진다.
         */
        const t = (Math.log1p(sum / 3) / Math.log(257)) * V - 0.5
        const b0 = Math.floor(t)
        const fr = t - b0
        const v0 = Math.min(V - 1, Math.max(0, b0))
        const v1 = Math.min(V - 1, Math.max(0, b0 + 1))
        /**
         * 🔴 **가운데를 무겁게 센다.** 사람 상자는 가운데가 몸이고 가장자리로
         * 갈수록 배경이다. 다 같은 무게로 세면 그 배경(산울타리 · 펜스 · 코트)이
         * 표를 지배해서, 옷이 다른 두 사람이 서로 닮아 보인다.
         * 가장자리에서 0 이 되는 포물선이라 경계가 딱 끊기지 않는다.
         */
        const du = ((i + 0.5) / GX) * 2 - 1
        const dv = ((j + 0.5) / GY) * 2 - 1
        const wgt = (1 - du * du) * (1 - dv * dv)
        /**
         * 🔴 밝기 칸에는 **걸쳐서** 넣는다. 딱 한 칸에만 넣으면 조금만 어두워져도
         * 표가 통째로 옆 칸으로 옮겨 가 같은 사람이 남이 된다 — 칸 경계에서
         * 뚝 끊기는 것을 막는 흔한 방법이다.
         */
        out[base + (v0 * C + bj) * C + bi] += wgt * (1 - fr)
        out[base + (v1 * C + bj) * C + bi] += wgt * fr
        n += wgt
      }
    }
    // 🔴 자리마다 **따로 0.5 로** 맞춘다. 그래야 위아래가 같은 무게로 셈에
    // 들어간다 — 한쪽 표본이 많다고 그쪽이 이기면 안 된다.
    if (n > 0) for (let i = 0; i < PART_N; i += 1) out[base + i] *= 0.5 / n
  }
  return out
}

/**
 * 두 히스토그램이 얼마나 닮았나 — 바타차리야 계수(0~1). 클수록 닮았다.
 *
 * 같은 사람이면 대개 0.8 위, 다른 사람이면 0.5 아래로 갈린다. 겹치는 정도를
 * 그대로 재는 값이라 문턱을 감으로 잡아도 뜻이 통한다.
 */
export function histSim(a: Float32Array, b: Float32Array): number {
  let s = 0
  for (let i = 0; i < a.length; i += 1) s += Math.sqrt(a[i] * b[i])
  return s
}
