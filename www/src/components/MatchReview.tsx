"use client";

import { useEffect, useState } from 'react'
import BlankPlayerCard from '@/components/BlankPlayerCard'
import PlayerCardView from '@/components/PlayerCardView'
import type { PublicPlayerCard } from '@/server/backend'
import type { PitchPlayer } from '@/lib/teamMatch' 

/**
 * **경기 리뷰** — 경기가 끝난 뒤 함께 뛴 사람들을 평가하는 작은 판
 * (사용자 요청, 2026-09-17).
 *
 * 🔴 **별점도 자유 글도 아니다 — 고르는 것이다.** 계약이 그렇게 정했고
 * 이유까지 적어 두었다(3-9절): *「`review` 에 총점·별점이 없다. 고른 것이
 * `review_selection` 에 행으로 남는다 — 나쁜 평가 하나가 줄 수 있는 피해에
 * 상한을 두기 위해서다」*. 그래서 참조로 받은 ★5.0 + 글 모양과 다르다.
 *
 * 🔴 **강제가 아니다**(사용자 요청). 아무도 안 고르고 닫아도 된다.
 *
 * ⚠️ **아직 저장이 안 된다 — 지금은 흉내만 낸다**(사용자 판단: 「하드코딩으로만
 * 되게, 나중에 바꾸면 되니까」). 두 가지가 막고 있다:
 *
 *   1. **팀↔팀 경기의 참가자는 리뷰 참가자가 아니다** — 계약의
 *      `is_confirmed_participant` 가 `match_application`(용병이 경기에 지원
 *      → 양쪽 수락)만 본다. 팀↔팀 수락은 `match` 만 만들고 그 행을 안 만들어서
 *      `POST /matches/{id}/reviews` 가 **422 `NOT_A_PARTICIPANT`** 다.
 *   2. **평가 대상의 `user_id` 를 화면이 모른다** — 스쿼드 응답은 `nickname`·
 *      `card_public_slug` 만 준다. `reviewee_id` 에 넣을 값이 없다.
 *
 * 🔴 **둘 다 열리면 `submit()` 한 곳만 바꾸면 된다** — 고른 값은 이미 계약이
 * 받는 모양(`option_codes`)으로 들고 있다.
 */

/**
 * 고를 수 있는 항목 — 🔴 **서버 시드와 같은 값이다**(마이그레이션
 * `20260903_review_trust_tables.py` 의 `_REVIEW_OPTIONS`). 문구를 지어내지
 * 않으려고 그대로 옮겼다.
 *
 * ⚠️ **정본은 `GET /review-options` 다.** 그 경로가 화면에 붙으면 이 목록을
 * 걷는다 — 배열 **순서가 곧 노출 순서**이고(계약), 알파벳순으로 정렬하면
 * 「주의」가 맨 앞에 온다.
 */
const OPTIONS: { code: string; category: string; label: string }[] = [
  { category: "manner", code: "manner_time", label: "시간을 잘 지켰다" },
  { category: "manner", code: "manner_respect", label: "매너가 좋았다" },
  {
    category: "manner",
    code: "manner_communication",
    label: "소통이 원활했다",
  },
  {
    category: "skill",
    code: "skill_above_expected",
    label: "실력이 기대 이상이었다",
  },
  {
    category: "skill",
    code: "skill_position_fit",
    label: "포지션 소화가 좋았다",
  },
  { category: "skill", code: "skill_teamplay", label: "팀플레이가 좋았다" },
  { category: "repeat", code: "repeat_yes", label: "다시 함께 뛰고 싶다" },
  {
    category: "caution",
    code: "caution_position_mismatch",
    label: "포지션이 안 맞았다",
  },
  {
    category: "caution",
    code: "caution_would_not_repeat",
    label: "다시 함께 뛰고 싶지 않다",
  },
];

type Picked = Record<string, string[]>;

