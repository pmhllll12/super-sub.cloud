# 앱 화면 이식 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `www/` 의 웹 화면을 Flutter 앱(`flutter/`)과 같은 화면 구성으로 다시 만든다 — 같은 토큰, 같은 컴포넌트, 같은 하단 내비바, 같은 홈 런처.

**Architecture:** 토큰과 자산을 먼저 깔고, 그 위에 공용 컴포넌트를 세우고, 셸(하단 내비바)을 붙인 뒤, 화면을 하나씩 갈아입힌다. 기존 Route Handler·데이터 레이어는 건드리지 않는다 — 이 계획은 **표현 계층만** 바꾼다.

**Tech Stack:** Next.js (App Router) · TypeScript · Tailwind CSS · Vitest + React Testing Library

**Spec:** `www/docs/2026-08-28-app-parity-design.md`

## Global Constraints

- **토큰 값은 스펙 1절의 표에서 그대로 가져온다.** 눈대중으로 고치지 않는다: 배경 `#000000`, 전경 `#FFFFFF`, 강조 `#70ED88`, 에러 `#FF8A80`, 스크림 `#00000026`, 시트 반경 `28px`, 버튼 높이 `54px` / 반경 `27px` / 라벨 `16px`, 워드마크 `34px`.
- **워드마크 자간은 `크기 × 1.2 / 44`.** 앱의 `BrandMark.letterSpacingFor` 와 같은 공식이어야 크기를 바꿔도 같은 글자로 읽힌다.
- **RubikGlitch 는 워드마크 `SUPERSUB` 에만 쓴다.** 본문·버튼·라벨에 쓰지 않는다.
- **아이콘은 Material Symbols Outlined.** 구형 Material Icons 를 쓰지 않는다 — 획 두께가 달라 줄이 들쭉날쭉해진다.
- **🔴 접근성 계약을 깨뜨리지 않는다.** 기존 테스트가 이 접점으로 요소를 집는다: `getByLabelText('이메일')`, `getByLabelText('비밀번호')`, `getByLabelText('닉네임')`, `getByRole('button', { name: '로그인' })`, `getByRole('button', { name: '가입하기' })`, `getByRole('button', { name: '저장' })`, `role="alert"`, `role="status"`, `getByRole('heading', { name: 'Super-Sub' })`(랜딩), `getByRole('link', { name: '로그인' })`(랜딩).
- **기존 테스트 40개가 계속 통과해야 한다.** 표현을 바꾸되 동작·문구·역할은 유지한다.
- **`NEXT_PUBLIC_` 접두사를 백엔드 관련 값에 붙이지 않는다.**
- `www/` 아래만 건드린다. `www/docs/`, 저장소 루트 공용 파일, `flutter/`(읽기만), `fastapi/`, `agent/` 는 건드리지 않는다.
- 커밋 메시지는 한국어.

---

### Task 1: 토큰 · 폰트 · 자산

**Files:**
- Modify: `www/src/app/globals.css`
- Modify: `www/src/app/layout.tsx`
- Create: `www/public/home_figure.jpg`, `www/public/player_mono.jpg`, `www/public/ink_field.png` (복사)
- Modify: `www/package.json` (`material-symbols`)

**Interfaces:**
- Consumes: 없음
- Produces: CSS 변수 `--ss-bg`, `--ss-fg`, `--ss-accent`, `--ss-error`, `--ss-scrim`, `--ss-radius-sheet`, `--ss-btn-h`, `--ss-btn-r`; 폰트 변수 `--font-rubik`, `--font-rubik-glitch`; `/home_figure.jpg` 등 자산 경로

- [ ] **Step 1: 자산 복사**

```bash
cd /Users/psg/project/super-sub.cloud
cp flutter/assets/images/home_figure.jpg www/public/
cp flutter/assets/images/player_mono.jpg www/public/
cp flutter/assets/images/ink_field.png  www/public/
ls -la www/public/*.jpg www/public/*.png
```

심볼릭 링크가 아니라 **복사**다. Vercel 빌드는 Root Directory(`www`) 밖을 보지 않는다.

- [ ] **Step 2: 아이콘 폰트 설치**

```bash
cd www && npm i material-symbols
```

자체 호스팅한다 — 외부 요청을 늘리지 않는다.

- [ ] **Step 3: 폰트를 레이아웃에 건다**

`www/src/app/layout.tsx` 의 기존 Geist 폰트를 교체한다:

```tsx
import { Rubik, Rubik_Glitch } from "next/font/google";
import "material-symbols/outlined.css";
import "./globals.css";

const rubik = Rubik({
  variable: "--font-rubik",
  subsets: ["latin"],
});

// 워드마크 전용. 본문에 쓰지 않는다.
const rubikGlitch = Rubik_Glitch({
  variable: "--font-rubik-glitch",
  weight: "400",
  subsets: ["latin"],
});
```

`<body>` 의 className 에 `${rubik.variable} ${rubikGlitch.variable}` 를 넣고, 기존 Geist 변수는 지운다. `<html lang>` 은 건드리지 않는다.

- [ ] **Step 4: 토큰을 CSS 변수로 깐다**

