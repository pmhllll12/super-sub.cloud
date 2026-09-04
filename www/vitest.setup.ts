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
