/**
 * 검출된 사람들 중에서 **내 사람**을 골라 잇는다(tracking-by-detection).
 *
 * ## 🔴 무늬 따라가기를 버린 이유
 *
 * 처음에는 사람이 묶은 자리의 무늬를 떠서 다음 프레임에서 닮은 자리를 찾는
 * 방식으로 만들었다. 세 번 고쳤지만 끝내 실패했다 — 버그가 아니라 **방식**이
 * 틀렸다:
 *
 * | 무늬 따라가기 | 지금(실제 시스템과 같은 방식) |
 * |---|---|
 * | 무늬와 닮은 **자리**를 찾는다 | 매 프레임 **사람을 검출**한다 |
 * | 자리는 배경일 수도 있다 — 펜스 · 산울타리에 눌러앉았다 | 박스는 **언제나 검출된 사람 위에만** 있다 |
 * | 지난 자리 ±5% 만 본다 — 한 번 놓치면 영영 못 찾는다 | 검출은 화면 전체 — 다시 나타나면 다시 잡힌다 |
 * | 사람이 돌아서면 무늬가 무너진다 | 검출기는 뒷모습도 사람으로 찾는다 |
 *
 * 이 파일이 하는 일은 그 **짝짓기**다. 검출기가 프레임마다 사람 여럿을 주면,
 * 그중 어느 것이 내 사람인지 고른다. ByteTrack · BoT-SORT · DeepSORT 가 하는
 * 일이고, 여기서는 뼈대만 쓴다 — **움직임 + 겹침 + 생김새**.
 *
 * ## 🔴 두 번째로 고친 것 — 지나가던 사람에게 옮겨 붙었다
 *
 * 검출로 바꾼 뒤에도 박스가 다른 사람에게 갈아탔다. 원인이 둘이었다:
 *
 * 1. **생김새를 회색조 무늬로 쟀다.** 이 영상에서 사람을 가르는 것은 유니폼
 *    색인데 회색으로 바꾸면 그게 사라진다 → `appearance.ts` 의 색 히스토그램
 * 2. **놓친 뒤 거리 문턱만 넓혔다.** 그러니 멀리 있는 아무나 후보가 됐다 →
 *    지금은 멀리서 다시 찾을 때 **거리가 아니라 닮음을 더 요구한다**
 *    (`MIN_SIM_FAR`). 가까이 있을 때보다 **문턱이 높아진다** — 멀리 있는데
 *    닮기까지 애매하면 그건 남이다
 *
 * ## 🔴 세 번째로 고친 것 — 잘못이 스스로를 굳혔다
 *
 * 그러고도 박스가 한 번씩 옆 사람에게 건너뛰었다. 원인이 둘이었다:
 *
 * 1. **생김새를 조금씩 갱신했다.** 처음 것과 "지금 것" 둘로 재서 더 나은 쪽을
 *    썼는데, 한 번 잘못 붙으면 **지금 것이 그 사람 쪽으로 갱신되어** 그 뒤로는
 *    그 사람이 계속 더 잘 맞는다 — 되먹임 고리다. **갱신을 없앴다.** 사람이
 *    고른 그 순간의 생김새 하나만 끝까지 쥔다. 유니폼은 변하지 않고, 그늘은
 *    이미 색도(`appearance.ts`)가 흡수한다
 *
 * 2. **가까이만 있으면 다른 몸으로도 건너뛸 수 있었다.** 이제 예측 자리와
 *    **겹치지 않는 후보**(= 다른 몸)로 옮겨 타려면 늘 엄격한 문턱을 넘어야
 *    한다(`JUMP_IOU`). 옆에 붙어 서 있다는 것은 같은 사람이라는 근거가 아니다
 *
 * 🔴 남은 하나의 원칙: **애매하면 안 붙는다.** 그 사람이 이번 프레임에 안
 * 잡혔으면 옆 사람을 대신 잡는 것보다 **그대로 서서 기다리는 편**이 낫다 —
 * 검출은 화면 전체를 보므로 다음 프레임에 다시 붙는다.
 *
 * ## 🔴 네 번째로 고친 것 — 잘못 붙으면 되돌아올 길이 없었다
 *
 * 위의 것들을 다 하고도, 한 번 남에게 붙으면 **거기서 안 떨어졌다.** 그 남이
 * 계속 예측 자리 옆에 있으니 이어짐(움직임)으로는 늘 그가 이기고, 정작 진짜
 * 그 사람이 화면 한복판에 서 있어도 후보로조차 안 올랐다.
 *
 * 그래서 매 프레임 **모든 검출을 처음 생김새와 견줘 본다**(`bestLook`). 지금
 * 붙들고 있는 것보다 **훨씬 더 닮은** 사람이 있으면 그쪽으로 옮긴다. 이어짐을
 * 깨는 일이라 문턱이 높다(`SWITCH_MARGIN` · `MIN_SIM_FAR`) — 그래도 이 길이
 * 없으면 한 번의 실수가 영원한 실수가 된다.
 */

