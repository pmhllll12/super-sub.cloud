'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { apiErrorMessage, apiPost } from '@/lib/api/client'
import PillButton from '@/components/ui/PillButton'
import type { PlayerCard } from '@/server/backend'
import CardMark, { MARKS } from '@/components/CardMark'
import { useCardStyle } from './cardStyle'

/**
 * 선 아래의 카드 편집기.
 *
 * ⚠️ **지금 바꿀 수 있는 것이 거의 없다.** 계약에 카드를 고치는 경로가 없고
 * (`POST /me/card` 는 **만들기**뿐이다), 카드에 보이는 별명 · 인물은 화면의
 * 붙박이다 — 서버가 주는 값이 아니다(`PlayerCardView` 주석). 호칭은 분석
 * 결과로 붙어서 사람이 고를 수 있는 것도 아니다.
 *
 * 그래서 이 자리는 지금 **둘로 갈린다**:
 *   카드가 없으면 → 만들기 (미결 jin-7 이 요청한 자리)
 *   카드가 있으면 → 꾸미개
 *
 * ⚠️ 한때 여기에 "카드에 담긴 것"(공유 주소 · 호칭)도 함께 뒀다가 걷어냈다
 * (사용자 요청) — 편집기는 **고치는 자리**이지 읽는 자리가 아니고, 호칭은
 * 왼쪽 `정보` 절에 이미 있다.
 */
