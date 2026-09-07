import { DEFAULT_CARD_STYLE } from './cardStyle'
import { CARD_STYLE_KEY, loadCardStyle, saveCardStyle } from './cardStyleStore'

/**
 * 꾸민 카드를 어디에 두는가.
 *
 * ⚠️ **서버가 아니라 이 브라우저다** — 계약에 카드를 꾸미는 필드가 없다
 * (미결 paik 3번).
 */
describe('꾸민 카드 저장', () => {
  beforeEach(() => localStorage.clear())

  it('저장한 적이 없으면 null 이다', () => {
    expect(loadCardStyle(DEFAULT_CARD_STYLE)).toBeNull()
  })

  it('저장한 것을 그대로 읽는다', () => {
    expect(saveCardStyle({ ...DEFAULT_CARD_STYLE, text: '세 개의 폐' })).toBe(true)
    expect(loadCardStyle(DEFAULT_CARD_STYLE)?.text).toBe('세 개의 폐')
  })

  /**
   * 🔴 값이 늘어나도 옛 저장본이 화면을 깨지 않게 **기본값 위에 얹는다.**
   * 안 그러면 나중에 넣은 값이 `undefined` 로 들어와 카드가 통째로 안 그려진다.
   */
  it('모르는 값은 기본값으로 채운다', () => {
    localStorage.setItem(CARD_STYLE_KEY, JSON.stringify({ text: '옛날 것만' }))
    const s = loadCardStyle(DEFAULT_CARD_STYLE)
    expect(s?.text).toBe('옛날 것만')
    expect(s?.bg).toBe(DEFAULT_CARD_STYLE.bg)
    expect(s?.mode).toBe(DEFAULT_CARD_STYLE.mode)
  })

  it('저장된 값이 깨져 있으면 없는 것으로 본다', () => {
    localStorage.setItem(CARD_STYLE_KEY, '{{{')
    expect(loadCardStyle(DEFAULT_CARD_STYLE)).toBeNull()
  })

  /**
   * 🔴 사진은 data URL 이라 몇 MB 가 된다 — 저장소 한도(약 5MB)를 넘으면
   * 브라우저가 던진다. 화면이 죽으면 안 되고, **못 저장했다는 것을 알려야**
   * 한다. 조용히 성공한 척하면 다시 열었을 때 사라져 있다.
   */
  it('저장소가 넘치면 false 를 돌려준다', () => {
    vi.stubGlobal('localStorage', {
      getItem: () => null,
      setItem() {
        throw new Error('QuotaExceededError')
      },
    })
    expect(saveCardStyle(DEFAULT_CARD_STYLE)).toBe(false)
    vi.unstubAllGlobals()
  })

  it('저장소를 못 쓰면 읽기도 조용히 null 이다', () => {
    vi.stubGlobal('localStorage', {
      getItem() {
        throw new Error('denied')
      },
    })
    expect(loadCardStyle(DEFAULT_CARD_STYLE)).toBeNull()
    vi.unstubAllGlobals()
  })
})
