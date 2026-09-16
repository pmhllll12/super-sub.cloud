import type { PublicVideo } from '@/server/backend'
import { FEED, feedWith } from './feed'

/**
 * 🔴 **남의 공개 영상까지 얹힌다**(CCC 20, 미결 `paik` 5번). 전에는 브라우저
 * 저장소라 내 것만 붙었다.
 */
const clip: PublicVideo = {
  id: 'v3',
  sport_code: 'basketball',
  duration_ms: 15600,
  created_at: '2026-09-04T11:05:00Z',
  title: '학교 끝나고 농구 연습',
  description: '디딤발이 공보다 앞서지 않는 순간',
  width: 1920,
  height: 1080,
}
const urls = { v3: 'https://s3.example.com/v3.mp4?sig=1' }

describe('영상 모음에 공개된 것을 얹는다', () => {
  it('공개한 것이 없으면 원래 목록 그대로다', () => {
    expect(feedWith([], {}, '홍길동')).toEqual(FEED)
  })

  // 방금 공개한 것이 뒤에 묻혀 있으면 공개가 됐는지 알 수가 없다.
  it('공개한 것이 맨 앞에 온다', () => {
    const list = feedWith([clip], urls, '홍길동')
    expect(list).toHaveLength(FEED.length + 1)
    expect(list[0]).toMatchObject({
      title: '학교 끝나고 농구 연습',
      what: '디딤발이 공보다 앞서지 않는 순간',
      by: '홍길동',
      at: '2026-09-04',
    })
  })

  /* 🔴 **저장 키가 아니라 사전 서명 주소다.** 목록에는 아예 안 실려 오므로
     클립마다 `playback-url` 로 따로 받는다(계약 3-6절). */
  it('재생 주소는 따로 받은 것을 쓴다', () => {
    expect(feedWith([clip], urls, '홍길동')[0].src).toBe(urls.v3)
  })

  /* 아직 주소를 못 받은 칸은 빈 문자열이다 — 그 칸만 플레이어 없이 그려지고
     목록이 통째로 안 무너진다. */
  it('주소를 아직 못 받았으면 비워 둔다', () => {
    expect(feedWith([clip], {}, '홍길동')[0].src).toBe('')
  })

  /* 계약이 제목에 `null` 을 허용한다 — 빈 자리로 두면 이름 없는 칸이 된다. */
  it('제목이 없으면 자리를 비우지 않는다', () => {
    const row = feedWith([{ ...clip, title: null, description: null }], urls, '홍길동')[0]
    expect(row.title).toBe('제목 없는 장면')
    expect(row.what).toBe('')
  })

  // ⚠️ 계약 5장에 댓글이 없다 — 없는 것을 지어내지 않는다.
  it('공개 영상에는 댓글이 붙어 있지 않다', () => {
    expect(feedWith([clip], urls, '홍길동')[0].comments).toEqual([])
  })

  // 🔴 id 는 리액트 key 이자 좋아요의 기준이다. 겹치면 남의 영상에 불이 켜진다.
  it('id 가 원래 목록과 겹치지 않는다', () => {
    const ids = feedWith([{ ...clip, id: 'f-001' }], urls, '홍길동').map((c) => c.id)
    expect(new Set(ids).size).toBe(ids.length)
  })

  /* 🔴 **칸은 영상 모양을 따라간다**(사용자 요청 — 세로로 찍은 것은 세로 그대로
     세운다). 서버가 `width`·`height` 를 주기 전에는 전부 16:9 로 가정해서, 폰으로
     세로로 찍어 올린 영상이 **가로 칸 안에 쪼그라들어** 좌우가 남았다. CCC 46
     (미결 `paik` 15번의 답)으로 목록에 실려 온다. */
  it('세로 영상은 세로 비율로 선다', () => {
    const row = feedWith([{ ...clip, width: 1080, height: 1920 }], urls, '홍길동')[0]
    expect(row.aspect).toBe('1080 / 1920')
  })

  it('가로 영상은 가로 비율로 선다', () => {
    expect(feedWith([clip], urls, '홍길동')[0].aspect).toBe('1920 / 1080')
  })

  /* 🔴 **옛 등록분은 둘 다 `null` 이다**(이 컬럼이 생기기 전). 계약이 "에러로
     다루지 말라"고 못 박았다 — 그때는 **지금까지의 동작(16:9 가정)** 그대로다. */
  it('비율을 모르는 옛 영상은 16:9 로 가정한다', () => {
    const row = feedWith([{ ...clip, width: null, height: null }], urls, '홍길동')[0]
    expect(row.aspect).toBe('16 / 9')
  })

  /* 한쪽만 온 응답은 계약에 없지만, 비율은 **둘이 다 있어야** 나온다. 한 칸을
     0 이나 1 로 메우면 칸이 화면을 넘거나 실처럼 눌린다 — 모르면 모른다고 둔다. */
  it('한쪽만 오면 비율을 지어내지 않는다', () => {
    expect(feedWith([{ ...clip, height: null }], urls, '홍길동')[0].aspect).toBe('16 / 9')
    expect(feedWith([{ ...clip, width: 0 }], urls, '홍길동')[0].aspect).toBe('16 / 9')
  })
})
