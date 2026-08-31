'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import AnalysisChat from '@/components/analysis/AnalysisChat'
import FigureBackground from '@/components/FigureBackground'
import { useHideChrome, useLeaving } from '@/lib/pageTransition'

/**
 * 영상 분석 화면 — **화면 한 장을 통째로 쓴다.**
 *
 * 연출 순서(사용자가 고른 흐름):
 *
 * ```
 *  들어오면       왼쪽에서 검은 판이 밀려 들어온다(헤더의 카드와 같이).
 *                 배경 사진은 **그만큼 오른쪽으로** 비켜 준다(레퍼런스: Grenada).
 *  영상을 놓으면   **그 판 안에서 먼저 재생된다.** 아래에 '분석 시작하기'.
 *  시작을 누르면   **먼저 나갈 것들이 나간다.** 제목 · 설명은 왼쪽으로, 시작
 *                 버튼은 아래로, 헤더는 들어온 방향 그대로, 배경 사진 · 큰
 *                 글자는 오른쪽으로.
 *  그 다음         **판이 화면 폭까지 자란다**(창 틀도 같이). 살짝 넘겼다
 *                 돌아오는 곡선이라 쫀득하게 늘어난다.
 *  다 자라면      오른쪽에서 리포트 · 대화 판이 떠오른다.
 *
 * 🔴 두 단계를 CSS 지연으로만 나누지 않고 상태(`grown`)로 나눈 이유: 자라는
 * 순간 제목 · 설명이 **흐름에서 빠져야** 창 틀이 그 키를 가져가는데, `position`
 * 은 전이가 안 되어 지연을 못 준다. 상태로 끊어야 그 순간을 정할 수 있다.
 *
 * 🔴 판의 폭(`--ss-shot-panel-w`)이 이 연출의 **하나뿐인 손잡이**다. 판은 그
 * 값으로 넓어지고, 배경 사진 · 흐림 막 · 오려 낸 그림자는 그 값만큼 오른쪽으로
 * 비켜선다. 시작하면 그 값이 화면 폭이 되므로 **한 번에 다 맞아 떨어진다** —
 * 자라는 것과 밀려나는 것을 따로 맞출 필요가 없다.
 *
 * 🔴 고르자마자 시작하지 않는다(사용자 요청) — 잘못 고른 영상을 되돌릴 자리가
 * 없어진다. 판 안에서 확인하고 **직접 시작을 눌러야** 넘어간다.
 * ```
 *
 * 🔴 **자리를 바꾸는 것은 전부 `transform` 이다**(`left`·`width` 가 아니라).
 * 화면 절반을 옮기는 움직임이라 레이아웃을 다시 계산하게 두면 프레임이 떨어진다.
 * 그래서 판들은 늘 DOM 에 있고 밖으로 밀어 둔 것뿐이다 — 상태에 따라 붙였다
 * 뗐다 하면 나타날 때마다 애니메이션의 시작 프레임이 튄다.
 *
 * ⚠️ **파이프라인이 아직 없다.** 계약(api-contract.md 3-1)에 영상 등록과 결과
 * **적재**만 있고, 선수가 자기 리포트를 보는 경로는 "화면이 정해진 뒤에 낸다"고
 * 미뤄져 있다. 업로드 전송 경로도 객체 저장소가 정해지지 않아 없다(5장 ASM-003).
 * 그래서 **서버로 나가는 것이 하나도 없다** — 고른 영상은 브라우저 안에서만
 * 재생하고(`URL.createObjectURL`), 진행과 리포트는 자리 표시다.
 */

/**
 * 들어오고 이만큼 뒤에 왼쪽 판이 밀려 들어온다.
 *
 * 🔴 **내 프로필 카드가 나오기 시작하는 순간**이다(사용자 요청) —
 * `globals.css` 의 `[data-enter='true'] .ss-home-profile` 이 갖는 지연과 **같은
 * 값**이라야 둘이 한 몸으로 움직인다. 그 값을 고치면 여기도 같이 고칠 것.
 *
 * 한때 카드가 **다 도착한** 뒤(120 + 1150 = 1270ms)로 뒀는데, 헤더가 멎고 나서
 * 판이 따로 들어와 두 동작으로 읽혔다.
 */