import { centerDist, iou, sizeGap, cx, cy, type Box } from './box'
import { colorHist, histSim } from './appearance'
import type { Point } from './pose'

/** 검출기가 준 사람 하나. 관절은 검출기가 줄 때만 있다(시험에서는 없다). */
export type Det = { box: Box; score: number; keypoints?: Point[] }

/** 프레임 한 장(RGBA). 생김새를 재는 데만 쓴다. */
export type Frame = { data: Uint8ClampedArray; width: number; height: number }

const clamp01 = (n: number) => Math.min(1, Math.max(0, n))

/**
 * 한 칸 사이에 사람이 갈 수 있는 거리(자기 키 대비).
 *
 * 🔴 넉넉하게 잡으면 안 된다. 1.2 로 뒀다가 **옆 사람에게 그대로 갈아탔다** —
 * 70ms 에 자기 키만큼 가는 사람은 없다.
 */
const GATE = 0.55

/** 못 찾은 칸마다 이만큼씩 더 멀리 본다. 다시 찾기 위한 여유다. */
const GATE_PER_MISS = 0.45
const GATE_MAX = 3.5

/**
 * 요구하는 최소 닮음(바타차리야 계수, 0~1).
 *
 * 🔴 **멀수록 더 닮아야 한다.** 바로 옆이면 움직임만으로도 거의 확실하지만,
 * 멀리서 다시 찾는 것은 "저 사람이 그 사람일 것" 이라는 주장이라 근거가 더
 * 있어야 한다. 반대로 두면(멀수록 헐겁게) 아무에게나 갈아탄다 — 실제로 그랬다.
 */
/**
 * 상자의 **가운데**가 이보다 바깥이면 "화면 밖으로 나가는 중" 으로 본다.
 *
 * 🔴 상자의 변이 화면 끝에 닿았는지로 재면 안 된다 — 걸어 나가는 사람은
 * 상자가 가늘어져서 변이 끝에 안 닿는다. 실제로 그래서 이 검사를 빠져나갔다.
 */
const OUT_EDGE = 0.85

/** 나간 쪽에서 돌아올 때 보는 띠 — 이 안쪽만 후보로 인정한다. */
const EDGE_BAND = 0.6

const MIN_SIM_NEAR = 0.55
const MIN_SIM_FAR = 0.78


/**
 * 예측 자리와 이만큼도 안 겹치면 **다른 몸**으로 본다.
 *
 * 🔴 그럴 때는 가까이 있어도 늘 엄격한 문턱(`MIN_SIM_FAR`)을 쓴다. 옆에 붙어
 * 서 있다는 것은 같은 사람이라는 근거가 아니다 — 그렇게 건너뛰었다.
 */
const JUMP_IOU = 0.1