`www/src/app/globals.css` 에 넣는다. 값은 스펙 1절 그대로다.

```css
:root {
  --ss-bg: #000000;
  --ss-fg: #ffffff;
  --ss-accent: #70ed88;
  --ss-error: #ff8a80;
  --ss-scrim: rgba(0, 0, 0, 0.15);

  --ss-radius-sheet: 28px;
  --ss-btn-h: 54px;
  --ss-btn-r: 27px;
  --ss-btn-label: 16px;
  --ss-brand-size: 34px;

  /* 글래스 — flutter/lib/core/widgets/glass_panel.dart 를 옮긴 것 */
  --ss-glass-bg: rgba(255, 255, 255, 0.08);
  --ss-glass-border: rgba(255, 255, 255, 0.12);
  --ss-glass-blur: 20px;
}

body {
  background: var(--ss-bg);
  color: var(--ss-fg);
  font-family: var(--font-rubik), system-ui, sans-serif;
}

/* 앱의 잉크 질감. 화면 전체에 아주 옅게 깐다. */
body::before {
  content: "";
  position: fixed;
  inset: 0;
  background: url("/ink_field.png") center / cover no-repeat;
  opacity: 0.06;
  pointer-events: none;
  z-index: 0;
}
```

- [ ] **Step 5: 빌드와 테스트를 돌린다**

Run: `cd www && npm test && npm run build`
Expected: 40/40 통과, 빌드 성공. 이 태스크는 화면 마크업을 바꾸지 않으므로 테스트는 그대로 통과해야 한다. **깨지면 멈추고 보고한다.**

- [ ] **Step 6: 커밋**

```bash
git add www/
git commit -m "feat(www): 앱의 토큰·폰트·자산을 웹으로 가져온다"
```

---

### Task 2: 기본 컴포넌트

**Files:**
- Create: `www/src/components/ui/BrandMark.tsx`
- Create: `www/src/components/ui/GlassPanel.tsx`
- Create: `www/src/components/ui/PillButton.tsx`
- Create: `www/src/components/ui/Field.tsx`
- Test: `www/src/components/ui/BrandMark.test.tsx`
- Test: `www/src/components/ui/Field.test.tsx`

**Interfaces:**
- Consumes: Task 1의 CSS 변수
- Produces:
  - `<BrandMark size?: number />` — 기본 34
  - `<GlassPanel className?: string>{children}</GlassPanel>`
  - `<PillButton variant?: 'primary' | 'ghost' type? disabled? onClick?>{children}</PillButton>`
  - `<Field label: string type?: string value: string onChange: (v: string) => void required? minLength? maxLength? hint?: string />`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`www/src/components/ui/BrandMark.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import BrandMark, { letterSpacingFor } from './BrandMark'

describe('BrandMark', () => {
  it('SUPERSUB 를 그린다', () => {
    render(<BrandMark />)
    expect(screen.getByText('SUPERSUB')).toBeInTheDocument()
  })

  it('자간은 크기 × 1.2 / 44 다 — 앱과 같은 공식', () => {
    expect(letterSpacingFor(44)).toBeCloseTo(1.2)
    expect(letterSpacingFor(34)).toBeCloseTo(34 * 1.2 / 44)
    expect(letterSpacingFor(88)).toBeCloseTo(2.4)
  })
})
```

`www/src/components/ui/Field.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Field from './Field'

describe('Field', () => {
  it('라벨로 입력칸을 찾을 수 있다 — 기존 테스트가 이 접점을 쓴다', () => {
    render(<Field label="이메일" value="" onChange={() => {}} />)
    expect(screen.getByLabelText('이메일')).toBeInTheDocument()
  })

  it('입력하면 onChange 에 값이 온다', async () => {
    const onChange = vi.fn()
    render(<Field label="닉네임" value="" onChange={onChange} />)
    await userEvent.type(screen.getByLabelText('닉네임'), 'a')
    expect(onChange).toHaveBeenCalledWith('a')
  })

  it('hint 를 주면 함께 그린다', () => {
    render(<Field label="비밀번호" value="" onChange={() => {}} hint="8자 이상" />)
    expect(screen.getByText('8자 이상')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd www && npm test -- ui/`
Expected: FAIL — 모듈이 없다.

- [ ] **Step 3: `BrandMark` 를 구현한다**

```tsx
/** 앱의 BrandMark.letterSpacingFor 와 같은 공식. 크기가 바뀌어도 같은 글자로 읽혀야 한다. */
export function letterSpacingFor(size: number): number {
  return (size * 1.2) / 44
}

export default function BrandMark({
  size = 34,
  className = '',
}: {
  size?: number
  className?: string
}) {
  return (
    <span
      className={`select-none ${className}`}
      style={{
        fontFamily: 'var(--font-rubik-glitch)',
        fontSize: `${size}px`,
        letterSpacing: `${letterSpacingFor(size)}px`,
        color: 'var(--ss-accent)',
        lineHeight: 1,
      }}
    >
      SUPERSUB
    </span>
  )
}
```

- [ ] **Step 4: `GlassPanel` 을 구현한다**

앱 `glass_panel.dart` 의 상단 하이라이트 밴드(`0xE6FFFFFF`)를 `::before` 그라디언트로 옮긴다.

