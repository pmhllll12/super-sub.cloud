<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

## 백엔드 계약 (`fastapi/`)

이 앱은 같은 저장소의 `fastapi/` 백엔드를 부른다. **계약이 바뀌면 백엔드 쪽에서
문서로 알린다.** 작업을 시작하기 전에 아래 두 번째 파일을 본다.

- 전체 규격 — `fastapi/docs/api-contract.md`
- 🔴 **반영할 변경 목록 — `fastapi/docs/client-contract-changes.md`**
  (`jekyll/pages/pending.markdown` 의 「클라이언트의 백엔드 계약 반영」)

🔴 **고치기 전에 그 문서의 「먼저 확인」을 실제로 돌린다. 이미 됐으면 손대지 않는다.**
처리 방식의 정본은 저장소 루트 `CLAUDE.md` 의 「미결 항목」 절이다 — 여기서
되풀이하지 않는다.

> 위 `nextjs-agent-rules` 블록은 `next dev` 가 다시 써넣는 자리다. 이 절은 그
> 블록 **밖**에 있어야 유지된다.