/**
 * 움직임 저울 — 🔴 **누구인지를 정하는 데는 안 쓴다.** 닮음이 엇비슷한
 * 후보끼리 가르는 동점 처리에만 쓴다(아래 `SIM_TIE`).
 */
const W_IOU = 1
const W_DIST = 0.6
const W_SIZE = 0.5

/**
 * 닮음이 이 안에서 엇비슷하면 **움직임으로 가른다.** 그보다 벌어지면
 * 더 닮은 쪽이 무조건 이긴다.
 *
 * 🔴 예전에는 닮음과 움직임을 한 저울에 섞어 더했는데, **슛하려고 팔을 드는
 * 순간** 그 사람 상자가 위로 튀어 겹침이 떨어지고 가만히 서 있던 옆 사람이
 * 이겼다. 누구인지는 생김새가 정해야 한다 — 움직임은 동점 처리다.
 */
const SIM_TIE = 0.05

/**
 * 이어짐을 깨고 다른 사람으로 옮기려면 지금 것보다 이만큼 더 닮아야 한다.
 *
 * 🔴 0.12 → 0.06. **실제 영상을 재서 고친 값이다**(`scripts/track-check.test.ts`).
 * 잘못 붙어 있던 78~80번 프레임에서 진짜 그 사람은 0.03 · 0.10 · 0.07 만큼만
 * 더 닮아 있었다 — 0.12 로는 세 프레임을 남에게 붙은 채로 흘려보냈다.
 *
 * 낮추면 비슷한 둘 사이를 오갈 위험이 있지만, 같은 측정에서 **정상 구간의
 * 닮음은 0.85~0.96 이고 2등과는 훨씬 벌어져 있었다** — 오갈 여지가 애초에 적다.
 */
const SWITCH_MARGIN = 0.06

export type Assoc = { index: number; cost: number; sim: number }

/** 움직임을 아예 안 보고 **가장 닮은** 검출 하나를 찾는다. */
export function bestLook(
  pred: Box,
  dets: Det[],
  frame: Frame,
  hist: Float32Array,
  missed = 0,
): { index: number; sim: number } | null {
  let best: { index: number; sim: number } | null = null
  for (const i of eligible(pred, dets, missed)) {
    const sim = histSim(hist, colorHist(frame, dets[i].box))
    if (!best || sim > best.sim) best = { index: i, sim }
  }
  return best
}

/**
 * 예측 자리와 가장 잘 맞는 검출 하나를 고른다. 없으면 `null`.
 *
 * `missed` 는 연속으로 못 찾은 칸 수다 — 오래 못 찾을수록 더 멀리 보되,
 * **그만큼 더 닮기를 요구한다**(위 주석).
 */
/**
 * 자리만 보고 **말이 되는 후보**를 걸러 낸다. 생김새는 안 본다.
 *
 * 🔴 **되돌아오는 길(`bestLook`)도 이 거름망을 지나야 한다.** 그 길이 거리
 * 검사를 건너뛰고 있어서, 대상이 오른쪽 끝으로 걸어 나간 직후 화면 **한복판**의
 * 다른 선수를 잡아 버렸다(실측 70번 프레임: 0.96 → 0.44). 그 사람이 마침
 * 제일 닮아 보였으므로 생김새로는 못 막는다 — 막는 것은 자리다.
 */
export function eligible(pred: Box, dets: Det[], missed = 0): number[] {
  const gate = Math.min(GATE_MAX, GATE + missed * GATE_PER_MISS)
  // 화면 밖으로 나간 사람은 **나간 쪽에서** 돌아온다.
  const out = missed > 0 ? cx(pred) : 0.5
  const atRight = out >= OUT_EDGE
  const atLeft = out <= 1 - OUT_EDGE

  const list: number[] = []
  for (let i = 0; i < dets.length; i += 1) {
    const b = dets[i].box
    if (atRight && cx(b) < EDGE_BAND) continue
    if (atLeft && cx(b) > 1 - EDGE_BAND) continue
    if (centerDist(pred, b) > gate) continue
    list.push(i)
  }
  return list
}