export default function CardEditor({ card }: { card: PlayerCard | null }) {
  const router = useRouter()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function make() {
    setError(null)
    setBusy(true)
    try {
      /* 🔴 멱등이라 여러 번 눌러도 카드는 하나고 슬러그도 그대로다 —
         재시도해도 이미 공유한 주소가 죽지 않는다(계약 3장). */
      await apiPost('/api/me/card', {})
      router.refresh()
    } catch (e) {
      setError(apiErrorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  if (!card) {
    return (
      <div className="ss-profile-editor">
        <h2 className="ss-profile-h">선수 카드 만들기</h2>
        {/* 🔴 **분석을 기다릴 필요가 없다**는 것이 이 문장의 요점이다.
            카드는 부탁하면 바로 생기고(계약 3장), 분석이 붙이는 것은 카드가
            아니라 호칭이다. */}
        <p className="ss-profile-muted">
          지금 바로 만들 수 있습니다 — 분석을 기다리지 않아도 됩니다. 만들면 공유할 수 있는
          주소가 생기고, 호칭은 나중에 경기 영상이 분석되면 카드에 붙습니다.
        </p>
        {error && (
          <p role="alert" className="ss-profile-video-reason">
            {error}
          </p>
        )}
        <PillButton type="button" onClick={make} disabled={busy} className="self-start">
          카드 만들기
        </PillButton>
      </div>
    )
  }

  return <CardTools />
}

/** 꾸미개의 갈래. 한 번에 **하나만** 편다. */
const TOOLS = [
  { key: 'card', label: '카드' },
  { key: 'photo', label: '사진' },
  { key: 'brush', label: '붓' },
] as const

type Tool = (typeof TOOLS)[number]['key']

/**
 * 🔴 설정을 갈래로 나눠 **고른 것만** 편다(사용자 요청). 한 화면에 다 쌓았더니
 * 아래로 길어져 판을 넘쳤고, 무엇이 무엇에 딸린 설정인지도 흐렸다.
 */
function CardTools() {
  const [tool, setTool] = useState<Tool>('card')

  return (
    <div className="ss-profile-editor">
      <div className="ss-profile-tabs" role="tablist" aria-label="카드 꾸미기">
        {TOOLS.map((t) => (
          <button
            key={t.key}
            type="button"
            role="tab"
            aria-selected={tool === t.key}
            className="ss-profile-tab"
            data-on={tool === t.key}
            onClick={() => setTool(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tool === 'card' && <CardLooks />}
      {tool === 'photo' && <CardPhoto />}
      {tool === 'brush' && <CardBrushTool />}
    </div>
  )
}

/** 색 하나를 고르는 줄 — 이름표 · 색판 · 값. */
function ColorRow({
  label,
  value,
  onChange,
}: {
  label: string
  value: string
  onChange: (v: string) => void
}) {
  return (
    <div className="ss-profile-info-row">
      <dt className="ss-profile-info-label">{label}</dt>
      <dd className="ss-profile-info-value">
        <label className="ss-card-color">
          {/* 🔴 색 고르개는 브라우저 것을 쓴다. 직접 만들면 화면 하나에
              고르개가 또 생기고, 손·키보드·모바일을 다 다시 다뤄야 한다. */}
          <input
            type="color"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            aria-label={label}
          />
          <span className="ss-card-color-hex">{value.toUpperCase()}</span>
        </label>
      </dd>
    </div>
  )
}

/** 1단계 — 바탕 · 로고 · 글자와 그 색. 사진 · 붓은 다음 단계다. */
function CardLooks() {
  const { style, set, reset, save } = useCardStyle()
  /** 방금 저장했는가 — `null` 이면 아직 아무 말도 안 한다. */
  const [savedOk, setSavedOk] = useState<boolean | null>(null)
  return (
    <div className="ss-card-looks">
      <dl>
        <ColorRow label="카드 바탕" value={style.bg} onChange={(v) => set({ bg: v })} />
        <ColorRow label="로고 색" value={style.logo} onChange={(v) => set({ logo: v })} />

        <div className="ss-profile-info-row">
          <dt className="ss-profile-info-label">글자</dt>
          <dd className="ss-profile-info-value">
            <input
              type="text"
              className="ss-card-text-input"
              value={style.text}
              maxLength={24}
              placeholder="비우면 글자 없이"
              aria-label="카드에 넣을 글자"
              onChange={(e) => set({ text: e.target.value })}
            />
          </dd>
        </div>

        <ColorRow
          label="글자 색"
          value={style.textColor}
          onChange={(v) => set({ textColor: v })}
        />
      </dl>

      {/* 🔴 **초기화는 화면의 값만** 되돌린다. 담아 둔 것까지 지우면 되돌리기가
          곧 삭제가 되어 무섭게 쓰인다 — 되돌린 뒤 저장을 눌러야 저장본도 바뀐다. */}
      <div className="ss-card-actions">
        <button type="button" className="ss-profile-tab" onClick={reset}>
          초기화
        </button>
        <button
          type="button"
          className="ss-profile-tab"
          data-on="true"
          onClick={() => setSavedOk(save())}
        >
          저장
        </button>
      </div>

      {/* ⚠️ 서버가 아니라 이 브라우저에 담긴다는 것을 숨기지 않는다 — 다른
          기기에서 안 보일 때 고장으로 읽힌다(계약에 필드가 없다, 미결 paik 3번). */}
      {savedOk === true && (
        <p className="ss-profile-publish-note" role="status">
          저장했습니다 — 아직 이 브라우저에만 담깁니다. 공개 카드 링크에는 반영되지
          않습니다.
        </p>
      )}
      {savedOk === false && (
        <p className="ss-profile-video-reason" role="alert">
          저장하지 못했습니다. 올린 사진이 너무 크면 담을 자리가 모자랍니다.
        </p>
      )}
    </div>
  )
}

/** 값 하나를 미는 줄 — 이름표 · 슬라이더 · 지금 값. */
function SlideRow({
  label,
  value,
  min,
  max,
  step,
  suffix = '',
  onChange,
}: {
  label: string
  value: number
  min: number
  max: number
  step: number
  suffix?: string
  onChange: (v: number) => void
}) {
  return (
    <div className="ss-profile-info-row">
      <dt className="ss-profile-info-label">{label}</dt>
      <dd className="ss-profile-info-value">
        <label className="ss-card-slide">
          <input
            type="range"
            min={min}
            max={max}
            step={step}
            value={value}
            aria-label={label}
            onChange={(e) => onChange(Number(e.target.value))}
          />
          <span className="ss-card-slide-value">
            {value}
            {suffix}
          </span>
        </label>
      </dd>
    </div>
  )
}

/**
 * 사진 — 고르면 **바로 카드에 들어간다**(사용자 요청).
 *
 * 🔴 파일을 서버로 보내지 않는다. 브라우저에서 읽어 data URL 로 카드에
 * 얹을 뿐이다 — 카드 이미지를 둘 자리가 계약에 아직 없다(`cardStyle` 주석).
 */
function CardPhoto() {
  const { style, set } = useCardStyle()

  function pick(file: File | undefined) {
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => set({ photo: String(reader.result) })
    reader.readAsDataURL(file)
  }

  return (
    <div className="ss-card-looks">
      {/* 🔴 두 길을 **먼저** 고르게 한다. 누끼를 따야 하는지 아닌지가
          사진을 준비하는 방법을 통째로 바꾸기 때문이다(사용자 요청). */}
      <div className="ss-profile-tabs" role="group" aria-label="사진 놓는 방법">
        <button
          type="button"
          className="ss-profile-tab"
          data-on={style.mode === 'cutout'}
          aria-pressed={style.mode === 'cutout'}
          onClick={() => set({ mode: 'cutout' })}
        >
          사람만 오려서
        </button>
        <button
          type="button"
          className="ss-profile-tab"
          data-on={style.mode === 'full'}
          aria-pressed={style.mode === 'full'}
          onClick={() => set({ mode: 'full' })}
        >
          사진 그대로
        </button>
      </div>

      <p className="ss-profile-muted">
        {style.mode === 'cutout'
          ? '배경을 지운 그림(PNG)이면 카드에 자연스럽게 섭니다.'
          : '오려 내지 않은 사진을 그대로 깝니다 — 로고와 PLAYER CARD 만 위에 얹힙니다.'}
      </p>

      <label className="ss-card-file">
        <input
          type="file"
          accept="image/*"
          aria-label="사진 고르기"
          onChange={(e) => pick(e.target.files?.[0])}
        />
        <span>{style.photo ? '다른 사진으로' : '사진 고르기'}</span>
      </label>

      {style.photo && (
        <>
          <dl>
            <SlideRow
              label="크기"
              value={style.photoScale}
              min={0.4}
              max={2.4}
              step={0.05}
              suffix="배"
              onChange={(v) => set({ photoScale: v })}
            />
            <SlideRow
              label="좌우"
              value={style.photoX}
              min={-50}
              max={50}
              step={1}
              suffix="%"
              onChange={(v) => set({ photoX: v })}
            />
            <SlideRow
              label="위아래"
              value={style.photoY}
              min={-50}
              max={50}
              step={1}
              suffix="%"
              onChange={(v) => set({ photoY: v })}
            />
          </dl>

          <button
            type="button"
            className="ss-profile-tab self-start"
            onClick={() => set({ photo: null, photoScale: 1, photoX: 0, photoY: 0 })}
          >
            사진 빼기
          </button>
        </>
      )}
    </div>
  )
}

/** 붓 — 열 가지 자국 중 하나를 고르고 색 · 크기 · 자리를 정한다. */
function CardBrushTool() {
  const { style, set } = useCardStyle()
  return (
    <div className="ss-card-looks">
      {/* 🔴 이름만 늘어놓지 않고 **모양을 보여준다** — 「빗살」과 「격자」는
          글자로는 구별이 안 된다. */}
      <ul className="ss-card-marks">
        {MARKS.map((name, i) => (
          <li key={name}>
            <button
              type="button"
              className="ss-card-mark-pick"
              data-on={style.brush === i}
              aria-pressed={style.brush === i}
              aria-label={name}
              onClick={() => set({ brush: i })}
            >
              {/* 🔴 고르는 칸에도 **같은 컴포넌트**를 그린다. 미리보기를 따로
                  만들면 자국을 고칠 때 두 벌이 따로 늙는다. */}
              {i === 1 ? (
                <span className="ss-card-mark-none">없음</span>
              ) : (
                <CardMark index={i} seed="pick" />
              )}
            </button>
          </li>
        ))}
      </ul>

      {/* '없음'(1) 일 때만 조정할 것이 없다 — 기본(0)도 색 · 크기 · 자리를 따른다. */}
      {style.brush !== 1 && (
        <dl>
          <ColorRow
            label="자국 색"
            value={style.brushColor}
            onChange={(v) => set({ brushColor: v })}
          />
          <SlideRow
            label="크기"
            value={style.brushScale}
            min={0.4}
            max={2}
            step={0.05}
            suffix="배"
            onChange={(v) => set({ brushScale: v })}
          />
          <SlideRow
            label="좌우"
            value={style.brushX}
            min={-50}
            max={50}
            step={1}
            suffix="%"
            onChange={(v) => set({ brushX: v })}
          />
          <SlideRow
            label="위아래"
            value={style.brushY}
            min={-50}
            max={50}
            step={1}
            suffix="%"
            onChange={(v) => set({ brushY: v })}
          />
        </dl>
      )}
    </div>
  )
}
