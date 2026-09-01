<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

## 백엔드 계약 (`fastapi/`)

이 앱은 같은 저장소의 `fastapi/` 백엔드를 부른다. **계약이 바뀌면 백엔드 쪽에서
문서로 알린다.** 작업을 시작하기 전에 아래 두 번째 파일을 먼저 본다.

- 전체 규격 — `fastapi/docs/api-contract.md`
- 🔴 **반영할 변경 목록 — `fastapi/docs/client-contract-changes.md`**

변경 목록에는 **"조치 필요"로 표시된 것만** 손대면 된다. 이미 잘 도는 것은
`✅ 조치 불필요` 와 그 이유가 적혀 있다 — 멀쩡한 코드를 고치지 않기 위한 표시다.

> 위 `nextjs-agent-rules` 블록은 `next dev` 가 다시 써넣는 자리다. 이 절은 그
> 블록 **밖**에 있어야 유지된다.
