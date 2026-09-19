import type { RegisteredVideo } from '@/server/backend'

/**
 * **같은 영상을 다시 올렸을 때 그 자리에서 할 말** (CCC 48, 미결 `ho` 41번).
 *
 * 🔴 **왜 있나**: 게이트에 걸려 떨어진 영상을 사람들이 **아홉 번까지 그대로
 * 다시 올렸다** — 매번 같은 이유로 떨어지는데 화면이 그 사실을 안 알려 줬기
 * 때문이다. 서버는 이제 새 분석을 안 걸고 앞 결과를 등록 응답에 실어 준다.
 *
 * 🔴 **막지 않는다.** 이건 **안내**지 차단이 아니다(계약의 「하지 말 것」) —
 * 촬영을 다시 해서 올린 것일 수도 있다.
 *
 * 🔴 **받는 즉시 써야 한다.** 이 세 필드는 **등록 응답에만** 산다 — 나중에
 * `GET /videos` 로 같은 영상을 읽으면 전부 `null` 이라 다시 볼 방법이 없다.
 *
 * 값이 없으면 `null` — 부르는 쪽은 그때 아무것도 안 보이면 된다.
 */
export function duplicateNotice(v: RegisteredVideo): string | null {
  if (!v.duplicate_of_video_id) return null

  if (v.duplicate_status === 'failed') {
    const why = v.duplicate_failure_reason?.trim()
    /* 🔴 **사유를 지어내지 않는다.** 에이전트 문구가 아직 안 올 수 있고
       (정상호 몫), 그때는 「같은 이유」까지만 말한다 — 없는 이유를 채우면
       사람이 엉뚱한 곳을 고치러 간다. */
    return why
      ? `이 영상은 앞서 같은 이유로 분석되지 않았습니다 — ${why}`
      : '이 영상은 앞서 올렸을 때도 분석되지 않았습니다.'
  }

  if (v.duplicate_status === 'succeeded') {
    return '이 영상은 앞서 분석한 것과 같습니다 — 그때 결과를 그대로 씁니다.'
  }

  /* `queued`·`running`·값이 없는 경우. **앞 작업이 아직 도는 중**이라 결과를
     약속하지 않는다 — 「곧 나온다」고 적었다가 그 작업이 실패하면 거짓말이 된다. */
  return '이 영상은 앞서 올린 것과 같습니다 — 새로 분석하지 않았습니다.'
}
