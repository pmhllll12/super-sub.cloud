import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ReportView, { type ReportBody } from './ReportView'

/**
 * 🔴 **레이더의 축과 범례가 번호로 이어져 있어야 한다** (2026-09-11, 사용자 요청).
 *
 * 앞서는 축 끝에 아무것도 안 적고 아래 범례에만 이름을 늘어놓았다 — 어느
 * 꼭짓점이 어느 이름인지 알 길이 없었다. 이름을 축 끝에 직접 놓는 길도
 * 있었지만 **한국어 이름은 길이가 제각각이라 6축에서 서로 파고든다**(그래서
 * 원래 범례로 뺐던 것이다). 번호는 한 글자라 **겹침이 구조적으로 안 생긴다.**
 */
const base: ReportBody = {
  summary: '디딤발이 공보다 앞서 있습니다.',
  points: [],
  scenes: [],
  totalScore: null,
  overallGrade: null,
  radar: [],
}

/** 6축이 최악이다 — 루브릭이 정하는 상한이고, 이름도 가장 길다. */
const SIX = [
  { name: '차고 난 뒤 마무리', stat: 63 },
  { name: '골반 돌리기', stat: 88 },
  { name: '디딤발 위치', stat: 91 },
  { name: '디딤발 무릎 굽히기', stat: 23 },
  { name: '차는 다리 뻗기', stat: 94 },
  { name: '상체 기울기', stat: 41 },
]

describe('분석 리포트 — 레이더', () => {
  it('축 끝의 번호와 범례의 번호가 같은 순서로 짝이 된다', () => {
    const { container } = render(<ReportView report={{ ...base, radar: SIX }} />)

    // 🔴 그림과 범례가 **같은 클래스**를 쓰므로(생김새를 한곳에서 정하려고)
    //    차트 쪽은 `svg` 안으로 좁혀서 센다.
    const onChart = [...container.querySelectorAll('svg .ss-report-radar-num')].map(
      (el) => el.textContent
    )
    const inLegend = [...container.querySelectorAll('.ss-report-radar-legend li')].map((li) => ({
      num: li.querySelector('.ss-report-radar-num')?.textContent,
      name: li.querySelector('.ss-report-radar-name')?.textContent,
    }))

    expect(onChart).toEqual(['1', '2', '3', '4', '5', '6'])
    expect(inLegend.map((x) => x.num)).toEqual(onChart)
    // 🔴 번호가 축 **순서**를 가리켜야 한다 — 정렬하거나 뒤섞으면 그림과 어긋난다.
    expect(inLegend.map((x) => x.name)).toEqual(SIX.map((a) => a.name))
  })

  /**
   * 🔴 **점수와 번호는 생김새가 달라야 한다.** 범례에 `디딤발 위치 91` 처럼
   * 숫자가 이미 있어서, 번호를 맨숫자로 두면 둘이 같은 것으로 읽힌다.
   */
  it('번호와 점수를 다른 것으로 그린다', () => {
    const { container } = render(<ReportView report={{ ...base, radar: SIX }} />)

    const first = container.querySelector('.ss-report-radar-legend li')!
    expect(first.querySelector('.ss-report-radar-num')).not.toBeNull()
    expect(first.querySelector('b')?.textContent).toBe('63')
  })

  /**
   * 🔴 **그림이 제 상자 안에서 가운데 있어야 한다** (2026-09-11, 사용자 지적).
   *
   * 상자를 정사각으로 두면 **축 개수가 홀수일 때 아래가 빈다** — 삼각형은
   * 위로 뾰족하고 아래는 평평한 밑변이라, 원에 내접시켜도 잉크가 위로
   * 쏠린다. 그러면 위아래 가로선과의 간격이 눈에 띄게 어긋난다.
   *
   * 상자를 **그려진 것에 맞춰 잘라** 그 문제를 없앤다. 여기서는 그 셈을
   * 다시 하지 않고 **성질만** 본다 — 번호 위의 여백과 아래의 여백이 같은가.
   */
  it.each([3, 5])('축이 %i 개여도 위아래 여백이 같다', (n) => {
    const axes = Array.from({ length: n }, (_, i) => ({ name: `축${i}`, stat: 70 }))
    const { container } = render(<ReportView report={{ ...base, radar: axes }} />)

    const svg = container.querySelector('svg')!
    const [, minY, , height] = svg.getAttribute('viewBox')!.split(' ').map(Number)
    const cys = [...svg.querySelectorAll('.ss-report-radar-numdot')].map((c) =>
      Number(c.getAttribute('cy'))
    )
    const r = Number(svg.querySelector('.ss-report-radar-numdot')!.getAttribute('r'))

    const above = Math.min(...cys) - r - minY
    const below = minY + height - (Math.max(...cys) + r)
    expect(Math.abs(above - below)).toBeLessThan(0.5)
  })

  /** 다각형이 안 되는 축 개수 — 그리지 않는다(있던 성질을 지킨다). */
  it('축이 셋보다 적으면 안 그린다', () => {
    const { container } = render(
      <ReportView report={{ ...base, radar: [{ name: '하나', stat: 50 }] }} />
    )
    expect(container.querySelector('.ss-report-radar')).toBeNull()
  })

  /**
   * ⚠️ 그림은 `aria-hidden` 이라 낭독기에 안 들린다 — **범례가 그 몫을
   * 대신한다.** 범례를 치우면 레이더가 통째로 안 읽히는 그림이 된다.
   */
  it('범례가 이름과 점수를 글자로 남긴다', () => {
    render(<ReportView report={{ ...base, radar: SIX }} />)
    expect(screen.getByText('차고 난 뒤 마무리')).toBeInTheDocument()
    expect(screen.getByText('63')).toBeInTheDocument()
  })
})