```tsx
export default function GlassPanel({
  className = '',
  children,
}: {
  className?: string
  children: React.ReactNode
}) {
  return (
    <div
      className={`relative overflow-hidden ${className}`}
      style={{
        borderRadius: 'var(--ss-radius-sheet)',
        background: 'var(--ss-glass-bg)',
        border: '1px solid var(--ss-glass-border)',
        backdropFilter: 'blur(var(--ss-glass-blur))',
        WebkitBackdropFilter: 'blur(var(--ss-glass-blur))',
      }}
    >
      <span
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-px"
        style={{
          background:
            'linear-gradient(90deg, transparent 0%, transparent 20%, rgba(255,255,255,0.9) 50%, transparent 80%, transparent 100%)',
        }}
      />
      {children}
    </div>
  )
}
```

- [ ] **Step 5: `PillButton` 을 구현한다**

```tsx
export default function PillButton({
  variant = 'primary',
  type = 'button',
  disabled,
  onClick,
  className = '',
  children,
}: {
  variant?: 'primary' | 'ghost'
  type?: 'button' | 'submit'
  disabled?: boolean
  onClick?: () => void
  className?: string
  children: React.ReactNode
}) {
  const primary = variant === 'primary'
  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={`inline-flex items-center justify-center px-8 transition disabled:opacity-50 ${className}`}
      style={{
        height: 'var(--ss-btn-h)',
        borderRadius: 'var(--ss-btn-r)',
        fontSize: 'var(--ss-btn-label)',
        background: primary ? 'var(--ss-accent)' : 'transparent',
        color: primary ? 'var(--ss-bg)' : 'var(--ss-fg)',
        border: primary ? 'none' : '1px solid var(--ss-glass-border)',
      }}
    >
      {children}
    </button>
  )
}
```

- [ ] **Step 6: `Field` 를 구현한다**

**`<label>` 로 감싸는 형태를 유지한다** — 기존 테스트가 `getByLabelText` 로 집는다.

```tsx
export default function Field({
  label,
  type = 'text',
  value,
  onChange,
  required,
  minLength,
  maxLength,
  hint,
}: {
  label: string
  type?: string
  value: string
  onChange: (v: string) => void
  required?: boolean
  minLength?: number
  maxLength?: number
  hint?: string
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-sm text-white/60">{label}</span>
      <input
        type={type}
        value={value}
        required={required}
        minLength={minLength}
        maxLength={maxLength}
        onChange={(e) => onChange(e.target.value)}
        className="bg-transparent px-4 py-3 outline-none focus:border-white/40"
        style={{
          borderRadius: '14px',
          border: '1px solid var(--ss-glass-border)',
        }}
      />
      {hint && <span className="text-xs text-white/40">{hint}</span>}
    </label>
  )
}
```

- [ ] **Step 7: 통과를 확인한다**

Run: `cd www && npm test -- ui/`
Expected: PASS (5 tests)

- [ ] **Step 8: 커밋**

```bash
git add www/src/components/ui/
git commit -m "feat(www): 앱의 브랜드·글래스·알약버튼을 컴포넌트로 옮긴다"
```

---

### Task 3: 하단 플로팅 내비바와 셸

**Files:**
- Create: `www/src/components/ui/FloatingNavBar.tsx`
- Create: `www/src/components/ui/FloatingNavBar.test.tsx`
- Create: `www/src/app/(app)/layout.tsx`
- Move: `www/src/app/me/` → `www/src/app/(app)/me/`, `www/src/app/analysis/` → `www/src/app/(app)/analysis/`

**Interfaces:**
- Consumes: Task 2의 `BrandMark`, `GlassPanel`
- Produces: `<FloatingNavBar />` — 로그인한 화면의 레이아웃이 그린다

**설계 메모:** Next.js 의 **라우트 그룹** `(app)` 을 쓴다. URL 에 `(app)` 이 들어가지 않으므로 `/me`, `/analysis` 경로는 그대로다. 바를 띄울 화면만 이 그룹에 넣으면 "로그인 안 한 화면에는 바를 숨긴다"가 파일 배치로 해결된다 — 화면마다 조건문을 두지 않아도 된다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```tsx
import { render, screen } from '@testing-library/react'
import FloatingNavBar from './FloatingNavBar'

vi.mock('next/navigation', () => ({ usePathname: () => '/home' }))

describe('하단 내비바', () => {
  it('앱과 같은 목적지를 그린다', () => {
    render(<FloatingNavBar />)
    expect(screen.getByRole('link', { name: '홈' })).toHaveAttribute('href', '/home')
    expect(screen.getByRole('link', { name: '영상 분석' })).toHaveAttribute('href', '/analysis')
    expect(screen.getByRole('link', { name: '내 선수 카드' })).toHaveAttribute('href', '/me/card')
    expect(screen.getByRole('link', { name: '내 프로필' })).toHaveAttribute('href', '/me')
  })

  it('현재 위치를 표시한다', () => {
    render(<FloatingNavBar />)
    expect(screen.getByRole('link', { name: '홈' })).toHaveAttribute('aria-current', 'page')
  })
})
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd www && npm test -- FloatingNavBar`
Expected: FAIL — 모듈이 없다.