export function associate(
  pred: Box,
  dets: Det[],
  frame: Frame,
  hist: Float32Array,
  missed = 0,
): Assoc | null {
  const gate = Math.min(GATE_MAX, GATE + missed * GATE_PER_MISS)
  // 문턱을 0(바로 옆) ~ 1(가장 멀리) 로 놓고 두 값 사이를 잇는다.
  const far = gate > GATE ? Math.min(1, (gate - GATE) / (GATE_MAX - GATE)) : 0
  const minSim = MIN_SIM_NEAR + (MIN_SIM_FAR - MIN_SIM_NEAR) * far

  const ok: Assoc[] = []
  for (const i of eligible(pred, dets, missed)) {
    const d = dets[i]
    const dist = centerDist(pred, d.box)
    const overlap = iou(pred, d.box)
    // 다른 몸으로 건너뛰는 것이면 가까워도 엄격하게 본다.
    const need = overlap >= JUMP_IOU ? minSim : Math.max(minSim, MIN_SIM_FAR)

    const sim = histSim(hist, colorHist(frame, d.box))
    if (sim < need) continue

    const cost = W_IOU * (1 - overlap) + W_DIST * dist + W_SIZE * sizeGap(pred, d.box)
    ok.push({ index: i, cost, sim })
  }
  if (ok.length === 0) return null

  // 🔴 **가장 닮은 쪽이 이긴다.** 움직임은 닮음이 엇비슷할 때만 가른다.
  let top = ok[0]
  for (const c of ok) if (c.sim > top.sim) top = c
  let best = top
  for (const c of ok) {
    if (top.sim - c.sim > SIM_TIE) continue
    if (c.cost < best.cost) best = c
  }
  return best
}

export type PersonTracker = {
  readonly box: Box
  readonly missed: number
  step(dets: Det[], frame: Frame): { box: Box; lost: boolean; sim: number; det: Det | null }
}

/** 이만큼 연속으로 못 찾았으면 "놓쳤습니다" 라고 말한다. */
const LOST_AFTER = 4

/**
 * 이만큼(≈1.5초) 계속 못 찾았고 **화면에 사람이 하나뿐이면** 그 사람으로
 * 다시 건다.
 *
 * 🔴 마지막 안전장치다. 처음 생김새가 어쩌다 나쁘게 잡히면(헐거운 네모 ·
 * 순간의 역광) 그 뒤로는 무엇과도 안 닮아 **영영 "놓쳤습니다"** 가 된다 —
 * 한 사람만 나오는 영상에서 실제로 그랬다. 후보가 하나뿐이면 누구인지
 * 헷갈릴 여지가 없으므로, 그때만 기준을 다시 뜬다.
 *
 * 🔴 **후보가 둘 이상이면 절대 안 한다.** 기준을 다시 뜨는 것은 남에게 옮겨
 * 타는 가장 빠른 길이기도 하다(그래서 평소의 갱신을 없앴다).
 */
const RELOCK_AFTER = 20

/**
 * 사람이 묶은 자리에서 생김새를 뜨고 따라가기 시작한다.
 *
 * 🔴 **생김새는 처음 것 하나뿐이다. 갱신하지 않는다.** 조금씩 갱신하면 한 번
 * 잘못 붙었을 때 그 사람 쪽으로 기준이 옮겨 가서 잘못이 스스로를 굳힌다
 * (위 "세 번째로 고친 것"). 사람이 고른 그 순간이 유일한 기준이다.
 */
