'use client'

import { useEffect, useState } from 'react'
import SpotNudge from '@/components/SpotNudge'
import { ENTER_MS } from './ProfileStage'

/**
 * **아직 카드가 없는 사람**이 내 프로필에 들어오면(사용자 요청, 2026-09-19) —
 * 화면이 다 들어온 뒤 어두워지며 카드 자리와 「프로필 카드 수정」만 밝게 두고,
 * 그 단추 오른쪽에 「먼저 내 카드를 만들어주세요.」를 띄운다. 홈의 「내 프로필에서
 * 카드를 먼저 만들어주세요」와 같은 동작(5초 또는 어디든 한 번 누르면 걷힘).
 *
 * 🔴 **카드가 있으면 안 부른다**(부르는 쪽이 가른다) — 프로필에 들어올 때마다가
 * 아니라 카드 없는 사람에게만이다(사용자 정정).
 * 🔴 **들어오는 연출이 끝난 뒤에** 켠다 — 먼저 켜면 아직 날아 들어오는 카드
 * 자리를 쫓아 구멍이 움직인다.
 */
export default function NoCardNudge() {
  const [on, setOn] = useState(false)
  const [done, setDone] = useState(false)
  useEffect(() => {
    const t = setTimeout(() => setOn(true), ENTER_MS)
    return () => clearTimeout(t)
  }, [])
  if (!on || done) return null
  return (
    <SpotNudge
      targets={['.ss-profile-face', '.ss-profile-edit-link']}
      message="먼저 내 카드를 만들어주세요."
      note="right"
      onDone={() => setDone(true)}
    />
  )
}
