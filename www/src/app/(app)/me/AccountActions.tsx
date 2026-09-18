'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { apiDelete, apiErrorMessage, apiPost } from '@/lib/api/client'
import Field from '@/components/ui/Field'
import PillButton from '@/components/ui/PillButton'
import { SECTION_GLASS } from './glass'
import SearchablePref from './SearchablePref'

/**
 * 계정 다루기 — **로그아웃과 탈퇴**.
 *
 * ⚠️ 비밀번호 변경은 화면을 **나중에** 붙이기로 했다(사용자 요청). 계약 쪽은
 * 이미 다 들어와 있다 — `Backend.changePassword` 와 `PATCH /api/me/password`
 * (세션 쿠키까지 지운다). 화면만 여기 한 절 더 두면 된다.
 *
 * 🔴 **평소에는 접혀 있다.** 프로필은 보여주는 화면인데 탈퇴는 되돌릴 수 없는
 * 동작이라, 단추가 늘 펴져 있으면 실수로 누를 자리가 늘 열려 있는 셈이다.
 */
export default function AccountActions({
  searchable,
  nickname,
}: {
  searchable: boolean
  /** 아래 스위치가 `PATCH /me` 에 **함께 실어야** 하는 값 — 계약이 늘 받는다. */
  nickname: string
}) {
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [password, setPassword] = useState('')

  /**
   * **로그아웃** — 세션 쿠키만 지운다(`LogoutButton` 과 같은 경로).
   *
   * 🔴 홈의 로그아웃은 `router.refresh()` 로 제자리에 머물지만 여기는
   * **`/login` 으로 옮긴다.** `/me` 는 로그인해야 열리는 화면이라, 쿠키를
   * 지운 자리에 그대로 두면 **방금 지운 내 정보가 화면에 남아 있다가**
   * 다음 요청에서야 튕긴다. 탈퇴가 같은 자리로 보내는 것과 같은 이유다.
   */
  async function onLogout() {
    setError(null)
    setBusy(true)
    try {
      await apiPost('/api/auth/logout', {})
      router.replace('/login')
    } catch (err) {
      setError(apiErrorMessage(err))
      setBusy(false)
    }
    /* 🔴 성공하면 `busy` 를 **안 되돌린다** — 화면이 곧 바뀌는데 단추가
       다시 눌리게 두면 그 사이에 두 번 나갈 수 있다. */
  }

  async function onDelete(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      /* 🔴 비밀번호를 **빈 문자열이면 안 보낸다.** 구글로만 가입한 계정에는
         확인할 비밀번호가 없어서, 빈 값을 보내면 서버가 틀린 비밀번호로 읽어
         탈퇴할 방법이 사라진다(계약 2장). */
      await apiDelete('/api/me', password ? { password } : undefined)
      // 계정이 없어졌다. 라우트 핸들러가 쿠키를 지우므로 자리만 옮기면 된다.
      router.replace('/login')
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="ss-profile-account" style={SECTION_GLASS}>
      <h2 className="ss-profile-h">계정</h2>

      {/* 🔴 **공개 범위가 판의 왼쪽 위**다(사용자 요청, 2026-09-16). 평소에
          보고 만지는 설정이라 위에 오고, 되돌릴 수 없는 탈퇴는 아래 구석으로
          간다 — 자주 쓰는 것이 위, 위험한 것이 아래다. */}
      <SearchablePref searchable={searchable} nickname={nickname} />

      {/* 🔴 **오른쪽 아래**(사용자 요청). 판 안에서 제일 눈에 안 띄는 자리다 —
          실수로 누를 자리가 늘 열려 있지 않게. */}
      <div className="ss-profile-account-foot">
        {/* 🔴 **로그아웃이 탈퇴 왼쪽에 선다**(사용자 요청, 2026-09-18). 여태
            로그아웃은 홈 오른쪽 아래 구석에만 있어서, 프로필을 보다가 나가려면
            홈으로 되돌아가야 했다.

            🔴 **접지 않고, 빨갛지도 않다.** 탈퇴를 접어 둔 이유는 되돌릴 수
            없어서인데(위 머리말) 로그아웃은 다시 로그인하면 그만이다. 같은
            줄에서 빨강을 나눠 쓰면 **탈퇴의 빨강이 경고로 안 읽힌다.**
            위험한 쪽이 **오른쪽 끝**이다(자주 쓰는 것 먼저). */}
        <button
          type="button"
          className="ss-profile-tab ss-profile-tab--sm"
          disabled={busy}
          onClick={onLogout}
        >
          로그아웃
        </button>
        <button
          type="button"
          className="ss-profile-tab ss-profile-tab--sm ss-profile-tab--danger"
          aria-expanded={open}
          onClick={() => {
            setOpen((v) => !v)
            setError(null)
          }}
        >
          회원 탈퇴
        </button>
      </div>

      {/* 🔴 탈퇴 폼이 닫혀 있어도 로그아웃 실패는 말해야 한다 — 폼 안에 두면
          접힌 동안 통째로 안 보인다. */}
      {!open && error && (
        <p role="alert" className="ss-profile-video-reason">
          {error}
        </p>
      )}

      {open && (
        <form onSubmit={onDelete} className="ss-profile-account-form ss-form-compact">
          <p className="ss-profile-muted">
            탈퇴하면 카드 · 호칭 · 소속과 올린 영상이 함께 지워집니다. 되돌릴 수 없습니다.
          </p>
          <Field
            label="비밀번호"
            type="password"
            value={password}
            onChange={setPassword}
            hint="구글로만 가입했다면 비워 두세요"
          />
          {error && (
            <p role="alert" className="ss-profile-video-reason">
              {error}
            </p>
          )}
          <PillButton type="submit" disabled={busy} className="self-start">
            탈퇴하기
          </PillButton>
        </form>
      )}
    </section>
  )
}
