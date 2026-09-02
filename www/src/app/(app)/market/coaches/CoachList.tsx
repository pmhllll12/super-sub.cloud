'use client'

import { useState } from 'react'
import { TransitionLink } from '@/lib/pageTransition'
import { FilterBar, SortSelect } from '../FilterBar'
import {
  LEVEL_LABEL,
  SPORT_LABEL,
  won,
  type Coach,
  type Level,
  type SportCode,
} from '@/lib/market'

/**
 * 코치 목록과 거름망.
 *
 * 🔴 종목 알약은 **영상 분석과 같은 모양**을 쓴다(`.ss-shot-sport`). 사용자가
 * 이미 한 번 배운 조작이라 여기서 새로 배울 것이 없어야 한다 — 같은 뜻의 것에
 * 다른 모양을 주지 않는다.
 *
 * 거름망을 클라이언트에 둔 이유: 지금은 mock 이라 목록이 몇 개뿐이고, 서버로
 * 다시 물으면 화면이 한 번 비었다 돌아온다. API 가 붙으면 이 컴포넌트가 쿼리
 * 파라미터를 바꾸는 쪽으로 옮겨 가면 된다.
 */
/**
 * 줄 세우는 법.
 *
 * 🔴 `recommended`(추천순)는 **목록에 손을 안 대는 것**이다. 지금은 데이터가
 * 들어 있는 차례가 곧 우리 차례라, 여기서 정렬을 하나 더 만들면 그 차례가
 * 무엇이었는지 알 수 없게 된다. 추천 알고리즘이 생기면 그때 이 자리가 그것을
 * 부르는 곳이 된다.
 */
const COACH_SORTS = [
  { value: 'recommended', label: '추천순' },
  { value: 'price-asc', label: '가격 낮은 순' },
  { value: 'price-desc', label: '가격 높은 순' },
  { value: 'reviews', label: '후기 많은 순' },
] as const
type CoachSort = (typeof COACH_SORTS)[number]['value']

/** 카드 겉껍데기 — `onPick` 이 있으면 버튼, 없으면 링크다. */
function CardShell({
  id,
  onPick,
  children,
}: {
  id: string
  onPick?: (id: string) => void
  children: React.ReactNode
}) {
  if (onPick) {
    return (
      <button type="button" className="ss-coach-card" onClick={() => onPick(id)}>
        {children}
      </button>
    )
  }
  return (
    <TransitionLink href={`/market/coaches/${id}`} className="ss-coach-card">
      {children}
    </TransitionLink>
  )
}

