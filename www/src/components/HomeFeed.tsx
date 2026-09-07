'use client'

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { feedWith } from '@/lib/feed'
import { listPublished, type PublishedClip } from '@/lib/published'

/**
 * 홈을 내리면 나오는 **영상 모음** — 필름 한 줄이 화면 가운데를 지나간다.
 *
 * 참고한 짜임(사용자 제시, Filmnotec): 뒤에 크게 깔린 유령 글자, 가운데를
 * 지나가는 필름, 그 위에 얹힌 제목, 아래에 좌우 화살표.
 *
 * 🔴 여기는 **가볍게 훑는 자리**다(사용자 요청). 그래서
 *   · 소리 없이 저절로 돈다 — 누를 것이 하나 줄어든다
 *   · 지금 것만 튼다. 옆의 것은 다음 · 이전이 무엇인지 알려 주는 **미리보기**라
 *     멈춰 둔다(셋을 다 틀면 데이터도 배터리도 세 배로 쓴다)
 *   · 수치도 판정도 안 적는다. 누가 · 언제 · 무엇을 본 장면인지가 전부다
 *
 * 🔴 **뜬 상태에서만 산다.** 홈이 아직 위에 있을 때는 이 판이 화면 밖에 있으므로
 * 영상을 틀지 않는다 — 안 보이는 영상을 트는 것은 데이터만 쓰는 일이다.
 */