const PANEL_IN_MS = 120

/**
 * 큰 글자(VIDEO / ANALYSIS / AGENT)가 나타나기 시작하는 시각 — 판이 들어오고
 * **사진이 다 비켜선 뒤**다.
 *
 * 🔴 이 기다림을 CSS 지연이 아니라 상태로 둔 이유: 같은 규칙이 **되돌아올 때도**
 * 쓰이는데, 그때는 사진을 기다릴 필요가 없다. 지연에 넣어 두면 닫고 나서
 * 글자만 1초 뒤에 나타난다. `globals.css` 의 `--ss-shot-dur` 와 같은 값이다.
 */
const MARK_IN_MS = PANEL_IN_MS + 900

/** 나갈 것들이 다 빠지고 판이 자라기 시작하기까지. */
const GROW_MS = 420

/** 판이 다 자란 뒤 오른쪽 판이 떠오르기까지(시작을 누른 시점 기준). */
const SIDE_IN_MS = 1320

/**
 * 닫을 때 판이 줄고 사진이 돌아오는 데 걸리는 시간. 그 뒤에야 나머지가
 * 다시 나타난다 — 들어갈 때의 순서를 그대로 되감는다(사용자 요청).
 * `--ss-shot-dur`(900ms)보다 조금 짧게 잡아 두 단계가 살짝 겹치게 한다.
 */
const SHRINK_MS = 820

/** 실제 파이프라인의 단계 이름이다(제안서 3장) — 이름만 자리에 먼저 놓는다. */
const STEPS = [
  { key: 'register', label: '영상 등록', note: '클립을 등록하고 분석 작업을 만듭니다' },
  { key: 'prepare', label: '전처리', note: '프레임을 고르고 흔들림을 잡습니다' },
  { key: 'track', label: '자세 추적', note: '몸의 마디를 프레임마다 따라갑니다' },
  { key: 'judge', label: '실력 판단', note: '루브릭에 비추어 수준 · 역할 · 성향을 봅니다' },
  { key: 'verify', label: '근거 검증', note: '판단마다 그렇게 본 장면을 찾습니다' },
] as const

/** 한 단계에 머무는 시간. 진짜 분석은 이보다 오래 걸린다 — 화면 확인용이다. */
const STEP_MS = 1100

/**
 * 자리 표시 리포트.
 *
 * 🔴 **수치를 그리지 않는다.** 계약이 `report.summary` 에 총점 · 등급 숫자를
 * 넣지 말라고 못박아 뒀고(3장 4), 카드에 능력치 컬럼을 두지 않는 원칙과 짝이다.
 * 수치는 `analysis_metric_value` 한 곳에만 있고 여기로 나오지 않는다.
 */
const REPORT = {
  summary:
    '디딤발이 공보다 앞서 있습니다. 임팩트에서 무릎을 조금 더 덮어 주시면 방향이 안정됩니다.',
  traits: [
    '측면으로 벌리는 움직임이 많습니다',
    '공을 받기 전에 어깨를 먼저 돌립니다',
    '두 번째 동작으로 이어지는 속도가 빠릅니다',
  ],
  /** 받은 것만 그린다 — 못 받은 호칭을 미달 표식으로 남기지 않는다(4장). */
  titles: ['첫 리포트'],
  /** 판단의 근거가 된 장면. 시각은 수치가 아니라 찾아가는 자리다. */
  scenes: [
    { at: '0:04', what: '디딤발 착지' },
    { at: '0:07', what: '임팩트' },
    { at: '0:11', what: '팔로스루' },
  ],
}

