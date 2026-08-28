import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'
import BrandMark from '@/components/ui/BrandMark'
import PillButton from '@/components/ui/PillButton'
import { SESSION_COOKIE } from '@/server/session'

const MUTED = 'color-mix(in srgb, var(--ss-fg) 60%, transparent)'

/**
 * 마크업만 따로 뺀 것 — `Home` 이 서버 컴포넌트로 `cookies()` 를 부르게 되면서
 * 테스트가 이 함수를 직접 렌더한다(리다이렉트 분기를 타지 않는다).
 */
export function LandingBody() {
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

// 이미 로그인한 사람이 / 에 들어와 제품 소개를 다시 보는 건 어색하다 — 앱의
// 라우터도 로그인돼 있으면 로그인 화면을 건너뛰고 홈으로 보낸다.
// 쿠키 존재만 확인하고 백엔드는 부르지 않는다 — 랜딩은 공유 링크로도 열리는
// 자리라 매번 왕복을 넣지 않는다. 썩은 토큰은 /home 의 requireUser() 가
// 로그인으로 돌려보낸다 — 한 번 더 튀지만 그 편이 낫다.
export default async function Home() {
  if ((await cookies()).get(SESSION_COOKIE)) redirect('/home')
  return <LandingBody />
}
