'use client'

import { useRouter } from 'next/navigation'
import { useId, useState } from 'react'
import { ApiCallError, apiDelete, apiErrorMessage, apiPatch, apiPost } from '@/lib/api/client'
import { rememberHomeTeam } from '@/lib/homeTeam'
import { REGIONS, searchRegions } from '@/lib/regions'
import PillButton from '@/components/ui/PillButton'
import MatchPrefsForm from '@/components/MatchPrefs'
import { loadTeamPrefs, saveTeamPrefs } from '@/lib/teamPrefsStore'
import { EMPTY_PREFS, type MatchPrefs } from '@/lib/matchPrefs'

/**
 * 팀 만들기 폼 전용 입력칸 — **적은 만큼만 넓어진다**(사용자 요청, 2026-09-16).
 *
 * 🔴 **공용 `ui/Field` 를 안 쓴다.** 그것은 로그인·가입도 쓰는데, 거기서는
 * 칸이 판 너비를 꽉 채우는 것이 맞다(이메일·비밀번호는 길다). 공용 쪽에
 * 늘어나는 성질을 넣으면 그 화면들이 같이 바뀐다.
 *
 * 🔴 **너비는 CSS 가 잰다.** `size` 속성은 「0」 글자 폭으로 세는 것이라 한글
 * 에서 절반쯤 좁게 나오고, JS 로 재면 글자마다 렌더가 한 번 더 돈다. 감춘
 * 쌍둥이(`::after` 의 `content: attr(data-value)`)를 같은 칸에 겹쳐 두면
 * **어떤 글자든 브라우저가 알아서** 잰다(`globals.css` 의 `.ss-team-grow`).
 */
function GrowField({
  label,
  value,
  onChange,
  hint,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  hint?: string
}) {
  const id = useId()
  return (
    <div className="ss-team-field">
      {/* ⚠️ **예시는 라벨 옆 괄호로**(사용자 요청, 2026-09-16). 칸 아래 따로
          두었더니 한 줄을 더 먹으면서 「만들기」가 그만큼 밀려 내려갔고,
          가운데 정렬 속에서 저 혼자 왼쪽이라 떠 보였다. */}
      <label htmlFor={id}>
        {label}
        {hint && <span className="ss-team-hint"> ({hint})</span>}
      </label>
      {/* 🔴 `data-value` 가 **자(尺)** 노릇을 한다 — 값이 바뀌면 감춘 쌍둥이도
          같이 바뀌고, 칸이 그만큼 넓어진다. 빈 값일 때는 `min-width` 가 받쳐
          칸이 사라지지 않는다. */}
      <span className="ss-team-grow" data-value={value}>
        {/* 🔴 `size={1}` 이 있어야 한다. `<input>` 은 기본이 `size=20` 이라
            **제 힘으로 스무 글자만큼 자리를 차지하고**, 격자가 그 값을 따라
            가 버린다(실측: 빈 칸이 176px). 1 로 낮춰야 감춘 쌍둥이가 너비를
            정한다. */}
        <input
          id={id}
          size={1}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
      </span>
    </div>
  )
}

/** 적은 글자가 목록의 지역과 정확히 같은가 — 저장해도 되는 값인가. */
export function isRegion(value: string): boolean {
  return REGIONS.includes(value.trim())
}

/**
 * 지역 칸 — **자유 입력이지만 저장되는 값은 목록의 것**이다.
 *
 * 🔴 **왜 자유 입력만 두지 않나.** 「강남」·「강남구」·「서울 강남구」가 다 다른
 * 값으로 저장되면 **대조가 통째로 깨진다** — 「사람을 찾는 팀」이 지역으로
 * 거르기 때문에, 형식이 어긋난 팀은 경기가 검색에서 빠진다. 계약 52번이
 * 「고칠 수 있게」를 급하다고 한 이유가 정확히 그것이라, 고치는 자리에서 다시
 * 어긋난 값을 받으면 고쳐도 소용이 없다.
 *
 * 🔴 **경기 조건 판과 같은 방식**이다(`MatchPrefs`) — 거기는 여러 동네를
 * 고르고 여기는 하나라 마크업만 다르고, 후보는 같은 `searchRegions` 다.
 */
