'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { apiDelete, apiErrorMessage } from '@/lib/api/client'
import Field from '@/components/ui/Field'
import PillButton from '@/components/ui/PillButton'
import { SECTION_GLASS } from './glass'
import SearchablePref from './SearchablePref'

/**
 * 계정 다루기 — 지금은 **탈퇴만** 있다.
 *
 * ⚠️ 비밀번호 변경은 화면을 **나중에** 붙이기로 했다(사용자 요청). 계약 쪽은
 * 이미 다 들어와 있다 — `Backend.changePassword` 와 `PATCH /api/me/password`
 * (세션 쿠키까지 지운다). 화면만 여기 한 절 더 두면 된다.
 *
 * 🔴 **평소에는 접혀 있다.** 프로필은 보여주는 화면인데 탈퇴는 되돌릴 수 없는
 * 동작이라, 단추가 늘 펴져 있으면 실수로 누를 자리가 늘 열려 있는 셈이다.
 */
export default function AccountActions({ searchable }: { searchable: boolean }) {
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [password, setPassword] = useState('')

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
      <SearchablePref searchable={searchable} />

      {/* 🔴 **오른쪽 아래**(사용자 요청). 판 안에서 제일 눈에 안 띄는 자리다 —
          실수로 누를 자리가 늘 열려 있지 않게. */}
      <div className="ss-profile-account-foot">
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
