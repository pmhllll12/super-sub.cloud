import { skeletonShapes, type GridPoint } from './skeleton'

/** COCO 17 점 전부 보이는 서 있는 자세(격자 좌표). */
function standing(): GridPoint[] {
  return [
    { x: 500, y: 100 }, // 0 코
    { x: 490, y: 90 }, // 1 왼눈
    { x: 510, y: 90 }, // 2 오른눈
    { x: 470, y: 100 }, // 3 왼귀
    { x: 530, y: 100 }, // 4 오른귀
    { x: 440, y: 200 }, // 5 왼어깨
    { x: 560, y: 200 }, // 6 오른어깨
    { x: 420, y: 300 }, // 7 왼팔꿈치
    { x: 580, y: 300 }, // 8 오른팔꿈치
    { x: 410, y: 400 }, // 9 왼손목
    { x: 590, y: 400 }, // 10 오른손목
    { x: 460, y: 450 }, // 11 왼엉덩이
    { x: 540, y: 450 }, // 12 오른엉덩이
    { x: 455, y: 600 }, // 13 왼무릎
    { x: 545, y: 600 }, // 14 오른무릎
    { x: 450, y: 750 }, // 15 왼발목
    { x: 550, y: 750 }, // 16 오른발목
  ]
}

/** `M x yL x y` 조각 수 — 선 · 점 하나가 하나다. */
const moves = (d: string) => (d.match(/M/g) ?? []).length

describe('뼈대 모양', () => {
  // 🔴 얼굴 점 다섯(코 · 눈 · 귀)이 카드에서 흰 점 뭉치로 보였다 — 관절 고리는 몸의 마디만.
  it('관절 고리는 몸의 마디 열둘만 — 얼굴 점은 찍지 않는다', () => {
    const { joints } = skeletonShapes(standing())
    expect(moves(joints)).toBe(12)
    expect(joints).not.toContain('500.0 100.0')
    expect(joints).not.toContain('490.0 90.0')
  })

  it('머리는 원 하나로 그린다 — 두 귀 가운데가 중심, 크기는 몸통 길이로 잰다', () => {
    const { bones } = skeletonShapes(standing())
    // 두 귀 가운데(500,100), 반지름 = 몸통 250 × 0.22 = 55 → 왼쪽 끝 445
    expect(bones).toContain('M445.0 100.0a55.0 55.0 0 1 0 110.0 0a55.0 55.0 0 1 0 -110.0 0')
  })

  // 🔴 옆으로 선 자세 — 두 어깨가 겹치고 귀는 하나만 보인다. 폭으로 재면 머리가 사라졌다.
  it('옆모습(어깨가 겹치고 귀가 하나)에서도 머리가 사라지지 않는다', () => {
    const pts = standing()
    pts[5] = { x: 500, y: 200 }
    pts[6] = { x: 500, y: 200 }
    pts[3] = null
    pts[4] = { x: 480, y: 100 }
    pts[1] = null
    pts[2] = null
    const { bones } = skeletonShapes(pts)
    // 코(500,100)와 귀(480,100)의 가운데 490 이 중심, 반지름은 몸통 250 × 0.22 = 55
    expect(bones).toContain('M435.0 100.0a55.0 55.0')
  })

  // 🔴 겹쳐 그리는 판은 1000×1000 격자를 상자에 늘린다(`preserveAspectRatio="none"`) —
  //    격자 단위 그대로 원을 그리면 가로로 늘어난 타원이 된다.
  it('격자가 늘어나도 머리는 화면에서 원으로 보인다', () => {
    const { bones } = skeletonShapes(standing(), { sx: 2, sy: 1 })
    // 몸통은 세로라 화면 길이 250px → 반지름 55px → 가로 27.5 격자 · 세로 55 격자
    expect(bones).toContain('a27.5 55.0 0 1 0 55.0 0')
  })

  it('몸통은 옆선 대신 어깨 가운데 → 골반 가운데 척추 한 줄이다', () => {
    const { bones } = skeletonShapes(standing())
    expect(bones).toContain('M500.0 200.0L500.0 450.0')
    expect(bones).not.toContain('M440.0 200.0L460.0 450.0')
    expect(bones).not.toContain('M560.0 200.0L540.0 450.0')
  })

  // 한쪽 골반이 가려져 척추를 못 그으면 보이는 옆선이라도 남긴다 — 몸통이 통째로 비면 안 된다.
  it('척추를 못 그으면 보이는 몸통 옆선을 대신 긋는다', () => {
    const pts = standing()
    pts[12] = null
    const { bones } = skeletonShapes(pts)
    expect(bones).toContain('M440.0 200.0L460.0 450.0')
    expect(bones).not.toContain('L500.0 450.0')
  })

  it('차는 다리는 따로 모아 굵게 그릴 수 있게 한다', () => {
    const { bones, kick } = skeletonShapes(standing(), { kickingLeg: 'right' })
    expect(kick).toBe('M540.0 450.0L545.0 600.0M545.0 600.0L550.0 750.0')
    expect(bones).not.toContain('M540.0 450.0L545.0 600.0')
    // 디딤발은 그대로 뼈에 있다.
    expect(bones).toContain('M460.0 450.0L455.0 600.0')
  })

  it('차는 다리를 모르면 두 다리 다 뼈에 그린다', () => {
    const { bones, kick } = skeletonShapes(standing())
    expect(kick).toBe('')
    expect(bones).toContain('M540.0 450.0L545.0 600.0')
  })

  it('안 보이는 관절은 잇지도 찍지도 않는다', () => {
    const pts = standing()
    pts[9] = null
    const { bones, joints } = skeletonShapes(pts)
    expect(bones).not.toContain('410.0 400.0')
    expect(moves(joints)).toBe(11)
  })
})
