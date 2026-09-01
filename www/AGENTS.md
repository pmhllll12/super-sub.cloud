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

🔴 **고치기 전에 그 문서의 「먼저 확인」을 실제로 돌린다.** 문서는 특정 시점의
코드를 보고 쓴 것이라 **다른 방식으로 이미 해결됐을 수 있다.**

- **이미 만족한다 → 손대지 않는다.** 형태가 문서의 제안과 달라도 목적이 달성됐으면
  그대로 둔다. 문서에 적힌 파일·함수 이름은 **예시지 규격이 아니다.**
- 만족하지 않는 것만 고친다. 애매하면 고치지 말고 물어본다.

이미 잘 도는 것은 `✅ 조치 불필요` 와 그 이유가 적혀 있다 — 멀쩡한 코드를 고치는 것이
이 문서가 낼 수 있는 가장 나쁜 결과다.

> 위 `nextjs-agent-rules` 블록은 `next dev` 가 다시 써넣는 자리다. 이 절은 그
> 블록 **밖**에 있어야 유지된다.
