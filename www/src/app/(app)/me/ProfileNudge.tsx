'use client'

import { useEffect, useState } from 'react'
import SpotNudge from '@/components/SpotNudge'
import { ENTER_MS } from './ProfileStage'

/** 무엇이 모자라는가 — 그에 따라 밝힐 자리와 문장이 갈린다. */
const NUDGES = {
  /** 카드가 없다 → 빈 카드와 「프로필 카드 수정」. */
  card: {
    targets: ['.ss-profile-face .ss-pcard-inner', '.ss-profile-edit-link'],
    message: '먼저 내 카드를 만들어주세요.',
  },
  /** 카드는 있는데 팀이 없다 → 「팀 만들기」. 스쿼드 판도 경기 신청도 팀 밑이다. */
  team: {
    targets: ['.ss-team-create-btn'],
    message: '먼저 팀을 만들어주세요.',
  },
} as const

/**
 * **할 일이 남은 사람**이 내 프로필에 들어오면(사용자 요청, 2026-09-19) — 화면이 다
 * 들어온 뒤 어두워지며 할 일을 하는 단추만 밝게 두고, 그 오른쪽에 한 줄. 홈의
 * 「내 프로필에서 … 먼저 만들어주세요」와 같은 동작(5초 또는 어디든 한 번 누르면 걷힘).
 *
 * 순서는 **카드 → 팀**이다. 카드가 없으면 스쿼드 판에 설 것이 없고, 팀이 없으면
 * 설 판이 없다(부르는 쪽 `page.tsx` 가 가른다).
 * 🔴 **들어오는 연출이 끝난 뒤에** 켠다 — 먼저 켜면 아직 날아 들어오는 단추를 쫓아
 * 구멍이 움직인다.
 */
export default function ProfileNudge({ kind }: { kind: keyof typeof NUDGES }) {
  const [on, setOn] = useState(false)
  const [done, setDone] = useState(false)
  useEffect(() => {
    const t = setTimeout(() => setOn(true), ENTER_MS)
    return () => clearTimeout(t)
  }, [])
  if (!on || done) return null
  const n = NUDGES[kind]
  return <SpotNudge targets={[...n.targets]} message={n.message} note="right" onDone={() => setDone(true)} />
}
