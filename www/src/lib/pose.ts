/**
 * 관절 17개를 **막대기(뼈대)** 로 잇는 규칙과, 그것을 눅이는 도구.
 *
 * 🔴 관절은 **이미 오고 있었다.** MoveNet 은 사람 하나에 56 개 숫자를 주는데
 * 그중 51 개가 관절이고(`personDetector.ts` 의 표) 지금까지 상자 4 개만 쓰고
 * 나머지를 버렸다. 이 앱은 자세 분석 앱이라 관절이 덤이 아니라 본론이다.
 *
 * 순서는 COCO 17 점이다 — 코 · 눈 둘 · 귀 둘 · 어깨 둘 · 팔꿈치 둘 · 손목 둘 ·
 * 엉덩이 둘 · 무릎 둘 · 발목 둘.
 */

export type Point = { x: number; y: number; score: number }

/** 관절 이름 — 자리를 손으로 세지 않으려고 둔다. */
export const NOSE = 0
export const L_SHOULDER = 5
export const R_SHOULDER = 6

/**
 * 이어 그릴 뼈대.
 *
 * 🔴 얼굴(눈 · 귀)은 잇지 않는다. 점이 몰려 있어 선이 뭉개지기만 하고, 자세를
 * 보는 데 쓰이지도 않는다 — 대신 코와 두 어깨 사이를 이어 고개 방향만 남긴다.
 */
export const EDGES: readonly [number, number][] = [
  [5, 7], [7, 9], // 왼팔
  [6, 8], [8, 10], // 오른팔
  [5, 6], // 어깨
  [5, 11], [6, 12], [11, 12], // 몸통
  [11, 13], [13, 15], // 왼다리
  [12, 14], [14, 16], // 오른다리
]

/** 이 점수 아래의 관절은 그리지 않는다 — 가려진 자리를 억지로 잇지 않는다. */
export const MIN_KP = 0.3

/**
 * 관절을 눅인다.
 *
 * 🔴 상자와 **같은 이유**다(`smoothBox.ts`). 검출은 초당 15번이고 관절은 상자보다
 * 더 튀어서, 그대로 그리면 막대기가 덜덜 떨린다. 시간으로 재는 것도 같다 —
 * 프레임률이 달라도 같은 속도로 따라와야 한다.
 *
 * 🔴 점수가 낮아 안 보이던 관절이 다시 잡히면 **눅이지 않고 그 자리에 놓는다.**
 * 마지막으로 보이던 옛 자리에서 새 자리까지 미끄러지면 팔이 허공을 가로지른다.
 */
/**
 * 두 자세가 **같은 사람의 연속된 두 장**이라고 볼 만한가.
 *
 * 🔴 화면의 다른 사람들은 따라가지 않으므로 프레임 사이의 짝이 보장되지
 * 않는다(검출기가 주는 차례는 점수순이라 뒤바뀐다). 그래서 눅이기 전에
 * **너무 멀면 그냥 새로 놓는다** — 남의 자세에서 미끄러져 오면 팔다리가
 * 화면을 가로지른다.
 */
export function isSamePerson(a: Point[], b: Point[], max = 0.08): boolean {
  if (a.length !== b.length) return false
  let sum = 0
  let n = 0
  for (let i = 0; i < a.length; i += 1) {
    if (a[i].score < MIN_KP || b[i].score < MIN_KP) continue
    sum += Math.hypot(a[i].x - b[i].x, a[i].y - b[i].y)
    n += 1
  }
  return n >= 4 && sum / n <= max
}

export function smoothPose(
  cur: Point[] | null,
  next: Point[],
  dt: number,
  // 🔴 70 → 45. 검출이 프레임마다 두 번 돌면서 값이 늦게 오는데 눅이는 시간까지
  // 길면 관절이 눈에 띄게 뒤늦게 따라온다(사용자 지적). 2단계 덕에 값 자체가
  // 안정적이라 더 바짝 붙여도 떨리지 않는다.
  tau = 45,
): Point[] {
  if (!cur || cur.length !== next.length) return next
  const k = 1 - Math.exp(-Math.max(0, Math.min(200, dt)) / tau)
  return next.map((n, i) => {
    const c = cur[i]
    if (c.score < MIN_KP || n.score < MIN_KP) return n
    return { x: c.x + (n.x - c.x) * k, y: c.y + (n.y - c.y) * k, score: n.score }
  })
}
