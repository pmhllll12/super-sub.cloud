import BrandMark from '@/components/ui/BrandMark'
import PillButton from '@/components/ui/PillButton'

const MUTED = 'color-mix(in srgb, var(--ss-fg) 60%, transparent)'

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-6xl flex-col items-center gap-10 px-6 py-16 lg:flex-row lg:justify-between lg:gap-16">
      <div className="flex w-full max-w-lg flex-col items-start gap-6 lg:w-1/2">
        <BrandMark size={72} />
        <p className="text-lg" style={{ color: MUTED }}>
          생활체육 경기 영상을 분석해 용병을 찾고, 실력을 검증합니다.
        </p>
        <div className="flex flex-wrap gap-3">
          <PillButton href="/login">로그인</PillButton>
          <PillButton href="/signup" variant="ghost">
            회원가입
          </PillButton>
        </div>
      </div>

      <div
        className="relative aspect-square w-full max-w-lg overflow-hidden lg:w-1/2"
        style={{ borderRadius: 'var(--ss-radius-sheet)' }}
      >
        <div
          aria-hidden="true"
          className="absolute inset-0 bg-cover bg-center"
          style={{ backgroundImage: "url('/home_figure.jpg')" }}
        />
        <div className="absolute inset-0" style={{ background: 'var(--ss-scrim)' }} />
      </div>
    </main>
  )
}