- [ ] **Step 3: 내비바를 구현한다**

`www/src/components/ui/FloatingNavBar.tsx` — `'use client'`. 앱의 자리 배치를 따른다: **왼쪽에 로고 알약, 오른쪽에 아이콘 줄.** 화면 하단에 떠 있고(`fixed`), 가운데 정렬에 최대폭을 잡는다.

아이콘은 Material Symbols Outlined 글리프를 `<span className="material-symbols-outlined">` 로 쓴다. 글리프 이름은 앱과 같다: `videocam`, `sports_soccer`, `id_card`, `person`.

각 링크에 접근 가능한 이름을 준다(`aria-label`) — 아이콘만으로는 이름이 없다. 현재 경로면 `aria-current="page"` 를 단다.

- [ ] **Step 4: 통과를 확인한다**

Run: `cd www && npm test -- FloatingNavBar`
Expected: PASS (2 tests)

- [ ] **Step 5: 라우트 그룹으로 옮긴다**

```bash
cd /Users/psg/project/super-sub.cloud/www/src/app
mkdir -p "(app)"
git mv me "(app)/me"
git mv analysis "(app)/analysis"
```

`www/src/app/(app)/layout.tsx` 를 만든다 — 본문을 최대폭 1120px 로 감싸고, 하단 바에 가리지 않도록 아래 여백을 준 뒤 `<FloatingNavBar />` 를 그린다.

- [ ] **Step 6: 전체 테스트와 빌드**

Run: `cd www && npm test && npm run build`
Expected: 전부 통과. `/me`, `/me/card`, `/analysis` 의 URL 이 그대로인지 빌드 출력에서 확인한다.

- [ ] **Step 7: 커밋**

```bash
git add -A www/src/
git commit -m "feat(www): 하단 플로팅 내비바 — 로그인한 화면만 라우트 그룹으로 묶는다"
```

---

### Task 4: `/home` 런처

**Files:**
- Create: `www/src/app/(app)/home/page.tsx`
- Create: `www/src/components/DestinationCard.tsx`
- Test: `www/src/components/DestinationCard.test.tsx`

