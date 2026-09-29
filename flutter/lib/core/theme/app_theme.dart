import 'package:flutter/material.dart';

/// 판 · 하단바 · 로고 알약이 **나눠 쓰는 반투명 흰 면**(2026-09-22, 사용자가
/// 보낸 레퍼런스: 「흰색 살짝만 들어간 판으로 뒤에 비치긴 해야해」).
///
/// 🔴 **흐림이 아니다.** 레퍼런스는 간유리(blur)처럼 보이지만 이 저장소는
/// `BackdropFilter` 를 안 쓴다 — 흐림은 판 가장자리에서 퍼 올 것이 없어
/// 가장자리 값을 늘려 쓰고, 목록이 구르면 그 띠가 매 프레임 달라져 **흰
/// 직선**으로 보인다(2026-09-22에 세 번 고친 그것). 여기서는 **알파만** 쓴다 —
/// 뒤가 비치는 것은 같고, 가장자리에서 퍼 올 것이 없어도 아무 일이 안 난다.
///
/// 🔴 **셋이 같은 값이어야 한다.** 갈리면 알약이 바에서 떠 보이거나 판이
/// 층층이 다른 재질로 읽힌다.
/// 🔴 **10% → 30% → 18%**(2026-09-22, 사용자가 화면을 보고 두 번 정했다).
/// 10%(`#1A1A1A`)는 「흰색 맞냐」는 물음이 나올 만큼 어두웠고, 30%(`#4D4D4D`)는
/// 과했다. 18% 는 검은 바탕에서 `#2E2E2E` 다.
const Color kSurfaceWhite = Color(0x2EFFFFFF);

/// 홈의 **아래 판**(스쿼드·영상 분석 카드를 받치는 밝은 회색 판)과 「영상 분석」
/// 화면의 **흰 판**이 나눠 쓰는 면 (2026-09-25 사용자 요청: 「완전 흰색보다는
/// 그 홈페이지에서 스쿼드판 있는 그 판의 살짝 어두운 흰색」).
///
/// 🔴 **값을 베껴 적지 말 것.** 두 화면이 나란히 놓이는 자리라 조금만 달라도
/// **다른 판처럼** 보이고, 한쪽만 고치면 그 차이가 조용히 생긴다 — 그래서
/// 출처를 여기 하나로 뒀다.
///
/// ⚠️ 순백이 아니다. 순백은 어두운 화면에서 형광등처럼 튄다.
const Color kSheetPaper = Color(0xFFE4E9E7);

class AppTheme {
  const AppTheme._();

  static const seed = Color(0xFF70ED88);

  static ThemeData get light => ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(seedColor: seed),
        appBarTheme: const AppBarTheme(centerTitle: true),
      );

  static ThemeData get dark => ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: seed,
          brightness: Brightness.dark,
        ),
        appBarTheme: const AppBarTheme(centerTitle: true),
      );
}