export default function AnalysisStage() {
  /**
   * 이 화면을 떠나는 중인가 — 그러면 **들어온 것을 그대로 되감는다**
   * (사용자 요청): 왼쪽 판은 왼쪽으로 물러나고, 비켜 서 있던 배경 사진은
   * 원래 자리(왼쪽 끝)로 돌아간다. 판을 도로 내리는 상태가 곧 그 그림이라
   * 따로 만들 것이 없다 — 아래 data-* 에서 `leaving` 을 빼기만 하면 된다.
   */
  const leaving = useLeaving()

  /** 왼쪽 검은 판이 들어와 있는가. */
  const [panelIn, setPanelIn] = useState(false)
  /** 오른쪽 리포트 · 대화 판이 떠 있는가. */
  const [sideIn, setSideIn] = useState(false)
  /** '분석 시작하기' 를 눌렀는가 — 그 전까지 영상은 판 안에서만 재생된다. */
  const [started, setStarted] = useState(false)
  /** 나갈 것들이 다 빠져서 이제 판이 자라도 되는가. */
  const [grown, setGrown] = useState(false)
  /** 큰 글자가 나타나도 되는가(사진이 다 비켜섰는가). */
  const [markIn, setMarkIn] = useState(false)
  /**
   * 닫는 중인가 — 판이 줄어드는 1단계 동안 켜져 있다.
   *
   * 🔴 이게 없으면 2단계에서 `file` 이 null 이 되는 순간 `<video>` 가 통째로
   * 사라져 **뚝 끊긴다.** 줄어드는 내내 미리 흐려 두면, 정작 없어질 때는 이미
   * 안 보이는 상태다.
   */
  const [closing, setClosing] = useState(false)
  const [file, setFile] = useState<{ name: string; url: string } | null>(null)
  const [step, setStep] = useState(0)
  const [done, setDone] = useState(false)
  const [dragging, setDragging] = useState(false)

  // 판이 화면을 채우는 동안에는 헤더도 비킨다(사용자 요청) — 목적지 글자와
  // 내 프로필 카드가 영상 위에 떠 있으면 화면이 둘로 읽힌다.
  useHideChrome(started)
  const inputRef = useRef<HTMLInputElement>(null)
  const previewRef = useRef<HTMLVideoElement>(null)
  const timers = useRef<number[]>([])

  const later = useCallback((fn: () => void, ms: number) => {
    timers.current.push(window.setTimeout(fn, ms))
  }, [])

  // 화면을 떠날 때 예약해 둔 것을 전부 거둔다.
  useEffect(() => {
    const list = timers.current
    return () => list.forEach(clearTimeout)
  }, [])

  // 들어오면 왼쪽 판이 밀려 들어오고, 사진이 다 비켜선 뒤 큰 글자가 뜬다.
  useEffect(() => {
    later(() => setPanelIn(true), PANEL_IN_MS)
    later(() => setMarkIn(true), MARK_IN_MS)
  }, [later])

  // 🔴 objectURL 은 반드시 되돌려준다 — 안 그러면 고를 때마다 브라우저가
  // 파일을 통째로 붙들고 있는다(새로고침 전까지 안 풀린다).
  useEffect(() => {
    if (!file) return
    return () => URL.revokeObjectURL(file.url)
  }, [file])

  // 오른쪽 판이 떠오른 뒤부터 단계가 하나씩 넘어간다.
  useEffect(() => {
    if (!sideIn || done) return
    if (step >= STEPS.length) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setDone(true)
      return
    }
    const t = window.setTimeout(() => setStep((s) => s + 1), STEP_MS)
    return () => clearTimeout(t)
  }, [sideIn, step, done])

  /** 영상을 고른다 — 아직 시작은 아니다. 판 안에서 먼저 보여 준다. */
  function pick(picked: File | undefined) {
    if (!picked) return
    setFile({ name: picked.name, url: URL.createObjectURL(picked) })
  }

  /** 분석 시작 — 판이 물러나고 영상이 화면을 채운다. */
  function start() {
    if (!file) return
    setClosing(false)
    setStarted(true)
    // 판은 물러나지 않는다 — **화면 폭까지 자란다**(CSS 의 --ss-shot-panel-w).
    // 누른 것이 곧 재생 신호이기도 하다. 자동재생 정책상 사용자의 클릭에서
    // 이어지는 play() 는 허용된다. 막히더라도 화면은 그대로다.
    // ⚠️ `?.catch` 다 — `play()` 가 **프로미스를 안 돌려주는 환경**이 있다
    // (jsdom). 그냥 `.catch` 로 쓰면 거기서 TypeError 가 나고 **그 아래 줄이
    // 통째로 안 돈다** — 자라지도, 오른쪽 판이 뜨지도 않았다.
    previewRef.current?.play()?.catch(() => {})
    setStep(0)
    setDone(false)
    later(() => setGrown(true), GROW_MS)
    later(() => setSideIn(true), SIDE_IN_MS)
  }

  function reset() {
    // 1단계 — 판이 줄고, 비켜서 있던 배경 사진이 제자리로 돌아온다.
    // 영상은 그동안 미리 흐려진다(아래 closing 주석).
    setSideIn(false)
    setGrown(false)
    setClosing(true)
    // 2단계 — 다 줄어든 뒤에야 제목 · 설명 · 헤더가 다시 나타난다.
    // 🔴 `started` 를 여기서 끄는 것이 그 신호다. 같이 꺼 버리면 판이 줄기도
    // 전에 글자들이 되돌아와 두 동작이 겹친다.
    later(() => {
      setStarted(false)
      setClosing(false)
      setFile(null)
      setStep(0)
      setDone(false)
      if (inputRef.current) inputRef.current.value = ''
    }, SHRINK_MS)
  }

  return (
    <div
      className="ss-shot"
      data-panel={panelIn && !leaving ? 'true' : undefined}
      data-video={started && !leaving ? 'true' : undefined}
      data-side={sideIn && !leaving ? 'true' : undefined}
      data-grown={grown && !leaving ? 'true' : undefined}
      data-mark={markIn && !leaving ? 'true' : undefined}
      data-closing={closing ? 'true' : undefined}
      data-picked={file ? 'true' : undefined}
      data-leaving={leaving ? 'true' : undefined}
    >
      {/* 배경 사진 — 판이 들어오면 그만큼 오른쪽으로 비켜 준다. */}
      <FigureBackground className="ss-shot-figure" />

      {/* 사진의 왼쪽 변을 검정으로 잦아들게 하는 막. 사진에 마스크를 씌우지
          않고 **따로 한 겹**으로 둔 이유는 CSS 주석에 있다 — 켜고 끄는 것을
          부드럽게 하려면 불투명도를 전이시킬 수 있어야 한다. */}
      <div className="ss-shot-fade" aria-hidden="true" />

      {/* 🔴 **그림자만 오려 내는 필터.** 사진의 밝기를 알파로 바꾼 뒤
          (luminanceToAlpha) 어두운 곳만 1 로 남기고(feFuncA), 그 알파로 원본
          사진을 잘라 낸다(feComposite in) — 결과는 **인물 실루엣 모양의
          사진 조각**이다. 그걸 글자 위에 다시 덮으면 겹치는 부분만 사라진다.

          자르는 문턱은 밝기 0.08 ~ 0.13 사이다. 그 아래는 실루엣, 그 위는
          연기다. 계단이 아니라 짧은 경사라 실루엣 가장자리가 톱니지지 않는다.
          width/height 0 이라 자리를 차지하지 않는다 — 정의만 두는 자리다. */}
      <svg width="0" height="0" aria-hidden="true" focusable="false" className="absolute">
        <filter id="ss-shadow-cut" colorInterpolationFilters="sRGB">
          <feColorMatrix type="luminanceToAlpha" result="lum" />
          <feComponentTransfer in="lum" result="cut">
            <feFuncA type="linear" slope="-20" intercept="2.6" />
          </feComponentTransfer>
          <feComposite in="SourceGraphic" in2="cut" operator="in" />
        </filter>
      </svg>

      {/* 배경 사진 위의 큰 글자.

          🔴 **인물 그림자 뒤로 들어가야 한다**(사용자 요청). 사진은 한 장이라
          인물만 따로 떼어 위에 얹을 수가 없어서, `mix-blend-mode: overlay` 로
          푼다 — 이 혼합은 **바탕이 검을수록 글자를 어둡게** 만든다(어두운 쪽은
          곱하기, 밝은 쪽은 스크린). 인물 실루엣이 거의 순검정이라 그 위에서는
          글자가 통째로 사라지고, 밝은 연기 위에서만 떠오른다.

          장식이라 스크린리더에서 숨긴다 — 화면 이름은 왼쪽 판의 h1 이 한다. */}
      <p className="ss-shot-mark" aria-hidden="true">
        <span>VIDEO</span>
        <span>ANALYSIS</span>
        <span>AGENT</span>
      </p>

      {/* 오려 낸 그림자를 글자 **위에** 다시 덮는다. 같은 사진 · 같은 상자 ·
          같은 자르기라 자리가 저절로 맞는다 — SVG 좌표를 손으로 맞출 필요가
          없다. 덮인 자리는 원래 사진 그대로라 덮었다는 티도 안 난다. */}
      <div className="ss-shot-cut" aria-hidden="true">
        {/* eslint-disable-next-line @next/next/no-img-element -- 배경 사진과 같은 것을 다시 그린다 */}
        <img src="/home_figure.jpg" alt="" decoding="async" />
      </div>

      {/* ── 왼쪽 검은 판 — 영상을 올리는 곳 ─────────────────────────── */}
      <aside className="ss-shot-panel" aria-label="영상 올리기">
        <div className="ss-shot-head">
          <h1>영상 분석</h1>
          <p className="ss-shot-lead">
            경기 영상을 올리면 수준 · 역할 · 성향 세 축으로 정리해 드립니다.
            <br />
            하나의 점수로 매기지 않습니다.
          </p>
        </div>

        {/* 브라우저 창 모양의 틀. 참고한 화면에서 **신호등 점과 주소 알약만**
            남겼다(사용자 요청) — 뒤로/새로고침 같은 것은 여기서 할 일이 없다.
            알약에는 고른 영상의 이름이 뜬다. */}
        <div className="ss-shot-frame">
          <div className="ss-shot-frame-bar">
            <span className="ss-shot-frame-title">
              <span className="material-symbols-outlined" aria-hidden="true">
                movie
              </span>
              {file ? file.name : '고른 영상이 없습니다'}
            </span>

            {/* 점은 **오른쪽**에, 빨간 것이 **맨 오른쪽**이다(사용자 요청). */}
            <span className="ss-shot-dots">
              <span className="ss-shot-dot" aria-hidden="true" />
              <span className="ss-shot-dot" aria-hidden="true" />
              {/* 🔴 마지막 점은 **진짜 버튼**이다. 창 틀의 닫기 자리이므로
                  시작한 뒤에도 그대로 있어야 한다 — 한때 시작하면 장식으로
                  돌려놨더니 "왜 사라지냐"는 말을 들었다. 영상이 있는 동안은
                  늘 누를 수 있고, 누르면 고르기 전으로 돌아간다. */}
              {file ? (
                <button
                  type="button"
                  className="ss-shot-dot ss-shot-dot-close"
                  aria-label="영상 닫기"
                  onClick={reset}
                />
              ) : (
                <span className="ss-shot-dot" aria-hidden="true" />
              )}
            </span>

          </div>

          <div className="ss-shot-frame-body">
            {file ? (
              <video
                ref={previewRef}
                src={file.url}
                controls
                playsInline
                // 끝나면 처음부터 다시 — 사용자가 직접 세우기 전에는 멈추지
                // 않는다(사용자 요청). 분석하는 내내 자리를 지켜야 하는 화면이라
                // 마지막 프레임에서 굳어 있으면 멈춘 것처럼 보인다.
                loop
                aria-label={file.name}
              />
            ) : (
              <label
                className="ss-shot-drop"
                data-dragging={dragging ? 'true' : undefined}
                onDragOver={(e) => {
                  e.preventDefault()
                  setDragging(true)
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={(e) => {
                  e.preventDefault()
                  setDragging(false)
                  pick(e.dataTransfer.files[0])
                }}
              >
                <span className="material-symbols-outlined" aria-hidden="true">
                  upload
                </span>
                <strong>영상을 여기에 놓으세요</strong>
                <span className="ss-shot-drop-note">
                  눌러서 고를 수도 있습니다 · 한 번에 한 클립
                </span>
                {/* 파일 입력은 라벨 안에 두되 눈에서만 숨긴다 — display:none 은
                    일부 브라우저에서 키보드로 못 닿는다. */}
                <input
                  ref={inputRef}
                  type="file"
                  accept="video/*"
                  className="sr-only"
                  aria-label="분석할 영상"
                  onChange={(e) => pick(e.target.files?.[0])}
                />
              </label>
            )}
          </div>
        </div>

        {/* 시작한 뒤에는 지운다 — 판이 물러나는 동안 화면 밖에 남아 있으면
            키보드로는 여전히 닿아서 두 번 시작할 수 있다. */}
        {/* 🔴 **늘 DOM 에 있다.** 붙였다 뗐다 하면 그 순간 판의 키가 확 바뀌어
            안쪽 것들이 툭 떨어진다 — 영상을 고를 때(버튼이 생김)도, 닫을 때
            (버튼이 사라짐)도 그랬다. 접히고 펴지는 것은 CSS 가 하고
            (`data-picked`), 여기서는 못 누르게 잠그기만 한다. */}
        {
          <button
            type="button"
            className="ss-shot-start"
            disabled={!file || grown}
            onClick={start}
            // 🔴 backdrop-filter 는 **인라인으로만** 준다 — globals.css 에 두면
            // Lightning CSS 를 지나며 떨어져 나간 전례가 있다(추천 판).
            style={{
              backdropFilter: 'blur(var(--ss-glass-blur)) saturate(var(--ss-glass-saturate))',
              WebkitBackdropFilter: 'blur(var(--ss-glass-blur)) saturate(var(--ss-glass-saturate))',
            }}
          >
            분석 시작하기
          </button>
        }
      </aside>

      {/* ── 오른쪽 떠 있는 판 — 진행 · 리포트 · 대화 ────────────────── */}
      <aside className="ss-shot-side" aria-label="리포트와 대화">
        <header className="ss-shot-side-head">
          <h2>{done ? '리포트' : '보고 있습니다'}</h2>
          <button type="button" className="ss-shot-again" onClick={reset}>
            다른 영상
          </button>
        </header>

        {/* 시작을 누르기 전에는 단계도 리포트도 그리지 않는다 — 판이 화면
            밖에 있더라도 아무 일도 없는 진행 표시가 DOM 에 남으면 안 된다.
            고르기만 한 단계에서는 아직 아무것도 안 하고 있다. */}
        {started && (done ? (
          <div className="ss-report">
            <p className="ss-report-summary">{REPORT.summary}</p>

            <ul className="ss-report-traits">
              {REPORT.traits.map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>

            {/* 받은 호칭만 그린다. 못 받은 것을 미달 표식으로 남기지 않는다. */}
            {REPORT.titles.length > 0 && (
              <ul className="ss-report-titles" aria-label="받은 호칭">
                {REPORT.titles.map((t) => (
                  <li key={t}>{t}</li>
                ))}
              </ul>
            )}

            <h3>이렇게 본 장면</h3>
            <ul className="ss-report-scenes">
              {REPORT.scenes.map((s) => (
                <li key={s.at}>
                  <b>{s.at}</b>
                  {s.what}
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <ol className="ss-steps" aria-label="분석 진행">
            {STEPS.map((s, i) => {
              const state = i < step ? 'done' : i === step ? 'now' : 'todo'
              return (
                <li key={s.key} className="ss-step" data-state={state}>
                  <span className="ss-step-dot" aria-hidden="true" />
                  <span className="ss-step-text">
                    <span className="ss-step-label">{s.label}</span>
                    <span className="ss-step-note">{s.note}</span>
                  </span>
                  {/* 진행 상태는 색으로만 말하지 않는다 — 스크린리더에도 적는다. */}
                  <span className="sr-only">
                    {state === 'done' ? '끝남' : state === 'now' ? '진행 중' : '대기'}
                  </span>
                </li>
              )
            })}
          </ol>
        ))}

        <AnalysisChat />
      </aside>
    </div>
  )
}
