import BrandMark from '@/components/ui/BrandMark'
import GlassPanel from '@/components/ui/GlassPanel'

const MUTED = 'color-mix(in srgb, var(--ss-fg) 60%, transparent)'

/**
 * 로그인/회원가입 공통 껍데기 — 배경 위에 뜬 카드.
 *
 * 화면 전체에 어둡게 깐 사진, 그 위에 둥근 카드. 카드 왼쪽 절반은 같은
 * 사진(위: 브랜드 마크, 아래: 헤드라인) — lg 미만에서는 통째로 숨겨 폼만
 * 남긴다(375px 에서도 폼이 화면 안에 들어와야 하니까). 오른쪽 절반이
 * 실제 폼 — 그 내용(이메일/비밀번호 등)은 각 페이지가 children 으로 준다.
 *
 * GlassPanel 을 카드 전체에 두른다 — 사진 칸은 불투명한 <img> 가 위에
 * 덮이니 블러의 영향을 안 받고, 폼 칸은 GlassPanel 의 반투명+블러 배경이
 * 그대로 살아 우리 팔레트(검정+민트)를 유지한다.
 */
export default function AuthShell({
  formTitle,
  formDescription,
  children,
  footer,
}: {
  formTitle: string
  formDescription: string
  children: React.ReactNode
  footer: React.ReactNode
}) {
  return (
    <main className="relative flex min-h-screen w-full items-center justify-center overflow-hidden p-3 sm:p-4 lg:p-6">
      {/* 화면 전체 배경 — 카드가 도드라지도록 크게 어둡게 깐다 */}
      <div aria-hidden="true" className="fixed inset-0 -z-10 overflow-hidden">
        {/* eslint-disable-next-line @next/next/no-img-element -- 장식용 고정 배경 */}
        <img
          src="/login_figure.jpg"
          alt=""
          className="h-full w-full object-cover"
          style={{ filter: 'blur(6px) saturate(0.9)', transform: 'scale(1.05)' }}
        />
        <div
          className="absolute inset-0"
          style={{ background: 'color-mix(in srgb, var(--ss-bg) 80%, transparent)' }}
        />
      </div>

      {/* 카드 크기를 잡는 바깥 래퍼 — 화면 대비 가로세로 90% 안팎을 목표로
          하되 lg:h-[...] 로 뷰포트 높이의 90%(최대 920px)를 못 넘게 막는다.
          lg 미만에서는 사진 칸이 없어 폼 내용만큼만 높으면 되니 높이를
          강제하지 않는다(그래야 375px 에서도 넘치지 않는다). */}
      <div className="w-full max-w-[1600px] lg:h-[min(90vh,920px)]">
        <GlassPanel className="grid h-full w-full grid-cols-1 lg:grid-cols-2">
          {/* 카드 왼쪽 — 사진 칸. 좁은 화면에서는 숨긴다(폼만 남기기 위해). */}
          <div className="relative hidden lg:block">
            {/* eslint-disable-next-line @next/next/no-img-element -- 장식용 고정 사진 */}
            <img
              src="/login_figure.jpg"
              alt=""
              className="absolute inset-0 h-full w-full object-cover"
            />
            <div
              aria-hidden="true"
              className="absolute inset-0"
              style={{
                background:
                  'linear-gradient(to top, color-mix(in srgb, var(--ss-bg) 90%, transparent) 0%, color-mix(in srgb, var(--ss-bg) 10%, transparent) 45%, color-mix(in srgb, var(--ss-bg) 70%, transparent) 100%)',
              }}
            />
            <div className="relative flex h-full flex-col justify-between p-12">
              <BrandMark size={32} />
              <div className="flex max-w-md flex-col gap-3">
                <h2
                  className="text-4xl leading-tight font-semibold"
                  style={{ wordBreak: 'keep-all' }}
                >
                  안개 속에서도, 실력은 숨지 않습니다.
                </h2>
                <p className="text-sm" style={{ color: MUTED }}>
                  생활체육 경기 영상을 분석해 용병을 찾고, 실력을 검증합니다.
                </p>
              </div>
            </div>
          </div>

          {/* 카드 오른쪽 — 폼 칸. 카드가 커져도 입력칸이 화면 폭만큼
              늘어지면 읽기 나빠지니, 안쪽 내용은 max-w-sm 으로 가운데
              정렬한다. 세로가 짧은 화면(예: 1440×800)에서 폼이 카드보다
              길어지면 페이지 전체가 아니라 이 칸만 스크롤되게 한다. */}
          <div className="flex flex-col overflow-y-auto p-6 sm:p-10 lg:p-12">
            <div className="m-auto flex w-full max-w-sm flex-col gap-8 py-6">
              <BrandMark size={28} className="lg:hidden" />
              <div className="flex flex-col gap-2">
                <h1 className="text-2xl font-semibold sm:text-3xl">{formTitle}</h1>
                <p className="text-sm" style={{ color: MUTED }}>
                  {formDescription}
                </p>
              </div>
              {children}
              {footer}
            </div>
          </div>
        </GlassPanel>
      </div>
    </main>
  )
}