function RegionField({
  label,
  value,
  onChange,
}: {
  label: string
  value: string
  onChange: (v: string) => void
}) {
  const id = useId()
  const hits = searchRegions(value)
  const exact = isRegion(value)
  return (
    <div className="ss-team-field">
      <label htmlFor={id}>
        {label}
        <span className="ss-team-hint"> (예: 서울 강남구)</span>
      </label>
      <span className="ss-team-grow" data-value={value}>
        <input
          id={id}
          size={1}
          value={value}
          autoComplete="off"
          onChange={(e) => onChange(e.target.value)}
        />
      </span>
      {/* 고른 값과 똑같은 후보 하나만 남았으면 더 보여 줄 것이 없다. */}
      {hits.length > 0 && !(exact && hits.length === 1) && (
        <ul className="ss-team-hits">
          {hits.map((r) => (
            <li key={r}>
              <button type="button" className="ss-team-hit" onClick={() => onChange(r)}>
                {r}
              </button>
            </li>
          ))}
        </ul>
      )}
      {/* 🔴 **비어 있으면 고장으로 읽힌다** — 목록에 없다고 말한다. 지금 팀에
          적혀 있는 값이 목록 밖일 때(예전 자유 입력분)도 이 줄이 뜬다. */}
      {value.trim() && hits.length === 0 && (
        <p className="ss-team-none">그런 동네가 목록에 없습니다.</p>
      )}
    </div>
  )
}

/**
 * 「소속」 절의 손짓 — **팀 만들기**와 **팀 나가기**.
 *
 * 🔴 **팀이 없으면 이 서비스가 거의 안 돈다.** 스쿼드 · 경기 신청 · 알림이
 * 전부 `teams/{id}` 밑이라, 새로 가입한 사람은 팀을 만들기 전까지 홈이 빈
 * 판이다. 계약(`POST /teams`)은 처음부터 있었는데 화면이 없어서 실제로는
 * 팀을 만들 방법이 없었다(2026-09-16에 붙임).
 *
 * 🔴 **종목을 안 묻는다**(사용자 결정) — 지금은 풋살만 다룬다. BFF 가 상수로
 * 채운다(`app/api/teams/route.ts`). 종목이 늘면 그 자리와 여기를 같이 연다.
 *
 * 🔴 **마지막 주장은 못 나간다**(`409 LAST_OWNER`). 화면에서 미리 막지 않고
 * 서버가 준 문구를 그대로 보여 준다 — 조건(주장이 몇이냐)은 서버만 알고,
 * 화면이 짐작해서 막으면 나갈 수 있는 사람까지 막힌다.
 */
