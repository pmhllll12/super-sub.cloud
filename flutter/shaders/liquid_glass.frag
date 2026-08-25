#include <flutter/runtime_effect.glsl>

// 좌표계 주의: FlutterFragCoord()는 이 필터가 걸리는 레이어(=화면)의 물리
// 픽셀이다. 위젯의 지역 좌표도, 논리 픽셀도 아니다. 그래서 바의 왼쪽 위
// 모서리를 uOrigin으로 받아 빼고, 기하값도 전부 물리 픽셀로 받는다.
uniform vec2 uSize;        // floats 0,1   — 엔진이 채운다
uniform vec2 uOrigin;      // floats 2,3   — 바 왼쪽 위 모서리
uniform vec4 uNotch;       // floats 4..7  — left, right, depth, radius
uniform float uWarpScale;  // float 8      — 물결 한 주기의 길이(px). 클수록 느긋하다
uniform float uWarp;       // float 9      — 변위 크기(px)
uniform float uDispersion; // float 10     — 채널 분산 비율
uniform float uStrength;   // float 11     — 스크롤 세기 0~1
uniform float uDebug;      // float 12     — 0이 아니면 SDF 영점만 그린다
uniform float uShape;      // float 13     — 0이면 홈 파인 바, 1이면 둥근 사각형
uniform sampler2D uTexture;

out vec4 fragColor;

float sdRoundBox(vec2 p, vec2 b, float r) {
  vec2 q = abs(p) - b + r;
  return min(max(q.x, q.y), 0.0) + length(max(q, 0.0)) - r;
}

// 길이 0인 선분도 받는다 — 반경이 깊이의 절반까지 차면 홈의 옆벽이 점으로
// 줄어든다. 그때 나누기를 그대로 하면 NaN이 min 사슬을 타고 번진다.
float sdSegment(vec2 p, vec2 a, vec2 b) {
  vec2 pa = p - a;
  vec2 ba = b - a;
  float dd = dot(ba, ba);
  float h = dd > 0.0 ? clamp(dot(pa, ba) / dd, 0.0, 1.0) : 0.0;
  return length(pa - ba * h);
}

// 중심 c, 반경 r인 원의 4분 호까지의 거리. u1·u2는 호의 양 끝을 가리키는
// 서로 직교하는 단위벡터다. 그 사이 부채꼴 밖이면 가까운 끝점까지 잰다.
float sdArcQuarter(vec2 p, vec2 c, float r, vec2 u1, vec2 u2) {
  vec2 v = p - c;
  if (dot(v, u1) >= 0.0 && dot(v, u2) >= 0.0) {
    return abs(length(v) - r);
  }
  return min(length(v - u1 * r), length(v - u2 * r));
}