export function createPersonTracker(frame: Frame, box: Box): PersonTracker {
  let anchor = colorHist(frame, box)
  let cur = box
  let vx = 0
  let vy = 0
  let missed = 0

  return {
    get box() {
      return cur
    },
    get missed() {
      return missed
    },
    step(dets: Det[], f: Frame) {
      // 지난 칸에 움직인 만큼 앞질러 간 자리에서 찾는다. 검출이 절대 좌표를
      // 주므로 카메라 움직임을 따로 잴 필요가 없다 — 무늬 따라가기에서 사고를
      // 냈던 그 계산이 통째로 사라졌다.
      const pred = { ...cur, x: clamp01(cur.x + vx), y: clamp01(cur.y + vy) }

      const hit = associate(pred, dets, f, anchor, missed)

      /**
       * 🔴 **되돌아오는 길.** 이어짐만 보면 한 번 잘못 붙었을 때 거기서 못
       * 떨어진다 — 그 남이 늘 예측 자리 옆에 있기 때문이다. 움직임을 아예
       * 빼고 "누가 제일 닮았나" 를 따로 물어, 지금 것보다 훨씬 더 닮은 사람이
       * 있으면 그쪽으로 옮긴다.
       */
      const look = bestLook(pred, dets, f, anchor, missed)
      const better =
        look &&
        look.sim >= MIN_SIM_FAR &&
        (!hit || (look.index !== hit.index && look.sim > hit.sim + SWITCH_MARGIN))
          ? look
          : null

      const pick = better ?? hit
      if (!pick) {
        missed += 1
        vx = 0
        vy = 0

        // 마지막 안전장치 — 오래 못 찾았는데 화면에 사람이 하나뿐이면
        // 헷갈릴 여지가 없다. 그 사람으로 다시 건다(위 RELOCK_AFTER).
        if (missed >= RELOCK_AFTER && dets.length === 1) {
          cur = dets[0].box
          anchor = colorHist(f, cur)
          missed = 0
          return { box: cur, lost: false, sim: 1, det: dets[0] }
        }

        return { box: cur, lost: missed >= LOST_AFTER, sim: 0, det: null }
      }

      const next = dets[pick.index].box
      vx = cx(next) - cx(cur)
      vy = cy(next) - cy(cur)
      cur = next
      missed = 0

      return { box: cur, lost: false, sim: pick.sim, det: dets[pick.index] }
    },
  }
}

/**
 * 사람이 그린 네모를 **검출된 사람에 맞춰 준다.** 맞출 것이 없으면 `null`.
 *
 * 🔴 **처음 생김새는 반드시 검출된 상자에서 떠야 한다.** 손으로 그린 네모는
 * 헐거워서 절반이 배경일 수 있는데(세로 영상에서 하늘이 그랬다), 그걸 기준으로
 * 삼으면 이후의 진짜 검출과 영영 안 닮아 **처음부터 끝까지 "놓쳤습니다"** 가 된다.
 * 그래서 못 맞추면 그린 대로 쓰지 않고 **없다고 답한다** — 부를 쪽에서 다음
 * 프레임을 기다리면 된다.
 *
 * 겹침이 얕아도 **그린 네모 안에 사람의 가운데가 들어와 있으면** 맞춘 것으로
 * 본다. 사람을 크게 감싸 그리는 것은 자연스러운 일이고, 그때 겹침 비율은
 * 작아지지만 가리키는 대상은 분명하다.
 */
export function snapToDetection(drawn: Box, dets: Det[]): Box | null {
  let best: Box | null = null
  let bestIou = 0.05
  for (const d of dets) {
    const v = iou(drawn, d.box)
    if (v > bestIou) {
      bestIou = v
      best = d.box
    }
  }
  if (best) return best

  // 겹침으로는 못 골랐다 — 그린 네모 안에 가운데가 들어온 것 중 가장 가까운 것.
  let near: Box | null = null
  let nearD = Infinity
  for (const d of dets) {
    const px = cx(d.box)
    const py = cy(d.box)
    if (px < drawn.x || px > drawn.x + drawn.w) continue
    if (py < drawn.y || py > drawn.y + drawn.h) continue
    const dd = centerDist(drawn, d.box)
    if (dd < nearD) {
      nearD = dd
      near = d.box
    }
  }
  return near
}
