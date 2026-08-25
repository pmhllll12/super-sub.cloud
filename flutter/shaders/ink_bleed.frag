#include <flutter/runtime_effect.glsl>

// 기본 정밀도로는 안 된다. 문턱값과 지도값의 차가 작아 mediump에서는
// 자릿수를 잃고 알갱이가 뭉텅이로 떨어진다.
precision highp float;

uniform vec2 uSize;       // 0,1  그리는 영역 (논리 픽셀 — 아래 주의)
uniform float uProgress;  // 2    잉크 진행도 0~1
uniform float uSeed;      // 3    프레임마다 바뀌는 정수 씨앗
uniform float uBoil;      // 4    끓음 최대 폭 (0이면 안 끓는다)
uniform float uEdge;      // 5    문턱 경계 폭
uniform float uErase;     // 6    0이면 잉크가 번지고, 1이면 물러난다
uniform vec3 uInk;        // 7,8,9  잉크 색 (0~1)
uniform sampler2D uField; // sampler 0  잉크가 앉는 순서 지도 (샘플러는 float
                           //            유니폼과 별도 인덱스 공간이다 — Dart는
                           //            setImageSampler(0, …)로 부른다)

out vec4 fragColor;

// 좌표 해시. sin 기반은 기기마다 정밀도가 갈리므로 곱셈·소수부 쪽을 쓴다.
//
// **알갱이 크기가 지도와 여기서 다르다 — 알고 그대로 둔 것이다.**
// `make_ink_field.py`가 구운 지도의 점은 `GRAIN_PX`(2) 기기 픽셀짜리인데,
// 이 해시는 `frag`(1 기기 픽셀)마다 다른 값을 낸다 — 가라앉은 잉크는 2px
// 점인데 끓는 경계는 1px로 지글거린다는 뜻이다. 2026-08-13에 실기기로
// 나란히 보고 **거슬리지 않아 그대로 두기로 했다** — 경계가 더 잘게
// 지글거리는 편이 자연스럽다. 맞추려면 `frag`를 같은 배율로 양자화해야
// 하지만(`floor(frag / g) * g` 같은 식) 하지 않는다.
float hash(vec2 p, float seed) {
  vec3 q = fract(vec3(p.x, p.y, p.x) * 0.1031 + seed * 0.0037);
  q += dot(q, vec3(q.y, q.z, q.x) + 33.33);
  return fract((q.x + q.y) * q.z);
}

void main() {
  vec2 frag = FlutterFragCoord().xy;
  vec2 uv = clamp(frag, vec2(0.5), uSize - 0.5) / uSize;

  float order = texture(uField, uv).r;   // 낮을수록 일찍 젖는다
  float n = hash(frag, uSeed) - 0.5;

  // 끓음은 양끝에서 0이다. 흰 화면에 점이 튀지 않고, 다 젖은 뒤에도
  // 지직대지 않는다. p(1-p)의 최댓값이 0.25라 4를 곱해 1로 맞춘다.
  //
  // **참조의 마지막 5초는 밝기가 ±0.05로 평탄했다.** 끝에서 안 멎으면
  // 검은 화면이 지직거리는 꼴이 된다.
  float boil = uBoil * uProgress * (1.0 - uProgress) * 4.0;

  // 지도가 랭크 정규화라 order의 최솟값이 정확히 0.0, 최댓값이 정확히
  // 1.0이다. **그냥 `uProgress`를 문턱값으로 쓰면 안 된다** — `uProgress=0`
  // 이 `order=0`인 픽셀과 정확히 맞닿아 `smoothstep(order-uEdge,
  // order+uEdge, 0)`이 그 픽셀에 알파 0.5를 준다. 순백이어야 할 첫
  // 프레임에 부분 착색 픽셀이 남는 원인이었다(실측: 59,464개, 2.35%,
  // 화면 평균 밝기 253.78 — 255가 아니었다). 문턱값의 범위를
  // `[-uEdge, 1+uEdge]`로 넓혀 `uProgress=0`에서 문턱값이 -uEdge까지
  // 내려가야 `order=0` 픽셀도 완전히 바깥(0)이 되고, `uProgress=1`에서는
  // 반대로 `order=1` 픽셀도 완전히 안쪽(1)이 된다.
  float t = mix(-uEdge, 1.0 + uEdge, uProgress) + n * boil;
  float inked = smoothstep(order - uEdge, order + uEdge, t);

  // **`uErase`가 1이면 알파를 뒤집는다 — 같은 지도로 반대 일을 한다.**
  //
  // 지도는 "가운데부터 젖는 순서"다. 그대로 쓰면 가운데부터 검어지고,
  // 뒤집으면 가운데부터 **구멍이 뚫려** 넓어진다. 인트로가 끝나고 다음
  // 화면으로 넘어갈 때, 검은 화면이 글자 있던 자리부터 점으로 벗겨지며
  // 그 틈으로 다음 화면이 드러나는 것이 이것이다.
  //
  // 양 끝도 그대로 맞는다 — `uProgress=0`이면 inked가 0이라 뒤집으면 1
  // (화면이 온전히 검다), `=1`이면 0이 되어 말끔히 사라진다.
  //
  // **프리멀티플라이드로 낸다** — rgb에 알파를 미리 곱해서 낸다. 검정일
  // 때는 rgb가 0이라 안 곱해도 같았지만, 색이 붙으면 안 곱한 값은 가장자리
  // 반투명 화소에서 색이 진하게 뜬다.
  float a = mix(inked, 1.0 - inked, uErase);
  fragColor = vec4(uInk * a, a);
}
