import '@testing-library/jest-dom/vitest'

/**
 * 🔴 이 jsdom 조합은 `window.localStorage` 를 안 깔아 준다(URL 은
 * `http://localhost:3000/` 로 멀쩡한데도 `undefined` 다 — 실측).
 * 실제 브라우저에는 있으므로 시험만 다른 세상이 되지 않도록 메모리 저장소를
 * 세운다. **있으면 건드리지 않는다** — 언젠가 jsdom 이 제대로 깔면 그쪽을 쓴다.
 */
if (typeof globalThis.localStorage === 'undefined') {
  const memory = new Map<string, string>()
  const storage: Storage = {
    get length() {
      return memory.size
    },
    clear: () => memory.clear(),
    getItem: (k) => memory.get(k) ?? null,
    key: (i) => [...memory.keys()][i] ?? null,
    removeItem: (k) => void memory.delete(k),
    setItem: (k, v) => void memory.set(k, String(v)),
  }
  Object.defineProperty(globalThis, 'localStorage', { value: storage, configurable: true })
}

/**
 * 🔴 jsdom 은 `HTMLMediaElement` 의 `play` · `pause` 를 **안 만들어 준다** —
 * 부르면 "Not implemented" 를 찍고 `play()` 는 약속(Promise)이 아니라
 * `undefined` 를 돌려준다. 그래서 브라우저에서는 멀쩡한
 * `play().catch(...)` 가 시험에서만 터진다(실제로 그렇게 터졌다).
 *
 * 실제 브라우저에는 있으므로 시험만 다른 세상이 되지 않도록 세운다 —
 * `localStorage` 를 세운 것과 같은 이유 · 같은 방식이다. 어느 시험이 재생을
 * **직접 세고 싶으면** 그 시험이 `vi.spyOn` 으로 덮으면 된다.
 */
for (const [name, impl] of [
  ['play', function play(this: HTMLMediaElement) {
    return Promise.resolve()
  }],
  ['pause', function pause(this: HTMLMediaElement) {}],
] as const) {
  Object.defineProperty(HTMLMediaElement.prototype, name, {
    value: impl,
    writable: true,
    configurable: true,
  })
}

/**
 * 🔴 jsdom 은 `HTMLCanvasElement.getContext` 를 **안 만들어 준다**(`canvas`
 * npm 패키지를 깔아야 한다). 그런데 영상 분석 화면의 사람 따라가기는 축소본
 * 한 장을 떠서 생김새를 재므로, 화판이 없으면 **루프가 시작도 못 한다** —
 * 그러면 관절이 영영 안 붙고 「이 사람이 맞습니까?」 관문을 시험할 수 없다.
 *
 * 실제 브라우저에는 있으므로 시험만 다른 세상이 되지 않도록 세운다 —
 * `localStorage` · `HTMLMediaElement.play` 와 같은 이유 · 같은 방식이다.
 * **그림을 진짜로 그리지는 않는다.** 그릴 필요가 없어서다: 검출기는 대역이고,
 * 우리가 재는 것은 "루프가 도는가 · 관절이 붙는가"이지 픽셀이 아니다.
 *
 * ⚠️ 무거운 `canvas` 패키지를 안 싣는 덤이 있다. 픽셀 자체를 재야 하는 시험이
 * 생기면 그때 그 패키지를 들이고 이 대역을 걷어낸다.
 */
if (typeof HTMLCanvasElement !== 'undefined') {
  Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', {
    value(this: HTMLCanvasElement, kind: string) {
      if (kind !== '2d') return null
      // jsdom 에서 `video.videoWidth` 가 0 이라 호출 쪽 계산이 NaN 이 될 수
      // 있다 — 여기서 한 번 잡아 준다(0 짜리 ImageData 는 만들 수 없다).
      const size = (n: number) => (Number.isFinite(n) && n > 0 ? Math.round(n) : 1)
      return {
        drawImage() {},
        getImageData(_x: number, _y: number, w: number, h: number) {
          const width = size(w)
          const height = size(h)
          return { data: new Uint8ClampedArray(width * height * 4), width, height }
        },
      }
    },
    writable: true,
    configurable: true,
  })
}
