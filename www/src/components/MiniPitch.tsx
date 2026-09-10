import BlankPlayerCard from '@/components/BlankPlayerCard'
import PlayerCardView from '@/components/PlayerCardView'
import type { PublicPlayerCard } from '@/server/backend'
import { COLS, ROWS, cellExists } from '@/lib/pitchGrid'
import type { PitchPlayer } from '@/lib/teamMatch'

/**
 * **읽기 전용 스쿼드 판** — 대기 팝업의 양옆에 서는 판.
 *
 * 🔴 **홈의 판과 같은 모양이어야 한다**(사용자 지적, 2026-09-10). 처음에는
 * 네모 칸에 이름만 찍었는데, 그건 스쿼드 판이 아니라 표였다. 그래서
 * **`SquadPanel` 이 쓰는 클래스를 그대로 쓴다** — 경기장 선(`ss-squad-pitch`),
 * 격자(`ss-squad-board`), 자리(`ss-squad-seat`), 카드(`ss-pcard-mini`),
 * 자리 이름표(`ss-squad-pos`). 새 모양을 만들면 두 판이 갈린다.
 *
 * 🔴 **`SquadPanel` 자체는 재사용하지 않는다.** 그쪽은 끌어 옮기기 · 추천 판 ·
 * 등재 · 서버 저장까지 든 900줄짜리라 여기 쓰려면 그 전부를 꺼야 한다 —
 * 끌 것이 많다는 것 자체가 재사용하면 안 된다는 뜻이다. 나눠 쓰는 것은
 * **모양(CSS)과 격자 규칙(`lib/pitchGrid.ts`)** 이고, 동작은 안 가져온다.
 *
 * 이 조각은 **상태가 없다.** 받은 것을 그대로 그린다.
 */
export default function MiniPitch({
  team,
  players,
  side,
  myCard = null,
}: {
  /** 판 위에 적을 팀 이름. */
  team: string
  players: PitchPlayer[]
  /** 어느 쪽에 서는가 — 우리는 왼쪽, 상대는 오른쪽. */
  side: 'us' | 'them'
  /**
   * 내 선수 카드 — **우리 판에서 내 자리에만** 진짜 카드를 그린다.
   * 없으면(카드를 아직 안 만든 사람) 다른 자리처럼 이름 카드로 그린다.
   */
  myCard?: PublicPlayerCard | null
}) {
  const at = (col: number, row: number) => players.find((p) => p.col === col && p.row === row)

  return (
    <section className="ss-mini" data-side={side} aria-label={`${team} 스쿼드`}>
      <h3 className="ss-mini-team">{team}</h3>

      {/* 🔴 홈의 판과 **같은 클래스**다 — 모양을 베끼지 않고 나눠 쓴다. */}
      <div className="ss-squad">
        {/* 경기장 선 — 장식이라 낭독기에서 숨긴다. 좌표는 홈의 판과 같아야
            선이 같은 자리에 그어진다(다르면 두 판이 다른 경기장이 된다). */}
        <svg
          className="ss-squad-pitch"
          viewBox="0 0 100 140"
          preserveAspectRatio="none"
          aria-hidden="true"
          focusable="false"
        >
          <rect className="ss-squad-pitch-edge" x="1" y="1" width="98" height="138" />
          <line x1="1" y1="70" x2="99" y2="70" />
          <circle cx="50" cy="70" r="14" />
          <circle className="ss-squad-pitch-dot" cx="50" cy="70" r="1.2" />
          <rect x="27" y="1" width="46" height="20" />
          <rect x="38" y="1" width="24" height="9" />
          <rect x="27" y="119" width="46" height="20" />
          <rect x="38" y="130" width="24" height="9" />
        </svg>

        <div className="ss-squad-board">
          {Array.from({ length: COLS * ROWS }, (_, i) => {
            const col = i % COLS
            const row = Math.floor(i / COLS)
            /* 🔴 **없는 칸은 아예 안 그린다** — 골키퍼 줄의 양옆이 그것이다.
               홈의 판이 같은 규칙을 쓴다(`lib/pitchGrid.ts`). */
            if (!cellExists(col, row)) return null
            const p = at(col, row)
            // 사람이 없는 칸은 자리도 안 그린다 — 여기는 짜는 자리가 아니다.
            if (!p) return null
            return (
              <div
                key={i}
                className="ss-squad-seat"
                style={{ gridColumn: col + 1, gridRow: row + 1 }}
              >
                <div className="ss-pcard-mini">
                  {/* 내 카드만 진짜 카드다 — 나머지는 이름을 얹은 빈 카드다. */}
                  {p.mine && myCard ? (
                    <PlayerCardView card={myCard} />
                  ) : (
                    <BlankPlayerCard>
                      <span className="ss-squad-name">{p.nickname}</span>
                    </BlankPlayerCard>
                  )}
                </div>
                {/* 🔴 자리 이름표는 카드 **아래**다 — 홈의 판과 같다. */}
                <span className="ss-squad-pos">{p.pos}</span>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