**Interfaces:**
- Consumes: Task 2의 `GlassPanel`, Task 3의 셸
- Produces: `/home` 경로

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```tsx
import { render, screen } from '@testing-library/react'
import DestinationCard from './DestinationCard'

describe('목적지 카드', () => {
  it('갈 수 있는 곳은 링크다', () => {
    render(<DestinationCard title="영상 분석" icon="videocam" href="/analysis" />)
    expect(screen.getByRole('link', { name: /영상 분석/ })).toHaveAttribute('href', '/analysis')
  })

  it('준비 중인 곳은 링크가 아니고 그렇게 표시한다', () => {
    render(<DestinationCard title="용병 매칭" icon="sports_soccer" />)
    expect(screen.queryByRole('link')).toBeNull()
    expect(screen.getByText(/준비 중/)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: 실패 확인 → 구현 → 통과 확인**

Run: `cd www && npm test -- DestinationCard`

`DestinationCard` 는 `href` 가 있으면 `<Link>`, 없으면 `<div>` + "준비 중입니다" 표시. `GlassPanel` 을 바탕으로 쓴다.

- [ ] **Step 3: `/home` 을 만든다**

서버 컴포넌트. `requireUser()` 로 로그인을 확인하고 닉네임으로 인사한 뒤, 카드 6개를 격자로 그린다. 목록은 앱 `home_screen.dart` 의 `_kDestinations` 그대로:

| 제목 | 아이콘 | 링크 |
|---|---|---|
| 영상 분석 | `videocam` | `/analysis` |
| 용병 매칭 | `sports_soccer` | (준비 중) |
| 내 선수 카드 | `id_card` | `/me/card` |
| 내 팀 | `groups` | (준비 중) |
| 레슨 · 코치 | `school` | (준비 중) |
| 내 프로필 | `person` | `/me` |

- [ ] **Step 4: 로그인 후 목적지를 `/home` 으로 바꾼다**

`www/src/app/login/page.tsx` 의 `router.push('/me')` 를 `router.push('/home')` 으로 바꾼다. 앱도 로그인하면 홈으로 간다.

**기존 로그인 테스트가 `next/navigation` 을 모킹하고 있어 이 변경으로 깨지지 않는다** — 확인하고, 만약 경로를 단언하는 테스트가 있으면 함께 고친다.

- [ ] **Step 5: 전체 테스트와 빌드 → 커밋**

```bash
git add www/
git commit -m "feat(www): 홈 런처 — 앱의 목적지 카드 여섯 장"
```

---

### Task 5: 로그인 · 회원가입 화면을 앱 모양으로

**Files:**
- Modify: `www/src/app/login/page.tsx`
- Modify: `www/src/app/signup/page.tsx`

**Interfaces:**
- Consumes: Task 2의 `BrandMark`, `GlassPanel`, `PillButton`, `Field`
- Produces: 없음 (화면만)

**🔴 이 태스크의 핵심 위험:** 기존 테스트가 `getByLabelText('이메일')`, `getByLabelText('비밀번호')`, `getByRole('button', { name: '로그인' })`, `role="alert"` 로 요소를 집는다. 마크업을 바꾸되 **이 접점과 문구를 그대로 둔다.** `Field` 와 `PillButton` 이 그 형태를 유지하도록 만들어져 있다.

- [ ] **Step 1: 기존 테스트를 먼저 돌려 기준선을 잡는다**

Run: `cd www && npm test -- login/page`
Expected: PASS (2 tests) — 바꾸기 전 상태

- [ ] **Step 2: 로그인 화면을 갈아입힌다**

배경에 `player_mono.jpg` 를 깔고 스크림(`--ss-scrim`)을 얹은 뒤, 가운데 `GlassPanel` 시트(최대 420px)를 둔다. 시트 위에 `<BrandMark />`, 그 아래 `Field` 두 개, `PillButton` 으로 제출. 에러는 `role="alert"` 로 `--ss-error` 색.

**로직은 건드리지 않는다** — `apiPost`, `apiErrorMessage`, `busy` 처리, 이동 경로 전부 그대로.

- [ ] **Step 3: 테스트가 여전히 통과하는지 확인한다**

Run: `cd www && npm test -- login/page`
Expected: PASS (2 tests) — **깨지면 마크업이 접근성 계약을 어긴 것이다.** 테스트를 고치지 말고 마크업을 고친다.

- [ ] **Step 4: 회원가입 화면을 같은 모양으로**

같은 시트, `Field` 세 개(이메일·비밀번호(hint "8자 이상")·닉네임(hint "1~20자")). 로직 그대로.

- [ ] **Step 5: 전체 테스트와 빌드 → 커밋**

```bash
git add www/src/app/login/ www/src/app/signup/
git commit -m "feat(www): 로그인·회원가입을 앱의 글래스 시트로"
```

---

### Task 6: 프로필 · 카드 화면을 앱 모양으로

**Files:**
- Modify: `www/src/app/(app)/me/page.tsx`
- Modify: `www/src/app/(app)/me/NicknameForm.tsx`
- Modify: `www/src/app/(app)/me/card/page.tsx`
- Modify: `www/src/app/c/[slug]/page.tsx`
- Modify: `www/src/components/PlayerCardView.tsx`

**Interfaces:**
- Consumes: Task 2의 컴포넌트
- Produces: 없음 (화면만)

**🔴 두 가지를 지킨다:**
1. `NicknameForm` 의 `getByLabelText('닉네임')`, `getByRole('button', { name: '저장' })`, `role="status"`, `role="alert"`
2. **카드에 수치를 그리지 않는다** — `PlayerCardView.test.tsx` 의 가드가 `★`, `%`, 소수, `점`, `등급`, `<progress>`, `<meter>` 를 검사한다. 디자인을 입히면서 별점이나 능력치 바를 넣지 않는다

- [ ] **Step 1: 기준선**

Run: `cd www && npm test -- "NicknameForm|PlayerCardView"`
Expected: PASS (6 tests)

- [ ] **Step 2: `PlayerCardView` 를 앱 카드 모양으로**

`GlassPanel` 바탕에 닉네임(크게), 호칭을 알약 태그로. 배경에 `player_mono.jpg` 를 옅게. **수치 없음.**

- [ ] **Step 3: 가드가 여전히 통과하는지 확인한다**

Run: `cd www && npm test -- PlayerCardView`
Expected: PASS (3 tests). **실패하면 디자인에 수치가 들어간 것이다.** 테스트가 아니라 디자인을 고친다.

- [ ] **Step 4: 프로필·내 카드·공개 카드 화면을 갈아입힌다**

`/me` 는 좌측 프로필 `GlassPanel` + 우측 소속 팀 목록(2열, 좁은 화면에선 1열). **빈 소속 팀 상태를 유지한다.** `/me/card` 와 `/c/[slug]` 는 카드를 가운데.

`NicknameForm` 은 `Field` + `PillButton` 으로 갈아끼우되 로직과 role 은 그대로.

- [ ] **Step 5: 전체 테스트와 빌드 → 커밋**

```bash
git add www/src/
git commit -m "feat(www): 프로필·선수 카드를 앱 모양으로 — 수치는 여전히 그리지 않는다"
```

---

### Task 7: 랜딩과 영상 분석 화면

**Files:**
- Modify: `www/src/app/page.tsx`
- Create: `www/src/app/(app)/analysis/page.tsx` (Task 3에서 옮겨진 자리, 없으면 생성)
- Modify: `www/src/app/page.test.tsx` (필요시)

**Interfaces:**
- Consumes: Task 2의 컴포넌트
- Produces: 없음

**🔴 랜딩의 기존 테스트**가 `getByRole('heading', { name: /Super-Sub/i })` 와 `getByRole('link', { name: '로그인' })` 을 집는다. 워드마크를 `BrandMark`(SUPERSUB) 로 바꾸면 heading 텍스트가 달라져 깨진다. **이건 의도된 변경이므로 테스트를 함께 고친다** — 단, 고칠 때 "로그인 링크가 `/login` 을 가리킨다"는 단언은 유지한다.

- [ ] **Step 1: 랜딩을 갈아입힌다**

좌측에 `<BrandMark size={72} />` + 설명 문구 + `PillButton` 두 개(로그인 primary, 회원가입 ghost), 우측에 `home_figure.jpg` + 스크림. 좁은 화면에서는 세로로 쌓는다.

- [ ] **Step 2: 랜딩 테스트를 새 마크업에 맞춘다**

```tsx
it('워드마크를 보여준다', () => {
  render(<Home />)
  expect(screen.getByText('SUPERSUB')).toBeInTheDocument()
})

