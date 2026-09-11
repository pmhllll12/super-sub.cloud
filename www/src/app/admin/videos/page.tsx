import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'
import { BackendError, getBackend } from '@/server/backend'
import type { AdminVideoListResult, AdminVideoRow } from '@/server/backend'
import { SESSION_COOKIE } from '@/server/session'
import GlassPanel from '@/components/ui/GlassPanel'
import AdminVideoSearchForm from './AdminVideoSearchForm'

const MUTED = 'color-mix(in srgb, var(--ss-fg) 60%, transparent)'

const STATUS_LABEL: Record<string, string> = {
  queued: '대기 중',
  running: '분석 중',
  succeeded: '완료',
  failed: '실패',
}

const STATUS_COLOR: Record<string, string> = {
  queued: MUTED,
  running: 'var(--ss-accent)',
  succeeded: '#3bb273',
  failed: '#e5484d',
}

function StatusBadge({ row }: { row: AdminVideoRow }) {
  if (!row.passed) {
    return (
      <span className="text-xs" style={{ color: MUTED }}>
        반려 — {row.reject_reason}
      </span>
    )
  }
  if (!row.analysis_status) {
    return (
      <span className="text-xs" style={{ color: MUTED }}>
        —
      </span>
    )
  }
  return (
    <span
      className="rounded-full px-2 py-0.5 text-xs font-medium"
      style={{
        color: STATUS_COLOR[row.analysis_status] ?? MUTED,
        border: `1px solid ${STATUS_COLOR[row.analysis_status] ?? MUTED}`,
      }}
    >
      {STATUS_LABEL[row.analysis_status] ?? row.analysis_status}
    </span>
  )
}

export default async function AdminVideosPage({
  searchParams,
}: {
  searchParams: Promise<{ user?: string }>
}) {
  const token = (await cookies()).get(SESSION_COOKIE)?.value
  if (!token) redirect('/login')

  const { user } = await searchParams

  let result: AdminVideoListResult | null = null
  let notFound = false
  if (user) {
    try {
      result = await getBackend().listAdminVideos(token, user)
    } catch (e) {
      if (e instanceof BackendError && e.status === 401) redirect('/login')
      if (e instanceof BackendError && e.status === 403) redirect('/')
      if (e instanceof BackendError && e.status === 404) notFound = true
      else throw e
    }
  }

  return (
    <main className="mx-auto flex max-w-5xl flex-col gap-6 px-6 py-12">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">영상 · 분석 상태</h1>
          <p className="text-sm" style={{ color: MUTED }}>
            {result
              ? `${result.nickname} (${result.email}) · 영상 ${result.items.length}건`
              : '한 사람의 영상 전부와 분석 실패 사유를 봅니다.'}
          </p>
        </div>
        <AdminVideoSearchForm defaultValue={user ?? ''} />
      </header>

      {notFound && (
        <GlassPanel>
          <p className="px-8 py-10 text-center text-sm" style={{ color: MUTED }}>
            해당 사용자를 찾을 수 없습니다 — id 또는 이메일을 다시 확인해 주세요.
          </p>
        </GlassPanel>
      )}

      {!user && !notFound && (
        <GlassPanel>
          <p className="px-8 py-10 text-center text-sm" style={{ color: MUTED }}>
            위 검색창에 사용자 id 또는 이메일을 넣어 조회하세요.
          </p>
        </GlassPanel>
      )}

      {result && (
        <GlassPanel className="overflow-hidden">
          {result.items.length === 0 ? (
            <p className="px-8 py-10 text-center text-sm" style={{ color: MUTED }}>
              올린 영상이 없습니다.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left" style={{ color: MUTED }}>
                    <th className="px-6 py-3 font-medium">파일</th>
                    <th className="px-6 py-3 font-medium">종목</th>
                    <th className="px-6 py-3 font-medium">상태</th>
                    <th className="px-6 py-3 font-medium">실패 사유</th>
                    <th className="px-6 py-3 font-medium">업로드</th>
                    <th className="px-6 py-3 font-medium">저장 / 공개</th>
                  </tr>
                </thead>
                <tbody>
                  {result.items.map((row) => (
                    <tr key={row.id} style={{ borderTop: '1px solid var(--ss-glass-border)' }}>
                      <td className="px-6 py-3">
                        <p>{row.original_filename ?? row.storage_key}</p>
                        <p className="text-xs" style={{ color: MUTED }}>
                          {row.report_prefix}
                        </p>
                      </td>
                      <td className="px-6 py-3">{row.sport_code}</td>
                      <td className="px-6 py-3">
                        <StatusBadge row={row} />
                      </td>
                      <td className="px-6 py-3 max-w-xs">
                        {row.analysis_failure_reason ? (
                          <span className="text-xs" style={{ color: STATUS_COLOR.failed }}>
                            {row.analysis_failure_reason}
                          </span>
                        ) : (
                          <span className="text-xs" style={{ color: MUTED }}>
                            —
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-3 whitespace-nowrap" style={{ color: MUTED }}>
                        {row.created_at.slice(0, 16).replace('T', ' ')}
                      </td>
                      <td className="px-6 py-3 whitespace-nowrap text-xs" style={{ color: MUTED }}>
                        {row.kept ? '저장됨' : '임시'} · {row.is_public ? '공개' : '비공개'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </GlassPanel>
      )}
    </main>
  )
}
