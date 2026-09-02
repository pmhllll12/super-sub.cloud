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
/** 신청 단추. 🔴 신청서와 **떨어져 있다** — 단추는 머리글 오른쪽에 남고 신청서는
    머리글 **아래**에서 펴진다(사용자 요청). 그래서 여는 상태는 밖(`CoachDetail`)이
    쥐고, 여기서는 모양만 맡는다. */
export function LessonApplyButton({
  onClick,
  /** 신청서가 펴져 있는가 — 그동안 이 단추는 흐려져 물러난다. */
  hidden,
}: {
  onClick: () => void
  hidden: boolean
}) {
  return (
    <button
      type="button"
      className="ss-apply-open"
      data-hidden={hidden}
      // 흐려진 동안에는 자판으로도 안 걸린다 — 보이지 않는 것을 누를 수는 없다.
      inert={hidden || undefined}
      onClick={onClick}
    >
      레슨 신청
    </button>
  )
}

export default function LessonApply({
  coachName,
  /** 내 리포트에서 고를 수 있는 항목. 지금은 자리 표시다. */
  myFindings,
  /** 펴져 있는가. 단추가 머리글에 따로 있으므로 밖에서 받는다. */
  open,
  onClose,
}: {
  coachName: string
  myFindings: string[]
  open: boolean
  onClose: () => void
}) {
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

  return (
    /* 🔴 **높이를 격자 칸(0fr ↔ 1fr)으로 여닫는다.** `max-height` 로 하면 넉넉한
       값을 미리 찍어 둬야 하고, 그 값이 실제 높이와 다른 만큼 여는 동안 빨라졌다
       느려진다(거름망 서랍과 같은 방식).
       🔴 접혀 있을 때는 **낭독기에도 없어야** 한다 — 눈에만 안 보이게 하면 폼
       칸들이 그대로 읽히고 자판 이동에도 걸린다. */
    <div className="ss-apply-drawer" data-open={open} aria-hidden={!open}>
      <div className="ss-apply-drawer-inner">
    <form
      className="ss-apply"
      // 접힌 동안에는 자판으로도 안 걸린다.
      inert={!open || undefined}
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
        {/* 🔴 '신청 보내기' 와 **같은 크기 · 같은 글자**다(사용자 요청). 하는 일이
            반대라 색만 다르다 — 크기가 다르면 둘 중 하나가 덜 중요한 조작으로
            보이는데, 여기서는 둘 다 이 신청서를 끝내는 길이다. */}
        <button type="button" className="ss-apply-close" onClick={onClose}>
          닫기
        </button>
      </div>
    </form>
      </div>
    </div>
  )
}