// 유리 조각의 부호거리. p는 조각 왼쪽 위 모서리 기준. 안쪽이 음수다.
//
// uShape가 1이면 그냥 둥근 사각형이다(로고 알약). 그때 uNotch는 뜻이
// 달라진다 — x는 0~right, y는 0~depth인 사각형이고 left는 안 쓴다.
//
// 매끄러운 뺄셈(smoothSubtract)으로 근사하면 입구 필렛이 실제 아크와
// 최대 2.9px 어긋난다 — 다항식 혼합은 원호가 아니라 포물선을 그린다.
// 그래서 윤곽을 이루는 아크 넷과 선분 다섯까지의 거리를 각각 재고 최소값을
// 취한다. 부호는 안팎 판정으로 따로 붙인다. 길지만 결과가 결정적이다.
float barSdf(vec2 p) {
  if (uShape > 0.5) {
    // half는 GLSL 예약어라 못 쓴다.
    vec2 halfSize = vec2(uNotch.y, uNotch.z) * 0.5;
    return sdRoundBox(
        p - halfSize, halfSize, min(uNotch.w, min(halfSize.x, halfSize.y)));
  }

  float left = uNotch.x;
  float right = uNotch.y;
  float depth = uNotch.z;
  // 반경이 자리보다 크면 위 필렛과 아래 라운드가 겹친다. Dart의 클리퍼가
  // 쓰는 것과 같은 식으로 조인다 — 두 기하가 갈라지면 안 된다.
  float r = min(uNotch.w, min(depth * 0.5, (right - left) * 0.5));

  // 바 바깥까지 확실히 뻗는 길이. 좌·우 윗변은 화면 밖에서 끝난다.
  float far = uSize.x + uSize.y;

  vec2 mL = vec2(left - r, r);        // 왼쪽 입구 필렛(볼록 모서리를 만다)
  vec2 mR = vec2(right + r, r);       // 오른쪽 입구 필렛
  vec2 bL = vec2(left + r, depth - r);  // 왼쪽 바닥 라운드
  vec2 bR = vec2(right - r, depth - r); // 오른쪽 바닥 라운드

  float d = sdSegment(p, vec2(-far, 0.0), vec2(left - r, 0.0));
  d = min(d, sdArcQuarter(p, mL, r, vec2(1.0, 0.0), vec2(0.0, -1.0)));
  d = min(d, sdSegment(p, vec2(left, r), vec2(left, depth - r)));
  d = min(d, sdArcQuarter(p, bL, r, vec2(-1.0, 0.0), vec2(0.0, 1.0)));
  d = min(d, sdSegment(p, vec2(left + r, depth), vec2(right - r, depth)));
  d = min(d, sdArcQuarter(p, bR, r, vec2(1.0, 0.0), vec2(0.0, 1.0)));
  d = min(d, sdSegment(p, vec2(right, r), vec2(right, depth - r)));
  d = min(d, sdArcQuarter(p, mR, r, vec2(-1.0, 0.0), vec2(0.0, -1.0)));
  d = min(d, sdSegment(p, vec2(right + r, 0.0), vec2(far, 0.0)));

  // 홈 공동: 위로 열린 둥근 사각형. 위쪽 모서리는 화면 밖이라 안 보인다.
  float h = uSize.y + depth;
  vec2 c = vec2((left + right) * 0.5, depth - h);
  bool inCavity =
      sdRoundBox(p - c, vec2((right - left) * 0.5, h), r) < 0.0;
  // 입구 필렛이 도려낸 자리: 필렛 정사각형 안이면서 원 밖.
  bool cutL = p.x >= left - r && p.x <= left && p.y <= r &&
      length(p - mL) > r;
  bool cutR = p.x >= right && p.x <= right + r && p.y <= r &&
      length(p - mR) > r;

  bool inside = p.y >= 0.0 && !inCavity && !cutL && !cutR;
  return inside ? -d : d;
}

// 부르는 쪽이 이미 구한 barSdf(q)를 d로 받아 전방차분한다. 중심차분이면
// q±e에서 네 번을 더 불러야 하는데, barSdf는 아크 넷과 선분 다섯을 전부
// 재는 무거운 함수다. 전방차분은 두 번이면 된다.
vec2 sdfNormal(vec2 q, float d) {
  const float e = 1.0;
  vec2 g = vec2(
    barSdf(q + vec2(e, 0.0)) - d,
    barSdf(q + vec2(0.0, e)) - d
  );
  // 기울기가 0인 자리(거리장의 골)에서 normalize(vec2(0,0))은 NaN이다.
  // NaN이 좌표에 들어가면 그 픽셀이 검게 튀고 원인 찾기가 아주 어렵다.
  float len = length(g);
  return len > 1e-5 ? g / len : vec2(0.0);
}

// 바 안의 변위장. 가장자리 가중치를 쓰지 않는다 — 영역 전체에 똑같이 걸린다.
// 느린 물결 둘을 겹쳐 방향이 한쪽으로 쏠리지 않게 한다.
// 주기가 다른 층 셋을 겹쳐 규칙적인 물결무늬로 보이지 않게 한다.
//
// 가로 성분은 0.35로 눌러 둔다. 가로로 밀면 글자가 통째로 기울어 보여
// "유리"가 아니라 "비뚤어짐"으로 읽힌다. 세로로 흔들려야 흐물거린다.
vec2 warpAt(vec2 q) {
  float s = uWarpScale;
  vec2 w = vec2(sin(q.y / s), 0.35 * cos(q.x / s));
  w += 0.5 * vec2(sin(q.y / (s * 0.41) + 1.7), 0.35 * cos(q.x / (s * 0.37) + 2.3));
  w += 0.25 * vec2(sin(q.y / (s * 0.19) + 4.1), 0.35 * cos(q.x / (s * 0.23) + 0.9));
  return w * uWarp;
}

