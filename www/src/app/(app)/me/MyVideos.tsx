'use client'

import { useState } from 'react'
import type { MyVideo } from '@/server/backend'

/**
 * 내가 올린 클립 — **두 갈래로 갈라 한 번에 한 편만** 보여준다(사용자 요청).
 *
 *   분석 영상  — 분석을 걸어 둔 것(영상 분석 화면에서 저장한 클립)
 *   업로드 영상 — 분석 없이 올리기만 한 것
 *
 * 🔴 가르는 기준은 **분석 작업이 걸렸는가**(`analysis_job_id`)다. 상태
 * (`analysis_status`)로 가르면 분석을 걸었지만 아직 대기 중인 클립이
 * "그냥 올린 것" 쪽으로 새어 나간다.
 *
 * 🔴 규격에 걸려 반려된 클립은 **분석을 아예 하지 않으므로**(계약 3-6절)
 * 업로드 쪽에 남는다 — 작업이 없는 것이 사실이고, 그 자리에서 반려 사유를
 * 보는 것이 사용자에게도 맞다.
 */

/** 클립 한 줄이 어떤 상태인가 — 알약 아래 배지로 나온다. */
function videoState(v: MyVideo): { key: string; label: string } {
  // 🔴 반려를 먼저 본다. 반려된 클립은 분석 작업이 없어 `analysis_status` 가
  // null 인데, 분석을 안 건 클립도 null 이라 순서를 바꾸면 둘이 섞인다.
  if (!v.passed) return { key: 'rejected', label: '규격 반려' }
  switch (v.analysis_status) {
    case 'succeeded':
      return { key: 'analyzed', label: '분석 완료' }
    case 'queued':
    case 'running':
      return { key: 'running', label: '분석 중' }
    case 'failed':
      return { key: 'failed', label: '분석 실패' }
    default:
      return { key: 'raw', label: '분석 안 함' }
  }
}

/**
 * 이 클립을 화면에서 **틀어 볼 수 있는가.**
 *
 * 🔴 계약이 주는 것은 저장 키뿐이고 **조회용 주소가 아직 없다**(3-6절
 * "아직 없는 것"). 그래서 `/` 로 시작하는 키 — 지금은 mock 이 넣어 준
 * `public/` 의 목업 영상 — 만 그대로 재생하고, 진짜 백엔드가 주는
 * `videos/<user_id>/<uuid>.mp4` 는 null 을 돌려 그림 없이 메타만 그린다.
 *
 * 조회용 사전 서명 URL 이 생기면 **이 함수 하나만** 고치면 된다.
 */
function previewSrc(v: MyVideo): string | null {
  return v.storage_key.startsWith('/') ? v.storage_key : null
}

type TabKey = 'analyzed' | 'uploaded'

