'use client'

import { useEffect, useState } from 'react'
import type { MyVideo } from '@/server/backend'
import { SPORTS, SPORT_CODE, type SportKey } from '@/lib/sports'
import { checkClip, uploadClip, type ClipMeta } from '@/lib/uploadClip'
import { listPublished, publish, unpublish } from '@/lib/published'

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

  /**
   * 이 화면에서 방금 올린 것. ⚠️ **새로고침하면 사라진다** — 목록은 서버가 주는
   * 것이고(`listMyVideos`) 여기서 다시 받아 오지 않는다. 올린 직후에 목록에
   * 안 나타나면 올라간 건지 알 수가 없어서 앞에 얹어 둔다.
   */
  const [added, setAdded] = useState<MyVideo[]>([])
  /** 고른 파일. 크기를 재기 전에는 아직 못 올린다. */
  const [picked, setPicked] = useState<File | null>(null)
  const [pickedUrl, setPickedUrl] = useState<string | null>(null)
  const [meta, setMeta] = useState<ClipMeta | null>(null)
  /** 거른 사유 · 반려 사유 · 실패 사유가 다 여기로 나온다. */
  const [notice, setNotice] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  /**
   * 공개로 돌린 영상들.
   *
   * 🔴 `listPublished()` 를 그릴 때 부르지 않는다 — 저장소는 서버에 없으므로
   * 서버가 그린 첫 화면과 브라우저가 그린 것이 갈려 하이드레이션이 깨진다.
   * 붙은 **뒤에** 한 번 읽는다.
   */
  const [pubIds, setPubIds] = useState<string[]>([])
  /** 공개 폼이 열린 영상 id 와 적고 있는 값. */
  const [form, setForm] = useState<{ id: string; title: string; what: string } | null>(null)

  // eslint-disable-next-line react-hooks/set-state-in-effect -- 위 주석 참고: 붙은 뒤에 읽어야 한다.
  useEffect(() => setPubIds(listPublished().map((c) => c.id)), [])

  useEffect(() => {
    if (!picked) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- 주소는 파일에서 만들어야 하고, 만든 것은 정리에서 거둬야 한다.
      setPickedUrl(null)
      return
    }
    // jsdom 에는 없다 — 없으면 미리보기만 없고 재는 일은 그대로 돈다.
    let url: string | null = null
    try {
      url = URL.createObjectURL(picked)
    } catch {
      url = null
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect -- 위와 같다.
    setPickedUrl(url)
    return () => {
      if (url) URL.revokeObjectURL(url)
    }
  }, [picked])

  const all = [...added, ...videos]
  const analyzed = all.filter((v) => v.analysis_job_id !== null)
  const uploaded = all.filter((v) => v.analysis_job_id === null)

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

  /**
   * 파일을 골랐다. 🔴 **형식·용량은 여기서 막는다** — 그 둘은 `upload-url` 이
   * 422 로 튕겨 아무 데도 안 남는다. 길이·해상도는 반대로 서버가 반려 사유로
   * 남겨야 하는 것이라(SFR-001) 여기서 가로채지 않는다.
   */
  function onPick(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0] ?? null
    // 🔴 같은 파일을 다시 골라도 change 가 오게 비운다. 안 그러면 반려된 영상을
    // 고쳐서 다시 고를 때 아무 일도 안 일어난다.
    e.target.value = ''
    setNotice(null)
    setMeta(null)
    if (!f) return
    const bad = checkClip(f)
    if (bad) {
      setPicked(null)
      setNotice(bad)
      return
    }
    setPicked(f)
  }

  async function send(sport: SportKey) {
    if (!picked || !meta || busy) return
    setBusy(true)
    setNotice(null)
    try {
      const saved = await uploadClip({
        file: picked,
        sportCode: SPORT_CODE[sport],
        meta,
        analyze: false,
      })
      setAdded((prev) => [saved, ...prev])
      setPicked(null)
      setMeta(null)
      if (!saved.passed) {
        setNotice(saved.reject_reason ?? '규격에 맞지 않아 반려됐습니다.')
      } else {
        /* 🔴 **보낸 뜻이 아니라 돌아온 응답을 믿는다.** 계약이 아직 `analyze` 를
           모르므로 백엔드가 그것을 무시하고 분석을 걸 수 있다 — 그러면
           `analysis_job_id` 가 채워져 오고, 그때는 「분석 영상」이 사실이다. */
        setTab(saved.analysis_job_id === null ? 'uploaded' : 'analyzed')
        setAt(0)
      }
    } catch (err) {
      setNotice(err instanceof Error ? err.message : '올리지 못했습니다.')
    } finally {
      setBusy(false)
    }
  }

  function togglePublish(target: MyVideo) {
    if (pubIds.includes(target.id)) {
      unpublish(target.id)
      setPubIds((prev) => prev.filter((x) => x !== target.id))
      setForm(null)
      return
    }
    // 켜는 것만으로는 안 올린다 — 제목이 있어야 영상 모음에서 이름이 생긴다.
    setForm({ id: target.id, title: '', what: '' })
  }

  function savePublish(target: MyVideo) {
    if (!form || !form.title.trim()) return
    publish({
      id: target.id,
      title: form.title.trim(),
      what: form.what.trim(),
      /* 조회용 주소가 없어(계약 3-6절 "아직 없는 것") 실제 백엔드가 준 키는
         영상 모음에서도 안 틀린다 — `previewSrc` 와 같은 한계다. */
      src: previewSrc(target) ?? target.storage_key,
      aspect: ratio ? `${ratio} / 1` : '16 / 9',
      at: target.created_at.slice(0, 10),
    })
    setPubIds((prev) => [...prev, target.id])
    setForm(null)
  }

  return (
    <>
      <div className="ss-profile-tabrow">
      <div className="ss-profile-tabs" role="tablist" aria-label="내 영상">
        {/* 🔴 편수를 **안 적는다**(사용자 요청). 몇 편인지는 영상 아래 `1 / N`
            이 이미 말하고 있어서 같은 말이 두 곳에 있던 자리다. */}
        {(
          [
            ['analyzed', '분석 영상'],
            ['uploaded', '업로드 영상'],
          ] as const
        ).map(([key, label]) => (
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
          </button>
        ))}
      </div>

      {/* 🔴 `accept` 는 **힌트일 뿐**이다 — 파일 고르기 창에서 거름망을 "모든
          파일" 로 바꾸면 무엇이든 들어온다. 진짜 관문은 `checkClip` 이다. */}
      <label className="ss-profile-upload" data-busy={busy ? 'true' : undefined}>
        <input
          type="file"
          accept="video/*"
          aria-label="올릴 영상"
          disabled={busy}
          onChange={onPick}
        />
        <span className="material-symbols-outlined" aria-hidden="true">
          upload
        </span>
        업로드
      </label>
      </div>

      {/* 올리는 중에 무슨 일이 있었는지 — 거른 사유 · 반려 사유 · 실패 사유. */}
      {notice && (
        <p className="ss-profile-notice" role="alert">
          {notice}
        </p>
      )}

      {picked && (
        <div className="ss-profile-picked">
          {/* 🔴 크기를 재려고 둔다. 서버가 다시 재려면 원본을 받아야 하고 그러면
              PER-002 가 무너진다 — 잰 값을 우리가 실어 보낸다(계약 3-6절). */}
          <video
            data-picked="true"
            className="ss-profile-picked-preview"
            src={pickedUrl ?? undefined}
            muted
            playsInline
            preload="metadata"
            onLoadedMetadata={(e) => {
              const el = e.currentTarget
              setMeta({
                duration_ms: Math.round((el.duration || 0) * 1000),
                width: el.videoWidth || 0,
                height: el.videoHeight || 0,
              })
            }}
          />
          <div className="ss-profile-picked-ask">
            <p className="ss-profile-picked-name">{picked.name}</p>
            {/* 🔴 기본값을 축구로 박아 두면 야구 영상이 축구 루브릭으로 조용히
                채점된다 — 고르는 순간 올라간다. */}
            <span className="ss-shot-sports" role="group" aria-label="종목">
              {SPORTS.map((sp) => (
                <button
                  key={sp.key}
                  type="button"
                  className="ss-shot-sport"
                  disabled={!meta || busy}
                  onClick={() => send(sp.key)}
                >
                  <span className="material-symbols-outlined" aria-hidden="true">
                    {sp.icon}
                  </span>
                  {sp.label}
                </button>
              ))}
            </span>
            <p className="ss-profile-picked-hint">
              {busy ? '올리는 중입니다…' : '종목을 고르면 올라갑니다.'}
            </p>
          </div>
        </div>
      )}

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

          {/* 🔴 **업로드 갈래에서만** 낸다. 분석을 건 영상은 리포트를 보려고 올린
              것이고, 영상 모음은 올린 장면을 훑는 자리다 — 성격이 다르다. */}
          {tab === 'uploaded' && (
            <div className="ss-profile-publish">
              <button
                type="button"
                className="ss-profile-publish-toggle"
                data-on={pubIds.includes(v.id) ? 'true' : undefined}
                aria-pressed={pubIds.includes(v.id)}
                onClick={() => togglePublish(v)}
              >
                <span className="material-symbols-outlined" aria-hidden="true">
                  {pubIds.includes(v.id) ? 'visibility' : 'visibility_off'}
                </span>
                {pubIds.includes(v.id) ? '공개 중' : '공개'}
              </button>

              {form?.id === v.id && (
                <div className="ss-profile-publish-form">
                  <label htmlFor="ss-pub-title">제목</label>
                  <input
                    id="ss-pub-title"
                    value={form.title}
                    maxLength={40}
                    onChange={(e) => setForm({ ...form, title: e.target.value })}
                  />
                  <label htmlFor="ss-pub-what">한 줄 설명</label>
                  <input
                    id="ss-pub-what"
                    value={form.what}
                    maxLength={60}
                    onChange={(e) => setForm({ ...form, what: e.target.value })}
                  />
                  {/* ⚠️ 서버에 공개 여부를 둘 자리가 아직 없다(미결). 그것을
                      숨기면 다른 기기에서 안 보일 때 고장으로 읽힌다. */}
                  <p className="ss-profile-publish-note">
                    아직 이 브라우저에만 남습니다 — 다른 기기나 다른 사람에게는 보이지
                    않습니다.
                  </p>
                  <button
                    type="button"
                    className="ss-profile-publish-save"
                    disabled={!form.title.trim()}
                    onClick={() => savePublish(v)}
                  >
                    공개하기
                  </button>
                </div>
              )}
            </div>
          )}

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
