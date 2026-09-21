import { render } from '@testing-library/react'
import CardMark, { HIDDEN_MARKS, MARKS } from './CardMark'

/**
 * 🔴 이 파일이 붙드는 것은 **번호가 안 밀린다**는 것 하나다.
 *
 * `brush` 는 서버에 **숫자로** 저장된다(계약 `brush: int`). `MARKS` 의 앞쪽에서
 * 하나를 빼거나 끼우면 그 뒤 자국을 쓰던 사람들의 카드가 **말없이 다른 그림으로
 * 바뀐다** — 화면에도 로그에도 아무 표시가 안 난다. 그래서 거두는 자국은
 * 배열에서 지우지 않고 `HIDDEN_MARKS` 로 **감추기만** 한다.
 */
describe('카드 자국 목록', () => {
  // 🔴 여기 적힌 열넷은 **이미 실서버에 나가 있는 자리**다. 순서를 바꾸거나
  //    중간에 끼우면 남의 카드가 바뀌므로, 새 자국은 반드시 **뒤에 붙인다.**
  //    (2026-09-18 에 넷을 뺄 때 이 규칙을 세웠다 — 그날 뺀 넷은 배포된 적이
  //    없어서 통째로 지울 수 있었고, 점선 별 둘은 나가 있어서 감추기만 했다.)
  it('실서버에 나간 자국(0~13)의 자리가 안 바뀐다', () => {
    expect(MARKS.slice(0, 14)).toEqual([
      '기본',
      '없음',
      '서예 번짐',
      '유화',
      '튄 자국',
      '손그림 격자',
      '캘리 S',
      '점선 별',
      '점선 별 굵게',
      '부드러운 유화',
      '물감 구름',
      '수채 구름',
      '오려낸 X',
      '긁힌 X',
    ])
  })

  it('감춘 자국도 배열에서는 자리를 지킨다', () => {
    for (const i of HIDDEN_MARKS) {
      expect(MARKS[i]).toBeDefined()
    }
    // 감추는 것과 지우는 것은 다르다 — 지우면 뒤가 당겨진다.
    expect(MARKS[7]).toBe('점선 별')
    expect(MARKS[8]).toBe('점선 별 굵게')
  })

  // 🔴 이미 그 자국을 쓰고 있던 카드는 **그대로 그려져야** 한다. 안 그리면
  //    거두는 순간 그 사람들의 카드에서 자국이 사라진다.
  it('감춘 자국도 이미 쓰고 있던 카드에는 그려진다', () => {
    for (const i of HIDDEN_MARKS) {
      const { container } = render(<CardMark index={i} seed="pick" />)
      expect(container.querySelector('.ss-card-mark-img')).not.toBeNull()
    }
  })

  // 그림 파일은 1 번부터 이어진다 — 배열의 앞 둘(기본 · 없음)은 그림이 아니다.
  it('그림 번호가 배열 자리와 어긋나지 않는다', () => {
    const last = MARKS.length - 1
    const { container } = render(<CardMark index={last} seed="pick" />)
    const mask = container.querySelector<HTMLElement>('.ss-card-mark-img')!
    expect(mask.style.maskImage).toContain(`/marks/${String(last - 1).padStart(2, '0')}.png`)
  })

  it('목록보다 큰 값이 와도 아무것도 안 그린다', () => {
    // 저장된 값이 목록보다 클 수 있다 — 자국을 거둔 뒤의 옛 카드가 그렇다.
    const { container } = render(<CardMark index={MARKS.length + 5} seed="pick" />)
    expect(container.firstChild).toBeNull()
  })
})
