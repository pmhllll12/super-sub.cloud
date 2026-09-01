import Link from 'next/link'
import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'
import { BackendError, getBackend } from '@/server/backend'
import { SESSION_COOKIE } from '@/server/session'
import GlassPanel from '@/components/ui/GlassPanel'
import AdminSearchForm from './AdminSearchForm'

const MUTED = 'color-mix(in srgb, var(--ss-fg) 60%, transparent)'
const PAGE_SIZE = 20

function pageHref(q: string | undefined, page: number): string {
  const params = new URLSearchParams()
  if (q) params.set('q', q)
  params.set('page', String(page))
  return `/admin/users?${params}`
}

export default async function AdminUsersPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; page?: string }>
}) {
  const token = (await cookies()).get(SESSION_COOKIE)?.value
  if (!token) redirect('/login')

  const { q, page: pageParam } = await searchParams
  const page = Math.max(1, Number(pageParam) || 1)

  let result
  try {
    result = await getBackend().listUsers(token, { q, page, size: PAGE_SIZE })
  } catch (e) {
    if (e instanceof BackendError && e.status === 401) redirect('/login')
    // 관리자 화이트리스트(계약 문서 3-2절)에 없는 계정이다 — admin 화면 밖으로 보낸다.
    if (e instanceof BackendError && e.status === 403) redirect('/')
    throw e
  }

  const lastPage = Math.max(1, Math.ceil(result.total / PAGE_SIZE))

  return (
    <main className="mx-auto flex max-w-4xl flex-col gap-6 px-6 py-12">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">회원 관리</h1>
          <p className="text-sm" style={{ color: MUTED }}>
            총 {result.total}명
          </p>
        </div>
        <AdminSearchForm defaultValue={q ?? ''} />
      </header>

      <GlassPanel className="overflow-hidden">
        {result.items.length === 0 ? (
          <p className="px-8 py-10 text-center text-sm" style={{ color: MUTED }}>
            {q ? '검색 결과가 없습니다.' : '가입한 회원이 없습니다.'}
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left" style={{ color: MUTED }}>
                  <th className="px-6 py-3 font-medium">이메일</th>
                  <th className="px-6 py-3 font-medium">닉네임</th>
                  <th className="px-6 py-3 font-medium">가입일</th>
                </tr>
              </thead>
              <tbody>
                {result.items.map((u) => (
                  <tr key={u.id} style={{ borderTop: '1px solid var(--ss-glass-border)' }}>
                    <td className="px-6 py-3">
                      <Link
                        href={`/admin/users/${u.id}`}
                        className="underline"
                        style={{ color: 'var(--ss-accent)' }}
                      >
                        {u.email}
                      </Link>
                    </td>
                    <td className="px-6 py-3">{u.nickname}</td>
                    <td className="px-6 py-3" style={{ color: MUTED }}>
                      {u.created_at.slice(0, 10)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </GlassPanel>

      {lastPage > 1 && (
        <nav className="flex items-center justify-center gap-4 text-sm" style={{ color: MUTED }}>
          <Link
            href={pageHref(q, page - 1)}
            aria-disabled={page <= 1}
            className={page <= 1 ? 'pointer-events-none opacity-40' : 'underline'}
          >
            이전
          </Link>
          <span>
            {page} / {lastPage}
          </span>
          <Link
            href={pageHref(q, page + 1)}
            aria-disabled={page >= lastPage}
            className={page >= lastPage ? 'pointer-events-none opacity-40' : 'underline'}
          >
            다음
          </Link>
        </nav>
      )}
    </main>
  )
}
