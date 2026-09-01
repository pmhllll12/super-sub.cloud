import type { Box } from './box'
import { centerDist, iou } from './box'
import { colorHist, histSim } from './appearance'
import {
  associate,
  createPersonTracker,
  eligible,
  snapToDetection,
  type Det,
} from './personTrack'

const W = 160
const H = 120

type RGB = [number, number, number]

/** 흰 조끼 · 검은 유니폼 · 파란 셔츠 — 이 클립의 세 부류다. */
const WHITE: RGB = [235, 230, 220]
const BLACK: RGB = [34, 32, 38]
const BLUE: RGB = [30, 90, 200]

/** 배경(코트 · 펜스) 위에 사람 몇을 그린 가짜 프레임. */
function frameOf(people: { box: Box; color: RGB }[]): ImageData {
  const data = new Uint8ClampedArray(W * H * 4)
  for (let y = 0; y < H; y += 1) {
    for (let x = 0; x < W; x += 1) {
      const p = (y * W + x) * 4
      // 청록빛 코트.
      data[p] = 90
      data[p + 1] = 130
      data[p + 2] = 125
      data[p + 3] = 255
    }
  }
  for (const { box, color } of people) {
    const x0 = Math.round(box.x * W)
    const y0 = Math.round(box.y * H)
    const x1 = Math.round((box.x + box.w) * W)
    const y1 = Math.round((box.y + box.h) * H)
    for (let y = Math.max(0, y0); y < Math.min(H, y1); y += 1) {
      for (let x = Math.max(0, x0); x < Math.min(W, x1); x += 1) {
        const p = (y * W + x) * 4
        data[p] = color[0]
        data[p + 1] = color[1]
        data[p + 2] = color[2]
      }
    }
  }
  return { data, width: W, height: H } as ImageData
}

const me: Box = { x: 0.4, y: 0.3, w: 0.09, h: 0.4 }
const det = (box: Box, score = 0.8): Det => ({ box, score })

describe('상자 셈', () => {
  it('겹치면 1, 안 겹치면 0', () => {
    expect(iou(me, me)).toBeCloseTo(1)
    expect(iou(me, { ...me, x: 0.9 })).toBe(0)
  })

  it('거리는 상자 키로 잰다 — 원근에 상관없이 같은 자로 재진다', () => {
    expect(centerDist(me, { ...me, y: me.y + me.h / 2 })).toBeCloseTo(0.5)
  })
})

describe('색으로 사람 가르기', () => {
  // 🔴 회색조로 재던 것을 색으로 바꾼 이유가 이것이다 — 흰 조끼와 검은
  // 유니폼은 회색조에서도 갈리지만, 파란 셔츠와 검은 유니폼은 안 갈렸다.
  it('같은 사람은 닮고 다른 옷은 안 닮는다', () => {
    const f = frameOf([
      { box: me, color: WHITE },
      { box: { ...me, x: 0.7 }, color: BLACK },
      { box: { ...me, x: 0.1 }, color: BLUE },
    ])
    const mine = colorHist(f, me)

    expect(histSim(mine, colorHist(f, me))).toBeCloseTo(1)
    expect(histSim(mine, colorHist(f, { ...me, x: 0.7 }))).toBeLessThan(0.5)
    expect(histSim(mine, colorHist(f, { ...me, x: 0.1 }))).toBeLessThan(0.5)
  })

  // 🔴 흰 조끼와 검은 유니폼은 **색도가 똑같다**(둘 다 r=g=b). 밝기 칸이
  // 그걸 갈라야 하는데, 위아래를 뭉쳐 세면 배경에 묻혀 안 갈렸다.
  it('흰 상의와 검은 상의를 가른다', () => {
    const f = frameOf([
      { box: me, color: WHITE },
      { box: { ...me, x: 0.7 }, color: BLACK },
    ])
    expect(histSim(colorHist(f, me), colorHist(f, { ...me, x: 0.7 }))).toBeLessThan(0.45)
  })

  // 🔴 상의가 같아도 하의가 다르면 다른 사람이다 — 위아래를 따로 세는 이유다.
  it('상의가 같아도 하의가 다르면 갈린다', () => {
    const mine = frameOf([{ box: me, color: WHITE }])
    const twoTone = frameOf([
      { box: { ...me, h: me.h * 0.5 }, color: WHITE },
      { box: { ...me, y: me.y + me.h * 0.5, h: me.h * 0.5 }, color: BLUE },
    ])
    expect(histSim(colorHist(mine, me), colorHist(twoTone, me))).toBeLessThan(0.75)
  })

  // 🔴 그늘에 들어가도 같은 사람이어야 한다 — 그래서 밝기로 나눈 색도를 쓴다.
  it('그늘에 들어가도 같은 사람으로 본다', () => {
    const lit = frameOf([{ box: me, color: BLUE }])
    const dim = frameOf([{ box: me, color: [18, 54, 120] }])
    expect(histSim(colorHist(lit, me), colorHist(dim, me))).toBeGreaterThan(0.7)
  })
})

