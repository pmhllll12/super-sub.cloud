import BrandMark from '@/components/ui/BrandMark'

const MUTED = 'color-mix(in srgb, var(--ss-fg) 60%, transparent)'

/**
 * 로그인/회원가입 공통 껍데기 — 배경 위에 뜬 카드.
 *
 * 화면 전체에 어둡게 깐 사진(home_figure.jpg) 위에 둥근 카드. 카드 왼쪽
 * 절반은 다른 사진(login_figure.jpg) 위에 헤드라인을 얹는다 — lg 미만에서는
 * 통째로 숨겨 폼만 남긴다(375px 에서도 폼이 화면 안에 들어와야 하니까).
 * 오른쪽 절반이 실제 폼 — 워드마크(BrandMark)를 폼 칸 맨 위에 두고, 그 아래
 * 내용(이메일/비밀번호 등)은 각 페이지가 children 으로 준다.
 *
 * 사진 칸은 불투명한 <img> 가 덮이니 유리 재질이 필요 없다. 폼 칸만
 * `GlassPanel`(`components/ui/GlassPanel.tsx`)과 같은 반투명+블러+테두리
 * 빛 질감을 직접 낸다 — GlassPanel 컴포넌트 자체는 네 모서리를 똑같이
 * 둥글리는데, 폼 칸은 lg 이상에서 카드의 절반(오른쪽)만 차지해 왼쪽 모서리는
 * 사진과 맞닿아 각져야 하니 그대로 재사용하지 않고 같은 CSS 값을 가져와
 * 모서리만 다르게 적용한다(`lg` 미만에서는 폼 칸이 카드 전체이므로 네
 * 모서리 다 둥글다).
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
      {/* 화면 전체 배경 — 카드가 도드라지도록 크게 어둡게 깐다. 카드가
          주인공이라 사진은 흐리고 어둡게만 깔린다. */}
      <div aria-hidden="true" className="fixed inset-0 -z-10 overflow-hidden">
        {/* eslint-disable-next-line @next/next/no-img-element -- 장식용 고정 배경 */}
        <img
          src="/home_figure.jpg"
          alt=""
          className="h-full w-full object-cover"
          style={{ filter: 'blur(6px) saturate(0.9)', transform: 'scale(1.05)' }}
        />
        <div
          className="absolute inset-0"
          style={{ background: 'color-mix(in srgb, var(--ss-bg) 70%, transparent)' }}
        />
      </div>

      {/* 카드 크기를 잡는 바깥 래퍼 — 화면 대비 가로세로 90% 안팎을 목표로
          하되 lg:h-[...] 로 뷰포트 높이의 90%(최대 920px)를 못 넘게 막는다.
          lg 미만에서는 사진 칸이 없어 폼 내용만큼만 높으면 되니 높이를
          강제하지 않는다(그래야 375px 에서도 넘치지 않는다). 카드 자체는
          더 이상 GlassPanel 이 아니다 — 사진 칸(불투명 이미지)과 폼 칸(글라스)
          이 서로 다른 재질이라 바깥은 모서리만 잡는 투명 틀로 두고, 각
          칸이 자기 몫의 배경을 스스로 그린다.

          도는 테두리 빛(ss-traveling-edge)은 이 바깥 래퍼에 준다 — 카드가
          사진 칸+폼 칸 두 조각이라도 빛은 "카드 하나"의 둘레를 한 바퀴
          돌아야 한다. 안쪽 폼 칸에 따로 주면 오른쪽 절반만 돈다(예전 버그).
          `border-radius: inherit` 로 그려지는 링이라 바깥 래퍼의 둥근
          모서리를 그대로 따라간다. */}
      {/* 유리 굴절(warp) — backdrop-filter 는 흐림·채도만 다루고 **뒤
          배경을 휘게 하지는 못한다.** 그건 SVG 필터의 몫이다: 부드러운
          잡음(feTurbulence)을 만들고 그 값만큼 픽셀을 밀어(feDisplacementMap)
          두께 있는 유리를 통과한 것처럼 보이게 한다.

          scale 이 미는 세기다. 처음에 5 로 뒀다가 실측해 보니 화면이
          0.6%만 달라지고 최대 차이가 4(255 중)라 **눈에 보이지 않았다** —
          뒤가 부드러운 연기 그라디언트라 5px 밀어도 거의 같은 색이 온다.
          같은 자리에서 잰 값: scale 20 → 2.1% · 최대차 15, scale 60 →
          13.7% · 최대차 38. 눈에 보이는 최소치는 20 이었지만 "있는 듯
          없는 듯"이라 60 으로 올렸다 — 뒤 형태가 확실히 휘어 두께 있는
          유리를 통과한 것으로 읽힌다. 더 키우면 유리가 아니라 물결·열기가
          되므로 여기서 멈춘다.

          seed 를 고정해 두어 새로고침해도 같은 무늬가 나온다.

          width/height 0 인 svg 라 자리를 차지하지 않는다 — 정의만 두는
          자리다. */}
      <svg width="0" height="0" aria-hidden="true" focusable="false" className="absolute">
        <filter id="ss-glass-warp" x="-10%" y="-10%" width="120%" height="120%" colorInterpolationFilters="sRGB">
          <feTurbulence type="fractalNoise" baseFrequency="0.006 0.01" numOctaves="2" seed="7" result="warp" />
          <feDisplacementMap in="SourceGraphic" in2="warp" scale="60" xChannelSelector="R" yChannelSelector="G" />
        </filter>
      </svg>

      <div className="w-full max-w-[1600px] lg:h-[min(90vh,920px)]">
        <div
          className="ss-traveling-edge relative grid h-full w-full grid-cols-1 overflow-hidden lg:grid-cols-2"
          style={{ borderRadius: 'var(--ss-radius-sheet)', border: '1px solid var(--ss-glass-border)' }}
        >
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
            {/* 헤드라인+설명은 한 덩어리로 사진 칸의 세로 가운데에 놓는다
                (가로는 기존대로 왼쪽 정렬 유지). 줄바꿈은 자연 줄바꿈에
                맡기지 않고 명시적으로 두 줄로 고정한다 — "안개 속에서도," /
                "실력은 숨지 않습니다." 폭이 아주 좁아 둘째 줄이 넘칠 때만
                keep-all 로 자연 줄바꿈을 허용한다. */}
            <div className="relative flex h-full flex-col justify-center p-12">
              <div className="flex max-w-md flex-col gap-3">
                <h2
                  className="text-4xl leading-tight font-semibold"
                  style={{ wordBreak: 'keep-all' }}
                >
                  <span className="block">안개 속에서도,</span>
                  <span className="block">실력은 숨지 않습니다.</span>
                </h2>
                {/* 이 문구도 헤드라인처럼 줄바꿈을 고정한다 — 폭에 따라
                    "실력을" 같은 한 도막만 아래로 떨어지면 보기 나쁘다.
                    쉼표에서 끊어 두 줄로 나눈다. */}
                <p className="text-sm" style={{ color: MUTED, wordBreak: 'keep-all' }}>
                  <span className="block">생활체육 경기 영상을 분석해 용병을 찾고,</span>
                  <span className="block">실력을 검증합니다.</span>
                </p>
              </div>
            </div>
          </div>

          {/* 카드 오른쪽 — 폼 칸. 카드가 커져도 입력칸이 화면 폭만큼
              늘어지면 읽기 나빠지니, 안쪽 내용은 max-w-sm 으로 가운데
              정렬한다. 세로가 짧은 화면(예: 1440×800)에서 폼이 카드보다
              길어지면 페이지 전체가 아니라 이 칸만 스크롤되게 한다.
              워드마크는 폼 칸 맨 위, 카드 전체에서 유일하게 쓰인다 —
              사진 칸에는 더 이상 없다. 375px 에서도 안 넘치도록 좁은
              화면에서는 작은 크기를 쓰고 sm 이상에서 더 키운다(둘 다
              "SUPERSUB" 텍스트라 한쪽은 항상 display:none 이라 접근성
              트리에 중복으로 안 잡힌다). formTitle 은 더는 화면에 안
              보이지만, 페이지에 제목이 있어야 하니 sr-only <h1>으로
              남긴다(랜딩 페이지 `<BrandMark /><h1 className="sr-only">`
              패턴과 동일).

              GlassPanel 과 같은 값(--ss-glass-bg/blur)으로 직접 유리
              재질(반투명+블러)을 낸다 — lg 이상에서는 폼 칸이 카드 오른쪽
              절반이라 왼쪽 모서리는 사진과 맞닿아 각지고 오른쪽만
              둥글다(lg 미만은 폼 칸이 카드 전체라 네 모서리 다 둥글다).
              테두리(고정 선 + 도는 빛)는 더 이상 여기서 그리지 않는다 —
              바깥 카드 래퍼(위)가 카드 전체 둘레를 한 번에 돈다. 여기서도
              그리면 바깥 것과 같은 자리(위/오른쪽/아래 변)에 겹쳐 두
              겹으로 보인다. */}
          <div
            className="relative flex flex-col overflow-y-auto rounded-[var(--ss-radius-sheet)] p-6 sm:p-10 lg:rounded-l-none lg:p-12"
            style={{
              // 전역 유리 값(--ss-glass-*)보다 **옅고 덜 흐리게** 이 칸에서만
              // 덮는다. 뒤에 연기가 비치는 자리라 20px 로 뭉개고 흰색을 8%
              // 얹으면 그 결이 죽어 그냥 반투명 검은 판으로 보인다. 다른
              // 유리(GlassPanel 을 쓰는 화면)는 그대로 둔다.
              background: 'color-mix(in srgb, var(--ss-fg) 4%, transparent)',
              // url(#…) 은 아래 SVG 필터 — 뒤 배경을 미세하게 일그러뜨린다.
              // 🔴 **흐린 뒤에 휘어야 한다.** 반대로 두면(휘고 나서 흐리면)
              // 8px 블러가 5px 어긋남을 통째로 지운다 — 실측으로 확인했다
              // (화면이 0.6%만 달라졌고 최대 차이가 4였다, 사실상 무효).
              backdropFilter: 'blur(8px) saturate(var(--ss-glass-saturate)) url(#ss-glass-warp)',
              WebkitBackdropFilter: 'blur(8px) saturate(var(--ss-glass-saturate)) url(#ss-glass-warp)',
            }}
          >
            {/* 이 열의 버튼 높이는 구글이 정한다. 구글이 그리는 로그인
                버튼은 높이 44px 고정이고 우리가 바꿀 수 없으므로(감추면
                클릭 자체가 막힌다 — GoogleSignInButton.tsx 주석), 반대로
                우리 PillButton 을 그 높이에 맞춘다. 전역 --ss-btn-h(54px,
                앱의 _kButtonHeight)는 건드리지 않고 이 열에서만 덮는다. */}
            <div
              className="m-auto flex w-full max-w-sm flex-col gap-8 py-6"
              style={
                {
                  '--ss-btn-h': 'var(--ss-google-btn-h)',
                  '--ss-btn-r': 'calc(var(--ss-google-btn-h) / 2)',
                } as React.CSSProperties
              }
            >
              <div className="flex flex-col items-center gap-3 text-center">
                <BrandMark size={34} className="sm:hidden" />
                <BrandMark size={48} className="hidden sm:inline" />
                <h1 className="sr-only">{formTitle}</h1>
                <p className="text-sm" style={{ color: MUTED }}>
                  {formDescription}
                </p>
              </div>
              {children}
              <div className="flex flex-col items-center gap-3 text-center">{footer}</div>
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}
