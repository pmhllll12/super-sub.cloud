'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { apiErrorMessage, apiPatch } from '@/lib/api/client'

/**
 * **지인 검색에 내 닉네임을 내보일 것인가** (계약 3-12절, CCC 37번).
 *
 * 지인 찾기 판이 닉네임으로 사람을 찾는데(`GET /users/search`), 그 목록에서
 * 빠지고 싶은 사람이 뺄 자리가 필요하다. 기본은 **켜져 있다**.
 *
 * 🔴 **용병 매칭의 `is_searchable` 과 다른 스위치다.** 그쪽은 「뛸 사람을
 * 찾는 팀에게 보일 것인가」이고 이쪽은 「아는 사람이 나를 찾을 수 있는가」다 —
 * 이름이 닮아 한 스위치로 합치고 싶어지지만, 끄는 이유가 서로 다르다.
 *
 * 🔴 **낙관적으로 바꾸지 않는다.** 껐다고 화면만 먼저 끄면, 저장이 실패했을
 * 때 그 사람은 꺼진 줄 알고 화면을 떠난다 — 검색에는 계속 뜨는데. 서버가
 * 답한 값으로만 바꾼다(`router.refresh()`).
 *
 * ⚠️ **제 판(`<section>`)을 안 그린다.** 「계정」 판 안에 들어앉는 줄이라
 * (사용자 요청, 2026-09-16) 판과 제목은 `AccountActions` 것 하나뿐이다 —
 * 판을 둘 두면 같은 성격의 설정이 두 덩어리로 갈려 보인다.
 */
export default function SearchablePref({ searchable }: { searchable: boolean }) {
  const router = useRouter()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function toggle() {
    if (busy) return
    setBusy(true)
    setError(null)
    try {
      /* 🔴 **이 칸만 보낸다.** 닉네임을 같이 실어 보내면 계약상 그것도 고치는
         요청이 된다 — 여기서 이름을 건드릴 이유가 없다. */
      await apiPatch('/api/me', { is_nickname_searchable: !searchable })
      router.refresh()
    } catch (e) {
      setError(apiErrorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <div className="ss-pref-row">
        <span className="ss-pref-text">
          <span className="ss-pref-name">지인 검색에 나를 보이기</span>
          <span className="ss-pref-note">
            {searchable
              ? '닉네임으로 나를 찾아 지인 신청을 보낼 수 있습니다.'
              : '아무도 나를 찾을 수 없습니다. 이미 맺은 지인은 그대로입니다.'}
          </span>
        </span>
        {/* 🔴 `role="switch"` + `aria-checked` — 켜짐/꺼짐이 있는 단추라는 것이
            낭독기에도 전해져야 한다. 글자만 바꾸면 눈으로만 알 수 있다. */}
        <button
          type="button"
          role="switch"
          aria-checked={searchable}
          aria-label="지인 검색에 나를 보이기"
          className="ss-pref-switch"
          data-on={searchable ? 'true' : undefined}
          disabled={busy}
          onClick={() => void toggle()}
        >
          <span className="ss-pref-knob" aria-hidden="true" />
        </button>
      </div>
      {error && (
        <p className="ss-pref-error" role="alert">
          {error}
        </p>
      )}
    </>
  )
}
