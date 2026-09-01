'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import AnalysisChat from '@/components/analysis/AnalysisChat'
import FigureBackground from '@/components/FigureBackground'
import { useHideChrome, useLeaving } from '@/lib/pageTransition'
import type { Box } from '@/lib/box'
import { smoothStep } from '@/lib/smoothBox'
import {
  EDGES,
  L_SHOULDER,
  MIN_KP,
  NOSE,
  R_SHOULDER,
  isSamePerson,
  smoothPose,
  type Point,
} from '@/lib/pose'
import {
  detectPeople,
  refinePose,
  warmUpDetector,
  warmUpRefine,
} from '@/lib/personDetector'
import {
  createPersonTracker,
  snapToDetection,
  type PersonTracker,
} from '@/lib/personTrack'

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

/**
 * 고를 수 있는 종목.
 *
 * 🔴 **에이전트가 종목을 알아야 세세하게 본다**(정상호 · 사용자 전달). 루브릭이
 * 종목마다 다르므로 영상만 받아서는 "무엇에 비추어 볼지"가 정해지지 않는다.
 * 그래서 **고르지 않으면 시작할 수 없다** — 기본값을 축구로 박아 두면 야구
 * 영상이 축구 루브릭으로 조용히 채점된다.
 *
 * ⚠️ 계약(api-contract.md 3-1)의 영상 등록에 **종목 필드가 아직 없다.** 지금은
 * 화면 안에만 있고 서버로 나가지 않는다 — 리포트 조회 규격을 낼 때 같이 낸다.
 */
const SPORTS = [
  { key: 'soccer', label: '축구', icon: 'sports_soccer' },
  { key: 'baseball', label: '야구', icon: 'sports_baseball' },
  { key: 'basketball', label: '농구', icon: 'sports_basketball' },
] as const

type SportKey = (typeof SPORTS)[number]['key']

/**
 * 분석 대상(선수)을 묶은 네모. 0~1 정규화 좌표다.
 *
 * 🔴 **누구를 볼지 사람이 정한다.** 검출기는 사람을 여럿 찾아내고(`pose.py` 의
 * RT-DETR), 지금은 그중 **가장 큰 박스**를 자동으로 고른다(`_largest_person_box`)
 * — 카메라에 가까운 사람일 뿐 분석하고 싶은 사람이라는 보장이 없다.
 *
 * 🔴 이건 미결 8번("분석 대상 selector 미확정")을 **우회가 아니라 해소**한다.
 * 그 항목의 결론이 "continuity 는 처음 잡은 대상이 맞으면 이기고 틀리면 진다"
 * 인데, 사람이 첫 프레임에서 찍어 주면 그 전제가 늘 참이 된다.
 *
 * ⚠️ 계약(`POST /api/v1/videos`)에 아직 이 필드가 없다. 붙일 자리는 정해져
 * 있다 — `side`(던지는 팔 · 차는 발)가 "자동 판별이 신뢰할 수 없어 사람이
 * 지정할 수 있게 열어 둔" 필드이고, 없으면 자동 판별로 떨어진다. 대상자도
 * 같은 규칙으로 그 옆에 붙이면 된다.
 */
const clamp01 = (n: number) => Math.min(1, Math.max(0, n))

/**
 * 오버레이 기준 좌표를 **영상 그림 안** 좌표로 옮긴다.
 *
 * 🔴 둘은 같지 않다. `<video>` 는 `object-fit: contain` 이라 상자 비율과 영상
 * 비율이 다르면 위아래(또는 좌우)에 **레터박스 여백**이 생긴다. 그 여백까지
 * 포함한 좌표를 그대로 보내면 에이전트가 원본 프레임에서 엉뚱한 자리를 본다 —
 * 세로 영상일수록 크게 어긋난다.
 */
function toVideoBox(box: Box, el: HTMLElement, video: HTMLVideoElement | null): Box {
  const r = el.getBoundingClientRect()
  const vw = video?.videoWidth ?? 0
  const vh = video?.videoHeight ?? 0
  if (!vw || !vh || !r.width || !r.height) return box
  // 상자 안에서 영상 그림이 차지하는 비율과, 한쪽에 남는 여백.
  const scale = Math.min(r.width / vw, r.height / vh)
  const cw = (vw * scale) / r.width
  const ch = (vh * scale) / r.height
  const ox = (1 - cw) / 2
  const oy = (1 - ch) / 2
  const x1 = clamp01((box.x - ox) / cw)
  const y1 = clamp01((box.y - oy) / ch)
  const x2 = clamp01((box.x + box.w - ox) / cw)
  const y2 = clamp01((box.y + box.h - oy) / ch)
  return { x: x1, y: y1, w: x2 - x1, h: y2 - y1 }
}

/** `toVideoBox` 의 짝 — 영상 안 좌표를 다시 오버레이 좌표로. */
function toViewBox(box: Box, el: HTMLElement, video: HTMLVideoElement | null): Box {
  const r = el.getBoundingClientRect()
  const vw = video?.videoWidth ?? 0
  const vh = video?.videoHeight ?? 0
  if (!vw || !vh || !r.width || !r.height) return box
  const scale = Math.min(r.width / vw, r.height / vh)
  const cw = (vw * scale) / r.width
  const ch = (vh * scale) / r.height
  return {
    x: (1 - cw) / 2 + box.x * cw,
    y: (1 - ch) / 2 + box.y * ch,
    w: box.w * cw,
    h: box.h * ch,
  }
}

/** 0:07 꼴로. 리포트의 '이렇게 본 장면' 과 같은 표기다. */
function fmtTime(sec: number): string {
  if (!Number.isFinite(sec) || sec < 0) return '0:00'
  const m = Math.floor(sec / 60)
  const r = Math.floor(sec % 60)
  return `${m}:${String(r).padStart(2, '0')}`
}

/**
 * 관절 한 점을 영상 안 좌표 → 오버레이 좌표로. `toViewBox` 와 같은 셈이다.
 *
 * 🔴 상자와 **같은 보정**을 거쳐야 한다. 한쪽만 보정하면 막대기가 상자와
 * 어긋난 자리에 그려진다 — 세로 영상에서 특히 크게 벌어진다.
 */