// 샘플 좌표를 바 안으로 가둔다. 아직 바에 닿지 않은 내용이 끌려 들어오면
// 안 된다는 조건을, 코드가 아니라 이 수식이 보장한다.
vec2 clampToBar(vec2 q) {
  float d = barSdf(q);
  // 바 밖(양수)이면 법선 반대로 밀어 경계 안쪽에 붙인다.
  return d > 0.0 ? q - sdfNormal(q, d) * (d + 0.5) : q;
}

// 화면 가장자리에 다가갈수록 변위를 줄인다.
//
// clampToBar는 표본을 **바 안**에만 가둔다. 그런데 바는 화면 좌·우·아래로
// 번져 있어서 "바 안이면서 화면 밖"인 자리가 있다. 거기를 읽으면 샘플러가
// 마지막 픽셀 줄을 그대로 늘려 붙여 줄무늬가 된다(실측: 바닥 줄에서 2843
// 픽셀). 뒤가 검으면 안 보이고 이미지가 오면 드러난다.
//
// 띠 폭은 변위 최대치에서 나온다. smoothstep(0,b,r)은 r/b=0.75에서 r 대비
// 가장 가파르고(1.125배), 세로 최대 변위는 uWarp의 1.75배에 분산 여유
// 1.35배라 3.0·uWarp면 어디서도 밖을 짚지 않는다. 가로는 0.35로 눌려
// 있으니 1.0·uWarp면 된다 — 좁은 왼쪽 띠의 흔들림을 살리려고 축마다 따로 준다.
vec2 fadeAtEdge(vec2 pAbs, vec2 w) {
  vec2 room = min(pAbs, uSize - pAbs);
  w.x *= smoothstep(0.0, 1.0 * uWarp, room.x);
  w.y *= smoothstep(0.0, 3.0 * uWarp, room.y);
  return w;
}

// 바 지역 좌표를 텍스처 uv로 옮긴다. 변위는 이 함수에 들어오기 **전에**
// 다 더해져 있어야 한다. 뒤집힌 uv에 변위를 더하면 세로 방향이 반대가
// 된다 — 실측으로 확인된 함정이다.
//
// 마지막 clamp는 fadeAtEdge가 이미 막은 것을 한 번 더 막는 빗장이다. 값을
// 손보다 띠 폭 계산이 어긋나도 줄무늬로 되돌아가지 않는다.
vec2 toUv(vec2 q) {
  vec2 uv = clamp(q + uOrigin, vec2(0.5), uSize - 0.5) / uSize;
#ifdef IMPELLER_TARGET_OPENGLES
  uv.y = 1.0 - uv.y;
#endif
  return uv;
}

void main() {
  vec2 p = FlutterFragCoord().xy;

  if (uDebug > 0.5) {
    float band = 1.0 - smoothstep(0.0, 1.5, abs(barSdf(p - uOrigin)));
    fragColor = vec4(0.0, 1.0, 0.0, 1.0) * band;
    return;
  }

  // q는 바 기준 지역 좌표다. 디버그 분기가 쓰는 것과 같은 식이다.
  vec2 q = p - uOrigin;
  vec2 w = fadeAtEdge(p, warpAt(q));

  // 채널마다 변위 크기를 달리해 조금씩 다른 자리를 읽는다. 읽는 건 같은
  // 배경 텍스처 하나뿐이라, 나오는 색은 전부 배경이 원래 갖고 있던 값이다.
  // 채널마다 따로 가둔다 — 늘어난 변위가 바 밖을 짚으면 안 닿은 내용이
  // 빨강으로만 끌려 들어온다.
  float disp = uDispersion * uStrength;

  // 세기가 0이면 읽기 한 번으로 끝낸다. 유니폼만으로 갈리는 분기라 픽셀마다
  // 갈라지지 않고, 정지 상태의 비용이 분산을 넣기 전과 같다.
  if (disp <= 0.0) {
    fragColor = texture(uTexture, toUv(clampToBar(q + w)));
    return;
  }

  // 초록과 알파는 같은 자리라 한 번만 읽는다.
  vec4 mid = texture(uTexture, toUv(clampToBar(q + w)));
  fragColor = vec4(
    texture(uTexture, toUv(clampToBar(q + w * (1.0 + disp)))).r,
    mid.g,
    texture(uTexture, toUv(clampToBar(q + w * (1.0 - disp)))).b,
    mid.a
  );
}
