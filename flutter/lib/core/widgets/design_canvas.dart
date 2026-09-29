import 'package:flutter/widgets.dart';

/// 화면을 짜던 **기준 기기**의 논리 크기 — 411×891(SM-A366N, 상태 바 포함).
///
/// 🔴 **여기가 도면이다.** 모든 화면은 이 크기에서 만들어졌고, 다른 기기에서는
/// [DesignCanvas] 가 통째로 확대·축소만 한다.
const Size kDesignSize = Size(411, 891);

/// 🔴 **도면 한 장을 통째로 늘였다 줄인다** (2026-09-29 사용자 요청: 「다른
/// 어떤 휴대폰이든 그 휴대폰의 비율에 맞게(대신 내 휴대폰에서 보는 그 비율대로
/// 다른 사용자의 휴대폰에도 비율이 동일하게) 자동으로 고쳐지는건 안돼?」).
///
/// ⚠️ **전에는 화면마다 고정 픽셀을 쌓았다.** 그래서 세로가 짧은 폰에서
/// 홈 영상 줄이 통째로 사라지고 인사말이 판에 덮였다(720×1280 에서 재현했다).
/// 조각조각 줄이는 방법도 해 봤지만 **요소마다 비율이 달라져** 사용자가
/// 「글자나 버튼 판들이 휴대폰 길이마다 다 달라져서 별로」라고 했다.
///
/// 🔴 **배율은 한 개다** — `min(폭/411, 높이/891)`. 가로·세로를 따로 늘이면
/// 그림이 찌그러진다. 그래서 **비율이 다른 기기에서는 남는 쪽에 여백**이
/// 생긴다(9:16 폰에서 위아래). 사용자가 그 대가를 알고 고른 것이다:
/// 「9:16 은 당연히 어쩔 수 없잖아. 여백생기는게 맞지」.
///
/// ⚠️ **작은 폰에서는 글자가 물리적으로 작아진다** — 비율은 같지만 실제
/// 크기는 준다. 시스템 글꼴 배율(`clampTextScale`)과는 다른 축이다.
///
/// 🔴 **기준보다 큰 화면에서는 키운다**(태블릿). 안 키우면 도면이 화면
/// 가운데에 작게 떠서 둘레가 통째로 빈다.
class DesignCanvas extends StatelessWidget {
  const DesignCanvas({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final view = MediaQuery.of(context);
    final size = view.size;
    if (size.isEmpty) return child;

    final scale = _scaleFor(size);

    /* 🔴 **안쪽은 자기가 도면 크기라고 믿는다.** `MediaQuery` 를 갈아 끼워
       `size`·`padding` 을 도면 좌표로 바꿔 준다 — 안 그러면 `SafeArea` 와
       `MediaQuery.sizeOf` 를 쓰는 화면들이 **실제 기기 값**을 보고 도면과
       어긋난 자리를 잡는다. */
    final inner = view.copyWith(
      size: kDesignSize,
      padding: _scaleInsets(view.padding, scale),
      viewPadding: _scaleInsets(view.viewPadding, scale),
      viewInsets: _scaleInsets(view.viewInsets, scale),
    );

    return ColoredBox(
      // 여백은 앱 바탕과 같은 검정이라 「띠」로 안 읽힌다.
      color: const Color(0xFF000000),
      child: Center(
        child: SizedBox(
          width: kDesignSize.width * scale,
          height: kDesignSize.height * scale,
          child: FittedBox(
            fit: BoxFit.fill,
            child: SizedBox(
              width: kDesignSize.width,
              height: kDesignSize.height,
              child: MediaQuery(data: inner, child: child),
            ),
          ),
        ),
      ),
    );
  }
}

/// 기기 크기에서 도면 배율을 구한다 — 🔴 **둘 중 작은 쪽**이라야 다 들어간다.
@visibleForTesting
double scaleFor(Size device) => _scaleFor(device);

double _scaleFor(Size device) {
  final byWidth = device.width / kDesignSize.width;
  final byHeight = device.height / kDesignSize.height;
  return byWidth < byHeight ? byWidth : byHeight;
}

/// 기기 여백(상태 바·홈 인디케이터)을 도면 좌표로 옮긴다.
///
/// 🔴 **나눈다**(곱하지 않는다) — 도면 안쪽은 축소되기 **전** 좌표계다.
EdgeInsets _scaleInsets(EdgeInsets v, double scale) => EdgeInsets.fromLTRB(
      v.left / scale,
      v.top / scale,
      v.right / scale,
      v.bottom / scale,
    );