describe('내 사람 고르기', () => {
  it('바로 옆을 지나가는 다른 옷에게 넘어가지 않는다', () => {
    const near = { ...me, x: me.x + 0.06 }
    const f = frameOf([
      { box: me, color: WHITE },
      { box: near, color: BLACK },
    ])
    const hit = associate(me, [det(near), det(me)], f, colorHist(f, me))
    expect(hit?.index).toBe(1)
  })

  it('아무도 안 잡히면 못 찾았다고 답한다', () => {
    const f = frameOf([{ box: me, color: WHITE }])
    expect(associate(me, [], f, colorHist(f, me))).toBeNull()
  })

  // 🔴 "한 번 놓치면 영영 못 따라간다" 를 없애는 부분.
  it('오래 못 찾을수록 더 멀리까지 본다', () => {
    const far = { ...me, x: me.x + 0.25 }
    const f = frameOf([{ box: far, color: WHITE }])
    const mine = colorHist(frameOf([{ box: me, color: WHITE }]), me)

    expect(associate(me, [det(far)], f, mine, 0)).toBeNull()
    expect(associate(me, [det(far)], f, mine, 4)).not.toBeNull()
  })

  // 🔴 이게 지나가던 사람에게 옮겨 붙던 것을 막는다. 멀리서 다시 찾을 때는
  // 거리를 넓히는 만큼 **닮기를 더 요구한다.**
  it('멀리 있는 남에게는 아무리 오래 못 찾아도 안 붙는다', () => {
    const far = { ...me, x: me.x + 0.25 }
    const f = frameOf([{ box: far, color: BLACK }])
    const mine = colorHist(frameOf([{ box: me, color: WHITE }]), me)

    expect(associate(me, [det(far)], f, mine, 8)).toBeNull()
  })
})

describe('건너뛰지 않기', () => {
  // 🔴 사용자가 짚은 것 — "그 사람이 영상에 보이면 그 사람만 따라가야지".
  // 이번 프레임에 그 사람이 안 잡혔다면, 옆에 있는 남을 대신 잡는 것보다
  // **그대로 서서 기다리는 편**이 낫다. 다음 프레임에 다시 붙는다.
  it('대상이 이번에 안 잡히면 옆 사람으로 갈아타지 않는다', () => {
    const other = { ...me, x: me.x + 0.11 }
    const f = frameOf([{ box: other, color: BLACK }])
    const mine = colorHist(frameOf([{ box: me, color: WHITE }]), me)

    // 거리로만 보면 충분히 가깝다 — 그래도 남이면 안 붙는다.
    expect(centerDist(me, other)).toBeLessThan(0.55)
    expect(associate(me, [det(other)], f, mine)).toBeNull()
  })

  it('바로 옆에 겹쳐 선 남에게도 안 붙는다', () => {
    const beside = { ...me, x: me.x + 0.03 }
    const f = frameOf([{ box: beside, color: BLUE }])
    const mine = colorHist(frameOf([{ box: me, color: WHITE }]), me)
    expect(associate(me, [det(beside)], f, mine)).toBeNull()
  })

  // 🔴 되먹임 고리 — 한 번 잘못 붙으면 기준이 그 사람 쪽으로 옮겨 가서
  // 잘못이 스스로를 굳혔다. 생김새를 갱신하지 않으므로 이제 안 그런다.
  it('오래 따라가도 기준이 흔들리지 않는다', () => {
    const t = createPersonTracker(frameOf([{ box: me, color: WHITE }]), me)
    let at = me
    for (let i = 0; i < 20; i += 1) {
      at = { ...at, x: at.x + 0.005 }
      t.step([det(at)], frameOf([{ box: at, color: WHITE }]))
    }
    // 그 뒤에 검은 유니폼이 바로 옆에 나타나도 넘어가지 않는다.
    const near = { ...at, x: at.x + 0.02 }
    const f = frameOf([{ box: near, color: BLACK }])
    expect(t.step([det(near)], f).lost).toBe(false)
    expect(t.box.x).toBeCloseTo(at.x, 5)
  })
})