export default function TeamActions({
  teams,
  userId,
  homeTeamId,
}: {
  teams: { team_id: string; name: string; region: string; sport_code: string; role: string }[]
  /** 나가기가 이 id 로 나간다 — 계약의 `member_id` 는 곧 `user_id` 다. */
  userId: string
  /** 지금 홈에 보이는 팀. 소속이 여럿일 때만 고를 자리가 난다. */
  homeTeamId?: string
}) {
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [region, setRegion] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  /** 나가는 중인 팀 — 여러 팀이 있어도 누른 줄만 잠긴다. */
  const [leaving, setLeaving] = useState<string | null>(null)
  /**
   * **해체를 권할 팀** — 나가기가 `409 LAST_OWNER` 로 막힌 그 팀이다.
   *
   * 🔴 **서버가 그렇게 답했을 때만 찬다.** 주장이 몇인지는 서버만 알고,
   * 화면이 짐작해서 미리 해체를 들이밀면 **나갈 수 있는 사람이 팀을 없앤다.**
   */
  const [disbandable, setDisbandable] = useState<string | null>(null)
  /**
   * **이미 떠난 팀** — 나갔거나 해체한 팀의 id.
   *
   * 🔴 **`router.refresh()` 하나로는 모자랐다**(사용자 지적, 2026-09-18:
   * 「팀 해체 했는데, 팀 왜 안사라지고 …아예 안나와야지」). 개발 모드에서
   * Next 는 라우트 핸들러와 서버 컴포넌트를 **다른 모듈 그래프**로 묶어서,
   * mock 을 고친 쪽과 목록을 그리는 쪽이 갈린다 — 해체는 됐는데 줄이 그대로
   * 남았고, 거기서 나가기를 다시 누르니 **「구성원이 아닙니다」**가 떴다.
   * (1.11 회차가 스위치·호칭에서 겪고 「응답을 쓰라」고 적어 둔 그 함정이다.)
   *
   * 🔴 **mock 우회가 아니다.** 실서버에서도 다시 받아 오기를 기다리지 않고
   * 그 자리에서 사라지는 편이 맞다 — `router.refresh()` 는 그대로 두고,
   * 돌아온 목록에 그 팀이 없으면 이 값은 그냥 아무 일도 안 한다.
   */
  const [left, setLeft] = useState<string[]>([])
  /** 지금 고치는 중인 팀. 한 번에 하나만 편다 — 여럿이 펴져 있으면 어느 것을
   *  저장하는지가 안 읽힌다. */
  const [editing, setEditing] = useState<string | null>(null)
  const [editName, setEditName] = useState('')
  const [editRegion, setEditRegion] = useState('')
  const [saving, setSaving] = useState(false)
  /**
   * **경기 조건 판을 연 팀** (사용자 지적, 2026-09-18).
   *
   * 🔴 **여기가 없으면 스스로 빠져나올 수 없다.** 조건을 고치는 자리가
   * 「팀 매칭」 판 안에만 있었는데 그 판은 **스쿼드가 다 차야** 열린다.
   * 그런데 서버는 「팀이 경기 시간을 등록해 뒀으면 그 시간과 겹치는
   * 사람만」 추천 후보로 준다 — **시간을 한 번 잘못 저장하면 후보가 0명이
   * 되고 → 스쿼드를 못 채우고 → 고칠 판도 못 연다.** 실서버의 심사위원
   * 계정이 정확히 그 상태였다.
   */
  const [prefsFor, setPrefsFor] = useState<string | null>(null)
  /** 그 팀의 지금 조건. **`null` 은 「아직 안 정했다」**(빈 조건과 다르다). */
  const [teamPrefs, setTeamPrefs] = useState<MatchPrefs | null>(null)
  const [prefsBusy, setPrefsBusy] = useState(false)

  /**
   * **시간 조건만 비운다** — 지역은 그대로 둔다.
   *
   * 🔴 **왜 필요한가.** 서버는 「팀이 경기 시간을 등록해 뒀으면 그 시간과
   * 겹치는 사람만」 추천 후보로 준다. 시간이 **없으면 그 필터를 통째로
   * 건너뛴다** — 그래서 후보가 0명일 때 빠져나오는 가장 확실한 길이다.
   */
  async function clearTimes(teamId: string) {
    if (prefsBusy) return
    setError(null)
    setPrefsBusy(true)
    try {
      const now = (await loadTeamPrefs(teamId)) ?? EMPTY_PREFS
      const next = { ...now, times: [] }
      await saveTeamPrefs(teamId, next)
      setTeamPrefs(next)
    } catch {
      setError('시간 조건을 지우지 못했습니다 — 다시 시도해 주세요.')
    } finally {
      setPrefsBusy(false)
    }
  }

  async function openPrefs(teamId: string) {
    if (prefsFor === teamId) {
      setPrefsFor(null)
      return
    }
    setError(null)
    setPrefsBusy(true)
    /* 🔴 **지금 값부터 읽는다.** 빈 판을 먼저 열면 「그만두기」를 안 누르고
       저장했을 때 있던 조건이 통째로 지워진다 — 이 판은 **통째로 교체**다. */
    try {
      setTeamPrefs(await loadTeamPrefs(teamId))
    } catch {
      setTeamPrefs(null)
    } finally {
      setPrefsBusy(false)
      setPrefsFor(teamId)
    }
  }

  function openEdit(t: { team_id: string; name: string; region: string }) {
    setError(null)
    if (editing === t.team_id) {
      setEditing(null)
      return
    }
    setEditing(t.team_id)
    // 🔴 **지금 값으로 채운다** — 빈 칸에서 시작하면 「둘 다 새로 적어야 하나」가
    //    되고, 안 바꿀 필드까지 사람이 다시 적게 된다.
    setEditName(t.name)
    setEditRegion(t.region)
  }

  async function save(teamId: string, was: { name: string; region: string }) {
    if (saving) return
    /* 🔴 **바뀐 것만 싣는다**(계약의 「하지 말 것」) — 안 바꿀 필드는 `null` 도
       빈 값도 아니고 **아예 빼야** 한다. 둘 다 그대로면 부를 것이 없다. */
    const patch: { name?: string; region?: string } = {}
    if (editName.trim() !== was.name) patch.name = editName.trim()
    if (editRegion.trim() !== was.region) patch.region = editRegion.trim()
    if (Object.keys(patch).length === 0) {
      setEditing(null)
      return
    }
    setSaving(true)
    setError(null)
    try {
      await apiPatch(`/api/teams/${encodeURIComponent(teamId)}`, patch)
      setEditing(null)
      router.refresh()
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  async function create(e: React.FormEvent) {
    e.preventDefault()
    if (busy) return
    setBusy(true)
    setError(null)
    try {
      const made = await apiPost<{ id: string }>('/api/teams', { name, region })
      /* 🔴 **스쿼드도 같이 연다.** 팀만 만들면 `GET /teams/{id}/squad` 가
         404 라 홈 판이 빈 채로 뜨고, 거기 넣은 사람이 서버에 안 남는다.
         멱등이라 두 번 불러도 안전하다(계약 3-7절). */
      await apiPost(`/api/teams/${encodeURIComponent(made.id)}/squad`, {}).catch(() => {
        /* 스쿼드는 나중에 열려도 된다 — 팀이 생긴 것 자체를 실패로 돌리지
           않는다. 홈이 404 를 이미 빈 판으로 다룬다. */
      })
      setName('')
      setRegion('')
      setOpen(false)
      router.refresh()
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  async function leave(teamId: string) {
    if (leaving) return
    setLeaving(teamId)
    setError(null)
    setDisbandable(null)
    try {
      await apiDelete(`/api/teams/${encodeURIComponent(teamId)}/members/${encodeURIComponent(userId)}`)
      setLeft((prev) => [...prev, teamId])
      router.refresh()
    } catch (err) {
      setError(apiErrorMessage(err))
      /* 🔴 **여기가 「팀을 버릴 길」이 열리는 자리다**(사용자 지적,
         2026-09-18). 마지막 주장이면 나가기가 막히는데, 그때까지는 **거기서
         끝**이라 혼자 만든 팀을 없앨 방법이 없었다. 계약은 2026-09-17에
         이미 길을 냈다(`DELETE /teams/{id}`, 미결 `paik` 35번).

         🔴 **`LAST_OWNER` 일 때만** 권한다. 다른 이유로 막힌 사람에게
         해체를 들이밀면 **나갈 수 있는 사람이 팀을 없앤다.**
         🔴 status 가 아니라 `code` 로 가른다(계약이 정한 분기 방식). */
      if (err instanceof ApiCallError && err.code === 'LAST_OWNER') {
        setDisbandable(teamId)
      }
    } finally {
      setLeaving(null)
    }
  }

  /**
   * **팀을 해체한다** — 마지막 주장이 팀을 버리는 유일한 길.
   *
   * 🔴 **한 번 더 묻지 않는다.** 이 단추는 나가기가 막힌 뒤에야 나타나고,
   * 바로 위에 무엇이 일어나는지 적혀 있다 — 확인을 한 겹 더 두면 「왜 두 번
   * 묻나」가 된다(탈퇴는 비밀번호를 받으므로 사정이 다르다).
   */
  async function disband(teamId: string) {
    if (leaving) return
    setLeaving(teamId)
    setError(null)
    try {
      await apiDelete(`/api/teams/${encodeURIComponent(teamId)}`)
      setLeft((prev) => [...prev, teamId])
      setDisbandable(null)
      /* 🔴 **권유 문구도 같이 지운다.** 그 줄이 사라졌는데 「혼자뿐이라
         해체해야 합니다」가 남아 있으면 무엇에 대한 말인지 알 수 없다. */
      setError(null)
      router.refresh()
    } catch (err) {
      /* 🔴 **앞으로 있을 경기가 있으면 막힌다**(`409
         TEAM_HAS_UPCOMING_MATCH`) — 상대에게는 약속이다. 화면이 미리
         가리지 않고 서버가 준 문구를 그대로 보여 준다. 단추는 그대로
         두어 경기를 정리한 뒤 다시 누를 수 있게 한다. */
      setError(apiErrorMessage(err))
    } finally {
      setLeaving(null)
    }
  }

  /**
   * 화면에 그릴 팀 — **떠난 것은 뺀다**(위 `left` 주석).
   *
   * 🔴 목록과 「아직 소속된 팀이 없습니다」가 **같은 값**을 봐야 한다. 한쪽만
   * 거르면 마지막 팀을 떠난 뒤 목록은 비었는데 안내는 안 뜨는 빈 판이 된다.
   */
  const shown = teams.filter((t) => !left.includes(t.team_id))

  return (
    <>
      {shown.length === 0 ? (
        /* 🔴 **한 줄로 끝낸다**(사용자 요청, 2026-09-16). 앞서 여기에
           「팀을 만들어야 스쿼드와 경기 신청을 쓸 수 있습니다」를 덧붙여
           무엇이 막히는지 적었는데, 바로 아래에 **「팀 만들기」 단추가 이미
           서 있어서** 같은 말을 두 번 하는 자리였다. */
        <p className="ss-profile-muted">아직 소속된 팀이 없습니다.</p>
      ) : (
        <ul className="ss-profile-teams">
          {shown.map((t) => (
            <li key={t.team_id}>
              {/* 🔴 **나가기는 팀 이름 오른쪽**이다(사용자 요청, 2026-09-16) —
                  어느 팀을 나가는지가 이름 옆에 있어야 붙는다. 아래 따로 두면
                  팀이 여럿일 때 어느 줄의 것인지 한 번 더 짚어야 한다. */}
              <p className="ss-profile-team-name">
                <span>{t.name}</span>
                {/* 🔴 **단추 둘을 한 덩어리로 묶는다**(사용자 지적,
                    2026-09-18: 「너무 떨어져있어, 살짝 더 붙여」). 줄의
                    `gap`(14px)은 **이름과 단추**를 띄우려는 값이라, 그걸
                    줄이면 단추가 팀 이름에 붙어 읽힌다. 단추끼리만 좁히려면
                    제 `gap` 을 가진 상자가 하나 더 필요하다. */}
                <span className="ss-profile-team-acts">
                  {/* 🔴 **주장에게만 낸다**(계약 — 구성원이 부르면 403). */}
                  {t.role === 'owner' && (
                    <button
                      type="button"
                      className="ss-profile-team-leave ss-profile-team-edit"
                      aria-expanded={editing === t.team_id}
                      onClick={() => openEdit(t)}
                    >
                      {editing === t.team_id ? '접기' : '수정'}
                    </button>
                  )}
                  <button
                    type="button"
                    className="ss-profile-team-leave"
                    disabled={leaving === t.team_id}
                    onClick={() => void leave(t.team_id)}
                  >
                    {leaving === t.team_id ? '나가는 중…' : '팀 나가기'}
                  </button>
                </span>
              </p>
              <p className="ss-profile-muted">
                {t.region} · {t.sport_code}
              </p>
              {/* 팀 만들기와 같은 접기다 — 붙였다 뗐다 하지 않고 늘 그린다. */}
              {t.role === 'owner' && (
                <div
                  className="ss-profile-form-fold"
                  data-open={editing === t.team_id ? 'true' : 'false'}
                >
                  <div inert={editing !== t.team_id}>
                    <form
                      className="ss-profile-account-form ss-form-compact"
                      onSubmit={(e) => {
                        e.preventDefault()
                        void save(t.team_id, { name: t.name, region: t.region })
                      }}
                    >
                      <GrowField label="팀 이름" value={editName} onChange={setEditName} />
                      <RegionField label="지역" value={editRegion} onChange={setEditRegion} />
                      {/* 🔴 **종목은 없다** — 계약 본문에 자리가 없고, 포지션·
                          스쿼드·경기가 그 값에 매달려 있어서 바꾸면 이미 앉힌
                          포지션이 다른 종목 것이 된다. */}
                      <PillButton
                        type="submit"
                        disabled={saving || !editName.trim() || !isRegion(editRegion)}
                        className="self-center"
                      >
                        {saving ? '저장 중…' : '저장'}
                      </PillButton>
                    </form>

                    {/* 🔴 **경기 조건도 여기서 고친다**(사용자 지적,
                        2026-09-18). 「팀 매칭」 판은 스쿼드가 다 차야 열리는데,
                        조건이 추천 후보를 막고 있으면 스쿼드를 채울 수가
                        없다 — 그 고리를 끊는 자리다. 폼 **밖**에 두는 것은
                        저 위 `<form>` 의 submit 에 딸려 들어가지 않게 하려는
                        것이다. */}
                    <button
                      type="button"
                      className="ss-profile-tab ss-profile-tab--sm"
                      aria-expanded={prefsFor === t.team_id}
                      disabled={prefsBusy}
                      onClick={() => void openPrefs(t.team_id)}
                    >
                      {prefsFor === t.team_id ? '경기 조건 접기' : '경기 조건 고치기'}
                    </button>

                    {/* 🔴 **시간만 지우는 길**(사용자 지적, 2026-09-18).
                        조건 판의 「팀 찾기」는 `지역 ≥ 1 && 시간 ≥ 1` 이어야
                        눌려서 **그 판으로는 시간을 없앨 수가 없다.** 그런데
                        추천 후보를 막는 것이 바로 그 시간이다.

                        🔴 **지역은 남긴다** — 지역까지 지우면 우리 팀이 남의
                        「비슷한 팀」 후보에서도 빠진다(그쪽은 「지역 또는
                        시간을 하나라도 등록한 팀만」이다). */}
                    <button
                      type="button"
                      className="ss-profile-tab ss-profile-tab--sm"
                      disabled={prefsBusy}
                      onClick={() => void clearTimes(t.team_id)}
                    >
                      시간 조건 지우기
                    </button>

                    {prefsFor === t.team_id && (
                      <MatchPrefsForm
                        kind="team"
                        value={teamPrefs}
                        onCancel={() => setPrefsFor(null)}
                        onDone={(next) => {
                          setTeamPrefs(next)
                          setPrefsFor(null)
                          /* 🔴 **실패를 숨기지 않는다** — 조건이 안 바뀌면
                             추천 판은 계속 비어 있는데 화면만 성공으로
                             보인다(`myPrefsStore` 와 같은 판단). */
                          void saveTeamPrefs(t.team_id, next).catch(() =>
                            setError('경기 조건을 저장하지 못했습니다 — 다시 시도해 주세요.'),
                          )
                        }}
                      />
                    )}
                  </div>
                </div>
              )}
              {/* 🔴 **소속이 여럿일 때만 낸다.** 하나뿐이면 고를 것이 없고,
                  단추만 있으면 무엇을 고르는 자리인지가 안 읽힌다. */}
              {teams.length > 1 && (
                <button
                  type="button"
                  className="ss-profile-team-home"
                  data-on={homeTeamId === t.team_id ? 'true' : undefined}
                  aria-pressed={homeTeamId === t.team_id}
                  onClick={() => {
                    rememberHomeTeam(t.team_id)
                    router.refresh()
                  }}
                >
                  {homeTeamId === t.team_id ? '홈에 보이는 팀' : '홈에 이 팀 보기'}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      {/* 🔴 **팀 만들기는 늘 낸다**(사용자 지적, 2026-09-16 — 「마지막 주장이어도
          새로 만들고 싶을 수 있다」). 계약에 팀 해체도 소유권 이양도 없어서
          마지막 주장은 나갈 수가 없는데, 만들 자리까지 막으면 그 사람은 새
          팀을 시작할 방법이 아예 없다. 미결 `paik` 35번으로 올렸다.

          🔴 그래서 **홈에 보일 팀을 고르는 자리**가 함께 필요하다 — 없으면
          새로 만든 팀이 홈에 안 보인다(홈은 한 팀만 그린다). */}
      <>
          {/* 🔴 **오른쪽 아래 끝**(사용자 요청, 2026-09-16) — 「계정」 판의
              회원 탈퇴와 같은 자리다. 판마다 「지금 할 일」은 위, 「덜 쓰는
              것」은 아래 구석으로 모은다. */}
          <div className="ss-profile-account-foot">
            <button
              type="button"
              className="ss-profile-tab ss-profile-tab--sm"
              aria-expanded={open}
              onClick={() => {
                setOpen((v) => !v)
                setError(null)
              }}
            >
              {open ? '접기' : '팀 만들기'}
            </button>
          </div>

          {/* 🔴 **늘 그리고 접기만 한다**(사용자 요청 — 부드럽게 펴졌다 닫히게).
              `{open && …}` 로 붙였다 뗐다 하면 전환할 대상이 없어 툭 나타난다.
              접는 방식은 「내 경기」의 더보기와 같다(`grid-template-rows`
              0fr → 1fr) — `max-height` 로 하면 상한과 실제 높이가 달라 아무
              일도 안 일어나는 구간에서 시간이 새고 속도가 튄다.

              🔴 접힌 동안에는 **탭으로도 못 닿게** 한다(`inert`) — 안 그러면
              눈에 안 보이는 입력칸에 커서가 들어간다. `aria-hidden` 만으로는
              포커스를 막지 못한다. */}
          <div className="ss-profile-form-fold" data-open={open ? 'true' : 'false'}>
            <div inert={!open}>
              <form onSubmit={create} className="ss-profile-account-form ss-form-compact">
                <GrowField label="팀 이름" value={name} onChange={setName} />
                {/* 🔴 **여기도 목록에서 고른다**(2026-09-17, 계약 52번과 함께).
                    전에는 자유 입력이라 새 팀이 처음부터 어긋난 지역으로
                    들어갔고, 그러면 고치는 화면을 붙여도 「만들고 나서
                    고치는」 흐름이 된다. */}
                <RegionField label="지역" value={region} onChange={setRegion} />
                {/* 🔴 **가운데**(사용자 요청, 2026-09-16) — 폼이 좁아 왼쪽에
                    붙이면 아래 여백이 비어 보인다. */}
                <PillButton
                  type="submit"
                  disabled={busy || !name.trim() || !isRegion(region)}
                  className="self-center"
                >
                  만들기
                </PillButton>
              </form>
            </div>
          </div>
      </>

      {error && (
        <p role="alert" className="ss-profile-video-reason">
          {error}
          {/* 🔴 **막힌 자리에서 바로 길을 낸다**(사용자 지적, 2026-09-18:
              「1명밖에 없어도 나가기 누르면 해체 할 수 있어야 하잖아」).
              이유만 적고 끝내면 **혼자 만든 팀을 버릴 방법이 없다.** 같은
              줄에 두는 이유는 그 문장이 곧 이 단추의 까닭이기 때문이다. */}
          {disbandable && (
            <>
              {' '}
              혼자뿐이라 나가려면 팀을 해체해야 합니다. 구성원은 모두 나가고 다시
              모아야 하며, <strong>되돌릴 수 없습니다.</strong>{' '}
              <button
                type="button"
                className="ss-profile-team-leave"
                disabled={leaving === disbandable}
                onClick={() => void disband(disbandable)}
              >
                {leaving === disbandable ? '해체하는 중…' : '팀 해체하기'}
              </button>
            </>
          )}
        </p>
      )}
    </>
  )
}
