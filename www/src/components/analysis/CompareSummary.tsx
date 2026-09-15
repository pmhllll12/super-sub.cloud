'use client'

import { SIMILAR_DEG, describeComparison } from '@/lib/motion/describe'
import type { SummaryRequest } from '@/lib/motion/summaryContract'
import { MOMENT_LABEL, type MomentKey } from '@/lib/motion/types'

/**
 * 오른쪽 판 **내 분석 리포트 바로 아래**의 비교 요약(설계 §4).
 *
 * 🔴 **코드 규칙 문장이다**(`lib/motion/describe.ts`) — 서버를 부르지 않아 키 없이 로컬에서도
 * 보이고, 숫자가 늘 입력 그대로다. 줄을 누르면 세 순간 카드와 같은 동작(두 영상이 그 순간으로).
 */
export default function CompareSummary({
  playerName,
  request,
  failedReason,
  onSelect,
  onClose,
}: {
  playerName: string
  request: SummaryRequest | null
  failedReason: string | null
  onSelect: (key: MomentKey) => void
  /**
   * 비교를 걷는다 — 🔴 **선수 비교는 저장하지 않는다**(사용자 결정, 2026-09-15).
   * 닫으면 영상 칸 · 카드 · 이 절이 다 빠지고 내 리포트만 남는다.
   */
  onClose: () => void
}) {
  const head = (
    <div className="ss-compare-summary-head">
      <h3>비교 — {playerName}</h3>
      <button type="button" className="ss-compare-summary-close" aria-label="비교 닫기" onClick={onClose}>
        닫기
      </button>
    </div>
  )

  if (!request) {
    return (
      <section className="ss-compare-summary" aria-label={`비교 — ${playerName}`}>
        {head}
        <p>{failedReason ?? '비교할 수 없습니다'} — 슈팅 순간을 찾지 못해 비교하지 않았습니다.</p>
      </section>
    )
  }

  const text = describeComparison(request)
  return (
    <section className="ss-compare-summary" aria-label={`비교 — ${playerName}`}>
      {head}
      <p>{text.summary}</p>
      <ul className="ss-compare-summary-moments">
        {text.moments.map((m) => (
          <li key={m.key}>
            <button type="button" onClick={() => onSelect(m.key)}>
              <b>{MOMENT_LABEL[m.key]}</b>
              {m.lines.map((line) => (
                <span key={line} className="ss-compare-summary-line">
                  {line}
                </span>
              ))}
            </button>
          </li>
        ))}
      </ul>
      {/* 「브라우저에서 잰 값」 표기는 뺐다(사용자 요청, 2026-09-15). */}
      <p className="ss-compare-summary-note">차이 {SIMILAR_DEG}° 미만은 비슷함으로 봅니다</p>
    </section>
  )
}
