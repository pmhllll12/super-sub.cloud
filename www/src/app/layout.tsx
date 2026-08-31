import type { Metadata } from "next";
import { Abril_Fatface, Rubik, Rubik_Glitch, Young_Serif } from "next/font/google";
import "material-symbols/outlined.css";
import "./globals.css";
import IntroGate from "@/components/IntroGate";
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
        className={`${rubik.variable} ${rubikGlitch.variable} ${abrilFatface.variable} ${youngSerif.variable} min-h-full flex flex-col`}
      >
        <IntroGate />
        {/* 화면을 떠날 때 들어온 방향 그대로 되나가게 한다. 라우팅을 건너
            살아 있어야 해서 루트에 둔다(lib/pageTransition.tsx). */}
        <PageTransitionProvider>{children}</PageTransitionProvider>
      </body>
    </html>
  );
}
