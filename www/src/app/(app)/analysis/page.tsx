import { requireUser } from '@/server/currentUser'
import GlassPanel from '@/components/ui/GlassPanel'

const MUTED = 'color-mix(in srgb, var(--ss-fg) 60%, transparent)'

// 아직 분석 파이프라인이 붙지 않았다. 가짜 결과나 수치를 그리지 않는다 —
// 데모에서 오해받는다. 준비되면 이 자리에 실제 업로드/채팅 흐름이 들어간다.
export default async function AnalysisPage() {
  await requireUser()

  return (
    <main className="mx-auto flex min-h-[70vh] max-w-2xl flex-col items-center justify-center px-6 py-16">
      <GlassPanel className="flex w-full flex-col items-center gap-3 px-8 py-16 text-center">
        <span className="material-symbols-outlined text-4xl" aria-hidden="true" style={{ color: 'var(--ss-accent)' }}>
          videocam
        </span>
        <h1 className="text-xl font-semibold">준비 중입니다</h1>
        <p className="text-sm" style={{ color: MUTED }}>
          경기 영상을 올리면 실력 리포트가 나오는 기능을 만들고 있습니다.
        </p>
      </GlassPanel>
    </main>
  )
}
