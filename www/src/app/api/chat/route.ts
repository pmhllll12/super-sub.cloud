import { ApiError, GoogleGenAI, type Content, type FunctionDeclaration } from '@google/genai'
import { NextResponse, type NextRequest } from 'next/server'
import { BackendError, getBackend, type MercenaryCandidate, type Position } from '@/server/backend'
import { withAuth } from '@/server/handler'

/**
 * 흐름 B(모집 등록 돕기) + 흐름 D(용병 후보 검색, 2026-09-10 추가) 챗봇 서버 —
 * LLM 키가 사는 유일한 곳이다(미결 `min` 7번·17번).
 *
 * 🔴 **Claude가 아니라 Gemini다(2026-09-04 정정).** Claude API는 이 계정이
 * Free(평가) 플랜이라 결제 없이는 크레딧이 없어 막혔다 — Google AI Studio는
 * 카드 없이 바로 쓸 수 있는 무료 등급이 있어 Gemini로 바꿨다. 나머지 설계
 * (실제 쓰기는 안 함·DB 저장 없음)는 그대로다.
 *
 * 🔴 **DB 저장이 없다.** 대화 이력은 클라이언트가 매 요청마다 통째로 들고 와서
 * 되돌려 준다 — 새로고침하면 사라진다(열린 질문 3번 결정 그대로, 정어진에게
 * 새 백엔드를 요청하지 않는다).
 *
 * 🔴 **실제 쓰기(`POST /teams/{id}/matches`)는 여기서 하지 않는다.** LLM이
 * `propose_match_registration`을 부르면 확인 카드 데이터만 돌려주고, 실제
 * 등록은 화면의 [등록] 버튼이 `POST /api/teams/{teamId}/matches`를 따로 부른다
 * — LLM의 자연어 해석 오류가 곧바로 쓰기로 이어지는 경로를 막는 안전장치다.
 *
 * 🔴 **`search_candidates`는 다르다 — 읽기라 곧바로 실행한다.** 등록과 달리
 * 사람 확인 없이 결과를 보여줘도 되돌릴 수 없는 일이 없다(선수 카드를 실제로
 * 만지지 않는다, `fastapi/docs/api-contract.md` 3-11절). 검색 결과를 **다시
 * Gemini에 넣어 문장으로 요약**하게 한다 — 이게 RAG의 검색(fastapi/pgvector)
 * + 생성(이 두 번째 호출) 구조다.
 */

const MODEL = 'gemini-2.5-flash'

/**
 * 🔴 **포지션 목록을 더는 하드코딩하지 않는다**(CCC 28, 2026-09-10).
 *
 * 전에는 이 파일이 `{ football: { GK: '골키퍼', … } }` 를 들고 있었다 —
 * 마이그레이션이 바뀌면 **조용히 낡아서**, 챗봇만 없는 코드를 계속 제안하고
 * 등록에서야 422 가 났다. 이제 `GET /positions` 가 정본이다(계약 3-3절).
 *
 * 🔴 **주장인 팀의 종목만** 받아 온다. 전 종목을 받으면 야구 `C`(포수)와 농구
 * `C`(센터)가 같이 실려, LLM 이 남의 종목 코드를 고를 여지가 생긴다.
 */
async function positionsFor(
  token: string,
  ownerTeams: { sport_code: string }[],
): Promise<Position[]> {
  const sports = [...new Set(ownerTeams.map((t) => t.sport_code))]
  const lists = await Promise.all(
    sports.map((sport) =>
      // 한 종목이 422(없는 종목)여도 나머지는 살린다 — 목록이 조금 빈 채로
      // 대화가 도는 편이, 챗봇이 통째로 안 열리는 것보다 낫다. 어차피 등록은
      // 화면의 [등록] 버튼이 서버 검사를 다시 받는다.
      getBackend()
        .listPositions(token, { sport_code: sport })
        .catch(() => [] as Position[]),
    ),
  )
  return lists.flat()
}

const PROPOSE_TOOL_NAME = 'propose_match_registration'

const PROPOSE_TOOL: FunctionDeclaration = {
  name: PROPOSE_TOOL_NAME,
  description:
    '슬롯 4개(팀·시각·장소·필요 포지션)가 다 채워지고 사용자가 구두로 확인했을 때만 부른다. ' +
    '실제로 경기를 등록하지 않는다 — 확인 카드를 화면에 띄우는 신호일 뿐이다.',
  parametersJsonSchema: {
    type: 'object',
    properties: {
      team_id: { type: 'string', description: '시스템 프롬프트에 준 팀 목록 중 하나의 team_id' },
      played_at: { type: 'string', description: 'ISO 8601, 반드시 미래 시각, +09:00' },
      place: { type: 'string' },
      needs: {
        type: 'array',
        minItems: 1,
        items: {
          type: 'object',
          properties: {
            position_code: { type: 'string' },
            head_count: { type: 'integer', minimum: 1 },
          },
          required: ['position_code', 'head_count'],
        },
      },
    },
    required: ['team_id', 'played_at', 'place', 'needs'],
  },
}