export default function HomeFeed({ active, by }: { active: boolean; by: string }) {
  const [i, setI] = useState(0)
  /** 좋아요를 누른 영상. ⚠️ 이 화면 안에서만 산다(계약에 좋아요가 없다). */
  const [liked, setLiked] = useState<string[]>([])
  /**
   * 오른쪽 목록이 펼쳐져 있는가(사용자 요청).
   *
   * 🔴 펼치면 보던 영상은 **왼쪽으로 비켜설 뿐 화면 밖으로 안 나간다** — 목록을
   * 훑는 동안에도 지금 보던 것이 계속 보여야 "잠깐 옆을 본다"가 된다.
   */
  const [side, setSide] = useState<'none' | 'list' | 'comments'>('none')
  /** 오른쪽에 무언가 나와 있는가 — 영상이 비켜서는지를 이 값으로 정한다. */
  const library = side !== 'none'
  /**
   * 나오는 판이 **얼마나 기다렸다** 나올지(ms).
   *
   * 🔴 자리가 비어야 나온다: 가로 영상이면 영상이 먼저 비켜서고, 이미 다른 판이
   * 나와 있었으면 그것이 먼저 오른쪽으로 나간 뒤다(사용자 요청).
   */
  const [enterDelay, setEnterDelay] = useState(0)
  /**
   * 화면에서 쓴 댓글. ⚠️ **아무 데도 안 보낸다**(계약 5장에 댓글이 없다) —
   * 좋아요와 같은 규칙으로 이 화면 안에서만 붙고 새로고침하면 사라진다.
   */
  const [wrote, setWrote] = useState<Record<string, string[]>>({})
  const [draft, setDraft] = useState('')
  /**
   * 목록이 열렸을 때 영상이 **왼쪽으로 비켜서는 양**(px).
   *
   * 🔴 **크기는 그대로 두고 자리만** 옮긴다(사용자 요청). 그리고 **필요한 만큼만**
   * 옮긴다 — 세로 영상은 애초에 목록에 안 닿으므로 **한 픽셀도 안 움직인다**
   * (사용자 지적). 그래서 CSS 로는 못 하고 여기서 잰다: 지금 칸의 오른쪽 끝이
   * 목록의 왼쪽을 얼마나 넘는지가 곧 옮길 양이고, 왼쪽 끝이 판을 벗어나지 않는
   * 만큼까지만 옮긴다(화면 밖으로 안 나간다).
   */
  const [shift, setShift] = useState(0)
  /**
   * 목록이 서는 자리(px, 판 왼쪽에서).
   *
   * 🔴 **늘 화면 오른쪽 끝**이다(사용자 요청) — 가로든 세로든 같은 자리에 박아
   * 둔다. 목록 폭이 `clamp` 라 창마다 달라서 CSS 로는 못 잡고 여기서 잰다.
   *
   * ⚠️ 한때 **지금 영상의 오른쪽 끝 바로 옆**에 붙였다(세로 영상일 때 목록이 저
   * 혼자 멀찍이 떨어져 보인다는 이유였다). 되돌렸다 — 영상마다 목록이 다른 자리에
   * 서니 넘길 때마다 목록이 좌우로 움직여, 고정된 차림표로 안 읽혔다.
   */
  const [listX, setListX] = useState(0)
  /**
   * 댓글창이 서는 자리(px).
   *
   * 🔴 **목록과 따로 둔다.** 둘이 한 변수를 같이 보면, 판을 바꿀 때 그 값이
   * 바뀌면서 **나가는 중인 판까지 옆으로 툭 뛴다** — 번갈아 누를 때 버벅이는
   * 것처럼 보였던 원인이다(사용자 지적). 폭이 다르니 서는 자리도 다르다.
   */
  const [commentsX, setCommentsX] = useState(0)
  /**
   * 목록의 **세로 가운데**(px). 🔴 가운데 줄이 영상의 세로 한가운데에 오게
   * 맞춘다(사용자 요청) — 영상마다 키가 달라 CSS 로는 못 잡는다.
   */
  const [listY, setListY] = useState(0)
  const box = useRef<HTMLDivElement>(null)

  /** 앞뒤로 **끝없이** 돈다 — 마지막에서 오른쪽으로 가면 처음으로. */
  /**
   * 내가 공개로 돌린 클립.
   *
   * 🔴 그릴 때 저장소를 읽지 않는다 — 서버에는 그 값이 없어서 서버가 그린 첫
   * 화면과 브라우저가 그린 것이 갈리면 하이드레이션이 깨진다. 붙은 뒤에 읽는다.
   *
   * ⚠️ 아직 **내 것만** 붙는다. 남의 공개 영상은 계약에 목록도 재생 주소도
   * 없어서(미결) 못 가져온다.
   */
  const [published, setPublished] = useState<PublishedClip[]>([])
  // eslint-disable-next-line react-hooks/set-state-in-effect -- 저장소는 서버에 없다. 붙은 뒤에 읽어야 하이드레이션이 안 깨진다.
  useEffect(() => setPublished(listPublished()), [])
  const clips = feedWith(published, by)

  const go = (step: number) => setI((prev) => (prev + step + clips.length) % clips.length)

  /**
   * 🔴 좌우 화살표는 이 판이 떠 있을 때만 듣는다. 위아래는 홈이 쓰므로
   * (`HomeStage` 의 굴림 신호) 여기서 건드리지 않는다.
   */
  useEffect(() => {
    if (!active) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') go(1)
      else if (e.key === 'ArrowLeft') go(-1)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [active])

  /**
   * 자리를 재서 상태 셋(비켜설 양 · 목록의 가로 · 세로)을 갱신한다.
   *
   * 🔴 **여는 손짓에서도 이걸 먼저 부른다.** effect 에만 두면 목록이 열린 뒤에야
   * 값이 들어와서, 그 사이 한 프레임이 옛 값으로 그려진다 — 특히 "영상이 먼저
   * 비켜서고 목록이 나온다"의 기다리는 시간(`--ss-feed-list-delay`)이 0 인 채로
   * 전환이 시작돼 둘이 같이 움직였다(실측으로 확인했다).
   */
  const measure = useCallback((which: 'list' | 'comments') => {
    const stage = box.current?.querySelector('.ss-feed-stage')
    const frame = box.current?.querySelector('.ss-feed-frame[data-here="true"]')
    // 🔴 **나올 판을 잰다.** 댓글창이 목록보다 넓어서, 늘 목록을 재면 가로 영상이
    //    덜 비켜서고 댓글창이 영상 위로 파고든다.
    const 목록 = box.current?.querySelector('.ss-feed-list')
    const 댓글 = box.current?.querySelector('.ss-feed-comments')
    const list = which === 'comments' ? 댓글 : 목록
    if (!stage || !frame || !list || !목록 || !댓글) return 0

    const s = stage.getBoundingClientRect()
    const 목록폭 = list.getBoundingClientRect().width
    /**
     * 🔴 **안 옮겼을 때의 자리**로 센다. 지금 자리(옮긴 뒤)로 재면 그 값이 다시
     * 옮길 양에 더해져, 열 때마다 영상이 조금씩 더 왼쪽으로 간다(실제로 그랬다).
     * 칸은 판 한가운데에 있으므로 가운데와 폭만 알면 양 끝이 나온다.
     */
    const w = frame.getBoundingClientRect().width
    const 가운데 = s.left + s.width / 2
    const 오른끝 = 가운데 + w / 2

    const 사이 = 24
    const 가장자리 = 16
    // 목록이 화면 안에 들어오려면 영상이 이만큼 비켜야 한다.
    const 필요 = 오른끝 + 사이 + 목록폭 - (window.innerWidth - 가장자리)
    // 다만 영상의 왼쪽 끝이 판을 벗어나면 안 된다 — 그만큼까지만 옮긴다.
    const 여유 = 가운데 - w / 2 - s.left
    const 옮김 = Math.max(0, Math.min(필요, 여유))

    setShift(옮김)
    // 🔴 두 판 모두 **늘 화면 오른쪽 끝**이다 — 영상 폭을 따라다니지 않는다.
    //    위 `필요` 도 판이 여기 있다고 보고 비켜설 양을 계산한다(둘이 같은 자리를
    //    봐야 세로 영상에서 0 이 나온다).
    // 🔴 **둘 다 지금 정한다.** 나오는 쪽만 정하면 나가는 쪽이 옛 자리에 남거나,
    //    한 변수를 같이 쓰면 나가는 판이 옆으로 툭 뛴다.
    setListX(window.innerWidth - 가장자리 - 목록.getBoundingClientRect().width)
    setCommentsX(window.innerWidth - 가장자리 - 댓글.getBoundingClientRect().width)

    // 세로는 **영상의 한가운데**에 맞춘다. 목록이 제 키의 절반만큼 위로 올라가
    // 있으므로(CSS 의 translateY(-50%)) 여기서는 가운데 좌표만 주면 된다.
    const 판 = box.current?.getBoundingClientRect()
    if (판) setListY(s.top + s.height / 2 - 판.top)

    // 굴릴 것이 있을 때만 위아래를 흐린다 — 짧은 목록까지 흐리면 멀쩡한 줄이
    // 반쯤 지워진다.
    const ul = list.querySelector('ul')
    if (ul) ul.dataset.scroll = ul.scrollHeight > ul.clientHeight ? 'true' : 'false'
    return 옮김
  }, [])

  /**
   * 오른쪽 판을 연다 — 같은 것을 다시 누르면 닫힌다.
   *
   * 🔴 **재는 것이 먼저다**(위 `measure` 주석). 그리고 기다리는 시간을 여기서
   * 정한다: 이미 다른 판이 나와 있었으면 그것이 오른쪽으로 나갈 시간까지,
   * 아니면 영상이 비켜설 시간만, 비켜설 것이 없으면 0.
   */
  const openSide = (next: 'list' | 'comments') => {
    if (side === next) {
      setEnterDelay(0)
      setSide('none')
      return
    }
    const moved = measure(next) ?? 0
    setEnterDelay(side !== 'none' ? 460 : moved > 0 ? 360 : 0)
    setSide(next)
  }

  /* eslint-disable react-hooks/set-state-in-effect */
  useLayoutEffect(() => {
    if (side === 'none') {
      setShift(0)
      return
    }
    measure(side)
  }, [side, i, active, measure])
  /* eslint-enable react-hooks/set-state-in-effect */

  /**
   * 🔴 **가운데 것만 튼다**(사용자 요청).
   *
   * `src` 를 지우는 것만으로는 안 멈춘다 — 영상 요소는 주소를 떼어도 이미 읽어
   * 둔 것을 계속 튼다(그래서 넘긴 뒤에도 옆으로 밀려난 영상이 계속 돌았다).
   * **직접 세우고 처음으로 되감아야** 한다.
   *
   * 🔴 여기서 한꺼번에 다루는 이유: 어느 칸이 가운데인지는 이 컴포넌트만 안다.
   * 칸마다 제 상태를 보고 판단하게 하면 넘어가는 한 프레임 동안 둘이 같이 돈다.
   */
  useEffect(() => {
    // 🔴 **줄 안의 영상만** 센다. 목록 판의 미리보기도 `<video>` 라, 그냥 다
    //    긁으면 순번이 밀려 엉뚱한 것이 재생된다.
    const vids = box.current?.querySelectorAll<HTMLVideoElement>('.ss-feed-strip video') ?? []
    vids.forEach((v, n) => {
      if (n === i && active) {
        // 약속이 거절될 수 있다(아직 못 읽었거나 바로 넘겼거나) — 받아 둔다.
        v.play().catch(() => {})
        return
      }
      v.pause()
      // 다음에 가운데로 올 때 늘 같은 자리에서 시작하게.
      if (v.currentTime > 0.1) v.currentTime = 0.1
    })
  }, [i, active])

  return (
    <div className="ss-feed" ref={box} data-active={active} data-library={library}>
      <div
        className="ss-feed-stage"
        style={{ '--ss-feed-shift': `${Math.round(shift)}px` } as React.CSSProperties}
      >
        <ul className="ss-feed-strip">
          {clips.map((c, n) => {
            /**
             * 🔴 칸들은 **다 같은 자리에 겹쳐** 있고 지금 것만 보인다(사용자 요청).
             * 옆으로 늘어놓았더니 넘길 때 다른 영상이 화면을 가로질러 지나갔다 —
             * 겹쳐 두면 지금 것과 다음 것이 제자리에서 서로 녹기만 한다.
             */
            const here = n === i
            return (
              <li
                key={c.id}
                className="ss-feed-frame"
                data-here={here}
                // 🔴 비율을 칸에 그대로 넘긴다 — 칸이 영상 모양을 따라가야
                //    자르지 않고도 꽉 찬다(세로 영상은 세로 칸이 된다).
                style={{ '--ss-feed-ar': c.aspect } as React.CSSProperties}
                aria-hidden={!here}
              >
                {/* 🔴 `#t=0.1` 은 "0.1초 자리를 보여 달라"는 뜻이다 — 이게 없으면
                    멈춰 있는 옆 칸이 **까맣게** 남는다(브라우저가 정보만 읽고
                    그림은 안 그린다). 0 이 아닌 것은 첫 칸이 검은 영상이 흔해서. */}
                <video
                  src={`${c.src}#t=0.1`}
                  muted
                  loop
                  playsInline
                  preload="metadata"
                />
                {/* 🔴 영상 **위에는 아무 글자도 얹지 않는다**(사용자 요청). 제목도
                    이름도 아래 알약에 있다 — 영상에 글을 얹으면 그건 우리가 넣은
                    자막이 되고, 올린 사람이 직접 편집해 넣은 글자와 구분이 안 된다.
                    화면에 보이는 글자는 **올린 사람이 넣은 것뿐**이어야 한다. */}
              </li>
            )
          })}
        </ul>
      </div>

      {/* 아래 줄 — 가운데는 넘기는 길, 양옆은 알약 두 개.
          🔴 **가운데는 늘 화면 한가운데**여야 한다(사용자 요청). 그래서 세 칸
          격자(`1fr auto 1fr`)를 쓴다 — 양옆 칸이 **같은 몫**을 가지므로 알약의
          길이가 달라도 가운데가 안 밀린다. */}
      <div className="ss-feed-bar">
        {/* 왼쪽 알약 — 지금 보는 영상이 누구의 무엇인지. */}
        <p className="ss-feed-pill ss-feed-who">
          <b>{clips[i].by}</b>
          {/* 가르는 선. 낭독기는 이걸 읽을 필요가 없다 — 이름과 제목은 이미
              따로 읽힌다. */}
          <i aria-hidden="true">|</i>
          <span>{clips[i].title}</span>
        </p>

        {/* 🔴 넘기는 길은 **이 단추 둘뿐**이다(사용자 요청). 손짓(가로 굴림)으로도
            넘기게 해 봤다가 걷어냈다 — 브라우저의 뒤로/앞으로 손짓과 같은 몸짓이라
            서로 뺏고, 한 번 쓸었는데 두 칸 넘어가는 일이 잦았다.
            가운데 말은 **무엇을 하면 되는지**다 — 몇 번째인지 세는 자리가 아니다. */}
        <div className="ss-feed-acts">
          <button type="button" onClick={() => go(-1)} aria-label="이전 영상">
            <span className="material-symbols-outlined" aria-hidden="true">
              chevron_backward
            </span>
          </button>
          <span className="ss-feed-count">다음 영상</span>
          <button type="button" onClick={() => go(1)} aria-label="다음 영상">
            <span className="material-symbols-outlined" aria-hidden="true">
              chevron_forward
            </span>
          </button>
        </div>

        {/* 오른쪽 알약 — 영상에 대고 하는 것들.
            ⚠️ **아직 아무 데도 안 보낸다.** 계약에 좋아요 · 댓글 · 공유가 없다
            (5장). 좋아요만 **이 화면 안에서** 켜지고 꺼진다 — 눌러도 아무 표시가
            없으면 고장으로 읽히기 때문이다. 새로고침하면 사라진다. */}
        <div className="ss-feed-pill ss-feed-react">
          <button
            type="button"
            aria-pressed={liked.includes(clips[i].id)}
            aria-label="좋아요"
            onClick={() =>
              setLiked((prev) =>
                prev.includes(clips[i].id)
                  ? prev.filter((x) => x !== clips[i].id)
                  : [...prev, clips[i].id],
              )
            }
          >
            {/* 아이콘은 `mood_heart`(사용자 지정) — 엄지보다 "좋았다"는 마음이
                더 곧게 읽힌다. */}
            <span className="material-symbols-outlined" aria-hidden="true">
              mood_heart
            </span>
          </button>
          {/* 🔴 누르면 오른쪽에 **댓글창**이 나온다(사용자 요청). 목록과 **같은
              자리**를 쓰므로 둘이 같이 떠 있지 않는다 — 목록이 나와 있었으면
              그것이 먼저 오른쪽으로 나간다(`openSide`). */}
          <button
            type="button"
            aria-pressed={side === 'comments'}
            aria-label="댓글"
            onClick={() => openSide('comments')}
          >
            <span className="material-symbols-outlined" aria-hidden="true">
              comment
            </span>
          </button>
          <button type="button" aria-label="공유">
            <span className="material-symbols-outlined" aria-hidden="true">
              share
            </span>
          </button>
          {/* 🔴 맨 오른쪽 — **다음 영상들을 미리 보는 목록**(사용자 요청). 여는
              것과 닫는 것이 한 자리라 다시 누르면 접힌다. */}
          <button
            type="button"
            aria-pressed={side === 'list'}
            aria-label="영상 목록"
            onClick={() => openSide('list')}
          >
            <span className="material-symbols-outlined" aria-hidden="true">
              video_library
            </span>
          </button>
        </div>
      </div>

      {/* 오른쪽 목록. 🔴 **흐름 밖**이다 — 흐름에 두면 열 때마다 영상 칸이 좁아졌다
          넓어져 화면이 출렁인다. 영상이 비켜서는 것은 아래 CSS 가 따로 맡는다. */}
      {/* 🔴 **판이 아니다**(사용자 요청) — 테두리도 바탕도 없이 영상 상자와 이름 ·
          제목만 떠 있다. 목록처럼 보이게 만드는 것은 줄 간격뿐이다. */}
      <aside
        className="ss-feed-list"
        data-open={side === 'list'}
        aria-hidden={side !== 'list'}
        style={
          {
            '--ss-feed-list-x': `${Math.round(listX)}px`,
            '--ss-feed-list-y': `${Math.round(listY)}px`,
            /* 🔴 **영상이 비켜선 다음에** 목록이 나온다(사용자 요청) — 같이
               시작하면 가로 영상에서 목록이 영상 위로 겹쳐 들어온다.
               🔴 비켜설 것이 없으면(세로 영상) **기다리지 않는다.** 아무 일도
               안 일어나는 동안 목록만 늦게 나오면 굼떠 보인다. */
            '--ss-feed-list-delay': `${enterDelay}ms`,
          } as React.CSSProperties
        }
      >
        <ul>
          {clips.map((c, n) => (
            <li key={c.id}>
              <button
                type="button"
                data-here={n === i}
                onClick={() => setI(n)}
                // 지금 보는 것은 눌러도 갈 데가 없다.
                disabled={n === i}
              >
                {/* 미리보기는 **멈춘 한 장**이다. 목록에서까지 다 틀면 데이터가
                    몇 배로 든다 — `#t=0.1` 이 그 한 장을 그리게 한다. */}
                <video src={`${c.src}#t=0.1`} muted playsInline preload="metadata" />
                <span>
                  <b>{c.title}</b>
                  <em>{c.by}</em>
                </span>
              </button>
            </li>
          ))}
        </ul>
      </aside>

      {/* 🔴 **댓글창**(사용자 요청). 목록과 **같은 자리 · 같은 짜임**이다 — 판도
          테두리도 없이 글만 떠 있고, 나오고 들어가는 것도 같은 방식이다.
          둘이 같은 자리를 쓰므로 한 번에 하나만 떠 있다(`side`).

          ⚠️ **아무 데도 안 보낸다** — 계약(5장)에 댓글이 없다. 쓴 것은 이 화면
          안에서만 붙고 새로고침하면 사라진다(좋아요와 같은 규칙). */}
      <aside
        className="ss-feed-comments"
        data-open={side === 'comments'}
        aria-hidden={side !== 'comments'}
        aria-label="댓글"
        style={
          {
            '--ss-feed-list-x': `${Math.round(commentsX)}px`,
            '--ss-feed-list-y': `${Math.round(listY)}px`,
            '--ss-feed-list-delay': `${enterDelay}ms`,
          } as React.CSSProperties
        }
      >
        <p className="ss-feed-comments-head">
          댓글 <b>{clips[i].comments.length + (wrote[clips[i].id]?.length ?? 0)}</b>
        </p>
        <ul>
          {clips[i].comments.map((c, n) => (
            <li key={`${c.by}-${n}`}>
              <b>{c.by}</b>
              <span>{c.text}</span>
            </li>
          ))}
          {/* 이 화면에서 쓴 것은 아래에 붙는다 — 방금 쓴 것이 눈에 보여야 한다. */}
          {(wrote[clips[i].id] ?? []).map((text, n) => (
            <li key={`mine-${n}`} data-mine="true">
              <b>나</b>
              <span>{text}</span>
            </li>
          ))}
        </ul>
        <form
          className="ss-feed-comments-write"
          onSubmit={(e) => {
            e.preventDefault()
            const text = draft.trim()
            if (!text) return
            setWrote((prev) => ({
              ...prev,
              [clips[i].id]: [...(prev[clips[i].id] ?? []), text],
            }))
            setDraft('')
          }}
        >
          <label>
            <span className="sr-only">댓글 쓰기</span>
            <input
              type="text"
              value={draft}
              placeholder="댓글 쓰기"
              onChange={(e) => setDraft(e.target.value)}
            />
          </label>
          {/* 빈 칸으로는 못 보낸다 — 눌러도 아무 일이 없으면 고장으로 읽힌다. */}
          <button type="submit" disabled={!draft.trim()}>
            <span className="material-symbols-outlined" aria-hidden="true">
              send
            </span>
            <span className="sr-only">보내기</span>
          </button>
        </form>
      </aside>
    </div>
  )
}
