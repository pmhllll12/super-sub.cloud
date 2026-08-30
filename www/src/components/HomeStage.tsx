'use client'

import Link from 'next/link'
import { useState } from 'react'
import BrandMark from '@/components/ui/BrandMark'
import FigureBackground from '@/components/FigureBackground'
import HomeIndexList from '@/components/HomeIndexList'
import HomeNav, { type Destination } from '@/components/HomeNav'
import LogoutButton, { HEADER_LINK_CLASS, HEADER_LINK_HOVER_CLASS } from '@/components/LogoutButton'

export type { Destination }

/**
 * 홈 한 화면 — 배경 사진 위에 글자를 얹는 레퍼런스(Nile Travel) 배치다.
 *
 *   워드마크        영상분석 용병매칭 …        닉네임 로그아웃
 *   헤드라인(큰 글자)                          보조 문구
 *   정보 블록 3열
 *   SCROLL DOWN  소셜                          01~06 번호 목록
 *
 * 예전에는 화면 아래에 카드 6장이 가로로 흐르는 캐러셀이 있었다. 카드가
 * 배경 사진을 절반 넘게 가려서, 목적지는 위쪽 **글자**로만 적고 카드는
 * 그 글자를 가리켰을 때만 아래로 떠오르게 바꿨다(`HomeNav`).
 *
 * 지금 가리킨 목적지(`active`)를 여기서 쥔다 — 위쪽 글자와 우하단 번호
 * 목록이 **같은 항목을 같이 밝혀야** 해서다(레퍼런스에서 04 번이 그렇다).
 * 어느 쪽에 마우스를 올려도 반대쪽이 따라 밝아진다.
 *
 * 🔴 **글자는 마우스를 따라 움직이지 않는다.** 한때 마우스 시차로 헤더와
 * 헤드라인을 미세하게 흔들었는데(`useMouseParallax`), 글자가 화면을
 * 채우는 지금 배치에서는 읽는 내내 흔들려 어지러웠다 — 사용자 요청으로
 * 걷어냈다. 되살릴 거면 배경이나 사진 층에만 걸 것.
 */

// 레퍼런스의 `Meeting Point / Price / Duration` 자리. 아직 없는 기능을
// 있는 것처럼 적지 않는다 — 세 번째 칸은 준비 중인 목적지를 그대로 적는다.
const INFO_BLOCKS = [
  { heading: '시작하기', body: '영상 한 편이면 됩니다\n올린 뒤 기다리면 됩니다' },
  { heading: '무엇이 나오나', body: '점수가 아니라 호칭입니다\n잘한 것에 이름을 붙입니다' },
  { heading: '준비 중', body: '용병 매칭 · 내 팀\n레슨 · 상점 · 경기장 예약' },
]

const SOCIALS = ['FACEBOOK', 'INSTAGRAM', 'TIKTOK']

