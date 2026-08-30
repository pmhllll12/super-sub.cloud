import type { Metadata } from "next";
import { Bigshot_One, Rubik, Rubik_Glitch } from "next/font/google";
import "material-symbols/outlined.css";
import "./globals.css";
import IntroGate from "@/components/IntroGate";

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

// 홈의 큰 영문 글자("OWN THE PITCH" · "FIND YOUR SQUAD") 전용 디스플레이
// 글꼴. 굵기가 400 하나뿐이라 font-weight 를 올려도 가짜 굵게(synthetic
// bold)만 걸린다 — 주지 않는다. 라틴만 있고 한글 글리프가 없으므로
// 한글에 쓰지 않는다.
const bigshotOne = Bigshot_One({
  variable: "--font-display",
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
        className={`${rubik.variable} ${rubikGlitch.variable} ${bigshotOne.variable} min-h-full flex flex-col`}
      >
        <IntroGate />
        {children}
      </body>
    </html>
  );
}
