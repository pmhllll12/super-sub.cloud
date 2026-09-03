import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'node:path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.ts'],
    globals: true,
    // 🔴 route handler 시험은 mock.ts 의 정확한 동작을 검증한다 — getBackend()가
    // 이제 USE_MOCK=1 이 아니면 진짜 FastAPI(fastapiBackend)를 부르므로
    // (jin-10 해소), 여기서 켜 두지 않으면 시험이 존재하지도 않는
    // BACKEND_BASE_URL 로 네트워크 호출을 시도하게 된다.
    env: { USE_MOCK: '1' },
  },
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
})
