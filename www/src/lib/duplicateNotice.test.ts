import type { RegisteredVideo } from '@/server/backend'
import { duplicateNotice } from './duplicateNotice'

/**
 * **같은 영상을 다시 올렸을 때의 안내** (CCC 48, 미결 `ho` 41번).
 *
 * 🔴 사람들이 게이트에 걸린 영상을 **아홉 번 그대로 다시 올렸다** — 매번 같은
 * 이유로 떨어지는데 화면이 안 알려 줬기 때문이다.
 */
const base = { duplicate_of_video_id: 'v-앞서' } as RegisteredVideo

describe('duplicateNotice', () => {
  it('중복이 아니면 아무 말도 안 한다', () => {
    expect(duplicateNotice({} as RegisteredVideo)).toBeNull()
  })

  it('앞서 떨어졌으면 그 사유를 함께 말한다', () => {
    const msg = duplicateNotice({
      ...base,
      duplicate_status: 'failed',
      duplicate_failure_reason: '사람이 화면에 너무 작게 잡혔습니다',
    })
    expect(msg).toContain('앞서 같은 이유로 분석되지 않았습니다')
    expect(msg).toContain('사람이 화면에 너무 작게 잡혔습니다')
  })

  /* 🔴 사유를 지어내지 않는다 — 에이전트 문구가 아직 안 올 수 있다. */
  it('사유가 없으면 「같은 이유」까지만 말한다', () => {
    const msg = duplicateNotice({ ...base, duplicate_status: 'failed' })
    expect(msg).toBe('이 영상은 앞서 올렸을 때도 분석되지 않았습니다.')
  })

  it('앞서 성공했으면 그 결과를 쓴다고 말한다', () => {
    expect(duplicateNotice({ ...base, duplicate_status: 'succeeded' })).toContain(
      '그때 결과를 그대로 씁니다',
    )
  })

  /* 앞 작업이 도는 중이면 결과를 약속하지 않는다 — 그 작업이 실패하면
     「곧 나온다」가 거짓말이 된다. */
  it('앞 작업이 아직 도는 중이면 결과를 약속하지 않는다', () => {
    for (const status of ['queued', 'running', null] as const) {
      const msg = duplicateNotice({ ...base, duplicate_status: status })
      expect(msg).toBe('이 영상은 앞서 올린 것과 같습니다 — 새로 분석하지 않았습니다.')
    }
  })
})