function toViewPoint(p: Point, el: HTMLElement, video: HTMLVideoElement | null) {
  const r = el.getBoundingClientRect()
  const vw = video?.videoWidth ?? 0
  const vh = video?.videoHeight ?? 0
  if (!vw || !vh || !r.width || !r.height) return p
  const scale = Math.min(r.width / vw, r.height / vh)
  const cw = (vw * scale) / r.width
  const ch = (vh * scale) / r.height
  return { x: (1 - cw) / 2 + p.x * cw, y: (1 - ch) / 2 + p.y * ch, score: p.score }
}

/** 뼈대를 그리는 좌표계 — 실제 크기와 무관한 고정 격자다(아래 SVG 참고). */
const POSE_VB = 1000

/** 이보다 작게 그은 것은 실수로 본다(오버레이 폭 · 키 대비). */
const MIN_BOX = 0.04

/**
 * 축소본의 가로 픽셀.
 *
 * 🔴 160 에서 **256 으로 올렸다.** 160 이면 멀리 있는 사람이 20px 남짓이라
 * 무늬라고 할 것이 남지 않는다 — 네모가 사람을 놓치던 원인 중 하나였다.
 * 훑는 비용은 후보 수(≈1500)에만 걸리고 이 값에는 거의 안 걸린다.
 */
const TRACK_W = 256

/**
 * 따라가기를 다시 재는 **최소** 간격.
 *
 * 검출 한 장이 이보다 오래 걸리면 그 시간이 곧 간격이 된다 — 겹쳐 돌리지
 * 않는다(`busy`). 사람이 잠깐 안 잡혀도 검출은 화면 전체를 보므로 다음 장에서
 * 다시 잡힌다. 무늬 따라가기 때처럼 간격이 곧 실패로 이어지지 않는다.
 */
