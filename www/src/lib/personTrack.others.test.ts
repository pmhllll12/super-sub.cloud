import type { Point } from './pose'
import { othersOf, type Det } from './personTrack'

/**
 * 🔴 **화면에 한 사람뿐인데 회색 관절이 같이 그려졌다**(사용자 지적, 2026-09-14).
 *
 * 회색은 "찾긴 했지만 지금 보는 사람은 아니다" 라는 뜻인데, 전에는 「검출 전체 −
 * 추적기가 짝지은 검출」로 셌다. 그래서 **같은 사람**이 회색이 되는 길이 둘 있었다:
 *   ⑴ 추적기가 한 바퀴 짝을 못 지으면(`det: null`) 그 사람의 이번 검출이 남는다 —
 *      초록 막대기는 직전 자세로 서 있어서 **초록 위에 회색이 겹친다**
 *   ⑵ 검출기가 한 사람을 두 번 잡으면 짝이 안 된 쪽이 남는다
 */
const kp: Point[] = [{ x: 0.5, y: 0.5, score: 1 }]
const det = (x: number, y: number, w = 0.2, h = 0.5): Det => ({
  box: { x, y, w, h },
  score: 0.9,
  keypoints: kp,
})

describe('회색으로 그릴 나머지 사람들', () => {
  it('짝지어진 대상은 뺀다', () => {
    const me = det(0.3, 0.2)
    const other = det(0.7, 0.2)
    expect(othersOf([me, other], { box: me.box, det: me, lost: false })).toEqual([kp])
  })

  it('⑴ 이번 바퀴에 짝을 못 지었어도 대상 박스와 겹치는 검출은 회색이 아니다', () => {
    const me = det(0.31, 0.21) // 직전 박스에서 조금 움직였다
    expect(othersOf([me], { box: { x: 0.3, y: 0.2, w: 0.2, h: 0.5 }, det: null, lost: false })).toEqual([])
  })

  it('⑵ 같은 사람을 두 번 잡은 검출도 회색이 아니다', () => {
    const me = det(0.3, 0.2)
    const ghost = det(0.32, 0.22, 0.19, 0.47)
    expect(othersOf([me, ghost], { box: me.box, det: me, lost: false })).toEqual([])
  })

  // 🔴 옆에 바짝 붙은 **다른 사람**까지 지우면 회색의 뜻이 사라진다.
  it('살짝 겹친 옆 사람은 그대로 회색이다', () => {
    const me = det(0.3, 0.2)
    const next = det(0.45, 0.2)
    expect(othersOf([me, next], { box: me.box, det: me, lost: false })).toEqual([kp])
  })

  /* 놓친 동안에는 초록이 없다 — 그때 보이는 사람은 "찾긴 했지만 대상으로 못
     붙인 사람"이 맞으므로 회색으로 둔다(다시 붙으면 초록이 된다). */
  it('놓친 동안에는 빼지 않는다', () => {
    const someone = det(0.31, 0.21)
    expect(
      othersOf([someone], { box: { x: 0.3, y: 0.2, w: 0.2, h: 0.5 }, det: null, lost: true }),
    ).toEqual([kp])
  })

  it('관절이 없는 검출은 그리지 않는다', () => {
    const me = det(0.3, 0.2)
    const bare: Det = { box: { x: 0.7, y: 0.2, w: 0.2, h: 0.5 }, score: 0.9 }
    expect(othersOf([me, bare], { box: me.box, det: me, lost: false })).toEqual([])
  })
})