export default function MatchReview({
  us,
  them,
  onClose,
}: {
  us: { name: string; squad: PitchPlayer[] };
  them: { name: string; squad: PitchPlayer[] };
  /** 🔴 닫으면 **대기 화면까지 함께 닫힌다**(사용자 설계) — 부모가 그렇게 잇는다. */
  onClose: () => void;
}) {
  /** 사람마다 고른 항목들. 키는 `우리/상대 + 닉네임` 이다 — 이름이 겹칠 수 있다. */
  const [picked, setPicked] = useState<Picked>({});
  /** 열어 둔 사람 — 한 번에 하나만 편다(아홉 줄이 다 펼쳐지면 못 읽는다). */
  const [open, setOpen] = useState<string | null>(null);
  const [saved, setSaved] = useState(false)

  /**
   * 사람마다의 **진짜 카드** (사용자 요청, 2026-09-17: 「포지션 왼쪽에 각자
   * 카드 못 두나?」).
   *
   * 🔴 **판을 열 때 한 번만 읽는다.** 슬러그마다 한 번이고, 같은 슬러그는
   * 두 번 안 부른다 — 줄을 그릴 때마다 부르면 사람 수만큼 요청이 나간다.
   * ⚠️ 카드를 아직 안 만든 사람은 슬러그가 없다 — 그때는 이름 카드로 그린다.
   */
  const [cards, setCards] = useState<Record<string, PublicPlayerCard>>({});

  function toggle(key: string, code: string) {
    setPicked((cur) => {
      const now = cur[key] ?? [];
      return {
        ...cur,
        [key]: now.includes(code)
          ? now.filter((c) => c !== code)
          : [...now, code],
      };
    });
  }

  /**
   * 🔴 **지금은 저장을 흉내만 낸다**(위 머리말의 막힌 것 둘). 계약이 열리면
   * 여기서 사람마다 `POST /matches/{id}/reviews` 를 보내면 된다 — 보낼 값
   * (`option_codes`)은 이미 `picked` 가 들고 있다.
   */
  function submit() {
    setSaved(true);
  }

  const rows = [
    ...us.squad.map((p) => ({ side: "우리" as const, team: us.name, p })),
    ...them.squad.map((p) => ({ side: "상대" as const, team: them.name, p })),
  ];
  const total = Object.values(picked).reduce((n, v) => n + v.length, 0);

  return (
    /* 🔴 **화면 가운데에 띄운다**(사용자 요청). 오른쪽 아래 작은 판으로 뒀더니
       경기장 위에 얹혀 읽기 나빴다. 바깥을 눌러도 안 닫는다 — 고르던 것이
       실수 한 번에 날아가면 안 된다(「닫기」가 그 자리다). */
    <div className="ss-mr-scrim">
      <div
        className="ss-mr"
        role="dialog"
        aria-modal="true"
        aria-label="경기 리뷰"
      >
        <header className="ss-mr-head">
          <h2>경기 리뷰</h2>
          {/* 🔴 **강제가 아니라고 적는다**(사용자 요청) — 안 쓰고 닫아도 된다. */}
          <p className="ss-mr-note">
            함께 뛴 사람을 골라 남깁니다. 안 남기고 닫아도 됩니다.
          </p>
        </header>

        <div className="ss-mr-body">
          {(["우리", "상대"] as const).map((side) => (
            <section key={side} className="ss-mr-side">
              <h3 className="ss-mr-team">
                {side === "우리" ? us.name : them.name}
                <span className="ss-mr-side-tag">{side} 팀</span>
              </h3>

              {rows.filter((r) => r.side === side).length === 0 ? (
                <p className="ss-mr-note">판에 올린 사람이 없습니다</p>
              ) : (
                <ul className="ss-mr-list">
                  {rows
                    .filter((r) => r.side === side)
                    .map(({ p }) => {
                      const key = `${side}:${p.nickname}`;
                      const mine = picked[key] ?? [];
                      return (
                        <li key={key} className="ss-mr-row">
                          <button
                            type="button"
                            className="ss-mr-person"
                            aria-expanded={open === key}
                            onClick={() => setOpen(open === key ? null : key)}
                          >
                            {/* 🔴 **카드가 먼저다**(사용자 요청) — 누구인지는
                              이름보다 카드가 빨리 말한다. */}
                          {/* 🔴 **`ss-pcard-mini` 가 크기를 줄인다.** 그 클래스가 카드를
                              `transform: scale()` 로 접고 제 상자를 줄어든 크기로
                              들고 있다 — 안 붙이면 **원래 크기(380px) 카드가 그대로**
                              그려져 줄에 잘린다(2026-09-17에 그렇게 했다). */}
                          <span className="ss-pcard-mini ss-mr-card">
                            {p.cardSlug && cards[p.cardSlug] ? (
                              <PlayerCardView card={cards[p.cardSlug]} />
                            ) : (
                              <BlankPlayerCard>
                                <span className="ss-mr-card-name">{p.nickname}</span>
                              </BlankPlayerCard>
                            )}
                          </span>
                          <span className="ss-mr-pos">{p.pos}</span>
                            <span className="ss-mr-name">{p.nickname}</span>
                            {/* 고른 개수를 줄에 적는다 — 접어 둬도 뭘 남겼는지 보인다. */}
                            {mine.length > 0 && (
                              <span className="ss-mr-count">{mine.length}</span>
                            )}
                          </button>

                          {open === key && (
                            <ul className="ss-mr-opts">
                              {OPTIONS.map((o) => (
                                <li key={o.code}>
                                  <button
                                    type="button"
                                    className="ss-mr-opt"
                                    data-cat={o.category}
                                    data-on={
                                      mine.includes(o.code) ? "true" : undefined
                                    }
                                    aria-pressed={mine.includes(o.code)}
                                    onClick={() => toggle(key, o.code)}
                                  >
                                    {o.label}
                                  </button>
                                </li>
                              ))}
                            </ul>
                          )}
                        </li>
                      );
                    })}
                </ul>
              )}
            </section>
          ))}
        </div>

        <footer className="ss-mr-foot">
          {saved ? (
            <p className="ss-mr-saved" role="status">
              남겼습니다 — {total}개
            </p>
          ) : (
            <button
              type="button"
              className="ss-mr-save"
              disabled={total === 0}
              onClick={submit}
            >
              저장
            </button>
          )}
          <button type="button" className="ss-mr-close" onClick={onClose}>
            닫기
          </button>
        </footer>
      </div>
    </div>
  );
}