export default function MyVideos({ videos }: { videos: MyVideo[] }) {
  /**
   * 지금 영상의 가로세로 비. **선을 영상 폭에 맞추려고** 잰다(사용자 요청).
   *
   * 🔴 `object-fit: contain` 만으로는 안 된다 — 자르지는 않지만 **요소 폭은
   * 칸 폭 그대로**라, 세로 영상이면 검은 여백까지 선이 뻗는다. 비를 알아야
   * 상자 자체를 영상 크기로 좁힐 수 있고, 그러면 선은 `100%` 로 따라온다.
   *
   * 🔴 영상이 바뀌어도 **곧바로 지우지 않는다.** 새 비가 올 때까지 이전
   * 값으로 그리다가 옮겨 가므로 선이 부드럽게 늘어난다 — 0 으로 되돌리면
   * 한 번 접혔다 펴진다.
   */
  const [ratio, setRatio] = useState<number | null>(null)

  /**
   * 재생 막대를 보여줄 것인가 — **가져다 댔을 때만**(사용자 요청).
   *
   * 🔴 `controls` 를 늘 켜 두면 멈춰 있는 동안 막대가 영상 아래를 덮은 채로
   * 남는다(브라우저는 재생 중일 때만 스스로 감춘다). 속성 자체를 껐다 켠다.
   *
   * 🔴 포커스에도 켠다. 막대가 없으면 키보드로는 재생에 닿을 길이 아예
   * 없어서, 마우스에만 매달면 그 사람은 영상을 못 튼다.
   */
  const [showControls, setShowControls] = useState(false)

  const analyzed = videos.filter((v) => v.analysis_job_id !== null)
  const uploaded = videos.filter((v) => v.analysis_job_id === null)

  const [tab, setTab] = useState<TabKey>(analyzed.length > 0 ? 'analyzed' : 'uploaded')
  const [at, setAt] = useState(0)

  const shown = tab === 'analyzed' ? analyzed : uploaded
  // 🔴 자리를 상태로 들고 있으므로 목록이 짧은 갈래로 옮겨 가면 넘칠 수 있다.
  // 그릴 때 여기서 한 번 잡는다 — 탭을 누를 때만 0 으로 되돌리면, 목록 자체가
  // 줄어드는 경우(다시 받아 온 뒤)를 놓친다.
  const i = Math.min(at, Math.max(shown.length - 1, 0))
  const v = shown[i]

  function pick(next: TabKey) {
    setTab(next)
    setAt(0)
  }

  function step(delta: number) {
    setAt((prev) => {
      const n = shown.length
      if (n === 0) return 0
      // 끝에서 반대쪽으로 돈다 — 목록이 짧아 끝이 금방 온다.
      return (Math.min(prev, n - 1) + delta + n) % n
    })
  }

  return (
    <>
      <div className="ss-profile-tabs" role="tablist" aria-label="내 영상">
        {(
          [
            ['analyzed', '분석 영상', analyzed.length],
            ['uploaded', '업로드 영상', uploaded.length],
          ] as const
        ).map(([key, label, count]) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={tab === key}
            className="ss-profile-tab"
            data-on={tab === key}
            onClick={() => pick(key)}
          >
            {label}
            <span className="ss-profile-tab-count">{count}</span>
          </button>
        ))}
      </div>

      {!v ? (
        <p className="ss-profile-muted">
          {tab === 'analyzed'
            ? '아직 분석한 영상이 없습니다.'
            : '아직 업로드한 영상이 없습니다.'}
        </p>
      ) : (
        <div className="ss-profile-video" data-state={videoState(v).key}>
          <div
            className="ss-profile-video-frame"
            style={{ '--ss-video-r': ratio ?? 16 / 9 } as React.CSSProperties}
          >
            {previewSrc(v) && (
              /* 🔴 `key` 를 영상 id 로 준다. 없으면 다음 영상으로 넘길 때 리액트가
                 같은 <video> 를 재사용해서 **src 만 갈리고 재생 위치 · 재생 중
                 여부가 그대로 남는다.** `preload="metadata"` 인 것도 그대로다 —
                 목록이 아니라 한 편만 그리지만, 넘길 때마다 본편을 받으면 낭비다. */
              <video
                key={v.id}
                className="ss-profile-video-player"
                src={previewSrc(v) ?? undefined}
                controls={showControls}
                muted
                playsInline
                preload="metadata"
                /* 🔴 막대를 켜고 끄는 신호는 **영상 자신만** 듣는다.
                   ⚠️ 상자(frame)에서 들었다가 두 번 데였다: 아래 넘기는 줄에
                   손만 얹어도 떴고, 그 줄의 단추를 누르면 **단추가 받은
                   포커스**가 상자까지 올라와 또 떴다(React 의 onFocus 는
                   자식에서도 올라온다).
                   🔴 `tabIndex` 를 주는 이유 — 막대가 없는 `<video>` 는 포커스를
                   못 받아서, 없으면 키보드만 쓰는 사람은 재생에 닿을 길이
                   아예 없다. */
                tabIndex={0}
                onMouseEnter={() => setShowControls(true)}
                onMouseLeave={() => setShowControls(false)}
                onFocus={() => setShowControls(true)}
                onBlur={() => setShowControls(false)}
                onLoadedMetadata={(e) => {
                  const el = e.currentTarget
                  if (el.videoWidth && el.videoHeight) setRatio(el.videoWidth / el.videoHeight)
                }}
              />
            )}

          {/* ⚠️ 영상 아래 붙던 상자(종목 · 날짜 · 길이 · 상태 배지)는 걷어냈다
              (사용자 요청). 어떤 갈래인지는 **위 알약이 이미 말하고 있어서**
              같은 말을 두 번 하던 자리였다.

              🔴 반려 사유만 남긴다 — 그건 알약이 대신해 줄 수 없고, 없으면
              왜 안 됐는지 알 데가 사라진다. */}
          {v.reject_reason && <p className="ss-profile-video-reason">{v.reject_reason}</p>}

            {/* 🔴 **한 편뿐이어도 그린다**(사용자 요청) — `1 / 1` 이 보여야 갈래
                안에 몇 편이 있는지 알 수 있고, 갈래를 바꿔도 줄이 사라졌다
                나타나지 않는다. 다만 넘길 데가 없으므로 두 단추는 잠근다. */}
            <div className="ss-profile-video-nav">
              <button
                type="button"
                className="ss-profile-step"
                onClick={() => step(-1)}
                disabled={shown.length < 2}
                aria-label="이전 영상"
              >
                <span className="material-symbols-outlined" aria-hidden="true">
                  chevron_left
                </span>
              </button>
              <span className="ss-profile-video-count">
                {i + 1} / {shown.length}
              </span>
              <button
                type="button"
                className="ss-profile-step"
                onClick={() => step(1)}
                disabled={shown.length < 2}
                aria-label="다음 영상"
              >
                <span className="material-symbols-outlined" aria-hidden="true">
                  chevron_right
                </span>
              </button>
            </div>

            {/* 영상 폭에 맞춰 늘었다 줄었다 하는 흰 선(사용자 요청). 상자가
                이미 영상 크기라 `100%` 면 된다 — 폭을 다시 계산하지 않는다.

                🔴 **비를 알기 전에는 감춘다.** 그전에는 상자가 기본값(16:9)
                이라, 세로 영상이면 선이 영상보다 넓게 그어진 채로 한 박자
                보였다가 줄어든다(실측). 폭이 맞을 때만 나타나게 한다. */}
            <span
              className="ss-profile-video-rule"
              data-ready={ratio !== null}
              aria-hidden="true"
            />
          </div>

          {/* 🔴 선 아래의 **가로로 굴리는 목록**(사용자 요청). 넘기는 단추가
              한 편씩 앞뒤로만 가는 데 비해, 여기서는 보고 싶은 것을 바로
              고른다. 한 편뿐이어도 그린다 — 갈래를 오갈 때 이 줄이 생겼다
              없어지면 아래 것들이 그때마다 들썩인다. */}
          {
            <ul className="ss-profile-strip">
              {shown.map((sv, idx) => {
                const src = previewSrc(sv)
                return (
                  <li key={sv.id}>
                    <button
                      type="button"
                      className="ss-profile-strip-item"
                      data-on={idx === i}
                      aria-current={idx === i ? 'true' : undefined}
                      aria-label={`${idx + 1}번째 영상`}
                      onClick={() => setAt(idx)}
                    >
                      {src ? (
                        /* 🔴 소리를 끄고 메타데이터만 받는다 — 목록에 여럿이
                           놓이므로 본편까지 받으면 이 줄 하나로 수십 MB 가
                           나간다. 첫 프레임만 표지로 쓴다. */
                        <video src={src} muted playsInline preload="metadata" />
                      ) : (
                        /* 조회용 주소가 없는 클립(실물 백엔드) — 순서만 적는다. */
                        <span className="ss-profile-strip-blank">{idx + 1}</span>
                      )}
                    </button>
                  </li>
                )
              })}
            </ul>
          }
        </div>
      )}
    </>
  )
}