it('로그인으로 가는 링크가 있다', () => {
  render(<Home />)
  expect(screen.getByRole('link', { name: '로그인' })).toHaveAttribute('href', '/login')
})
```

- [ ] **Step 3: 영상 분석 화면**

`GlassPanel` 안에 "준비 중입니다" 와 설명. **가짜 분석 결과나 수치를 그리지 않는다** — 데모에서 오해받는다.

- [ ] **Step 4: 전체 테스트와 빌드**

Run: `cd www && npm test && npm run build`
Expected: 전부 통과

- [ ] **Step 5: 손으로 확인한다**

```bash
cd www && USE_MOCK=1 npm run dev
```

`/`, `/login`(데모 계정 `demo@super-sub.example` / `supersub2026`), `/home`, `/me`, `/me/card`, `/c/hong-gildong-4f2a`, `/analysis` 를 차례로 열어 하단 바가 로그인한 화면에만 뜨는지, 워드마크가 글리치 폰트로 나오는지 확인한다.

- [ ] **Step 6: 커밋**

```bash
git add www/
git commit -m "feat(www): 랜딩과 영상 분석 화면 — 글리치 워드마크"
```

---

### Task 8: 글리치 워드마크와 인트로

**Files:**
- Modify: `www/src/components/ui/BrandMark.tsx`
- Modify: `www/src/app/globals.css`
- Create: `www/src/components/IntroGate.tsx`
- Create: `www/src/lib/intro.ts`
- Test: `www/src/lib/intro.test.ts`
- Test: `www/src/components/ui/BrandMark.test.tsx` (기존 파일에 추가)

**Interfaces:**
- Consumes: Task 2의 `BrandMark`
- Produces:
  - `<BrandMark glitch?: boolean />`
  - `shouldPlayIntro(pathname: string, seen: boolean): boolean` — 순수 함수
  - `<IntroGate />` — 클라이언트 컴포넌트

**설계 메모:** 판단(언제 재생하나)을 순수 함수로 빼고, DOM·타이머·`sessionStorage` 는 얇은 껍데기로 둔다. 그래야 규칙을 테스트할 수 있다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`www/src/lib/intro.test.ts`:

```ts
import { shouldPlayIntro } from './intro'

describe('인트로 재생 규칙', () => {
  it('앱 진입에서는 재생한다', () => {
    expect(shouldPlayIntro('/', false)).toBe(true)
    expect(shouldPlayIntro('/login', false)).toBe(true)
  })

  it('공개 카드 링크에서는 재생하지 않는다 — 공유 링크의 목적을 깨뜨린다', () => {
    expect(shouldPlayIntro('/c/hong-gildong-4f2a', false)).toBe(false)
  })

  it('이미 본 세션에서는 재생하지 않는다', () => {
    expect(shouldPlayIntro('/', true)).toBe(false)
    expect(shouldPlayIntro('/login', true)).toBe(false)
  })

  it('로그인한 화면에서는 재생하지 않는다', () => {
    expect(shouldPlayIntro('/home', false)).toBe(false)
    expect(shouldPlayIntro('/me', false)).toBe(false)
  })
})
```

`BrandMark.test.tsx` 에 추가:

```tsx
it('glitch 를 주면 애니메이션 클래스가 붙는다', () => {
  const { container } = render(<BrandMark glitch />)
  expect(container.firstElementChild?.className).toMatch(/ss-glitch/)
})

it('기본값은 글리치가 아니다', () => {
  const { container } = render(<BrandMark />)
  expect(container.firstElementChild?.className).not.toMatch(/ss-glitch/)
})
```

- [ ] **Step 2: 실패 확인**

Run: `cd www && npm test -- "intro|BrandMark"`
Expected: FAIL

- [ ] **Step 3: `shouldPlayIntro` 를 구현한다**

```ts
/** 인트로를 재생할 자리. 앱 진입 두 곳뿐이다. */
const ENTRY_PATHS = ['/', '/login']

export function shouldPlayIntro(pathname: string, seen: boolean): boolean {
  if (seen) return false
  return ENTRY_PATHS.includes(pathname)
}

export const INTRO_SEEN_KEY = 'supersub_intro_seen'
```

- [ ] **Step 4: 글리치 애니메이션을 CSS 로 쓴다**

`globals.css` 에 넣는다. 앱의 인트로는 글자가 지지직대다 굳는다 — 색 어긋남(chromatic split)과 잘림(clip)이 핵심이다.

```css
@keyframes ss-glitch-shift {
  0%, 100% { transform: translate(0); }
  20% { transform: translate(-2px, 1px); }
  40% { transform: translate(2px, -1px); }
  60% { transform: translate(-1px, -1px); }
  80% { transform: translate(1px, 1px); }
}