describe('잘못 붙었을 때 되돌아오기', () => {
  // 🔴 이어짐만 보면 한 번 잘못 붙었을 때 거기서 못 떨어진다 — 그 남이 늘
  // 예측 자리 옆에 있기 때문이다. 정작 진짜 그 사람은 화면 한복판에 서 있었다.
  it('훨씬 더 닮은 사람이 화면에 있으면 그쪽으로 돌아온다', () => {
    const wrong = { ...me, x: 0.15 }
    // 검은 유니폼에 잘못 붙은 채로 시작한다(사람은 흰 조끼를 골랐다).
    const t = createPersonTracker(frameOf([{ box: me, color: WHITE }]), me)

    // 검은 유니폼이 예측 자리 바로 옆으로 온다 — 이어짐으로는 이쪽이 이긴다.
    const f = frameOf([
      { box: wrong, color: BLACK },
      { box: me, color: WHITE },
    ])
    t.step([det(wrong), det(me)], f)

    // 그래도 진짜 그 사람에게 붙어 있어야 한다.
    expect(t.box.x).toBeCloseTo(me.x, 5)
  })

  it('닮은 사람이 없으면 함부로 옮기지 않는다', () => {
    const t = createPersonTracker(frameOf([{ box: me, color: WHITE }]), me)
    const other = { ...me, x: 0.15 }
    const f = frameOf([{ box: other, color: BLACK }])
    expect(t.step([det(other)], f).lost).toBe(false)
    expect(t.box).toEqual(me)
  })
})

describe('따라가기', () => {
  it('검출을 이어 받아 자리를 옮긴다', () => {
    const other = { ...me, x: 0.05 }
    let at = me
    const t = createPersonTracker(
      frameOf([
        { box: me, color: WHITE },
        { box: other, color: BLACK },
      ]),
      me,
    )

    for (let i = 0; i < 6; i += 1) {
      at = { ...at, x: at.x + 0.02 }
      const f = frameOf([
        { box: at, color: WHITE },
        { box: other, color: BLACK },
      ])
      expect(t.step([det(other), det(at)], f).lost).toBe(false)
    }
    expect(t.box.x).toBeCloseTo(at.x, 5)
  })

  // 🔴 검출은 프레임마다 흔들린다. 한 장 빠졌다고 곧바로 "놓쳤습니다" 를
  // 띄우면 표시가 깜빡인다.
  it('한두 칸 못 찾은 것으로는 놓쳤다고 하지 않는다', () => {
    const f = frameOf([{ box: me, color: WHITE }])
    const t = createPersonTracker(f, me)
    expect(t.step([], f).lost).toBe(false)
    expect(t.step([], f).lost).toBe(false)
    expect(t.step([], f).lost).toBe(false)
    expect(t.step([], f).lost).toBe(true)
  })

  // 🔴 검출은 화면 전체를 보므로 다시 나타나면 다시 붙는다.
  it('놓쳤다가 다시 나타나면 이어 붙는다', () => {
    const f0 = frameOf([{ box: me, color: WHITE }])
    const t = createPersonTracker(f0, me)
    for (let i = 0; i < 5; i += 1) t.step([], f0)
    expect(t.missed).toBeGreaterThan(0)

    const back = { ...me, x: me.x + 0.12 }
    const f = frameOf([{ box: back, color: WHITE }])
    expect(t.step([det(back)], f).lost).toBe(false)
    expect(t.box.x).toBeCloseTo(back.x, 5)
  })

  it('못 찾은 칸에는 자리를 지킨다', () => {
    const f = frameOf([{ box: me, color: WHITE }])
    const t = createPersonTracker(f, me)
    t.step([], f)
    expect(t.box).toEqual(me)
  })
})

