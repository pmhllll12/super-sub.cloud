import type { Metadata } from "next";
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

export const metadata: Metadata = {
  title: "Super-Sub",
  description: "생활체육 경기 영상을 분석해 용병을 찾고, 실력을 검증합니다.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body
        className={`${rubik.variable} ${rubikGlitch.variable} min-h-full flex flex-col`}
      >
        {children}
      </body>
    </html>
  );
}
