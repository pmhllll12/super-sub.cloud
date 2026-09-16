'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { apiErrorMessage, apiPatch } from '@/lib/api/client'
import PillButton from '@/components/ui/PillButton'

/** 몇 개까지. 지금 화면이 칩 둘~셋이면 꽉 찬다. */
const MAX = 3
/** 한 줄 길이 — `tagline` 과 같은 값이고, AI 추천 판의 한 줄에 들어가야 한다. */
const MAX_LEN = 20

/**
 * **호칭 — 사람이 직접 적는다** (2026-09-16 결정, 미결 `paik` 36번).
 *
 * 🔴 **방향이 뒤집힌 자리다.** 원래는 분석이 붙이는 값이었고(계약 4장 「호칭은
 * 미부여 방식으로만 작동한다」), 그래서 화면은 읽기만 했다. 팀이 다시 정하면서
 * 사람이 적게 됐다 — 근거는 *"참이든 거짓이든 경기 후 리뷰로 남겨지니까
 * 상관없다"* 이고, 신뢰는 호칭이 아니라 리뷰가 떠받친다는 뜻이다.
 *
 * ⚠️ **저장 경로가 아직 계약에 없다**(36번). `PATCH /me/card` 에 `titles` 를
 * 실어 보내는데, **mock 만 받는다** — 진짜 서버가 그 칸을 열기 전까지 실서버
 * 에서는 저장이 안 된다. 🔴 그것을 숨기지 않고 실패하면 그대로 말한다.
 *
 * 🔴 **분류(강점 · 활동)를 안 받는다**(사용자 결정) — 자유 입력이라 분류를
 * 매길 사람이 없다. 읽는 쪽도 안 쓴다.
 */
export default function TitlesForm({ titles }: { titles: string[] }) {
  const router = useRouter()
  /**
   * 🔴 **서버가 돌려준 값을 여기 든다.** 서버 컴포넌트가 준 prop 만 믿으면
   * 개발 모드(`USE_MOCK=1`)에서 저장해도 화면이 안 바뀐다 — Next 가 서버
   * 컴포넌트와 라우트 핸들러를 **다른 모듈 그래프**로 컴파일해서 mock 이 두
   * 벌 생기고, 고친 쪽과 그리는 쪽이 갈린다(`mock.ts` 머리말. 실측: 라우트는
   * 새 호칭, 페이지는 옛 호칭). 지인 검색 스위치가 같은 자리에서 먼저 걸렸다.
   *
   * ⚠️ mock 을 위한 우회가 아니다 — `PATCH /me/card` 는 **고쳐진 카드를 그대로
   * 돌려준다**. 그 답을 버리고 화면을 다시 받아 오는 쪽이 한 번 더 도는 길이다.
   */
  const [shown, setShown] = useState<string[]>(titles)
  const [open, setOpen] = useState(false)
  /** 편집 중인 값. 빈 칸 하나는 늘 남겨 둔다 — 「추가」 단추를 따로 안 둔다. */
  const [values, setValues] = useState<string[]>(() => [...titles, ''].slice(0, MAX))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function setAt(i: number, v: string) {
    setValues((prev) => {
      const next = [...prev]
      next[i] = v
      // 마지막 칸을 채우면 빈 칸을 하나 더 내준다(상한까지).
      if (i === next.length - 1 && v.trim() && next.length < MAX) next.push('')
      return next
    })
  }

  async function save(e: React.FormEvent) {
    e.preventDefault()
    if (busy) return
    setBusy(true)
    setError(null)
    try {
      const next = values.map((v) => v.trim()).filter(Boolean)
      const saved = await apiPatch<{ titles?: { label: string }[] }>('/api/me/card', {
        titles: next,
      })
      // 서버가 말한 값으로 맞춘다. 안 실어 주는 옛 응답이면 보낸 값으로 둔다.
      setShown(saved?.titles?.map((t) => t.label) ?? next)
      setOpen(false)
      // 이 화면의 다른 자리(카드 미리보기 등)도 같은 카드에서 오므로 함께 맞춘다.
      router.refresh()
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      {/* 🔴 **비어 있을 때는 아무 말도 안 한다**(사용자 요청, 2026-09-16).
          앞서 「아직 정한 호칭이 없습니다」를 두었는데, 바로 옆에 「호칭
          정하기」 단추가 서 있어 **빈 것을 두 번 말하는** 자리였다. 단추만
          남으면 그 자리가 비었다는 것과 무엇을 할 수 있는지가 한 번에 읽힌다.

          🔴 여전히 **미달 표식은 아니다**(계약 4장) — 빈 것은 정상이라
          「없음」·자물쇠 같은 표를 대신 넣지 않는다. */}
      {shown.length > 0 && (
        <span className="ss-profile-pills">
          {shown.map((t) => (
            <span key={t} className="ss-profile-pill">
              {t}
            </span>
          ))}
        </span>
      )}

      <button
        type="button"
        className="ss-profile-titles-edit"
        aria-expanded={open}
        onClick={() => {
          setValues([...shown, ''].slice(0, MAX))
          setOpen((v) => !v)
          setError(null)
        }}
      >
        {open ? '접기' : shown.length === 0 ? '호칭 정하기' : '호칭 고치기'}
      </button>

      {/* 붙였다 뗐다 하지 않고 접는다 — 팀 만들기 폼과 같은 방식이다. */}
      <div className="ss-profile-form-fold" data-open={open ? 'true' : 'false'}>
        <div inert={!open}>
          <form onSubmit={save} className="ss-profile-account-form ss-form-compact">
            {values.map((v, i) => (
              <input
                key={i}
                type="text"
                className="ss-field-input ss-profile-title-input"
                aria-label={`호칭 ${i + 1}`}
                maxLength={MAX_LEN}
                value={v}
                placeholder="예: 시야가 넓은"
                onChange={(e) => setAt(i, e.target.value)}
              />
            ))}
            <p className="ss-profile-muted ss-profile-titles-hint">
              {MAX_LEN}자까지 · {MAX}개까지. 비우면 지워집니다.
            </p>
            <PillButton type="submit" disabled={busy} className="self-center">
              저장
            </PillButton>
          </form>
        </div>
      </div>

      {error && (
        <p role="alert" className="ss-profile-video-reason">
          {error}
        </p>
      )}
    </>
  )
}