export default function HomeStage({
  user,
  destinations,
}: {
  user: { nickname: string } | null
  destinations: Destination[]
}) {
  const [active, setActive] = useState<string | null>(null)

  return (
    <>
      <FigureBackground />

      {/* 헤더 — 워드마크 · 목적지 글자 · 인사말. 화면에 고정한다. */}
      <div
        // 워드마크 · 목적지 글자 · 인사말 세 덩어리 사이는 목적지 글자
        // **칸 사이(40px)보다 넉넉히** 띄운다 — 안 그러면 닉네임이 목적지
        // 글자 하나처럼 붙어 읽힌다(실측: 32px 이면 그렇게 보였다).
        className="fixed inset-x-0 top-0 z-20 flex items-start justify-between gap-16"
        style={{ padding: 'var(--ss-home-content-pad)' }}
      >
        <BrandMark size={26} />

        <div className="ss-home-nav-slot">
          <HomeNav
            destinations={destinations}
            loggedIn={Boolean(user)}
            active={active}
            onActivate={setActive}
          />
        </div>

        {user ? (
          <div className="flex shrink-0 items-center gap-1">
            {/* 닉네임이 곧 '내 프로필'이다 — 목적지 글자 줄에 같은 항목을
                또 두지 않는다(사용자 요청). 자기 이름을 눌러 자기 화면으로
                가는 건 어디서나 하는 동작이라 따로 설명이 필요 없다. */}
            <Link
              href="/me"
              className={`${HEADER_LINK_CLASS} ${HEADER_LINK_HOVER_CLASS}`}
              style={{ color: 'var(--ss-fg)' }}
            >
              {user.nickname}
            </Link>
            <LogoutButton />
          </div>
        ) : (
          <div className="flex shrink-0 items-center gap-1">
            <Link href="/login" className={`${HEADER_LINK_CLASS} ${HEADER_LINK_HOVER_CLASS}`} style={{ color: 'var(--ss-accent)' }}>
              로그인
            </Link>
            <Link href="/signup" className={`${HEADER_LINK_CLASS} ${HEADER_LINK_HOVER_CLASS}`} style={{ color: 'var(--ss-fg)' }}>
              회원가입
            </Link>
          </div>
        )}
      </div>

      {/* 헤드라인 · 보조 문구 · 정보 블록. 로그인 화면과 같은 문구를 쓴다 —
          두 화면이 한 목소리로 들리게. */}
      <div className="ss-home-stage" style={{ padding: 'var(--ss-home-content-pad)' }}>
        <div className="flex items-start justify-between gap-8">
          {/* 레퍼런스(THE CAMEL / AND / THE WHEEL)처럼 스텐실 글꼴로 두 줄.
              Bigshot One 은 라틴만 있어 한글을 못 쓴다 — 그래서 문구도 영문이다.

              PITCH 의 P 가 윗줄 THE 의 T 와 같은 자리에서 시작해야 해서
              (사용자 요청) 낱말 셋을 2열 그리드에 앉힌다: OWN | THE 가
              첫 줄, 둘째 줄은 첫 칸을 비우고 PITCH 가 둘째 칸에 온다.
              왼쪽 정렬을 그리드가 보장하므로 눈대중 여백이 필요 없다.

              낱말이 각자 span 이라 사이에 공백 문자가 없다 — 그냥 두면
              접근성 이름이 "OWNTHEPITCH" 로 붙어 읽힌다. 이름을 따로 준다. */}
          <h1 className="ss-home-display ss-home-headline" aria-label="OWN THE PITCH">
            <span>OWN</span>
            <span>THE</span>
            <span className="ss-home-headline-second">PITCH</span>
          </h1>

          {/* 오른쪽 짝 — 헤드라인과 같은 글꼴 · 같은 크기(ss-home-display)로
              세 줄. 줄이 내려갈수록 시작점이 조금씩 오른쪽으로 밀린다
              (사용자 요청, 레퍼런스의 THE CAMEL / AND / THE WHEEL 처럼
              계단 모양). 여기도 낱말이 각자 span 이라 이름을 따로 준다. */}
          <p className="ss-home-display ss-home-subhead" aria-label="FIND YOUR SQUAD">
            <span>FIND</span>
            <span>YOUR</span>
            <span>SQUAD</span>
          </p>
        </div>

        <dl className="ss-home-info">
          {INFO_BLOCKS.map((b) => (
            <div key={b.heading}>
              <dt>{b.heading}</dt>
              <dd>{b.body}</dd>
            </div>
          ))}
        </dl>
      </div>

      {/* 하단 줄 — 왼쪽(SCROLL DOWN · 소셜)과 오른쪽(번호 목록). */}
      <div className="ss-home-footer">
        <div className="ss-home-footer-left">
          <span className="ss-home-scroll">
            SCROLL DOWN <span aria-hidden="true">↓</span>
          </span>
          <ul className="ss-home-socials">
            {SOCIALS.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </div>

        <HomeIndexList destinations={destinations} active={active} onActivate={setActive} />
      </div>
    </>
  )
}
