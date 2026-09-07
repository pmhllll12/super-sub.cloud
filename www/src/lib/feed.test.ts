import { FEED, feedWith } from './feed'
import type { PublishedClip } from './published'

const mine: PublishedClip = {
  id: 'v3',
  title: '학교 끝나고 농구 연습',
  what: '디딤발이 공보다 앞서지 않는 순간',
  src: '/coach-c003.mp4',
  aspect: '1080 / 1920',
  at: '2026-09-04',
}

describe('영상 모음에 내가 공개한 것을 얹는다', () => {
  it('공개한 것이 없으면 원래 목록 그대로다', () => {
    expect(feedWith([], '홍길동')).toEqual(FEED)
  })

  // 방금 공개한 것이 뒤에 묻혀 있으면 공개가 됐는지 알 수가 없다.
  it('공개한 것이 맨 앞에 온다', () => {
    const list = feedWith([mine], '홍길동')
    expect(list).toHaveLength(FEED.length + 1)
    expect(list[0]).toMatchObject({
      title: '학교 끝나고 농구 연습',
      what: '디딤발이 공보다 앞서지 않는 순간',
      src: '/coach-c003.mp4',
      aspect: '1080 / 1920',
      by: '홍길동',
    })
  })

  // ⚠️ 계약 5장에 댓글이 없다 — 없는 것을 지어내지 않는다.
  it('내 영상에는 댓글이 붙어 있지 않다', () => {
    expect(feedWith([mine], '홍길동')[0].comments).toEqual([])
  })

  // 🔴 id 는 리액트 key 이자 좋아요의 기준이다. 겹치면 남의 영상에 불이 켜진다.
  it('id 가 원래 목록과 겹치지 않는다', () => {
    const ids = feedWith([{ ...mine, id: 'f-001' }], '홍길동').map((c) => c.id)
    expect(new Set(ids).size).toBe(ids.length)
  })
})
