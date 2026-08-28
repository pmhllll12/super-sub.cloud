import BrandMark from '@/components/ui/BrandMark'
import PillButton from '@/components/ui/PillButton'

const MUTED = 'color-mix(in srgb, var(--ss-fg) 60%, transparent)'

export default function Home() {
  return (
    <main className="grid min-h-screen w-full grid-cols-1 lg:grid-cols-2">
      <div className="flex flex-col items-start justify-center gap-6 px-6 py-16 sm:px-12 lg:px-16 xl:px-24">
        <BrandMark size={72} />
        <h1 className="sr-only">Super-Sub</h1>
        <p
          className="max-w-md text-lg"
          style={{ color: MUTED, wordBreak: 'keep-all' }}
        >
          생활체육 경기 영상을 분석해 용병을 찾고, 실력을 검증합니다.
        </p>
        <div className="flex flex-wrap gap-3">
          <PillButton href="/login">로그인</PillButton>
          <PillButton href="/signup" variant="ghost">
            회원가입
          </PillButton>
        </div>
      </div>

      {/* 앱 로그인 화면(_kPhotoScrim)과 같은 재질 — 사진을 꽉 채우고 스크림을 얹는다.
          작은 카드처럼 보이지 않도록 모서리를 둥글리지 않는다(화면 가장자리까지 닿는 판). */}
      <div className="relative min-h-[45vh] w-full overflow-hidden lg:min-h-screen">
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