describe('손으로 그린 네모 맞추기', () => {
  it('가장 잘 겹치는 검출로 붙여 준다', () => {
    const drawn = { ...me, x: me.x + 0.015, y: me.y + 0.02 }
    expect(snapToDetection(drawn, [det({ ...me, x: 0.05 }), det(me)])).toEqual(me)
  })

  // 🔴 사람을 크게 감싸 그리는 것이 보통이다. 그때 겹침 비율은 작아지지만
  // 가리키는 대상은 분명하다 — 가운데가 안에 들어와 있으면 맞춘 것으로 본다.
  it('헐겁게 크게 그려도 사람에 붙여 준다', () => {
    const loose = {
      x: me.x - me.w,
      y: me.y - me.h * 0.15,
      w: me.w * 3,
      h: me.h * 1.3,
    }
    expect(snapToDetection(loose, [det(me)])).toEqual(me)
  })

  // 🔴 못 맞추면 **그린 대로 쓰지 않는다.** 헐거운 네모를 기준으로 삼으면
  // 절반이 배경이라(세로 영상의 하늘) 이후 검출과 영영 안 닮는다.
  it('맞출 사람이 없으면 없다고 답한다', () => {
    expect(snapToDetection({ ...me, x: 0.85 }, [det(me)])).toBeNull()
    expect(snapToDetection(me, [])).toBeNull()
  })
})

describe('슛하는 순간에 옆 사람으로 안 넘어가기', () => {
  // 🔴 사용자가 짚은 것 — 팔을 드는 순간 그 사람 상자가 위로 튀어 겹침이
  // 떨어지고, 가만히 서 있던 옆 사람이 이겼다. 누구인지는 **생김새가** 정해야
  // 한다. 움직임은 닮음이 엇비슷할 때만 가르는 동점 처리다.
  it('팔을 들어 상자가 튀어도 그 사람에게 남는다', () => {
    const t = createPersonTracker(frameOf([{ box: me, color: WHITE }]), me)

    // 슛 — 내 사람 상자는 위로 튀고, 옆 사람은 제자리에 그대로 있다.
    const shooting = { ...me, y: me.y - me.h * 0.25, h: me.h * 1.1 }
    const beside = { ...me, x: me.x - 0.09 }
    const f = frameOf([
      { box: beside, color: BLACK },
      { box: shooting, color: WHITE },
    ])

    const r = t.step([det(beside), det(shooting)], f)
    expect(r.lost).toBe(false)
    expect(t.box).toEqual(shooting)
  })

  // 화면에 있는데 못 쫓아가면 분석이 안 된다 — 옆 사람을 잡느니 서 있는 게 낫다.
  it('내 사람이 없으면 옆 사람을 잡지 않고 기다린다', () => {
    const t = createPersonTracker(frameOf([{ box: me, color: WHITE }]), me)
    const beside = { ...me, x: me.x - 0.09 }
    const f = frameOf([{ box: beside, color: BLACK }])

    t.step([det(beside)], f)
    expect(t.box).toEqual(me)
  })
})

