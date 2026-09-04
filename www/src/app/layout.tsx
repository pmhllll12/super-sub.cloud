import type { Metadata } from "next";
import {
  Abril_Fatface,
  Anton,
  Freckle_Face,
  Grenze,
  Rakkas,
  Rubik,
  Rubik_Glitch,
  Shrikhand,
  Young_Serif,
} from "next/font/google";
import "material-symbols/outlined.css";
import "./globals.css";
import IntroGate from "@/components/IntroGate";
import AppFigure from "@/components/AppFigure";
import { PageTransitionProvider } from "@/lib/pageTransition";

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

// 홈의 큰 영문 글자("OWN THE PITCH") 전용 디스플레이
// 글꼴. 굵기가 400 하나뿐이라 font-weight 를 올려도 가짜 굵게(synthetic
// bold)만 걸린다 — 주지 않는다. 라틴만 있고 한글 글리프가 없으므로
// 한글에 쓰지 않는다.
const abrilFatface = Abril_Fatface({
  variable: "--font-display",
  weight: "400",
  subsets: ["latin"],
});

// 배경에 크게 깔리는 포스터 글자 전용(레슨 · 상점의 "TRAIN & GEAR UP").
//
// 굵기가 400 하나뿐인 장식 글꼴이라 **font-weight 를 주지 않는다** — 올려도
// 가짜 굵게(synthetic bold)만 걸려 획이 지저분해진다(Abril Fatface ·
// RubikGlitch 에서 이미 두 번 겪었다).
//
// 🔴 라틴만 있고 한글 글리프가 없다. 배경 글자에만 쓰고 본문에 쓰지 않는다.
const shrikhand = Shrikhand({
  variable: "--font-poster",
  weight: "400",
  subsets: ["latin"],
});

// 선수 카드의 영문 전용 세리프. 여기도 굵기가 400 하나뿐이라 font-weight
// 를 올리면 가짜 굵게(synthetic bold)만 걸린다 — 주지 않는다.
const youngSerif = Young_Serif({
  variable: "--font-card",
  weight: "400",
  subsets: ["latin"],
});

// 거름망 줄의 `Filters :` 전용(사용자 지정). 좁고 각진 세리프라 알약들
// 옆에서 이름표처럼 읽힌다.
//
// 🔴 굵기를 적어 준다. Google 쪽에서 가변 축을 가진 글꼴이라도 `next/font` 는
// 정적 굵기를 받아 오므로, 안 적으면 빌드에서 막힌다.
// 🔴 라틴만 있다 — 한글에 쓰지 않는다(다른 장식 글꼴들과 같은 규칙).
const grenze = Grenze({
  variable: "--font-label",
  weight: ["400", "600"],
  subsets: ["latin"],
});

// 홈의 큰 영문 헤드라인("OWN THE PITCH") 전용(사용자 지정, Rakkas).
//
// 🔴 굵기가 400 하나뿐인 장식 글꼴이라 **font-weight 를 주지 않는다** — 올리면
// 가짜 굵게(synthetic bold)만 걸려 획이 지저분해진다(Abril Fatface · Shrikhand ·
// RubikGlitch 에서 이미 겪었다).
// 🔴 라틴만 쓴다 — 한글에 쓰지 않는다(다른 장식 글꼴들과 같은 규칙).
const rakkas = Rakkas({
  variable: "--font-headline",
  weight: "400",
  subsets: ["latin"],
});

// 상점 배너 아래 한 마디("STORE") 전용(사용자 지정, Anton). 좁고 굵은 산세리프
// 라 짧은 대문자 한 단어가 간판처럼 읽힌다.
//
// 🔴 굵기가 400 하나뿐인 장식 글꼴이라 **font-weight 를 주지 않는다** — 올리면
// 가짜 굵게(synthetic bold)만 걸려 획이 지저분해진다(Abril Fatface · Shrikhand ·
// Rakkas · RubikGlitch 에서 이미 겪었다).
// 🔴 라틴만 쓴다 — 한글에 쓰지 않는다(다른 장식 글꼴들과 같은 규칙).
const anton = Anton({
  variable: "--font-sign",
  weight: "400",
  subsets: ["latin"],
});

// 프로필 화면의 큰 머리글("MY PROFILE") 전용(사용자 지정, Freckle Face).
// 손으로 뭉갠 듯한 굵은 대문자라 판 위에 얹는 한 마디에 맞는다.
//
// 🔴 굵기가 400 하나뿐인 장식 글꼴이라 **font-weight 를 주지 않는다** — 올리면
// 가짜 굵게(synthetic bold)만 걸려 획이 지저분해진다(Anton · Abril Fatface 등에서
// 이미 겪었다).
// 🔴 라틴만 쓴다 — 한글에 쓰지 않는다(다른 장식 글꼴들과 같은 규칙).
const freckleFace = Freckle_Face({
  variable: "--font-profile",
  weight: "400",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Super-Sub",
  description: "생활체육 경기 영상을 분석해 용병을 찾고, 실력을 검증합니다.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body
        className={`${rubik.variable} ${rubikGlitch.variable} ${abrilFatface.variable} ${shrikhand.variable} ${youngSerif.variable} ${grenze.variable} ${rakkas.variable} ${anton.variable} ${freckleFace.variable} min-h-full flex flex-col`}
      >
        <IntroGate />
        {/* 화면을 떠날 때 들어온 방향 그대로 되나가게 한다. 라우팅을 건너
            살아 있어야 해서 루트에 둔다(lib/pageTransition.tsx). */}
        <PageTransitionProvider>
          {/* 🔴 배경 사진은 **여기 한 곳에서만** 그린다. 홈과 `(app)` 이 각자
              그리던 때는 화면이 갈릴 때 이 컴포넌트가 새로 태어나서, 들어오는
              사진에 연출이 안 붙었다(나가는 쪽만 밀렸다). 라우팅을 건너 살아
              남아야 양쪽이 다 산다. 어느 화면에 무슨 사진인지는 AppFigure 가
              경로로 정하고, 배경이 없어야 하는 화면(로그인 등)은 거기서 뺀다. */}
          <AppFigure />
          {children}
        </PageTransitionProvider>
      </body>
    </html>
  );
}
