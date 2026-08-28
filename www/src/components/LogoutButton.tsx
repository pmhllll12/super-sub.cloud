'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { apiErrorMessage, apiPost } from '@/lib/api/client'

/**
 * 홈 우상단 헤더(워드마크 반대편)의 "로그인 · 회원가입" / "닉네임 ·
 * 로그아웃" — 참고 디자인처럼 알약 버튼이 아니라 글자만 있는 링크
 * 모양이다. `HomeParallax` 의 로그인·회원가입 링크와 이 로그아웃
 * 버튼이 같은 클래스를 공유해야 나란히 있을 때 모양이 어긋나지
 * 않는다 — 그래서 여기서 정의해 내보낸다(로그아웃이 먼저 이 모양이
 * 필요했던 자리라 여기 둔다).
 *
 * 글자만 남아도 클릭 영역이 너무 작아지면 안 된다 — px-2 py-3 로
 * 늘려서 실제 눌리는 높이가 글자 높이(20px)보다 훨씬 넉넉하다(실측
 * 44px, 손가락 탭 기준으로 흔히 쓰는 최소값과 맞춘다).
 *
 * 호버(밑줄) 부분은 별도 상수(HEADER_LINK_HOVER_CLASS)로 뺐다 — 닉네임
 * 처럼 눌리지 않는 자리는 이 hover 클래스 없이 HEADER_LINK_CLASS 만
 * 쓴다(같은 className 문자열 안에 hover:underline 을 넣고 뒤에
 * hover:no-underline 을 덧붙이는 식으로는 이길 거란 보장이 없다 —
 * Tailwind 는 등장 순서가 아니라 생성된 스타일시트 순서로 우선순위가
 * 정해진다). */
export const HEADER_LINK_CLASS = 'inline-flex items-center rounded-full px-2 py-3 text-sm font-medium transition disabled:opacity-50'
export const HEADER_LINK_HOVER_CLASS = 'underline-offset-4 hover:underline'

/**
 * `/api/auth/logout` 은 세션 쿠키를 지우기만 하고 어디로도 보내지 않는다.
 * `/` 가 이미 홈이라 이동할 필요가 없다 — `router.refresh()` 로 서버
 * 컴포넌트(`Home`)를 다시 그리게 해서 "로그인 함" 모습이 그 자리에서
 * "로그인 안 함"(로그인 · 회원가입 링크) 모습으로 바뀌게 한다.
 *
 * 로그아웃은 이동이 아니라 요청을 보내는 동작이라 `<button>` 이 맞다 —
 * 겉모습만 로그인·회원가입 링크와 같게 맞춘다.
 */
export default function LogoutButton() {
  const router = useRouter()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function onClick() {
    setError(null)
    setBusy(true)
    try {
      await apiPost('/api/auth/logout', {})
      router.refresh()
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col items-center gap-1">
      <button
        type="button"
        onClick={onClick}
        disabled={busy}
        className={`${HEADER_LINK_CLASS} ${HEADER_LINK_HOVER_CLASS}`}
        style={{ color: 'color-mix(in srgb, var(--ss-fg) 70%, transparent)' }}
      >
        로그아웃
      </button>
      {error && (
        <p role="alert" className="text-xs" style={{ color: 'var(--ss-error)' }}>
          {error}
        </p>
      )}
    </div>
  )
}