export default function CoachList({
  coaches,
  /**
   * 🔴 코치를 골랐을 때 **무엇을 할지는 밖이 정한다.**
   * 없으면 제 주소로 간다(목록 화면), 있으면 부르기만 한다 — 레슨 · 상점 입구의
   * 오른쪽 판은 화면을 갈지 않고 **그 판 안에서만** 상세로 바꾼다(사용자 요청).
   */
  onPick,
}: {
  coaches: Coach[]
  onPick?: (id: string) => void
}) {
  const [sport, setSport] = useState<SportCode | null>(null)
  const [level, setLevel] = useState<Level | null>(null)
  const [region, setRegion] = useState<string | null>(null)
  const [sort, setSort] = useState<CoachSort>('recommended')
  /**
   * 회당 가격의 **아래 · 위**. 🔴 손잡이가 아니라 **직접 적는다**(사용자 요청) —
   * "6만 5천에서 8만 사이"처럼 머리로 정한 폭을 손잡이로 맞추려면 눈금을 더듬어야
   * 한다. 빈 칸은 **끝이 없다**는 뜻이다(아래만 적으면 그 위로 전부).
   * 🔴 글자 그대로 들고 있는다(`number` 가 아니라 `string`). 지우는 도중의 빈
   * 칸을 `0` 으로 읽으면 다 지우자마자 아무도 안 남는다.
   */
  const [minPrice, setMinPrice] = useState('')
  const [maxPrice, setMaxPrice] = useState('')

  /**
   * 🔴 지역 후보는 **데이터에서 뽑는다.** 손으로 적어 두면 코치가 없는 지역이
   * 알약으로 남아, 골라도 늘 "조건에 맞는 코치가 없습니다"가 된다.
   */
  const regions = [...new Set(coaches.map((c) => c.region.split(' ')[0]))]

  const min = minPrice === '' ? null : Number(minPrice)
  const max = maxPrice === '' ? null : Number(maxPrice)
  const priced = min !== null || max !== null

  const filtered = Boolean(sport || level || region) || priced

  const shown = coaches
    .filter(
      (c) =>
        (!sport || c.sport === sport) &&
        (!level || c.levels.includes(level)) &&
        (!region || c.region.startsWith(region)) &&
        (min === null || c.pricePerSession >= min) &&
        (max === null || c.pricePerSession <= max),
    )
    // 🔴 `filter` 가 이미 새 배열을 준다 — 그래서 여기서 정렬해도 원래 목록을
    //    건드리지 않는다. props 로 받은 배열을 그 자리에서 뒤집으면 부모가 가진
    //    것까지 순서가 바뀐다.
    .sort((a, b) => {
      if (sort === 'price-asc') return a.pricePerSession - b.pricePerSession
      if (sort === 'price-desc') return b.pricePerSession - a.pricePerSession
      if (sort === 'reviews') return b.reviews.length - a.reviews.length
      return 0
    })

  /** 접힌 단추에 보이는 가격. 한쪽만 적었으면 그쪽만 말한다. */
  const priceLabel =
    min !== null && max !== null
      ? `${won(min)} ~ ${won(max)}`
      : min !== null
        ? `${won(min)} 이상`
        : max !== null
          ? `${won(max)} 이하`
          : null

  return (
    <>
      <FilterBar
        fields={[
          {
            key: 'sport',
            label: '종목',
            value: sport ? SPORT_LABEL[sport] : null,
            picked: sport,
            onPick: (v) => setSport(v as SportCode | null),
            options: (Object.keys(SPORT_LABEL) as SportCode[]).map((code) => ({
              value: code,
              label: SPORT_LABEL[code],
            })),
          },
          {
            key: 'level',
            label: '수준',
            value: level ? LEVEL_LABEL[level] : null,
            picked: level,
            onPick: (v) => setLevel(v as Level | null),
            options: (Object.keys(LEVEL_LABEL) as Level[]).map((code) => ({
              value: code,
              label: LEVEL_LABEL[code],
            })),
          },
          {
            key: 'region',
            label: '지역',
            value: region,
            picked: region,
            onPick: setRegion,
            options: regions.map((r) => ({ value: r, label: r })),
          },
          {
            key: 'price',
            label: '가격',
            value: priceLabel,
            // 🔴 여기만 고르는 것이 아니라 **적는** 자리다. 두 칸 사이의 `~` 가
            //    "이 사이"라는 뜻을 나른다 — 글로 설명하지 않아도 읽힌다.
            custom: (
              <div className="ss-pricerange">
                <label>
                  <span className="sr-only">회당 최저 가격</span>
                  <input
                    type="number"
                    inputMode="numeric"
                    min={0}
                    step={1000}
                    placeholder="최저"
                    value={minPrice}
                    onChange={(e) => setMinPrice(e.target.value)}
                  />
                </label>
                <b aria-hidden="true">~</b>
                <label>
                  <span className="sr-only">회당 최고 가격</span>
                  <input
                    type="number"
                    inputMode="numeric"
                    min={0}
                    step={1000}
                    placeholder="최고"
                    value={maxPrice}
                    onChange={(e) => setMaxPrice(e.target.value)}
                  />
                </label>
                <span className="ss-pricerange-unit">원 / 회</span>
              </div>
            ),
          },
        ]}
        end={
          <>
            {/* 🔴 **거른 결과를 숫자로.** 접힌 단추만 있으면 방금 고른 것이
                목록을 좁혔는지가 목록을 세어 봐야 안다. */}
            <span className="ss-filterbar-count">
              코치 <b>{shown.length}</b>
              {filtered ? <em> / {coaches.length}</em> : null}
            </span>
            <SortSelect value={sort} options={[...COACH_SORTS]} onChange={setSort} />
          </>
        }
      />

      {shown.length === 0 ? (
        <p className="ss-market-empty">조건에 맞는 코치가 아직 없습니다.</p>
      ) : (
        <ul className="ss-coach-list">
          {shown.map((c) => (
            <li
              key={c.id}
              // 🔴 **가져다 대면 돈다**(사용자 요청). 누르는 것은 코치를 고르는
              //    일이고, 훑어보는 동안 장면이 도는 것은 고르기 전의 일이라
              //    둘을 갈라 둔다.
              // 🔴 과녁을 카드가 아니라 **줄(li)** 로 잡는다 — 카드 안의 영상
              //    위로 마우스가 넘어갈 때 카드에서 나갔다 들어온 것으로 잡히면
              //    재생이 한 번 끊긴다.
              // 🔴 `play()` 는 약속(Promise)을 돌려주고 **거절될 수 있다**
              //    (아직 못 읽었거나, 바로 떠났거나). 안 받으면 콘솔에 잡히지
              //    않은 오류가 쌓인다.
              onMouseEnter={(e) => {
                e.currentTarget.querySelector('video')?.play().catch(() => {})
              }}
              onMouseLeave={(e) => {
                const v = e.currentTarget.querySelector('video')
                if (!v) return
                v.pause()
                // 처음으로 되돌린다 — 다음에 가져다 댔을 때 늘 같은 자리에서
                // 시작해야 "이 코치의 대표 장면"으로 읽힌다.
                v.currentTime = 0
              }}
            >
              {/* 누르면 하는 일만 다르고 안은 같다 — 두 벌로 두면 한쪽만 늙는다. */}
              <CardShell
                id={c.id}
                onPick={onPick}
              >
                <span className="ss-coach-card-text">
                <span className="ss-coach-card-head">
                  <b>{c.name}</b>
                  <span>
                    {SPORT_LABEL[c.sport]} · {c.region}
                  </span>
                </span>

                <span className="ss-coach-card-tagline">{c.tagline}</span>

                {/* 🔴 간판. 다른 곳은 코치가 자기 실력을 자기소개로 쓰지만
                    우리는 **같은 잣대로 잰 것**을 보여준다. 수치는 안 그린다
                    (부록 D.5) — 받은 호칭뿐이다. */}
                <span className="ss-coach-card-analysis">
                  <em>우리 분석을 받은 코치</em>
                  <span className="ss-coach-titles">
                    {c.titles.map((t) => (
                      <b key={t}>{t}</b>
                    ))}
                  </span>
                </span>

                <span className="ss-coach-card-foot">
                  회당 {won(c.pricePerSession)}
                  <i>후기 {c.reviews.length}</i>
                </span>
                </span>

                {/* 🔴 카드 오른쪽은 **그 코치의 대표 장면**이다(사용자 요청).
                    말로 하는 자기소개 대신 우리가 분석한 장면을 보여 주는 것이
                    이 화면의 주장이라, 목록에서부터 그것이 보이는 편이 맞다.

                    소리 없이 · 되풀이 · **가져다 대면** 시작한다(줄의 손잡이가
                    켠다). 🔴 `muted` 없이는 브라우저가 재생을 막는다.
                    `playsInline` 이 없으면 iOS 가 전체 화면으로 띄운다.
                    ⚠️ 아직 `clipUrl` 이 있는 코치가 없다 — 저장소에 영상 파일이
                    없어서다(`lib/market.ts` 주석). 그때는 멈춘 그림만 보인다. */}
                <span className="ss-coach-card-clip" aria-hidden="true">
                  <video
                    // 🔴 주소 뒤의 `#t=0.1` 은 "0.1초 자리를 보여 달라"는 뜻이다.
                    //    이게 없으면 브라우저가 `preload="metadata"` 만 보고 **그림은
                    //    안 그려서**, 멈춰 있는 동안 뒤의 `poster`(배경 사진)가 그대로
                    //    남는다 — 카드마다 배경 사진이 나오던 까닭이다(사용자 지적).
                    //    0 이 아니라 0.1 인 것은 맨 첫 칸이 검은 영상이 흔해서다.
                    src={c.report.clipUrl ? `${c.report.clipUrl}#t=0.1` : undefined}
                    // 🔴 대신 그림은 **클립이 없을 때만** 깐다. 클립이 있는데도 깔면
                    //    영상이 준비되기 전까지 엉뚱한 사진이 그 자리를 차지한다.
                    poster={c.report.clipPoster ?? (c.report.clipUrl ? undefined : '/market_figure.jpg')}
                    muted
                    loop
                    playsInline
                    preload="metadata"
                  />
                </span>
              </CardShell>
            </li>
          ))}
        </ul>
      )}
    </>
  )
}