describe('화면 밖으로 나갔을 때', () => {
  // 🔴 실측으로 잡은 것 — 대상이 오른쪽 끝으로 걸어 나간 직후(70번 프레임)
  // 화면 **한복판**의 다른 선수를 잡아 버렸다(0.96 → 0.44). 그 사람이 마침
  // 제일 닮아 보였으므로 생김새로는 못 막는다. 막는 것은 자리다.
  it('오른쪽으로 나간 사람을 한복판에서 찾지 않는다', () => {
    const gone = { ...me, x: 0.9 }
    const middle = { ...me, x: 0.4 }
    const stillRight = { ...me, x: 0.86 }

    // 놓치기 전에는 둘 다 후보다(거리 안에 있으면).
    expect(eligible(gone, [det(stillRight)], 0)).toEqual([0])
    // 놓친 뒤에는 나간 쪽만 본다.
    expect(eligible(gone, [det(middle), det(stillRight)], 3)).toEqual([1])
  })

  it('왼쪽으로 나갔으면 반대로 왼쪽만 본다', () => {
    const gone = { ...me, x: 0.02 }
    const middle = { ...me, x: 0.5 }
    const stillLeft = { ...me, x: 0.06 }
    expect(eligible(gone, [det(middle), det(stillLeft)], 3)).toEqual([1])
  })

  // 🔴 되돌아오는 길(bestLook)도 같은 거름망을 지나야 한다 — 그 길이 거리
  // 검사를 건너뛰고 있어서 실제로 저 사고가 났다.
  it('되돌아오는 길도 한복판으로 건너뛰지 않는다', () => {
    const gone = { ...me, x: 0.9 }
    const t = createPersonTracker(frameOf([{ box: gone, color: WHITE }]), gone)
    const middle = { ...me, x: 0.4 }
    const f = frameOf([{ box: middle, color: WHITE }])

    // 화면 밖으로 나간 뒤, 한복판에 똑같이 생긴 사람이 나타나도 안 붙는다.
    for (let i = 0; i < 6; i += 1) t.step([det(middle)], f)
    expect(t.box).toEqual(gone)
  })
})

describe('오래 놓쳤을 때의 마지막 안전장치', () => {
  // 🔴 처음 생김새가 어쩌다 나쁘게 잡히면(헐거운 네모 · 순간의 역광) 그 뒤로는
  // 무엇과도 안 닮아 영영 "놓쳤습니다" 가 된다. 한 사람만 나오는 세로 영상에서
  // 실제로 그랬다 — 사람은 화면 한가운데 멀쩡히 서 있었다.
  it('사람이 하나뿐이면 한참 뒤에 그 사람으로 다시 건다', () => {
    // 하늘만 든 네모에서 기준을 떴다고 치자 — 무엇과도 안 닮는다.
    const t = createPersonTracker(frameOf([]), me)
    const f = frameOf([{ box: me, color: BLUE }])

    let r = t.step([det(me)], f)
    expect(r.lost).toBe(false) // 아직 놓쳤다고까지는 안 한다
    for (let i = 0; i < 4; i += 1) r = t.step([det(me)], f)
    expect(r.lost).toBe(true)

    // 계속 그 사람 하나뿐이면 결국 다시 건다.
    for (let i = 0; i < 20; i += 1) r = t.step([det(me)], f)
    expect(r.lost).toBe(false)
    expect(t.box).toEqual(me)
  })

  // 🔴 기준을 다시 뜨는 것은 남에게 옮겨 타는 가장 빠른 길이기도 하다.
  it('사람이 둘 이상이면 아무리 오래 놓쳐도 다시 걸지 않는다', () => {
    const t = createPersonTracker(frameOf([{ box: me, color: WHITE }]), me)
    const a = { ...me, x: 0.1 }
    const b = { ...me, x: 0.8 }
    const f = frameOf([
      { box: a, color: BLACK },
      { box: b, color: BLUE },
    ])

    let r = t.step([det(a), det(b)], f)
    for (let i = 0; i < 40; i += 1) r = t.step([det(a), det(b)], f)
    expect(r.lost).toBe(true)
    expect(t.box).toEqual(me)
  })
})
