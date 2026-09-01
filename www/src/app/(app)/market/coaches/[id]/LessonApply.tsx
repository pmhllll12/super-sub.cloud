'use client'

import { useState } from 'react'

/**
 * 레슨 신청 시트.
 *
 * 🔴 **내 분석 리포트가 신청서에 붙어서 간다.** 숨고에는 "축구 배우고 싶어요"가
 * 오지만, 우리는 코치가 **무엇을 봐야 하는지 알고** 시작한다. 신청까지만 하는
 * A 안이 남들보다 나은 지점이 여기다(설계 문서 1-2).
 *
 * ⚠️ 보내는 곳이 아직 없다 — 계약에 `coach_referral` 생성 엔드포인트가 없다
 * (테이블은 부록 D ⑥ 에 있다). 지금은 보낸 척하고 확인만 보여준다.
 *
 * 🔴 나중에 B(예약 · 결제)로 갈 때 **이 시트만 바뀐다.** "연락처가 열린다"를
 * "시간을 고르고 결제한다"로 바꾸면 되고, 목록 · 상세는 그대로다.
 */
export default function LessonApply({
  coachName,
  /** 내 리포트에서 고를 수 있는 항목. 지금은 자리 표시다. */
  myFindings,
}: {
  coachName: string
  myFindings: string[]
}) {
  const [open, setOpen] = useState(false)
  const [sent, setSent] = useState(false)
  const [picked, setPicked] = useState<string[]>([])

  function toggle(f: string) {
    setPicked((prev) => (prev.includes(f) ? prev.filter((x) => x !== f) : [...prev, f]))
  }

  if (sent) {
    return (
      <div className="ss-apply-done" role="status">
        <b>신청을 보냈습니다.</b>
        <p>
          {coachName} 코치가 수락하면 연락처가 열립니다. 진행 상황은{' '}
          <a href="/me/lessons">내 레슨</a>에서 볼 수 있습니다.
        </p>
      </div>
    )
  }

  if (!open) {
    return (
      <button type="button" className="ss-apply-open" onClick={() => setOpen(true)}>
        레슨 신청
      </button>
    )
  }

  return (
    <form
      className="ss-apply"
      onSubmit={(e) => {
        e.preventDefault()
        setSent(true)
      }}
    >
      <fieldset>
        <legend>무엇을 고치고 싶으신가요?</legend>
        {/* 🔴 내 리포트에서 고른다 — 이게 이 신청서의 전부다. */}
        {myFindings.map((f) => (
          <label key={f} className="ss-apply-pick">
            <input type="checkbox" checked={picked.includes(f)} onChange={() => toggle(f)} />
            <span>{f}</span>
          </label>
        ))}
        <label className="ss-apply-field">
          <span>직접 적기</span>
          <input type="text" name="own" placeholder="예: 왼발 킥이 뜹니다" />
        </label>
      </fieldset>

      <div className="ss-apply-row">
        <label className="ss-apply-field">
          <span>희망 날짜</span>
          <input type="date" name="date" />
        </label>
        <label className="ss-apply-field">
          <span>시간대</span>
          <input type="text" name="hours" placeholder="평일 저녁" />
        </label>
      </div>

      <label className="ss-apply-field">
        <span>하고 싶은 말</span>
        <textarea name="note" rows={3} placeholder="처음 배웁니다" />
      </label>

      <div className="ss-apply-acts">
        <button type="submit" className="ss-apply-send">
          신청 보내기
        </button>
        <button type="button" className="ss-shot-pick-auto" onClick={() => setOpen(false)}>
          닫기
        </button>
      </div>
    </form>
  )
}