const TRACK_MS = 70

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
  /**
   * 고른 종목. **기본값을 두지 않는다** — 위 SPORTS 주석 참고.
   *
   * 영상을 물러도(reset) 지우지 않는다. 같은 사람이 연달아 올리는 클립은
   * 대개 같은 종목이라, 매번 다시 고르게 하면 손만 는다.
   */
  const [sport, setSport] = useState<SportKey | null>(null)
  /**
   * 지금 끌고 있는(또는 다 그린) 네모 — 오버레이 기준이다.
   * 확정 전이라 다시 끌면 그대로 덮어쓴다.
   */
  const [rect, setRect] = useState<Box | null>(null)
  /**
   * 확정된 분석 대상. **이게 정해져야 단계가 돌기 시작한다** — 누구를 보는지
   * 모르는 채로 "자세 추적"을 켤 수는 없다(사용자 요청).
   *
   * `auto` 는 사람이 안 그리고 에이전트의 자동 판별에 맡긴 경우다. 계약의
   * `side` 와 같은 규칙이라 값이 없는 것과 같은 뜻이고, 끌 수 없는 입력
   * 장치(키보드만 쓰는 경우)의 유일한 길이기도 하다.
   */
  const [subject, setSubject] = useState<{ box: Box | null; at: number } | null>(null)
  /**
   * 🔴 따라가는 네모는 **React 상태가 아니다.**
   *
   * 검출은 초당 15번인데 그리기는 60번이라(그래야 부드럽다) 상태에 두면 초당
   * 60번 다시 그린다. 자리는 ref 에 담고 DOM 에 직접 쓴다 — 화면에 관여하는
   * 상태(`lost`)만 React 가 들고 있으면 된다.
   */
  /** 검출이 준 **목표** 자리(영상 좌표). */
  const targetRef = useRef<Box | null>(null)
  /** 지금 실제로 그리고 있는 자리 — 목표를 부드럽게 좇는다. */
  const shownRef = useRef<Box | null>(null)
  const boxRef = useRef<HTMLDivElement>(null)
  /** 검출이 준 관절(영상 좌표)과, 지금 그리고 있는 눅인 관절. */
  const poseRef = useRef<Point[] | null>(null)
  const shownPoseRef = useRef<Point[] | null>(null)
  /**
   * 화면의 **나머지 사람들** 관절.
   *
   * 🔴 이 사람들은 따라가지 않는다 — 누가 누구인지 잇지 않으므로 프레임마다
   * 차례가 뒤바뀔 수 있다. 그래서 눅일 때 "같은 사람의 연속된 두 장인가" 를
   * 먼저 묻고(`isSamePerson`), 아니면 그냥 새로 놓는다.
   */
  const othersRef = useRef<Point[][]>([])
  const shownOthersRef = useRef<Point[][]>([])
  /** 뼈대와 관절점을 그리는 path 넷. 상자처럼 DOM 에 직접 쓴다. */
  const boneRef = useRef<SVGPathElement>(null)
  const jointRef = useRef<SVGPathElement>(null)
  const otherBoneRef = useRef<SVGPathElement>(null)
  const otherJointRef = useRef<SVGPathElement>(null)
  /** 놓쳤는가. 놓쳤으면 네모를 세워 두고 다시 묶으라고 말한다. */
  const [lost, setLost] = useState(false)
  /** 검출 모델을 못 올렸는가(오프라인 등) — 그러면 따라가기만 꺼진다. */
  const [trackFailed, setTrackFailed] = useState(false)
  /**
   * 묶는 동안 쓰는 재생 상태.
   *
   * 🔴 **직접 만든다.** 묶는 판이 영상 위를 통째로 덮어서 브라우저 기본
   * 컨트롤에 손이 안 닿는다(사용자 요청: "첫 화면에 원하는 사람이 안 나왔을
   * 수도 있으니까"). 판에 구멍을 내는 대신 판 안에 컨트롤을 둔다 — 컨트롤
   * 높이는 브라우저마다 달라서 구멍 크기를 맞출 방법이 없다.
   */
  const [playing, setPlaying] = useState(false)
  /**
   * 🔴 **사용자가 재생을 원했는가.**
   *
   * 묶는 동안 영상이 저 혼자 돌고 있었다 — 시작을 누른 뒤 `pause()` 를 부르는데도
   * 0초에서 3초로 흘러가 있었다(사용자 지적). 어디서 다시 트는지 한 곳으로
   * 좁히는 대신 **규칙을 코드로 못박는다**: 묶는 동안 재생은 우리 재생 단추와
   * 대상을 확정하는 순간, 그 둘에서만 시작한다. 그 밖에서 재생이 시작되면
   * (`onPlay`) 곧바로 도로 세운다.
   *
   * 상태가 아니라 ref 인 이유 — `onPlay` 는 다시 그리기를 기다리지 않고
   * 그 순간의 값을 봐야 한다.
   */
  const wantPlayRef = useRef(false)
  const [time, setTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [step, setStep] = useState(0)
  const [done, setDone] = useState(false)
  const [dragging, setDragging] = useState(false)

  // 판이 화면을 채우는 동안에는 헤더도 비킨다(사용자 요청) — 목적지 글자와
  // 내 프로필 카드가 영상 위에 떠 있으면 화면이 둘로 읽힌다.
  useHideChrome(started)
  const inputRef = useRef<HTMLInputElement>(null)
  const previewRef = useRef<HTMLVideoElement>(null)
  /** 네모를 끄는 판. 좌표를 재는 기준이라 ref 가 필요하다. */
  const pickRef = useRef<HTMLDivElement>(null)
  /** 끌기 시작한 자리(오버레이 기준 0~1). 끄는 동안에만 값이 있다. */
  const dragFrom = useRef<{ x: number; y: number } | null>(null)
  /** 따라가는 네모를 그리는 판. 화면 좌표를 재는 기준이다. */
  const trackRef = useRef<HTMLDivElement>(null)
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

  // 🔴 영상을 고르는 **순간** 검출 모델을 올리기 시작한다. 시작을 누른 뒤에
  // 올리면 첫 몇백 ms 동안 네모가 안 나와서 "안 따라간다" 로 보인다.
  useEffect(() => {
    if (!file) return
    void warmUpDetector()
      // 사람을 찾는 모델이 먼저다 — 그게 없으면 2단계는 쓸 데가 없다.
      // 🔴 2단계가 실패해도 **따라가기를 끄지 않는다.** 그건 관절을 더
      // 정확하게 하는 덤이고, 없으면 1단계 관절로 그리면 된다.
      .then(() => warmUpRefine().catch(() => {}))
      .catch(() => setTrackFailed(true))
  }, [file])

  // 영상의 재생 상태를 따라 읽는다 — 우리 컨트롤과 실제가 갈리면 안 된다
  // (기본 컨트롤 · 키보드 · 자동 재생 어디서 바뀌든 여기로 들어온다).
  useEffect(() => {
    const video = previewRef.current
    if (!file || !video) return
    const onPlay = () => setPlaying(true)
    const onPause = () => setPlaying(false)
    const onTime = () => setTime(video.currentTime)
    const onMeta = () => setDuration(Number.isFinite(video.duration) ? video.duration : 0)
    video.addEventListener('play', onPlay)
    video.addEventListener('pause', onPause)
    video.addEventListener('timeupdate', onTime)
    video.addEventListener('durationchange', onMeta)
    video.addEventListener('loadedmetadata', onMeta)
    return () => {
      video.removeEventListener('play', onPlay)
      video.removeEventListener('pause', onPause)
      video.removeEventListener('timeupdate', onTime)
      video.removeEventListener('durationchange', onMeta)
      video.removeEventListener('loadedmetadata', onMeta)
    }
  }, [file])

  // 🔴 objectURL 은 반드시 되돌려준다 — 안 그러면 고를 때마다 브라우저가
  // 파일을 통째로 붙들고 있는다(새로고침 전까지 안 풀린다).
  useEffect(() => {
    if (!file) return
    return () => URL.revokeObjectURL(file.url)
  }, [file])

  // 오른쪽 판이 떠오르고 **분석 대상이 정해진 뒤부터** 단계가 하나씩 넘어간다.
  // 🔴 누구를 보는지 모르는 채로 '자세 추적' 을 켤 수는 없다(사용자 요청).
  useEffect(() => {
    if (!sideIn || !subject || done) return
    if (step >= STEPS.length) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setDone(true)
      return
    }
    const t = window.setTimeout(() => setStep((s) => s + 1), STEP_MS)
    return () => clearTimeout(t)
  }, [sideIn, subject, step, done])

  /**
   * 🔴 **묶은 사람을 정말로 따라간다** — 매 프레임 사람을 검출하고, 그중에서
   * 내 사람을 골라 잇는다(tracking-by-detection).
   *
   * 왜 무늬 따라가기를 버렸는지는 `lib/personTrack.ts` 첫머리에 표로 적어 뒀다.
   * 한 줄로 줄이면 — **박스가 언제나 검출된 사람 위에만 있어서** 배경으로
   * 미끄러질 자리가 없고, 검출이 화면 전체라 **놓쳐도 돌아온다.**
   *
   * ⚠️ 모델을 못 올리면(오프라인 등) 화면은 그대로 돌아가되 따라가기만 꺼진다.
   */
  useEffect(() => {
    const video = previewRef.current
    const first = subject?.box
    // 🔴 닫기 시작하면 **곧바로** 멎는다. 판이 줄어드는 0.8초 동안 계속 돌면
    // 그 사이 네모가 남의 위에서 움직이는 것이 보인다(사용자 요청).
    if (!started || closing || !video || !first) return

    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d', { willReadFrequently: true })
    if (!ctx) return

    let stop = false
    let tracker: PersonTracker | null = null
    /**
     * 아직 사람에 못 맞춘 채로 몇 바퀴 돌았나.
     *
     * 🔴 **처음 생김새는 반드시 검출된 상자에서 떠야 한다.** 사람을 크게
     * 감싸 그리는 것은 자연스러운 일이라(대부분 그렇게 그린다) 손으로 그린
     * 네모는 절반이 배경일 수 있다 — 세로 영상에서는 하늘이 그랬다. 그걸
     * 기준으로 삼으면 이후의 진짜 검출과 영영 안 닮아 처음부터 끝까지
     * "놓쳤습니다" 가 된다.
     *
     * 그래서 **사람에 맞출 수 있을 때까지 기다린다.** 끝내 못 맞추면 그때
     * 그린 대로 쓴다 — 아무것도 안 하는 것보다는 낫다.
     */
    let waited = 0
    const WAIT_MAX = 20

    /**
     * 생김새를 재는 데 쓰는 축소본 한 장.
     *
     * 🔴 **색을 버리지 않는다.** 회색조로 줄였다가 유니폼 색이 사라져서
     * 박스가 남에게 옮겨 붙었다(`appearance.ts` 첫머리 참고).
     */
    const grab = () => {
      if (!canvas.width) {
        canvas.width = TRACK_W
        canvas.height = Math.max(1, Math.round((TRACK_W * video.videoHeight) / video.videoWidth))
      }
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
      return ctx.getImageData(0, 0, canvas.width, canvas.height)
    }

    const loop = async () => {
      while (!stop) {
        await new Promise((r) => setTimeout(r, TRACK_MS))
        if (stop) return
        if (video.readyState < 2 || !video.videoWidth) continue

        let dets
        try {
          dets = await detectPeople(video)
        } catch {
          // 모델을 못 올렸다 — 조용히 멎는다. 화면의 나머지는 그대로 돈다.
          if (!stop) setTrackFailed(true)
          return
        }
        if (stop) return

        const frame = grab()

        // 첫 바퀴 — 손으로 그린 네모를 **검출된 사람에 맞춰 주고** 시작한다.
        if (!tracker) {
          const snapped = snapToDetection(first, dets)
          if (!snapped && waited < WAIT_MAX) {
            waited += 1
            continue
          }
          const from = snapped ?? first
          tracker = createPersonTracker(frame, from)
          targetRef.current = from
          shownRef.current = from
          const me = dets.find((d) => d.box === from)
          if (me?.keypoints) {
            poseRef.current = me.keypoints
            shownPoseRef.current = me.keypoints
          }
          const fine = await refinePose(video, from)
          if (stop) return
          if (fine) {
            poseRef.current = fine
            shownPoseRef.current = fine
          }
          continue
        }

        // 멈춰 있으면 그림이 안 바뀐다 — 다시 잴 이유가 없다.
        if (video.paused) continue

        const r = tracker.step(dets, frame)
        setLost(r.lost)

        // 화면의 나머지 사람들 — 회색으로 그린다. 누구인지는 안 따진다.
        othersRef.current = dets
          .filter((d) => d !== r.det)
          .map((d) => d.keypoints)
          .filter((k): k is Point[] => Boolean(k))

        /**
         * 🔴 **놓치면 아예 없앤다**(사용자 요청). 예전에는 마지막 자리에
         * 점선으로 세워 뒀는데, 그 사람은 이미 화면에 없으므로 그 네모는
         * 아무것도 안 가리킨다 — 오히려 거기 있는 줄 알게 만든다.
         * 다시 나타나면 그 자리에서 바로 다시 그린다(눅인 값도 같이 지운다).
         */
        if (r.lost) {
          targetRef.current = null
          shownRef.current = null
          poseRef.current = null
          shownPoseRef.current = null
          continue
        }

        // 그리는 것은 아래 rAF 가 한다 — 여기서는 목표만 갈아 끼운다.
        targetRef.current = r.box
        if (r.det?.keypoints) poseRef.current = r.det.keypoints

        /**
         * 🔴 **2단계 — 그 사람만 잘라 확대해서 관절을 다시 잰다.**
         *
         * 1단계(MultiPose)는 화면 전체를 256px 로 줄여서 보므로, 멀리 있는
         * 선수는 가로 30px 남짓이다 — 그 크기의 손목 · 발목은 믿을 수 없다.
         * 같은 사람을 256×256 에 꽉 채워 다시 재면 픽셀이 여덟 배쯤 간다.
         *
         * 놓친 동안에는 안 한다 — 어디를 잘라야 할지 모르는 상태다.
         * 실패하면 1단계 값을 그대로 쓴다(위에서 이미 넣어 뒀다).
         */
        const fine = await refinePose(video, r.box)
        if (stop) return
        if (fine) poseRef.current = fine
      }
    }

    void loop()
    return () => {
      stop = true
    }
  }, [started, closing, subject])

  /**
   * 🔴 **그리기는 검출과 따로 돈다.**
   *
   * 검출 결과를 그대로 그리면 초당 15번만 움직여 뚝뚝 끊기고, 크기가 프레임마다
   * 흔들려 네모가 숨쉬듯 벌렁거린다(사용자 지적). 실제 서비스가 하는 대로
   * 목표만 검출에서 받고 **보이는 것은 60fps 로 눅여서** 그린다
   * (`lib/smoothBox.ts` — 자리는 빠르게, 크기는 그 네 배 천천히).
   */
  useEffect(() => {
    if (!started || closing || !subject?.box) return
    let raf = 0
    let prev = performance.now()

    const draw = (t: number) => {
      raf = requestAnimationFrame(draw)
      const dt = t - prev
      prev = t

      const target = targetRef.current
      const el = boxRef.current
      const layer = trackRef.current
      const video = previewRef.current
      if (!el || !layer) return

      // 나머지 사람들은 내 사람을 놓쳤든 말든 늘 그린다.
      drawOthers(dt, layer, video)

      // 🔴 놓쳤으면 네모도 막대기도 **아예 감춘다**(사용자 요청).
      if (!target) {
        el.style.opacity = '0'
        boneRef.current?.setAttribute('d', '')
        jointRef.current?.setAttribute('d', '')
        return
      }

      const next = shownRef.current ? smoothStep(shownRef.current, target, dt) : target
      shownRef.current = next

      const v = toViewBox(next, layer, video)
      el.style.left = `${v.x * 100}%`
      el.style.top = `${v.y * 100}%`
      el.style.width = `${v.w * 100}%`
      el.style.height = `${v.h * 100}%`
      // 처음 한 장은 자리가 정해지기 전이라 감춰 뒀다(CSS) — 이제 보인다.
      el.style.opacity = '1'

      drawPose(dt, layer, video)
    }

    /** 여러 사람의 자세를 뼈 · 관절 두 줄의 `d` 로 모은다. */
    const pathsFor = (poses: Point[][], layer: HTMLElement, video: HTMLVideoElement | null) => {
      let bones = ''
      let joints = ''
      for (const pose of poses) {
        const pt = pose.map((p) => toViewPoint(p, layer, video))
        const at = (i: number) =>
          `${(pt[i].x * POSE_VB).toFixed(1)} ${(pt[i].y * POSE_VB).toFixed(1)}`
        const seen = (i: number) => pt[i] && pt[i].score >= MIN_KP

        for (const [a, b] of EDGES) {
          if (!seen(a) || !seen(b)) continue
          bones += `M${at(a)}L${at(b)}`
        }
        // 목 — 코와 두 어깨의 가운데를 잇는다. 고개 방향만 남긴다.
        if (seen(NOSE) && seen(L_SHOULDER) && seen(R_SHOULDER)) {
          const mx = ((pt[L_SHOULDER].x + pt[R_SHOULDER].x) / 2) * POSE_VB
          const my = ((pt[L_SHOULDER].y + pt[R_SHOULDER].y) / 2) * POSE_VB
          bones += `M${at(NOSE)}L${mx.toFixed(1)} ${my.toFixed(1)}`
        }
        // 길이 0 인 선은 둥근 끝 때문에 점으로 그려진다.
        for (let i = 0; i < pt.length; i += 1) {
          if (seen(i)) joints += `M${at(i)}L${at(i)}`
        }
      }
      return { bones, joints }
    }

    /**
     * 화면의 나머지 사람들 — 회색. 🔴 **누구인지 잇지 않는다.** 그래서 눅이기
     * 전에 "같은 사람의 연속된 두 장인가" 를 묻고, 아니면 그냥 새로 놓는다
     * (남의 자세에서 미끄러져 오면 팔다리가 화면을 가로지른다).
     */
    const drawOthers = (dt: number, layer: HTMLElement, video: HTMLVideoElement | null) => {
      const bone = otherBoneRef.current
      const joint = otherJointRef.current
      if (!bone || !joint) return

      const raw = othersRef.current
      const prev = shownOthersRef.current
      const smoothed = raw.map((pose, i) =>
        prev[i] && isSamePerson(prev[i], pose) ? smoothPose(prev[i], pose, dt) : pose,
      )
      shownOthersRef.current = smoothed

      const { bones, joints } = pathsFor(smoothed, layer, video)
      bone.setAttribute('d', bones)
      joint.setAttribute('d', joints)
    }

    /**
     * 🔴 뼈대는 **한 줄짜리 `d` 두 개**로 그린다. 관절 17개에 선 12개를
     * 각각의 요소로 두면 프레임마다 DOM 을 수십 번 만지게 된다 — 그럴 이유가
     * 없다. 하나는 뼈(선), 하나는 관절(길이 0 인 선 + 둥근 끝 = 점)이다.
     */
    const drawPose = (dt: number, layer: HTMLElement, video: HTMLVideoElement | null) => {
      const bone = boneRef.current
      const joint = jointRef.current
      const raw = poseRef.current
      if (!bone || !joint) return
      if (!raw) {
        bone.setAttribute('d', '')
        joint.setAttribute('d', '')
        return
      }

      const pose = smoothPose(shownPoseRef.current, raw, dt)
      shownPoseRef.current = pose
      const { bones, joints } = pathsFor([pose], layer, video)
      bone.setAttribute('d', bones)
      joint.setAttribute('d', joints)
    }

    raf = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(raf)
  }, [started, closing, subject])

  /** 영상을 고른다 — 아직 시작은 아니다. 판 안에서 먼저 보여 준다. */
  function pick(picked: File | undefined) {
    if (!picked) return
    setFile({ name: picked.name, url: URL.createObjectURL(picked) })
  }

  /** 영상도 종목도 갖췄는가 — 둘 다 있어야 시작할 수 있다. */
  const ready = Boolean(file && sport)

  /** 분석 시작 — 판이 물러나고 영상이 화면을 채운다. */
  function start() {
    if (!ready) return
    setClosing(false)
    setStarted(true)
    // 판은 물러나지 않는다 — **화면 폭까지 자란다**(CSS 의 --ss-shot-panel-w).
    // 🔴 **여기서 재생하지 않는다.** 다 자란 화면에서 먼저 분석할 사람을
    // 네모로 묶어야 하는데(사용자 요청), 움직이는 그림 위에 네모를 긋는 것은
    // 아무 의미가 없다. 재생은 대상이 정해지는 순간 시작한다(commit).
    wantPlayRef.current = false
    previewRef.current?.pause()
    setRect(null)
    setStep(0)
    setDone(false)
    later(() => setGrown(true), GROW_MS)
    later(() => setSideIn(true), SIDE_IN_MS)
  }

  /** 오버레이 위 한 점을 0~1 로 — 판 밖으로 끌어도 안쪽에 붙잡아 둔다. */
  function pointAt(e: React.PointerEvent) {
    const r = e.currentTarget.getBoundingClientRect()
    // 상자를 못 재면(레이아웃 전 · jsdom) 0 으로 떨어뜨린다 — 나누면 NaN 이
    // 나오고 그대로 style 에 실려 네모가 통째로 사라진다.
    if (!r.width || !r.height) return { x: 0, y: 0 }
    return {
      x: clamp01((e.clientX - r.left) / r.width),
      y: clamp01((e.clientY - r.top) / r.height),
    }
  }

  function togglePlay() {
    const video = previewRef.current
    if (!video) return
    // ⚠️ `?.catch` 다 — play() 가 프로미스를 안 돌려주는 환경이 있다(jsdom).
    if (video.paused) {
      wantPlayRef.current = true
      video.play()?.catch(() => {})
    } else {
      wantPlayRef.current = false
      video.pause()
    }
  }

  function seek(to: number) {
    const video = previewRef.current
    if (!video) return
    video.currentTime = to
    setTime(to)
  }

  function dragStart(e: React.PointerEvent<HTMLDivElement>) {
    // 🔴 **긋기 시작하면 영상을 세운다.** 움직이는 그림 위에 그은 네모는
    // 확정하는 순간의 프레임과 어긋나 있고, 그 어긋난 자리에서 무늬를 뜨면
    // 추적이 시작부터 엉뚱한 것을 붙든다.
    previewRef.current?.pause()
    // 🔴 포인터를 **붙잡는다**(setPointerCapture). 안 잡으면 판 밖으로 끌고
    // 나갔을 때 pointerup 이 다른 요소로 가서 네모가 끌린 채로 남는다.
    e.currentTarget.setPointerCapture(e.pointerId)
    const p = pointAt(e)
    dragFrom.current = p
    setRect({ x: p.x, y: p.y, w: 0, h: 0 })
  }

  function dragMove(e: React.PointerEvent<HTMLDivElement>) {
    const from = dragFrom.current
    if (!from) return
    const p = pointAt(e)
    // 어느 방향으로 끌든 같은 네모다 — 좌표를 정렬해 음수 폭을 없앤다.
    setRect({
      x: Math.min(from.x, p.x),
      y: Math.min(from.y, p.y),
      w: Math.abs(p.x - from.x),
      h: Math.abs(p.y - from.y),
    })
  }

  function dragEnd() {
    const box = rect
    dragFrom.current = null
    // 톡 누르기만 한 것은 네모가 아니다 — 지워서 '이 사람으로' 가 안 켜지게 한다.
    if (box && (box.w < MIN_BOX || box.h < MIN_BOX)) setRect(null)
  }

  /** 그린 네모로 확정한다 — 여기서부터 단계가 돌고 영상이 재생된다. */
  function commit(box: Box | null) {
    const el = pickRef.current
    const video = previewRef.current
    setSubject({
      // 화면 좌표가 아니라 **영상 그림 안** 좌표로 바꿔 둔다(toVideoBox 주석).
      box: box && el ? toVideoBox(box, el, video) : null,
      // 어느 시점의 프레임에서 골랐는가 — 에이전트가 그 프레임부터 따라간다.
      at: Math.round((video?.currentTime ?? 0) * 1000),
    })
    setRect(null)
    // ⚠️ `?.catch` 다 — `play()` 가 **프로미스를 안 돌려주는 환경**이 있다
    // (jsdom). 그냥 `.catch` 로 쓰면 거기서 TypeError 가 나고 그 아래 줄이
    // 통째로 안 돈다.
    wantPlayRef.current = true
    video?.play()?.catch(() => {})
  }

  /** 놓쳤을 때 — 영상을 세우고 묶는 판으로 돌아간다. 단계는 그대로 이어진다. */
  function repick() {
    wantPlayRef.current = false
    previewRef.current?.pause()
    setSubject(null)
    targetRef.current = null
    shownRef.current = null
    poseRef.current = null
    shownPoseRef.current = null
    setLost(false)
    setRect(null)
  }

  function reset() {
    // 1단계 — 판이 줄고, 비켜서 있던 배경 사진이 제자리로 돌아온다.
    // 영상은 그동안 미리 흐려진다(아래 closing 주석).
    setSideIn(false)
    setGrown(false)
    setClosing(true)
    // 🔴 따라가는 네모는 **기다리지 않고 바로** 지운다(사용자 요청). 판이
    // 줄어드는 동안 네모만 남아 있으면 무엇을 가리키는지 알 수 없다 — 영상은
    // 이미 흐려지는 중이고 대상도 더는 의미가 없다.
    targetRef.current = null
    shownRef.current = null
    setLost(false)
    // 2단계 — 다 줄어든 뒤에야 제목 · 설명 · 헤더가 다시 나타난다.
    // 🔴 `started` 를 여기서 끄는 것이 그 신호다. 같이 꺼 버리면 판이 줄기도
    // 전에 글자들이 되돌아와 두 동작이 겹친다.
    later(() => {
      setStarted(false)
      setClosing(false)
      setFile(null)
      setSubject(null)
      targetRef.current = null
      shownRef.current = null
      poseRef.current = null
      shownPoseRef.current = null
      setLost(false)
      setRect(null)
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
      // 종목을 골랐는가 — 안 골랐으면 안내 줄이 펴진다(globals.css).
      data-sport={sport ?? undefined}
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

            {/* 머리줄 오른쪽 — 종목 알약 셋과 닫기 점.

                🔴 **장식 점 둘은 없앴다**(사용자 요청). 창 틀 흉내로 세 개를
                뒀었는데 누를 수 있는 것은 빨간 것 하나뿐이라, 나머지 둘은
                자리만 먹으면서 "눌리는 것처럼" 보였다. 종목 알약이 그 자리를
                가져간다. */}
            <span className="ss-shot-bar-right">
              {/* 🔴 종목을 골라야 시작할 수 있다 — 위 SPORTS 주석 참고.
                  라디오가 아니라 `aria-pressed` 누름 버튼이다: 라디오는
                  화살표 키 이동까지 손으로 만들어야 하는데, 알약 셋에는
                  Tab 으로 하나씩 닿는 편이 오히려 예측 가능하다. */}
              <span className="ss-shot-sports" role="group" aria-label="종목">
                {SPORTS.map((s) => (
                  <button
                    key={s.key}
                    type="button"
                    className="ss-shot-sport"
                    aria-pressed={sport === s.key}
                    // 시작한 뒤에는 못 바꾼다 — 돌고 있는 분석의 루브릭을
                    // 도중에 갈아끼우는 셈이 된다. 고른 것은 그대로 보인다.
                    disabled={started}
                    onClick={() => setSport(s.key)}
                  >
                    <span className="material-symbols-outlined" aria-hidden="true">
                      {s.icon}
                    </span>
                    {s.label}
                  </button>
                ))}
              </span>

              {/* 🔴 닫기 점은 **진짜 버튼**이다. 창 틀의 닫기 자리이므로
                  시작한 뒤에도 그대로 있어야 한다 — 한때 시작하면 장식으로
                  돌려놨더니 "왜 사라지냐"는 말을 들었다. 영상이 있는 동안은
                  늘 누를 수 있고, 누르면 고르기 전으로 돌아간다.
                  영상이 없을 때 같은 크기의 흐린 점을 두는 것은 **자리를
                  지키기 위해서다** — 없애면 영상을 고르는 순간 종목 알약이
                  점 하나만큼 옆으로 튄다. */}
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
              <>
                <video
                  ref={previewRef}
                  src={file.url}
                  // 🔴 묶는 동안에는 **기본 컨트롤을 끈다.** 묶는 판이 그 위를
                  // 덮어 어차피 못 누르고, 우리 컨트롤과 둘이 겹쳐 보인다.
                  controls={!(started && !subject)}
                  playsInline
                  // 끝나면 처음부터 다시 — 사용자가 직접 세우기 전에는 멈추지
                  // 않는다(사용자 요청). 분석하는 내내 자리를 지켜야 하는 화면이라
                  // 마지막 프레임에서 굳어 있으면 멈춘 것처럼 보인다.
                  loop
                  aria-label={file.name}
                  /**
                   * 🔴 **문지기.** 묶는 동안 우리가 시키지 않은 재생이 시작되면
                   * 곧바로 도로 세운다(위 `wantPlayRef` 주석). 분석이 시작된
                   * 뒤에는 막지 않는다 — 그때는 그냥 재생 중인 영상이다.
                   */
                  onPlay={() => {
                    if (started && !subject && !wantPlayRef.current) {
                      previewRef.current?.pause()
                    }
                  }}
                />

                {/* 🔴 **분석할 사람을 끌어서 묶는 판.** 판이 다 자란 뒤에만
                    나온다(사용자 요청) — 작은 창 틀에서는 사람이 너무 작아
                    정확히 묶을 수가 없다. 파이프라인 순서와도 맞는다:
                    전처리 다음이 '자세 추적' 이고, 누구를 따라갈지가 그
                    앞에 와야 한다.

                    자리만 덮을 뿐 흐름에 없으므로(absolute) 붙였다 뗐다 해도
                    판의 키가 흔들리지 않는다. */}
                {/* 🔴 묶은 사람을 **정말로 따라가는** 네모. 판 자체는 자리만
                    덮고 클릭을 안 먹는다(pointer-events: none) — 영상의 재생
                    컨트롤이 그 아래 있다. 되살리는 것은 **잎사귀(버튼)에서만**
                    이다(홈 바닥줄 · 추천 판에서 세 번 데인 자리). */}
                {started && subject?.box && !trackFailed && !closing && (
                  <div
                    ref={trackRef}
                    className="ss-shot-track"
                    data-lost={lost ? 'true' : undefined}
                    aria-hidden="true"
                  >
                    {/* 🔴 관절 막대기. `preserveAspectRatio="none"` 로 고정
                        격자(1000×1000)를 상자에 늘려 맞추고, 선 굵기만
                        `vector-effect="non-scaling-stroke"` 로 그 늘림에서
                        빼낸다 — 안 그러면 가로세로 비율만큼 선이 찌그러진다.

                        관절점은 **길이 0 인 선**이다. 둥근 끝이 붙어 점으로
                        보이므로, 원을 17개 만들 것 없이 path 하나면 된다. */}
                    <svg
                      className="ss-shot-pose"
                      viewBox="0 0 1000 1000"
                      preserveAspectRatio="none"
                      aria-hidden="true"
                      focusable="false"
                    >
                      {/* 🔴 회색이 **먼저** 온다 — 초록이 그 위에 그려져야
                          겹쳐 선 사람들 사이에서 내 사람이 묻히지 않는다. */}
                      <path
                        ref={otherBoneRef}
                        className="ss-shot-bone ss-shot-bone-other"
                        vectorEffect="non-scaling-stroke"
                      />
                      <path
                        ref={otherJointRef}
                        className="ss-shot-joint ss-shot-joint-other"
                        vectorEffect="non-scaling-stroke"
                      />
                      <path ref={boneRef} className="ss-shot-bone" vectorEffect="non-scaling-stroke" />
                      <path ref={jointRef} className="ss-shot-joint" vectorEffect="non-scaling-stroke" />
                    </svg>

                    {/* 자리는 위의 rAF 가 직접 쓴다 — 초당 60번 바뀌는 값을
                        React 상태에 두면 그만큼 다시 그린다. */}
                    <div ref={boxRef} className="ss-shot-track-box">
                      <span className="ss-shot-track-tag">
                        {lost ? '놓쳤습니다' : '따라가는 중'}
                      </span>
                    </div>
                  </div>
                )}

                {started && !subject && (
                  <div
                    ref={pickRef}
                    className="ss-shot-pick"
                    onPointerDown={dragStart}
                    onPointerMove={dragMove}
                    onPointerUp={dragEnd}
                    onPointerCancel={dragEnd}
                  >
                    {rect && (
                      <div
                        className="ss-shot-pick-box"
                        style={{
                          left: `${rect.x * 100}%`,
                          top: `${rect.y * 100}%`,
                          width: `${rect.w * 100}%`,
                          height: `${rect.h * 100}%`,
                        }}
                      />
                    )}
                    {/* 무엇을 하라는 것인지 영상 위에도 적는다 — 오른쪽 판은
                        1.3초 뒤에야 떠오르고, 그 전에 사람은 이미 화면을 보고
                        있다. 네모를 긋기 시작하면 비켜 준다. */}
                    <p className="ss-shot-pick-lead" data-drawn={rect ? 'true' : undefined}>
                      분석할 사람을 끌어서 네모로 묶어 주세요
                    </p>

                    {/* 🔴 첫 프레임에 그 사람이 없을 수 있다(사용자 요청) —
                        돌려 보고 원하는 자리에서 세운 뒤 묶는다.

                        🔴 `stopPropagation` 이 **꼭 있어야 한다.** 이 줄은 묶는
                        판의 자식이라, 막대를 끄는 pointerdown 이 위로 올라가면
                        그 순간 네모가 그려지기 시작한다. */}
                    <div
                      className="ss-shot-scrub"
                      onPointerDown={(e) => e.stopPropagation()}
                    >
                      <button
                        type="button"
                        className="ss-shot-scrub-play"
                        aria-label={playing ? '멈춤' : '재생'}
                        onClick={togglePlay}
                      >
                        <span className="material-symbols-outlined" aria-hidden="true">
                          {playing ? 'pause' : 'play_arrow'}
                        </span>
                      </button>

                      {/* range 인 이유는 키보드다 — 화살표로 프레임을 옮길 수
                          있어야 끌 수 없는 사람도 자리를 고를 수 있다. */}
                      <input
                        className="ss-shot-scrub-bar"
                        type="range"
                        min={0}
                        max={duration || 0}
                        step={0.05}
                        value={Math.min(time, duration || 0)}
                        aria-label="영상 위치"
                        onChange={(e) => seek(Number(e.target.value))}
                      />

                      <span className="ss-shot-scrub-time">
                        {fmtTime(time)} / {fmtTime(duration)}
                      </span>
                    </div>
                  </div>
                )}
              </>
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

                {/* 🔴 **찍는 법을 여기서 말한다.** 세 가지 다 실제로 겪은 것이다 —
                    카메라가 따라 움직이면 화면이 통으로 흘러 그 사람을 놓치고,
                    몸이 잘리면 볼 관절이 없고, 비슷한 옷을 입은 사람이 옆에
                    있으면 헷갈린다. 올리기 전에 알아야 다시 안 찍는다.

                    떨구는 자리 안에 두는 이유: 영상을 고르면 같이 사라져야 하고,
                    위쪽 설명(`ss-shot-lead`)에 붙이면 그 상자의 상한(320px)을
                    넘겨 아랫줄이 조용히 잘린다. */}
                <ul className="ss-shot-tips">
                  {/* 🔴 줄표 앞이 **권하는 말**, 뒤가 그 까닭이다. 앞을 통째로
                      온전한 흰색으로 두어 눈이 권하는 말만 훑고 지나갈 수 있게
                      한다(사용자 요청) — 까닭은 궁금할 때만 읽으면 된다.

                      🔴 셋 다 "…면 좋습니다" 로 맞춘다(사용자 요청). "해
                      주세요 · 들어와야 합니다" 는 **안 지키면 못 올린다**는
                      말로 읽히는데, 실제로는 그런 영상도 받아서 분석한다 —
                      잘 나오는 조건을 알려 주는 것이지 조건을 거는 게 아니다.
                      고르는 것은 올리는 사람 몫으로 남긴다. */}
                  <li>
                    <b>카메라는 고정하면 좋습니다</b> — 따라 움직이면 놓치기 쉽습니다
                  </li>
                  <li>
                    <b>온몸이 화면 안에 들어오면 좋습니다</b> — 자세는 발끝까지 봅니다
                  </li>
                  <li>
                    <b>혼자 나올수록 좋습니다</b> — 여럿이면 비슷한 옷과 헷갈립니다
                  </li>
                </ul>
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
            disabled={!ready || grown}
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

        {/* 영상은 골랐는데 종목을 안 골랐을 때만 펴지는 한 줄.

            🔴 **시작 버튼 아래다**(사용자 요청). 위에 뒀더니 창 틀과 버튼
            사이에 끼어서 "지금 나온 줄도 몰랐다" — 눈은 누르려는 버튼에
            가 있는데 안내는 그 위에 있었다. 잠긴 버튼 바로 아래, 강조색으로,
            계속 깜빡인다.

            🔴 **늘 DOM 에 있다.** 시작 버튼과 같은 이유다 — 붙였다 뗐다 하면
            그 순간 판의 키가 확 바뀌어 안쪽 것들이 툭 떨어진다. 펴고 접는
            것은 CSS 가 한다(`[data-picked]:not([data-sport])`).

            🔴 접혀 있는 동안에는 **접근성 트리에서도 뺀다.** 키가 0 일 뿐
            `display:none` 이 아니라서, 안 빼면 종목을 이미 골랐는데도 화면
            낭독기가 "종목을 먼저 골라 주세요"를 계속 읽는다. */}
        <p className="ss-shot-hint" aria-hidden={file && !sport ? undefined : 'true'}>
          {/* 깜빡임은 **안쪽 글자**가 맡는다. 바깥 <p> 는 펴고 접는 일(키 ·
              여백 · 불투명도 전이)을 하는데, 같은 요소에 무한 애니메이션을
              걸면 그 전이를 애니메이션이 덮어써 펴질 때 툭 나타난다. */}
          <span>종목을 먼저 골라 주세요</span>
        </p>
      </aside>

      {/* ── 오른쪽 떠 있는 판 — 진행 · 리포트 · 대화 ────────────────── */}
      <aside className="ss-shot-side" aria-label="리포트와 대화">
        <header className="ss-shot-side-head">
          <h2>{done ? '리포트' : subject ? '보고 있습니다' : '분석할 사람'}</h2>
          <button type="button" className="ss-shot-again" onClick={reset}>
            다른 영상
          </button>
        </header>

        {/* 시작을 누르기 전에는 단계도 리포트도 그리지 않는다 — 판이 화면
            밖에 있더라도 아무 일도 없는 진행 표시가 DOM 에 남으면 안 된다.
            고르기만 한 단계에서는 아직 아무것도 안 하고 있다. */}
        {/* 놓쳤으면 말한다. 🔴 **분석을 멈추지는 않는다** — 에이전트도
            "검출 실패 프레임은 지표 계산에서 배제한다"(agent/README)로
            같은 자리를 다룬다. 멈추는 게 아니라 그 구간을 빼는 것이 맞다. */}
        {started && subject && (trackFailed || lost) && (
          <div className="ss-shot-lost" role="status">
            <span>
              {trackFailed
                ? '검출 모델을 불러오지 못해 따라가기만 꺼졌습니다. 분석은 그대로 진행됩니다.'
                : '잠깐 놓쳤습니다. 다시 잡히면 이어서 따라갑니다 — 그동안의 프레임은 빼고 봅니다.'}
            </span>
            {!trackFailed && (
              <button type="button" className="ss-shot-pick-auto" onClick={repick}>
                다시 묶기
              </button>
            )}
          </div>
        )}

        {started && (!subject ? (
          /* 🔴 **아직 아무것도 보지 않는다.** 누구를 볼지 정해지기 전에
             진행 단계를 그리면, 대상과 무관하게 분석이 이미 돌고 있는 것처럼
             읽힌다 — 그러면 네모를 왜 그려야 하는지가 사라진다. */
          <div className="ss-shot-pickside">
            <p>
              영상에서 <b>분석할 사람</b>을 끌어서 네모로 묶어 주세요. 그 사람만
              끝까지 따라가며 봅니다.
            </p>
            <p className="ss-shot-pickside-note">
              첫 화면에 안 보이면 <b>돌려 보다가</b> 원하는 자리에서 세우고 묶으면
              됩니다. 다시 끌면 새로 그려집니다.
            </p>

            <div className="ss-shot-pick-acts">
              <button
                type="button"
                className="ss-shot-pick-go"
                disabled={!rect}
                onClick={() => commit(rect)}
              >
                이 사람으로 분석
              </button>
              {/* 🔴 끌 수 없는 입력 장치(키보드만 쓰는 경우)의 **유일한 길**이다.
                  동시에 계약의 `side` 와 같은 규칙이기도 하다 — 지정을 생략하면
                  에이전트의 자동 판별을 쓴다. */}
              <button type="button" className="ss-shot-pick-auto" onClick={() => commit(null)}>
                자동으로 고르기
              </button>
            </div>
          </div>
        ) : done ? (
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
