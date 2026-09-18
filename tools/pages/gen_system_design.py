"""「시스템 설계」 장 1절(시스템 구성도)을 실물(2026-09-17)로 다시 쓴다.

1절만 바꾼다 — `## 1) 시스템 구성도` 부터 `## 2) 데이터베이스 설계` 직전까지.
3·4절(파이프라인·AI 에이전트)은 정상호 영역이라 건드리지 않는다.
"""

from pathlib import Path

# 🔴 저장소 루트는 이 파일 위치에서 구한다 — 절대경로를 박지 않는다(`tools/README.md`).
ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "jekyll/chapters/06-시스템설계.markdown"
INK, INK2 = "#27262b", "#5c5962"
FONT = "font-family=\"-apple-system,BlinkMacSystemFont,'Segoe UI','Apple SD Gothic Neo','Noto Sans KR',sans-serif\""


def t(x, y, s, size=11, anchor="middle", color=INK2, weight=None):
    w = f' font-weight="{weight}"' if weight else ""
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" fill="{color}"{w}>{s}</text>'


def box(x, y, w, h, title, sub, sub2="", dashed=False):
    da = ' stroke-dasharray="6 4"' if dashed else ""
    cx = x + w / 2
    lines = t(cx, y + 22, title, 14, color=INK, weight="600") + t(cx, y + 39, sub, 11.5)
    if sub2:
        lines += t(cx, y + 54, sub2, 11)
    return (f'<g><title>{title} — {sub} {sub2}</title>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="#f6f5f1" stroke="{INK2}" stroke-width="1.5"{da}/>'
            f"{lines}</g>")


def arrow(d, both=False):
    s = ' marker-start="url(#m)"' if both else ""
    return f'<path d="{d}" fill="none" stroke="{INK2}" stroke-width="1.5" marker-end="url(#m)"{s}/>'


