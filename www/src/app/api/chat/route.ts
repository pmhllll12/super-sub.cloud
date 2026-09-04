import { ApiError, GoogleGenAI, type Content, type FunctionDeclaration } from '@google/genai'
import { NextResponse, type NextRequest } from 'next/server'
import { BackendError, getBackend } from '@/server/backend'
import { withAuth } from '@/server/handler'

/**
 * 흐름 B(모집 등록 돕기) 챗봇 서버 — LLM 키가 사는 유일한 곳이다(미결 `min` 7번).
 *
 * 🔴 **Claude가 아니라 Gemini다(2026-09-04 정정).** Claude API는 이 계정이
 * Free(평가) 플랜이라 결제 없이는 크레딧이 없어 막혔다 — Google AI Studio는
 * 카드 없이 바로 쓸 수 있는 무료 등급이 있어 Gemini로 바꿨다. 나머지 설계
 * (도구 하나·실제 쓰기는 안 함·DB 저장 없음)는 그대로다.
 *
 * 🔴 **DB 저장이 없다.** 대화 이력은 클라이언트가 매 요청마다 통째로 들고 와서
 * 되돌려 준다 — 새로고침하면 사라진다(열린 질문 3번 결정 그대로, 정어진에게
 * 새 백엔드를 요청하지 않는다).
 *
 * 🔴 **실제 쓰기(`POST /teams/{id}/matches`)는 여기서 하지 않는다.** LLM이
 * `propose_match_registration`을 부르면 확인 카드 데이터만 돌려주고, 실제
 * 등록은 화면의 [등록] 버튼이 `POST /api/teams/{teamId}/matches`를 따로 부른다
 * — LLM의 자연어 해석 오류가 곧바로 쓰기로 이어지는 경로를 막는 안전장치다.
 */

const MODEL = 'gemini-2.5-flash'

/** 마이그레이션에 박힌 값이 정본이다 — 조회 API가 없어 하드코딩한다
 *  (api-contract.md "포지션 목록은 마이그레이션이 넣는다"). */
const POSITIONS: Record<string, Record<string, string>> = {
  football: { GK: '골키퍼', DF: '수비수', MF: '미드필더', FW: '공격수' },
  futsal: { GK: '골키퍼', DF: '수비수', MF: '미드필더', FW: '공격수' },
  baseball: { P: '투수', C: '포수', IF: '내야수', OF: '외야수' },
  basketball: { G: '가드', F: '포워드', C: '센터' },
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

type ChatBody = { message?: unknown; history?: unknown }

type Proposal = {
  team_id: string
  team_name: string
  played_at: string
  place: string
  needs: { position_code: string; position_label: string; head_count: number }[]
}

function systemPrompt(ownerTeams: { team_id: string; name: string; sport_code: string }[]): string {
  const now = new Date().toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' })
  const teamLines = ownerTeams
    .map((t) => `- team_id="${t.team_id}" 이름="${t.name}" 종목=${t.sport_code}`)
    .join('\n')
  const posLines = Object.entries(POSITIONS)
    .map(([sport, codes]) => `- ${sport}: ` + Object.entries(codes).map(([c, l]) => `${c}(${l})`).join(' · '))
    .join('\n')

  return [
    '당신은 Super-Sub의 "모집 등록 도우미" 챗봇입니다. 팀 주장이 경기 인원 모집 글을',
    '등록하도록 대화로 돕습니다. 이것만 합니다 — 다른 요청(선수 검색·예약·잡담)은',
    '"지금은 경기 모집 등록만 도와드릴 수 있어요"라고 정중히 안내하고 범위를 벗어나지 않습니다.',
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

    const client = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY })
    let response: Awaited<ReturnType<typeof client.models.generateContent>>
    try {
      response = await client.models.generateContent({
        model: MODEL,
        contents: messages,
        config: {
          systemInstruction: systemPrompt(ownerTeams),
          tools: [{ functionDeclarations: [PROPOSE_TOOL] }],
        },
      })
    } catch (e) {
      throw toBackendError(e)
    }

    const reply = (response.text ?? '').trim()
    const toolCall = response.functionCalls?.find((fc) => fc.name === PROPOSE_TOOL_NAME)

    // 모델 턴을 그대로 되돌려 준다 — 다음 요청에서 이 history를 이어 보내면
    // functionCall이 있었다는 사실까지 대화 맥락에 남는다.
    const modelTurn: Content = response.candidates?.[0]?.content ?? {
      role: 'model',
      parts: [{ text: reply }],
    }
    messages.push(modelTurn)

    if (!toolCall) {
      return NextResponse.json({ history: messages, reply, proposal: null })
    }

    const input = toolCall.args as {
      team_id: string
      played_at: string
      place: string
      needs: { position_code: string; head_count: number }[]
    }
    const team = ownerTeams.find((t) => t.team_id === input.team_id)
    const labels = team ? POSITIONS[team.sport_code] : undefined

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
      })
    }

    const proposal: Proposal = {
      team_id: team.team_id,
      team_name: team.name,
      played_at: input.played_at,
      place: input.place,
      needs: input.needs.map((n) => ({ ...n, position_label: labels[n.position_code] ?? n.position_code })),
    }

    return NextResponse.json({ history: messages, reply, proposal })
  })
}
