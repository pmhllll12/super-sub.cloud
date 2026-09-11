'use client'

import { useEffect, useState } from 'react'
import type { MyVideo } from '@/server/backend'
import { SPORTS, SPORT_CODE, type SportKey } from '@/lib/sports'
import { checkClip, uploadClip, type ClipMeta } from '@/lib/uploadClip'
import { publish, unpublish } from '@/lib/published'
import { fetchReport, type ReportResult } from '@/lib/savedReports'
import { featuredOf, setFeatured } from '@/lib/featuredClip'
import { isDirectKey, usePlaybackUrls } from '@/lib/playbackUrl'
import ReportView from '@/components/analysis/ReportView'

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
 * 🔴 **사전 서명 주소가 생겨서 채웠다**(2026-09-08, 계약 3-6절
 * `GET /videos/{id}/playback-url` — 미결 paik 12번 해소). 그전에는 저장 키밖에
 * 없어서 진짜 백엔드에서는 null 을 돌려 **플레이어를 아예 안 그렸다**(키를
 * 그대로 `<video src>` 에 넣으면 403 과 깨진 플레이어가 뜬다).
 *
 * 🔴 주소는 **`usePlaybackUrls` 가 받아 온다** — 만료되는 값이라 컴포넌트가
 * 들고 있어야 다시 받을 수 있다. 여기서는 받아 둔 것을 꺼내기만 한다.
 * `/` 로 시작하는 키는 mock 이 주는 `public/` 경로라 그대로가 주소다.
 */
