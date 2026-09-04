import { listPublished, publish, unpublish, isPublished, PUBLISHED_KEY } from './published'

/**
 * 공개로 돌린 내 클립. ⚠️ **서버 저장이 아니다** — 계약에 클립 공개 여부가
 * 없어서(미결로 올렸다) 이 브라우저에만 남는다.
 */
describe('공개한 클립 목록', () => {
  const clip = {
    id: 'v3',
    title: '학교 끝나고 농구 연습',
    what: '디딤발이 공보다 앞서지 않는 순간',
    src: '/coach-c003.mp4',
    aspect: '1080 / 1920',
    at: '2026-09-04',
  }

  beforeEach(() => localStorage.clear())

  it('처음에는 비어 있다', () => {
    expect(listPublished()).toEqual([])
    expect(isPublished('v3')).toBe(false)
  })

  it('공개하면 목록에 들어간다', () => {
    publish(clip)
    expect(listPublished()).toEqual([clip])
    expect(isPublished('v3')).toBe(true)
  })

  // 🔴 토글을 두 번 켜거나 제목을 고쳐 다시 공개할 수 있다. 쌓이면 영상 모음에
  // 같은 영상이 두 번 나온다.
  it('같은 영상을 다시 공개하면 덮어쓴다', () => {
    publish(clip)
    publish({ ...clip, title: '고친 제목' })
    expect(listPublished()).toHaveLength(1)
    expect(listPublished()[0].title).toBe('고친 제목')
  })

  it('공개를 풀면 빠진다', () => {
    publish(clip)
    unpublish('v3')
    expect(listPublished()).toEqual([])
    expect(isPublished('v3')).toBe(false)
  })

  // 🔴 저장된 값은 사람이 손댈 수 있는 자리다. 깨져 있다고 화면이 통째로
  // 죽으면 안 된다 — 빈 목록으로 되돌린다.
  it('저장된 값이 깨져 있으면 빈 목록으로 본다', () => {
    localStorage.setItem(PUBLISHED_KEY, '{{{')
    expect(listPublished()).toEqual([])
  })

  it('배열이 아닌 것이 들어 있어도 빈 목록으로 본다', () => {
    localStorage.setItem(PUBLISHED_KEY, '{"a":1}')
    expect(listPublished()).toEqual([])
  })

  // 🔴 사생활 보호 모드에서는 localStorage 를 만지는 것만으로 던진다.
  // 공개 기능이 안 되는 것은 참을 수 있어도 화면이 죽는 것은 아니다.
  it('저장소를 못 쓰면 조용히 빈 목록으로 둔다', () => {
    vi.stubGlobal('localStorage', {
      getItem() {
        throw new Error('denied')
      },
      setItem() {
        throw new Error('denied')
      },
    })
    expect(listPublished()).toEqual([])
    expect(() => publish(clip)).not.toThrow()
    vi.unstubAllGlobals()
  })
})