const SEARCH_TOOL_NAME = 'search_candidates'

const SEARCH_TOOL: FunctionDeclaration = {
  name: SEARCH_TOOL_NAME,
  description:
    '사용자가 이번 경기에 필요한 용병(선수) 후보를 찾아달라고 할 때 부른다. ' +
    '팀·포지션이 정해지고 사용자가 원하는 조건(가능 시간·실력 등)을 말한 뒤에만 부른다. ' +
    '조건이 막연하면(포지션 미정 등) 먼저 되묻는다. 실제로 아무것도 등록·연결하지 않는다 — ' +
    '후보를 보여주기만 한다.',
  parametersJsonSchema: {
    type: 'object',
    properties: {
      team_id: { type: 'string', description: '시스템 프롬프트에 준 팀 목록 중 하나의 team_id' },
      position_code: { type: 'string', description: '그 팀 종목 안에서 유효한 포지션 코드' },
      query_text: {
        type: 'string',
        description:
          '사용자가 말한 조건을 검색어로 요약한 자연어 문장(예: "주말 저녁 가능한 골키퍼, 공중볼 강한 사람")',
      },
    },
    required: ['team_id', 'position_code', 'query_text'],
  },
}

type ChatBody = { message?: unknown; history?: unknown }

type Proposal = {
  team_id: string
  team_name: string
  played_at: string
  place: string
  needs: { position_code: string; position_label: string; head_count: number }[]
}

function systemPrompt(
  ownerTeams: { team_id: string; name: string; sport_code: string }[],
  positions: Position[],
): string {
  const now = new Date().toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' })
  const teamLines = ownerTeams
    .map((t) => `- team_id="${t.team_id}" 이름="${t.name}" 종목=${t.sport_code}`)
    .join('\n')
  const posLines = [...new Set(positions.map((p) => p.sport_code))]
    .map(
      (sport) =>
        `- ${sport}: ` +
        positions
          .filter((p) => p.sport_code === sport)
          .map((p) => `${p.code}(${p.label})`)
          .join(' · '),
    )
    .join('\n')

  return [
    '당신은 Super-Sub의 "용병 찾기" 챗봇입니다. 팀 주장을 도와 두 가지만 합니다:',
    '(1) 경기 인원 모집 글 등록 (2) 조건에 맞는 용병 후보 검색.',
    '이 둘만 합니다 — 다른 요청(경기장 예약·잡담)은 "지금은 모집 등록과 용병',
    '검색만 도와드릴 수 있어요"라고 정중히 안내하고 범위를 벗어나지 않습니다.',
    '',
    `지금 시각(서울): ${now}`,
    '',
    '이 사용자가 주장(owner)인 팀 목록 — team_id는 반드시 이 중 하나를 그대로 씁니다:',
    teamLines,
    '',
    '종목별 유효 포지션 코드 — 이 목록에 없는 코드는 쓰지 않습니다. 오타·다른 종목',
    '코드를 쓰면 팀의 종목 안에서 뜻이 없어 서버가 거부합니다:',
    posLines,
    '',
    '슬롯 4개(team_id·played_at·place·needs)가 모두 채워지고 사용자가 "네" 등으로',
    '구두 확인하면 그때만 propose_match_registration을 부릅니다. 확인 전에는 절대',
    '부르지 않고, 채워진 값을 요약해 먼저 되물어 확인을 받습니다.',
    '',
    '날짜·시간은 사용자의 자연어 표현("이번 주 토요일 저녁")을 위 현재 시각 기준으로',
    'ISO 8601(+09:00)로 바꿉니다. 과거 시각이 되면 안 됩니다 — 모호하면 되묻습니다.',
    '',
    '포지션을 정하지 않고 "아무나 상관없다"고 하면, 포지션을 특정해 달라고',
    '되묻습니다 — 지금 등록 API는 포지션+인원이 필수라 다른 방법이 없습니다.',
    '',
    '사용자가 "골키퍼 구해줘"처럼 **후보를 찾아달라고** 하면 search_candidates를',
    '씁니다. team_id·position_code(위 목록에 있는 코드)·query_text(사용자가 말한',
    '조건 요약)가 정해지면 곧바로 부릅니다 — 등록과 달리 확인을 먼저 구하지',
    '않습니다(무언가를 등록·연결하는 게 아니라 보여주기만 해서입니다).',
    '검색 결과가 이 대화에 다시 주어지면, 그걸 근거로 후보를 자연스러운',
    '문장으로 소개합니다 — 목록을 그대로 나열하지 말고 조건과 왜 맞는지를',
    '엮어서 짧게 말합니다. 결과가 비어 있으면 조건을 넓혀 다시 찾아볼지 묻습니다.',
    '',
    '팀이 둘 이상이면 어느 팀인지 먼저 묻고, 하나뿐이면 그 팀으로 바로 진행한다고',
    '알리기만 합니다. 항상 한국어로, 짧고 친근하게 답합니다.',
  ].join('\n')
}