.ss-glitch {
  position: relative;
  animation: ss-glitch-shift 220ms steps(2, end) infinite;
}

/* 색이 어긋난 두 겹. 원본 글자 위아래로 살짝 벌어진다. */
.ss-glitch::before,
.ss-glitch::after {
  content: attr(data-text);
  position: absolute;
  inset: 0;
  pointer-events: none;
}
.ss-glitch::before { color: #ff4d4d; transform: translate(-2px, 0); mix-blend-mode: screen; }
.ss-glitch::after  { color: #4dd2ff; transform: translate(2px, 0);  mix-blend-mode: screen; }

/* 움직임을 원치 않는 사용자에게는 흔들지 않는다. */
@media (prefers-reduced-motion: reduce) {
  .ss-glitch, .ss-glitch::before, .ss-glitch::after { animation: none; transform: none; }
}
```

- [ ] **Step 5: `BrandMark` 에 `glitch` 를 붙인다**

`glitch` 가 참이면 `ss-glitch` 클래스와 `data-text="SUPERSUB"` 를 단다 (`::before`/`::after` 가 `attr(data-text)` 를 읽는다).

- [ ] **Step 6: `IntroGate` 를 만든다**

`'use client'`. `usePathname()` 과 `sessionStorage` 를 읽어 `shouldPlayIntro` 로 판단하고, 참이면 검은 전면 오버레이에 `<BrandMark glitch size={72} />` 를 2.5초 띄운 뒤 사라진다. 끝나면 `sessionStorage.setItem(INTRO_SEEN_KEY, '1')`.

**`sessionStorage` 접근은 반드시 try/catch 로 감싼다** — 사파리 프라이빗 모드 등에서 던진다. 던지면 인트로를 건너뛰고 화면을 보여준다. 인트로 때문에 앱이 안 열리면 안 된다.

루트 `layout.tsx` 에 얹는다.

- [ ] **Step 7: 통과 확인 → 전체 테스트 → 빌드 → 커밋**

```bash
git add www/
git commit -m "feat(www): 글리치 워드마크와 인트로 — 공유 링크에서는 건너뛴다"
```

---

### Task 9: 로고 비행 (FLIP)

**Files:**
- Create: `www/src/lib/flight.ts`
- Test: `www/src/lib/flight.test.ts`
- Modify: `www/src/app/login/page.tsx`
- Modify: `www/src/components/ui/FloatingNavBar.tsx`

**Interfaces:**
- Consumes: Task 3의 `FloatingNavBar`, Task 5의 로그인 화면
- Produces: `computeFlight(from: Rect, to: Rect): { dx: number; dy: number; scale: number }` — 순수 함수

**설계 메모:** 앱은 `GlobalKey` 로 착지점의 화면 좌표를 읽어 글자를 직접 날린다(`brand_mark.dart` 주석). 웹도 같은 발상이다 — `getBoundingClientRect` 로 두 좌표를 재고 `transform` 으로 옮긴다. **계산을 순수 함수로 빼서 테스트한다.**

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```ts
import { computeFlight } from './flight'

const rect = (x: number, y: number, w: number, h: number) => ({
  left: x, top: y, width: w, height: h,
})

describe('로고 비행 계산', () => {
  it('중심에서 중심으로 옮기는 거리를 준다', () => {
    const from = rect(100, 100, 200, 40)   // 중심 (200, 120)
    const to = rect(500, 700, 100, 20)     // 중심 (550, 710)
    const { dx, dy } = computeFlight(from, to)
    expect(dx).toBeCloseTo(350)
    expect(dy).toBeCloseTo(590)
  })

  it('폭 비율로 크기를 줄인다', () => {
    const from = rect(0, 0, 200, 40)
    const to = rect(0, 0, 100, 20)
    expect(computeFlight(from, to).scale).toBeCloseTo(0.5)
  })

  it('같은 자리면 움직이지 않는다', () => {
    const r = rect(10, 20, 30, 40)
    expect(computeFlight(r, r)).toEqual({ dx: 0, dy: 0, scale: 1 })
  })
})
```

- [ ] **Step 2: 실패 확인 → 구현 → 통과 확인**

```ts
export type FlightRect = { left: number; top: number; width: number; height: number }

export function computeFlight(from: FlightRect, to: FlightRect) {
  const fromCx = from.left + from.width / 2
  const fromCy = from.top + from.height / 2
  const toCx = to.left + to.width / 2
  const toCy = to.top + to.height / 2
  return {
    dx: toCx - fromCx,
    dy: toCy - fromCy,
    scale: from.width === 0 ? 1 : to.width / from.width,
  }
}
```

Run: `cd www && npm test -- flight`
Expected: PASS (3 tests)

- [ ] **Step 3: 착지점에 표식을 단다**

`FloatingNavBar.tsx` 의 로고 알약에 `data-flight-target="brand"` 를 단다.

- [ ] **Step 4: 로그인 성공 때 날린다**

로그인 화면의 `<BrandMark />` 에 ref 를 달고, `apiPost` 가 성공한 뒤 `router.push('/home')` 하기 전에:

1. 출발 좌표를 잰다
2. `router.push('/home')` 후 착지점(`[data-flight-target="brand"]`)이 나타나기를 기다린다
3. 복제한 글자를 `position: fixed` 로 띄우고 `computeFlight` 값으로 `transform` 애니메이션
4. 끝나면 복제를 지운다

**착지점을 못 찾으면 그냥 넘어간다.** 연출 때문에 로그인이 막히면 안 된다. `prefers-reduced-motion` 이면 건너뛴다.

- [ ] **Step 5: 로그인 테스트가 여전히 통과하는지 확인한다**

Run: `cd www && npm test -- login/page`
Expected: PASS — 기존 2개. **깨지면 연출이 로직을 침범한 것이다.**

- [ ] **Step 6: 전체 테스트 → 빌드 → 손 확인 → 커밋**

```bash
git add www/
git commit -m "feat(www): 로고 비행 — 로그인 글자가 하단 바 노치로 날아간다"
```

---

### Task 10: 잉크 전환

**Files:**
- Create: `www/src/lib/ink.ts`
- Test: `www/src/lib/ink.test.ts`
- Create: `www/src/components/InkTransition.tsx`
- Modify: `www/src/app/login/page.tsx`

**Interfaces:**
- Consumes: `/ink_field.png` (Task 1에서 복사됨)
- Produces: `inkThreshold(elapsed: number, duration: number): number` — 순수 함수

**설계 메모:** `ink_bleed.frag` 를 WebGL 로 옮기지 않는다. `ink_field.png` 가 원래 그 셰이더가 샘플링하는 잉크 맵이므로, **canvas 2D 에서 그 이미지를 마스크로 쓰고 임계값을 애니메이션**하면 같은 재질의 "잉크가 걷히는" 연출이 나온다.

> ⚠️ **결과가 원본과 얼마나 같을지는 만들어봐야 안다.** 어설프면 넣지 않는 편이 낫다 — 어중간한 연출은 없는 것만 못하다. 구현 후 손으로 보고, 아니다 싶으면 그렇게 보고할 것.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```ts
import { inkThreshold } from './ink'

describe('잉크 임계값', () => {
  it('시작에는 완전히 덮여 있다', () => {
    expect(inkThreshold(0, 1000)).toBe(0)
  })

  it('끝에는 완전히 걷힌다', () => {
    expect(inkThreshold(1000, 1000)).toBe(1)
  })

  it('시간을 넘겨도 1 을 넘지 않는다', () => {
    expect(inkThreshold(5000, 1000)).toBe(1)
  })

  it('단조증가한다', () => {
    const xs = [0, 250, 500, 750, 1000].map((t) => inkThreshold(t, 1000))
    for (let i = 1; i < xs.length; i++) expect(xs[i]).toBeGreaterThan(xs[i - 1])
  })
})
```

- [ ] **Step 2: 실패 확인 → 구현 → 통과 확인**

```ts
/** 잉크가 걷힌 정도. 0 이면 완전히 덮인 상태, 1 이면 다 걷힌 상태. */
export function inkThreshold(elapsed: number, duration: number): number {
  if (duration <= 0) return 1
  const t = Math.min(1, Math.max(0, elapsed / duration))
  // 끝에서 부드럽게 멎는다.
  return 1 - Math.pow(1 - t, 3)
}
```

- [ ] **Step 3: `InkTransition` 을 만든다**

`'use client'`. 전면 canvas 를 띄우고, `/ink_field.png` 를 그린 뒤 `globalCompositeOperation` 과 `inkThreshold` 로 잉크가 걷히는 모습을 매 프레임 그린다. 끝나면 canvas 를 제거한다.

- 이미지 로드에 실패하면 **연출 없이 즉시 끝낸다** (`onerror`)
- `prefers-reduced-motion` 이면 재생하지 않는다
- 마무리 시 `cancelAnimationFrame` 으로 정리한다

- [ ] **Step 4: 로그인 → 홈 전환에 건다**

Task 9의 로고 비행과 **같은 전환에서 함께** 재생된다 (앱도 그렇다 — 잉크가 걷히는 위에 로고가 날아간다).

- [ ] **Step 5: 손으로 보고 판단한다**

```bash
cd www && USE_MOCK=1 npm run dev
```

데모 계정으로 로그인해 전환을 본다. **앱의 느낌이 안 나면 그대로 보고한다** — 억지로 통과시키지 말 것.

- [ ] **Step 6: 전체 테스트 → 빌드 → 커밋**

```bash
git add www/
git commit -m "feat(www): 잉크 전환 — 셰이더 대신 잉크 맵을 canvas 마스크로 쓴다"
```

---

## 이 계획에 넣지 않은 것

- **`liquid_glass.frag`** — 글래스는 CSS `backdrop-filter` 로 대신한다. 굴절까지 옮기려면 WebGL 이 필요하고 그 값어치가 없다
- **`design_scale` 의 1080px 환산** — 데스크톱 재배치라 옮기지 않는다
- **용병 매칭 · 내 팀 · 레슨·코치** — 백엔드가 없다. 홈에 "준비 중" 카드로만 둔다