def diagram():
    b = [f'<defs><marker id="m" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
         f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{INK2}"/></marker></defs>']
    b.append(f'<g><title>사용자 — 브라우저·휴대폰</title><rect x="10" y="176" width="80" height="50" rx="25" fill="none" '
             f'stroke="{INK2}" stroke-width="1.5"/>' + t(50, 206, "사용자", 13.5, color=INK, weight="600") + "</g>")
    b += [
        box(115, 100, 160, 66, "웹 서버", "Next.js · Vercel", "API 대리 호출 · 챗봇"),
        box(115, 236, 160, 62, "앱", "Flutter", "초기 단계", dashed=True),
        box(315, 10, 150, 62, "객체 저장소", "AWS S3", "원본 · 분석 산출물"),
        box(315, 160, 150, 62, "앞단", "Cloudflare → nginx", "TLS · 봇 차단"),
        box(315, 320, 150, 62, "Gemini", "외부 LLM", "임베딩 · 챗봇"),
        box(530, 10, 195, 62, "GPU 분석 워커", "g4dn · 쓸 때만 켬", "자세 추출 → 채점 → 리포트"),
        box(530, 160, 195, 62, "API 서버", "FastAPI · k3s", "7개 도메인 · 인증"),
        box(530, 320, 195, 62, "DB", "PostgreSQL 18 + pgvector", "API 서버와 같은 서버"),
    ]
    b += [
        arrow("M90,192 L113,150"), arrow("M90,212 L113,262"),
        arrow("M275,142 L313,180"), t(300, 132, "대리 호출"),
        arrow("M275,262 L313,205"), t(302, 250, "호출"),
        arrow("M465,191 L528,191"), t(496, 183, "전달"),
        arrow("M627,222 L627,318"), t(635, 275, "읽기·쓰기", anchor="start"),
        arrow("M540,222 L467,340"), t(500, 298, "임베딩", anchor="start"),
        arrow("M50,176 L50,41 L313,41"), t(180, 33, "원본 직접 업로드 · 200MB·60초·4K 이하"),
        arrow("M528,41 L467,41", both=True), t(497, 66, "원본·산출물"),
        arrow("M560,72 L440,158"), t(512, 128, "작업 가져가기 · 완료 보고", anchor="start"),
    ]
    b.append(f'<rect x="10" y="386" width="22" height="12" rx="3" fill="none" stroke="{INK2}" stroke-width="1.5" stroke-dasharray="5 3"/>')
    b.append(t(38, 396, "점선 = 초기 단계 · 챗봇 대화는 웹 서버가 Gemini 를 직접 부른다(선 생략)", 11.5, "start", INK))
    return (
        '<figure class="doc-figure">'
        f'<svg viewBox="0 0 740 404" width="740" role="img" aria-label="시스템 구성도: 사용자는 웹 서버나 앱으로 들어오고, 요청은 앞단(Cloudflare, nginx)을 지나 k3s 위의 API 서버로 간다. API 서버는 같은 서버의 PostgreSQL과 외부 Gemini를 쓴다. 원본 영상은 사용자가 객체 저장소에 직접 올리고, GPU 분석 워커는 앞단을 거쳐 작업을 가져가며 저장소와 원본·산출물을 주고받는다." {FONT} '
        f'style="max-width:100%;height:auto;display:block">{"".join(b)}</svg>'
        '<figcaption class="doc-figure-caption">'
        "그림 6-1. 시스템 구성도(2026-09-17 실물). 원본 영상은 API 서버를 거치지 않고 저장소로 직접 가고, "
        "무거운 분석은 GPU 워커가 대기열에서 가져가 따로 처리한다. 워커도 API 를 부를 때 앞단을 지난다."
        "</figcaption></figure>"
    )


SECTION = f"""## 1) 시스템 구성도

> **2026-09-17 실물 기준으로 다시 썼다**(처음 판은 09-10). 각 부분을 누가 만들었는지와
> 처음 판에서 무엇이 달라졌는지는 [프로젝트 전체 그림]({{{{ "/10-프로젝트전체그림/" | relative_url }}}})의
> 그림 1과 5절에 있다.

Super-Sub 는 **앞단 + 세 계층 + 비동기 분석 워커** 구조다. 화면(웹·앱)은 API 서버 하나를
창구로 삼고, 무거운 영상 분석은 GPU 인스턴스가 대기열에서 작업을 가져가 따로 처리한다.
원본 영상은 **API 서버를 거치지 않고** 객체 저장소로 직접 오간다.

{diagram()}

### 구성 요소

| 요소 | 역할 | 핵심 기술 | 배치 |
|---|---|---|---|
| 웹 | 화면. API 호출은 브라우저가 아니라 **웹 서버가 대신** 하고, 챗봇 대화도 여기서 처리 | Next.js 16 · React 19 | Vercel |
| 모바일 앱 | 촬영·업로드·리포트 열람 — **초기 단계** | Flutter | 스토어 배포 전 |
| 앞단 | TLS 종료 · 프록시 · 봇 차단 | Cloudflare · nginx · Let's Encrypt | 클라우드 서버 앞 |
| API 서버 | 인증·업무 로직·조회. 도메인 **7개**(사용자·팀 · 카드 · 영상 분석 · 매칭 · 평가·신뢰 · 과금 · 알림)로 나누고, 도메인끼리 코드를 가져다 쓰지 못하게 검사로 강제 | Python · FastAPI · SQLAlchemy | 클라우드 서버의 **k3s** (AWS `ap-northeast-2`) |
| 관계형 DB | 사용자·팀·카드·영상·분석 결과·매칭·평가·과금·알림. 스키마는 마이그레이션으로 관리 | PostgreSQL 18 · Alembic | API 서버와 **같은 클라우드 서버** |
| 벡터 색인 | **용병 검색**(사용자 임베딩 유사도). 선수 성향 비교용 벡터는 아직 채우지 않았다 | pgvector | 위 DB 확장 |
| 외부 LLM | 용병 검색용 임베딩(API 서버) · 챗봇 대화(웹 서버) | Gemini | 외부 API |
| 객체 저장소 | 원본 클립 · 분석 산출물(리포트·관절 데이터). 원본은 **사전 서명 URL** 로 직접 오감 (SFR-001 · PER-002) | AWS S3 | 클라우드 (리전 동일) |
| GPU 분석 워커 | 대기열에서 작업을 가져가 분석(자세 추출 → 특징 → 루브릭 채점 → 리포트) · 분석 대상 검출 | Python · Transformers · 소형 LLM | GPU 인스턴스(g4dn.xlarge). **쓸 때만 켜고** 유휴 시 자동 종료 |
| 문서 사이트 | 이 제안서 | Jekyll (Just the Docs) | GitHub Pages (`dev.supersub-ai.com`) |
| CI/CD | 백엔드 테스트(실제 DB 통합 검사 포함) · 백엔드 이미지 빌드·푸시 · Flutter 테스트 · 문서 배포 | GitHub Actions | — |

파이프라인 구간별 세부 기술은 아래 3)절 「파이프라인 기술 스택」, 판정 모델
선정 근거는 4)절 「모델 선정」에 있다.

### 클립 한 건이 리포트가 되기까지

1. 화면이 **업로드 자리**(사전 서명 URL)를 API 서버에 요청한다.
2. 원본 클립을 **객체 저장소에 직접** 올린다 — 서버 대역폭·저장소를 쓰지 않는다(PER-002).
3. 클립을 **등록**하면 API 서버가 규칙(용량 200MB · 길이 60초 · 해상도 4K 이하 등)으로
   검사한다. **반려돼도 등록 기록은 남긴다.** 통과하면 분석 작업을 대기열에 넣는다.
   같은 사람이 **같은 내용을 다시 올리면** 새 작업을 만들지 않고 앞 결과를 가리킨다.
4. GPU 워커가 API 서버를 불러 작업을 **가져가고**(대기 → 실행), 분석 산출물을 저장소에
   올린 뒤 **완료를 보고**한다. 보고 없이 30분 멈춘 작업은 한 번은 대기열로 되돌리고,
   두 번째는 실패로 끝낸다.
5. API 서버가 워커의 **리포트 봉투**(규격을 계약으로 고정한 JSON)를 읽어 DB에 적재한다.
6. 본인에게는 리포트 전체를, 남에게는 **등급·카드 불릿 같은 좁은 칸만** 보여 준다.
   추천 판과 매칭이 그 값을 쓴다.

> **상태:** 1\\~6 구현됨(2026-09-17). 선수 성향 비교용 벡터는 아직이다.

### 배포 형태

API 서버·DB·객체 저장소는 클라우드(AWS `ap-northeast-2`)에 둔다. API 서버는 클라우드
서버 위 **k3s** 에서 컨테이너로 돌고(2026-09-11 서비스 관리자에서 전환), DB는 같은 서버에
직접 설치돼 있다. 그 앞에 **Cloudflare 프록시와 nginx** 가 있고, GPU 워커도 같은 공개
경로로 API 서버를 부른다 — 그래서 앞단 규칙이 워커를 막으면 백엔드 로그에 흔적 없이 분석이
멈춘다(2026-09-16 실제로 겪었다). 웹은 Vercel 에, 분석 워커는 쓸 때만 켜는 별도 GPU
인스턴스에 둔다. 배포 절차·롤백 런북은 개발 저장소 문서로 관리한다.

"""

s = TARGET.read_text(encoding="utf-8")
start = s.index("## 1) 시스템 구성도")
end = s.index("## 2) 데이터베이스 설계")
TARGET.write_text(s[:start] + SECTION + s[end:], encoding="utf-8", newline="\n")
print("ok")