function toBackendError(e: unknown): BackendError {
  if (e instanceof ApiError) {
    if (e.status === 429) {
      return new BackendError(429, 'CHAT_RATE_LIMITED', '잠시 후 다시 시도해 주세요.')
    }
    if (e.status === 401 || e.status === 403) {
      return new BackendError(500, 'CHAT_MISCONFIGURED', 'AI 서비스 인증에 실패했습니다.')
    }
  }
  return new BackendError(502, 'CHAT_UPSTREAM_ERROR', 'AI 서비스와 통신하지 못했습니다.')
}

export async function POST(req: NextRequest) {
  return withAuth(req, async (token) => {
    let body: ChatBody
    try {
      body = await req.json()
    } catch {
      return NextResponse.json(
        { error: { code: 'BAD_REQUEST', message: '요청 형식이 잘못되었습니다.' } },
        { status: 400 },
      )
    }
    if (typeof body.message !== 'string' || !body.message.trim()) {
      return NextResponse.json(
        { error: { code: 'VALIDATION_ERROR', message: 'message가 필요합니다.' } },
        { status: 422 },
      )
    }
    const priorHistory = Array.isArray(body.history) ? (body.history as Content[]) : []

    const me = await getBackend().getMe(token)
    const ownerTeams = me.teams.filter((t) => t.role === 'owner')

    if (ownerTeams.length === 0) {
      // 대화형 슬롯을 채울 팀 자체가 없다 — LLM을 부르지 않고 바로 안내한다(비용 절약).
      return NextResponse.json({
        history: priorHistory,
        reply: '아직 주장으로 있는 팀이 없어서 경기를 등록해 드릴 수 없어요. 먼저 팀을 만들어 주세요.',
        proposal: null,
      })
    }

    if (!process.env.GEMINI_API_KEY) {
      throw new BackendError(503, 'CHAT_NOT_CONFIGURED', 'GEMINI_API_KEY가 설정되어 있지 않습니다.')
    }

    const messages: Content[] = [
      ...priorHistory,
      { role: 'user', parts: [{ text: body.message }] },
    ]

    // 🔴 프롬프트를 짓기 **전에** 받아 둔다 — 목록이 프롬프트의 일부다(CCC 28).
    const positions = await positionsFor(token, ownerTeams)

    const client = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY })
    let response: Awaited<ReturnType<typeof client.models.generateContent>>
    try {
      response = await client.models.generateContent({
        model: MODEL,
        contents: messages,
        config: {
          systemInstruction: systemPrompt(ownerTeams, positions),
          tools: [{ functionDeclarations: [PROPOSE_TOOL, SEARCH_TOOL] }],
        },
      })
    } catch (e) {
      throw toBackendError(e)
    }

    const reply = (response.text ?? '').trim()
    const toolCall = response.functionCalls?.find(
      (fc) => fc.name === PROPOSE_TOOL_NAME || fc.name === SEARCH_TOOL_NAME,
    )

    // 모델 턴을 그대로 되돌려 준다 — 다음 요청에서 이 history를 이어 보내면
    // functionCall이 있었다는 사실까지 대화 맥락에 남는다.
    const modelTurn: Content = response.candidates?.[0]?.content ?? {
      role: 'model',
      parts: [{ text: reply }],
    }
    messages.push(modelTurn)

    if (!toolCall) {
      return NextResponse.json({ history: messages, reply, proposal: null, candidates: null })
    }

    if (toolCall.name === SEARCH_TOOL_NAME) {
      const input = toolCall.args as {
        team_id: string
        position_code: string
        query_text: string
      }
      const team = ownerTeams.find((t) => t.team_id === input.team_id)
      /* 🔴 **그 팀의 종목 안에서** 찾는다 — 코드만으로 찾으면 야구 `C`(포수)에
         농구 `C`(센터) 검색이 섞인다(PROPOSE_TOOL 분기와 같은 이유, CCC 28). */
      const labels = team
        ? Object.fromEntries(
            positions.filter((p) => p.sport_code === team.sport_code).map((p) => [p.code, p.label]),
          )
        : undefined

      if (!team || !labels || !labels[input.position_code]) {
        // team_id·position_code가 시스템 프롬프트에 준 값을 벗어났다 — 검색을
        // 안 부르고 짝만 닫은 뒤 되묻는다.
        messages.push({
          role: 'user',
          parts: [
            {
              functionResponse: {
                id: toolCall.id,
                name: SEARCH_TOOL_NAME,
                response: { status: 'invalid_input' },
              },
            },
          ],
        })
        return NextResponse.json({
          history: messages,
          reply: reply || '어느 팀·포지션인지 다시 한번 말씀해 주시겠어요?',
          proposal: null,
          candidates: null,
        })
      }

      let candidates: MercenaryCandidate[]
      try {
        candidates = await getBackend().searchMercenaryCandidates(token, {
          sport_code: team.sport_code,
          position_code: input.position_code,
          query_text: input.query_text,
          limit: 5,
        })
      } catch (e) {
        // 검색 실패(백엔드 미배선 404·EMBEDDING_NOT_CONFIGURED 503 등, min
        // 17번)를 대화가 끊기지 않게 안내로 돌린다 — 등록 흐름의 네트워크
        // 오류 처리와 같은 원칙이다.
        messages.push({
          role: 'user',
          parts: [
            {
              functionResponse: {
                id: toolCall.id,
                name: SEARCH_TOOL_NAME,
                response: { status: 'search_failed' },
              },
            },
          ],
        })
        const message = e instanceof BackendError ? e.message : '검색 중 문제가 있었어요.'
        return NextResponse.json({
          history: messages,
          reply: `${message} 잠시 후 다시 시도해 주세요.`,
          proposal: null,
          candidates: null,
        })
      }

      // 검색 결과(실제 데이터)를 functionResponse에 실어 모델에게 돌려준다 —
      // 등록 흐름과 달리 "보여줬다"는 신호만 주지 않는다. 이걸 근거로 모델이
      // 다음 호출에서 자연어 소개 문장을 만든다(RAG의 생성 단계).
      messages.push({
        role: 'user',
        parts: [
          {
            functionResponse: {
              id: toolCall.id,
              name: SEARCH_TOOL_NAME,
              response: { candidates },
            },
          },
        ],
      })

      let searchReply = reply
      try {
        const followUp = await client.models.generateContent({
          model: MODEL,
          contents: messages,
          config: { systemInstruction: systemPrompt(ownerTeams, positions) },
        })
        searchReply = (followUp.text ?? '').trim() || searchReply
        messages.push(
          followUp.candidates?.[0]?.content ?? { role: 'model', parts: [{ text: searchReply }] },
        )
      } catch (e) {
        // 2차 호출(요약 문장 생성)이 실패해도 검색 결과 자체는 이미 있다 —
        // 카드는 보여주고 문장만 기본값으로 대신한다.
        searchReply =
          candidates.length > 0
            ? '조건에 맞는 후보를 찾았어요.'
            : '조건에 맞는 후보를 못 찾았어요. 조건을 넓혀서 다시 찾아볼까요?'
      }

      return NextResponse.json({
        history: messages,
        reply: searchReply,
        proposal: null,
        candidates,
      })
    }

    const input = toolCall.args as {
      team_id: string
      played_at: string
      place: string
      needs: { position_code: string; head_count: number }[]
    }
    const team = ownerTeams.find((t) => t.team_id === input.team_id)
    /* 🔴 **그 팀의 종목 안에서** 이름을 찾는다 — 코드만으로 찾으면 야구 `C`
       (포수)에 농구 `C`(센터) 이름이 붙는다(CCC 28). */
    const labels = team
      ? Object.fromEntries(
          positions.filter((p) => p.sport_code === team.sport_code).map((p) => [p.code, p.label]),
        )
      : undefined

    // 다음 사용자 턴이 이 functionCall과 짝을 이루는 functionResponse 없이 오면
    // 대화 맥락이 어긋난다 — 실제로 등록을 실행하지 않았으므로 안내로 짝을 닫는다.
    messages.push({
      role: 'user',
      parts: [
        {
          functionResponse: {
            id: toolCall.id,
            name: PROPOSE_TOOL_NAME,
            response: { status: 'shown_to_user', note: '확인 카드를 사용자에게 보여줬습니다.' },
          },
        },
      ],
    })

    if (!team || !labels) {
      // team_id가 시스템 프롬프트에 준 목록을 벗어났다 — 카드를 내지 않고 다시 묻는다.
      return NextResponse.json({
        history: messages,
        reply: reply || '어느 팀인지 다시 한번 말씀해 주시겠어요?',
        proposal: null,
        candidates: null,
      })
    }

    const proposal: Proposal = {
      team_id: team.team_id,
      team_name: team.name,
      played_at: input.played_at,
      place: input.place,
      needs: input.needs.map((n) => ({ ...n, position_label: labels[n.position_code] ?? n.position_code })),
    }

    return NextResponse.json({ history: messages, reply, proposal, candidates: null })
  })
}
