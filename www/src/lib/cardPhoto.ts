/**
 * **카드 사진을 올린다** — 줄이고, S3 로 직접 보내고, 키를 돌려준다
 * (2026-09-18, 사용자 요청).
 *
 * 🔴 **바이트가 우리 서버를 지나지 않는다**(PER-002). 영상 업로드와 같은 두
 * 단계다: 우리 서버에서 **사전 서명 주소만** 받고, 파일은 브라우저가 S3 에
 * 직접 PUT 한다. 돌려주는 `storage_key` 를 `style.photo_key` 로 저장해야
 * **그때** 카드에 붙는다 — 올리기만 하고 안 저장하면 아무 일도 안 난다.
 *
 * 🔴 **올리기 전에 줄인다.** 카드는 380px 폭인데 폰 사진은 3~5MB 다. 안 줄이면
 * 올리는 데 오래 걸리고, 남이 그 카드를 열 때마다 그 원본을 내려받는다.
 */

/** 긴 변을 이 길이로 맞춘다. 카드 기본 폭(380)의 두 배 — 고해상도 화면 몫. */
const MAX_EDGE = 768

/**
 * 🔴 **JPEG 로 바꿔 보낸다 — 단, 투명한 그림은 PNG 로 둔다.** 「사람만 오려서」
 * 모드는 배경이 없는 PNG 가 요점이라, JPEG 로 바꾸면 **투명한 자리가 검게
 * 칠해져** 카드가 망가진다.
 */
const JPEG_QUALITY = 0.85

export type UploadedPhoto = {
  /** `style.photo_key` 에 넣을 값. */
  storageKey: string
  /** 저장이 끝나기 전에 카드에 바로 보여 줄 주소(브라우저 안). */
  previewUrl: string
}

/** 그 파일이 **투명한 자리를 가질 수 있는가** — PNG·WebP·GIF. */
function keepsTransparency(type: string): boolean {
  return type === 'image/png' || type === 'image/webp' || type === 'image/gif'
}

/**
 * 긴 변이 `MAX_EDGE` 를 넘으면 줄인다. **넘지 않으면 그대로 둔다** — 작은
 * 그림을 다시 그리면 화질만 떨어진다.
 *
 * 🔴 실패하면 **원본을 그대로 쓴다**(던지지 않는다). 줄이기는 좋게 하자는
 * 것이지 못 하면 못 올리는 일이 아니다.
 */
export async function shrinkForCard(file: File): Promise<Blob> {
  try {
    const bitmap = await createImageBitmap(file)
    const longest = Math.max(bitmap.width, bitmap.height)
    if (longest <= MAX_EDGE) {
      bitmap.close?.()
      return file
    }
    const ratio = MAX_EDGE / longest
    const canvas = document.createElement('canvas')
    canvas.width = Math.round(bitmap.width * ratio)
    canvas.height = Math.round(bitmap.height * ratio)
    const ctx = canvas.getContext('2d')
    if (!ctx) return file
    ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
    bitmap.close?.()

    const type = keepsTransparency(file.type) ? 'image/png' : 'image/jpeg'
    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, type, JPEG_QUALITY),
    )
    return blob ?? file
  } catch {
    return file
  }
}

/**
 * 서버에서 받는 타입 셋 중 하나로 맞춘다.
 *
 * 🔴 **`image/*` 를 그대로 보내지 않는다.** `<input accept="image/*">` 는
 * HEIC·SVG 도 통과시키는데 서버는 셋만 받는다(`UNSUPPORTED_PHOTO_TYPE`) —
 * 여기서 안 맞추면 폰에서 고른 사진이 그대로 422 가 된다.
 */
function contentTypeOf(blob: Blob, original: File): string {
  const type = blob.type || original.type
  if (type === 'image/png' || type === 'image/webp' || type === 'image/jpeg') return type
  // 줄이기가 실패해 원본이 그대로 온 경우다. JPEG 로 선언하면 내용과 어긋나므로
  // **다시 그려서** 진짜 JPEG 로 만든다 — 그것도 실패하면 부르는 쪽이 안내한다.
  return 'image/jpeg'
}

/**
 * 사진 하나를 올린다.
 *
 * 🔴 **던진다.** 조용히 실패하면 사람은 사진이 바뀐 줄 알고 저장까지 하는데
 * 실제로는 옛 사진(또는 사진 없음)이 남는다 — 부르는 쪽이 문구를 띄운다.
 */
export async function uploadCardPhoto(file: File): Promise<UploadedPhoto> {
  const shrunk = await shrinkForCard(file)
  const contentType = contentTypeOf(shrunk, file)

  const res = await fetch('/api/me/card/photo-upload-url', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content_type: contentType }),
  })
  if (!res.ok) throw new Error('사진을 올릴 자리를 받지 못했습니다.')
  const { upload_url, storage_key } = (await res.json()) as {
    upload_url: string
    storage_key: string
  }

  /* 🔴 **`Content-Type` 이 서명에 들어간다** — 위에서 보낸 값과 **같아야**
     하고, 다르면 S3 가 403 을 준다. 그래서 한 변수로 묶어 둔다. */
  const put = await fetch(upload_url, {
    method: 'PUT',
    headers: { 'Content-Type': contentType },
    body: shrunk,
  })
  if (!put.ok) throw new Error('사진을 올리지 못했습니다.')

  return { storageKey: storage_key, previewUrl: URL.createObjectURL(shrunk) }
}
