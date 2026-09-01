import type { Metadata } from "next";
import {
  Abril_Fatface,
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

export const metadata: Metadata = {
  title: "Super-Sub",
  description: "생활체육 경기 영상을 분석해 용병을 찾고, 실력을 검증합니다.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body
        className={`${rubik.variable} ${rubikGlitch.variable} ${abrilFatface.variable} ${shrikhand.variable} ${youngSerif.variable} min-h-full flex flex-col`}
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