function previewSrc(v: MyVideo, urls: Record<string, string>): string | null {
  if (isDirectKey(v.storage_key)) return v.storage_key
  return urls[v.id] ?? null
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
  /**
   * 방금 지운 것. 목록의 정본은 서버가 준 `videos` 이고 여기서 다시 받아
   * 오지 않으므로, 지운 것을 이쪽에서 걸러 낸다 — 새로고침하면 서버 목록이
   * 이미 그것을 빼고 온다.
   */
  const [removed, setRemoved] = useState<string[]>([])
  /** 지울지 한 번 더 묻는 중인 영상 id. 되돌릴 수 없어서 곧바로 안 지운다. */
  const [confirming, setConfirming] = useState<string | null>(null)
  const [removing, setRemoving] = useState(false)
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
   * 🔴 **정본은 서버의 `is_public` 이다**(CCC 20) — 전에는 브라우저 저장소라
   * 다른 기기에서도 남에게도 안 보였다. 첫 값을 목록에서 뽑고 그 뒤로는 이
   * 화면이 들고 있는다(목록은 서버 컴포넌트가 준 prop 이라 다시 안 온다).
   *
   * 🔴 **그릴 때 읽어도 된다** — 저장소가 아니라 prop 이라 서버와 브라우저의
   * 첫 그림이 같다. effect 로 미뤄야 했던 이유가 사라졌다.
   */
  const [pubIds, setPubIds] = useState<string[]>(() =>
    videos.filter((v) => v.is_public).map((v) => v.id),
  )
  /** 공개 폼이 열린 영상 id 와 적고 있는 값. */
  const [form, setForm] = useState<{ id: string; title: string; what: string } | null>(null)

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

  const all = [...added, ...videos].filter((x) => !removed.includes(x.id))
  /**
   * 재생 주소 — 계약이 저장 키만 주므로 클립마다 사전 서명 주소를 따로 받는다
   * (`lib/playbackUrl.ts`). 목록이 바뀔 때만 다시 받는다.
   */
  const playbackUrls = usePlaybackUrls(all)
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

  /**
   * 이 영상의 분석 리포트 — 🔴 **서버에서 읽는다**(CCC 31, 미결 `paik` 7번).
   * 전에는 화면이 만든 자리 표시를 `localStorage` 에 둔 것이라 다른 기기에서는
   * 안 보였고, 애초에 진짜 분석 결과가 아니었다.
   *
   * 🔴 **영상이 바뀌면 다시 읽는다.** 늦게 온 응답이 새 영상의 리포트를
   * 덮지 않도록 `alive` 로 막는다 — 빠르게 넘기면 실제로 그렇게 엇갈린다.
   */
  /**
   * 🔴 **어느 영상의 리포트인지 함께 들고 있는다.** 그래야 영상을 넘길 때
   * 상태를 비우지 않아도 된다 — 비우는 일(effect 안의 즉시 setState)은
   * 렌더를 연쇄시킨다. id 가 다르면 그릴 때 없는 것으로 친다.
   */
  const [got, setGot] = useState<{ id: string; result: ReportResult } | null>(null)
  useEffect(() => {
    if (!v) return
    let alive = true
    void fetchReport(v.id).then((r) => {
      // 늦게 온 응답이 다른 영상의 자리에 앉지 않는다 — 빠르게 넘기면 실제로 엇갈린다.
      if (alive) setGot({ id: v.id, result: r })
    })
    return () => {
      alive = false
    }
  }, [v])
  const report = v && got?.id === v.id ? got.result : null

  /**
   * 나를 보여주는 **대표 영상**으로 세워 둔 클립의 id.
   *
   * 🔴 **정본은 서버의 `is_featured` 다**(CCC 27) — 전에는 `localStorage` 라
   * 다른 기기에서는 안 보였다. 첫 값을 목록에서 뽑고, 그 뒤로는 이 화면이
   * 들고 있는다(목록은 서버 컴포넌트가 준 prop 이라 다시 안 온다).
   *
   * 🔴 **그릴 때 읽어도 된다** — 저장소가 아니라 prop 이라 서버와 브라우저의
   * 첫 그림이 같다. 저장소를 읽던 때 effect 로 미뤄야 했던 이유가 사라졌다.
   */
  const [featured, setFeaturedId] = useState<string | null>(
    () => featuredOf(videos)?.id ?? null,
  )
  /** 대표를 바꾸다 실패한 사유 — 반려된 클립은 422 `CANNOT_FEATURE` 다. */
  const [featuredBusy, setFeaturedBusy] = useState(false)

  /**
   * 세우거나 푼다. 같은 영상을 다시 누르면 풀린다 — 대표는 하나뿐이다.
   *
   * 🔴 **서버가 바꾼 뒤에야 화면을 바꾼다.** 먼저 바꾸고 나중에 부르면,
   * 실패했을 때(반려된 클립 · 남의 클립) 세워진 것처럼 보이는데 실제로는
   * 아니다 — 지우기가 같은 이유로 같은 순서를 쓴다.
   * 🔴 **옛 대표를 따로 내리지 않는다.** 사람당 하나는 서버가 지킨다.
   */
  async function toggleFeatured(target: MyVideo) {
    if (featuredBusy) return
    setFeaturedBusy(true)
    setNotice(null)
    const on = featured === target.id
    try {
      await setFeatured(target.id, !on)
      setFeaturedId(on ? null : target.id)
    } catch (e) {
      setNotice(e instanceof Error ? e.message : '대표 영상을 바꾸지 못했습니다.')
    } finally {
      setFeaturedBusy(false)
    }
  }

  /**
   * 이 클립을 지운다 — **저장소의 영상과 그 분석 리포트까지.**
   *
   * 🔴 되돌릴 수 없어서 한 번 더 묻는다(`confirming`). `window.confirm` 을
   * 쓰지 않는다 — 이 사이트는 제 판을 그려 왔고, 그쪽은 시험에서도 못 누른다.
   *
   * 🔴 **서버가 지운 뒤에야 화면에서 뺀다.** 먼저 빼고 나중에 부르면, 실패한
   * 경우 사라진 것처럼 보이는데 실제로는 남아 있다.
   *
   * 🔴 아직 브라우저에만 있는 것들(공개 · 리포트)도 함께 거둔다 — 계약에
   * 자리가 없어 여기 남아 있는 값들이라(미결 paik 5·7번) 서버가 지워 주지
   * 못한다. **대표는 이제 여기 없다**(CCC 27) — 클립의 성질이라 클립이
   * 지워지면 서버에서 같이 없어진다.
   */
  async function removeVideo(target: MyVideo) {
    if (removing) return
    setRemoving(true)
    setNotice(null)
    try {
      const res = await fetch(`/api/videos/${encodeURIComponent(target.id)}`, {
        method: 'DELETE',
      })
      if (!res.ok) {
        const body: unknown = await res.json().catch(() => null)
        const msg =
          typeof body === 'object' && body !== null && 'error' in body
            ? ((body as { error?: { message?: string } }).error?.message ?? null)
            : null
        throw new Error(msg ?? '지우지 못했습니다.')
      }
      /* 🔴 **대표도 공개도 서버에 따로 지울 것이 없다** — 둘 다 클립의
         성질이라 클립이 사라지면서 같이 없어진다(CCC 20 · 27). 여기서
         `unpublish` 를 부르면 **방금 지운 영상에 PATCH 를 쏘게 되고** 404 다.
         화면에 남은 표시만 거둔다. */
      if (featured === target.id) setFeaturedId(null)
      setPubIds((prev) => prev.filter((id) => id !== target.id))
      /* 🔴 리포트도 따로 지울 것이 없다 — 서버에 있고 영상과 함께 사라진다
         (전에는 `localStorage` 라 여기서 손으로 지웠다). */
      setAdded((prev) => prev.filter((x) => x.id !== target.id))
      setRemoved((prev) => [...prev, target.id])
      setConfirming(null)
    } catch (e) {
      setNotice(e instanceof Error ? e.message : '지우지 못했습니다.')
    } finally {
      setRemoving(false)
    }
  }

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

  /**
   * 🔴 **서버가 바꾼 뒤에야 화면을 바꾼다.** 먼저 끄고 나중에 부르면, 실패한
   * 경우 비공개로 보이는데 실제로는 **남에게 계속 보인다** — 되돌릴 수 없는
   * 쪽으로 틀리는 것이라 지우기와 같은 순서를 쓴다.
   */
  async function togglePublish(target: MyVideo) {
    if (pubIds.includes(target.id)) {
      setNotice(null)
      try {
        await unpublish(target.id)
        setPubIds((prev) => prev.filter((x) => x !== target.id))
        setForm(null)
      } catch (e) {
        setNotice(e instanceof Error ? e.message : '공개를 풀지 못했습니다.')
      }
      return
    }
    // 켜는 것만으로는 안 올린다 — 제목이 있어야 영상 모음에서 이름이 생긴다.
    setForm({ id: target.id, title: '', what: '' })
  }

  async function savePublish(target: MyVideo) {
    if (!form || !form.title.trim()) return
    setNotice(null)
    try {
      /* 🔴 **공개와 제목을 한 번에 보낸다.** 나눠 보내면 그 사이에 끊겼을 때
         이름 없는 영상이 남에게 보인다. 재생 주소도 비율도 안 보낸다 —
         목록은 서버가 그리고, 재생은 `playback-url` 로 따로 받는다. */
      await publish(target.id, { title: form.title.trim(), description: form.what.trim() })
      setPubIds((prev) => [...prev, target.id])
      setForm(null)
    } catch (e) {
      setNotice(e instanceof Error ? e.message : '공개하지 못했습니다.')
    }
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
            {/* 🔴 **키가 고정된 자리다**(2026-09-08, 사용자 요청: "세로영상이든
                가로영상이든 단추 위치가 안 바뀌게"). 영상은 자기 비 그대로
                이 안에서 가운데 서고, 남는 자리는 비워 둔다 — 자리를 영상
                키에 맡기면 세로 영상에서 아래 것들이 통째로 64px 내려간다
                (실측). **영상을 늘리거나 자르지 않는다.**

                🔴 재생 주소가 없어도(배포에서 그렇다 — 미결 paik 12번) 이
                자리는 그대로 둔다. 비면 판이 접혀서 무엇이 잘못됐는지보다
                화면이 깨진 것처럼 보인다. */}
            <div className="ss-profile-video-slot">
            {previewSrc(v, playbackUrls) && (
              /* 🔴 `key` 를 영상 id 로 준다. 없으면 다음 영상으로 넘길 때 리액트가
                 같은 <video> 를 재사용해서 **src 만 갈리고 재생 위치 · 재생 중
                 여부가 그대로 남는다.** `preload="metadata"` 인 것도 그대로다 —
                 목록이 아니라 한 편만 그리지만, 넘길 때마다 본편을 받으면 낭비다. */
              <video
                key={v.id}
                className="ss-profile-video-player"
                src={previewSrc(v, playbackUrls) ?? undefined}
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
            </div>

          {/* ⚠️ 영상 아래 붙던 상자(종목 · 날짜 · 길이 · 상태 배지)는 걷어냈다
              (사용자 요청). 어떤 갈래인지는 **위 알약이 이미 말하고 있어서**
              같은 말을 두 번 하던 자리였다.

              🔴 반려 사유만 남긴다 — 그건 알약이 대신해 줄 수 없고, 없으면
              왜 안 됐는지 알 데가 사라진다. */}
          {v.reject_reason && <p className="ss-profile-video-reason">{v.reject_reason}</p>}

          {/* 🔴 **나를 보여주는 대표 영상**(사용자 요청, 2026-09-08). 영상
              오른쪽 아래 모서리에 붙는다 — 그 영상에 대한 일이라 영상에서
              멀어지면 무엇을 세우는 것인지 흐려진다.

              한 편만 세울 수 있다. 다른 영상에서 누르면 그쪽으로 옮겨 가고,
              같은 영상을 다시 누르면 풀린다 — 대표가 둘이면 어느 것이
              나를 보여주는지 정해지지 않는다.

              ⚠️ 반려된 클립에는 안 낸다 — 서버가 안 보는 영상이다. */}

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
                  {/* 🔴 **공개는 되돌릴 수 있지만 그 사이에 남이 본다.**
                      무엇이 일어나는지 누르기 전에 말한다(CCC 20 으로 서버에
                      올라가면서 이 문구가 「이 브라우저에만」에서 바뀌었다). */}
                  <p className="ss-profile-publish-note">
                    영상 모음에서 다른 사람에게도 보입니다 — 언제든 다시 내릴 수
                    있습니다.
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
              {/* 🔴 넘기는 줄과 **같은 줄**에 선다(사용자 지적) — 따로 두면
                  줄이 둘로 갈려 판이 그만큼 길어진다. 넘기는 단추는 가운데
                  그대로여야 하므로 이 단추만 흐름 밖으로 빼서 오른쪽에 건다.
                  ⚠️ 반려된 클립에는 안 낸다 — 서버가 안 보는 영상이다. */}
              {/* 🔴 **지우기는 줄의 왼쪽 끝**이다 — 대표 영상 단추와 마주 본다.
                  그 단추와 같은 이유로 흐름 밖으로 뺀다: 흐름에 두면 가운데
                  넘기는 단추가 그만큼 밀려 영상마다 자리가 갈린다.

                  ⚠️ 되돌릴 수 없는 단추가 화살표 바로 옆에 있으면 안 된다 —
                  그래서 반대쪽 끝이고, 누르면 한 번 더 묻는다. */}
              <span className="ss-profile-del">
                {confirming === v.id ? (
                  <>
                    <button
                      type="button"
                      className="ss-profile-del-btn"
                      data-armed="true"
                      disabled={removing}
                      onClick={() => removeVideo(v)}
                    >
                      {removing ? '지우는 중…' : '정말 지웁니다'}
                    </button>
                    <button
                      type="button"
                      className="ss-profile-del-btn"
                      disabled={removing}
                      onClick={() => setConfirming(null)}
                    >
                      취소
                    </button>
                  </>
                ) : (
                  <button
                    type="button"
                    className="ss-profile-del-btn"
                    onClick={() => setConfirming(v.id)}
                  >
                    <span className="material-symbols-outlined" aria-hidden="true">
                      delete
                    </span>
                    삭제
                  </button>
                )}
              </span>
              {v.passed && (
                <button
                  type="button"
                  className="ss-profile-featured-btn"
                  data-on={featured === v.id ? 'true' : undefined}
                  aria-pressed={featured === v.id}
                  onClick={() => toggleFeatured(v)}
                >
                  <span className="material-symbols-outlined" aria-hidden="true">
                    {featured === v.id ? 'stars' : 'star'}
                  </span>
                  나를 보여주는 대표 영상
                </button>
              )}
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

            {/* 상자 폭을 그대로 쓰는 흰 선 — `100%` 면 된다.

                🔴 **상자는 이제 영상 비를 안 따른다**(2026-09-08, 사용자 요청).
                세로 영상에서 줄이 좁아져 오른쪽 끝 단추가 가운데 화살표를
                덮었기 때문이다 — `globals.css` 의 `.ss-profile-video-frame`
                주석에 왜 뒤집었는지 적어 두었다.

                🔴 **비를 알기 전에는 감춘다.** 폭은 이제 안 틀리지만, 영상이
                아직 안 그려졌는데 선만 먼저 뜨면 허공에 그은 줄로 보인다. */}
            {/* 무엇에 쓰이는 값인지 밝힌다. 단추와 달리 이건 흐름 안에 둔다 —
                겹쳐 놓으면 넘기는 단추를 덮는다. */}
            {v.passed && featured === v.id && (
              <p className="ss-profile-featured-note">
                추천 판에서 나를 소개할 때 이 장면이 돕니다.
              </p>
            )}

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
                const src = previewSrc(sv, playbackUrls)
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

          {/* 🔴 **분석 리포트는 영상 목록 아래**다(사용자 요청, 2026-09-08).
              영상 분석 화면에서 `저장` 을 누른 것이 여기로 온다.

              🔴 **분석 갈래에서만** 낸다 — 그냥 올린 영상에는 리포트가 없다.
              그림은 분석 화면과 **같은 것**을 쓴다(`ReportView`) — 두 벌로
              두면 한쪽만 늙는다.

              🔴 **「아직」과 「없다」를 갈라 그린다**(미결 paik 7번의 「하지 말
              것」) — 분석 중인 클립에 빈 자리를 보이면 결과가 없는 것처럼
              읽힌다. */}
          {tab === 'analyzed' && report && (
            <section className="ss-profile-report" aria-label="분석 리포트">
              <h3 className="ss-profile-report-head">분석 리포트</h3>
              {report.state === 'ready' ? (
                <>
                  <ReportView report={report.report} />
                  <p className="ss-profile-report-note">{report.report.savedAt} 에 분석했습니다.</p>
                </>
              ) : (
                <p className="ss-profile-report-note" role="status">
                  {/* 🔴 **사유 문구를 서버에서 그대로 받아 쓰지 않는다.** 위
                      알림줄이 이미 같은 문장을 낼 수 있어(대표 세우기 실패 ·
                      지우기 실패) 같은 글이 화면에 둘이 뜬다 — 실제로 그렇게
                      겹쳤다. 여기는 리포트 자리라는 것이 드러나야 한다. */}
                  {report.state === 'not-ready'
                    ? '분석 중입니다 — 끝나면 여기에 나옵니다.'
                    : report.state === 'failed'
                      ? `분석에 실패했습니다 — ${report.reason}`
                      : report.state === 'missing'
                        ? '리포트를 찾을 수 없습니다.'
                        : '리포트를 읽지 못했습니다.'}
                </p>
              )}
            </section>
          )}
        </div>
      )}
    </>
  )
}
