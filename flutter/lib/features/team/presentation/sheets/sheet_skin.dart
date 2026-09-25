/// 팀 시트들이 **나눠 쓰는 면·색·틀**.
///
/// 🔴 **값을 새로 짓지 않는다.** 시트는 홈 위로 올라오므로 조금만 달라도 다른
/// 앱처럼 보인다 — 줄이 앉는 면은 홈 아래 판과 같은 [kSheetPaper] 다
/// (2026-09-25 사용자 요청).
///
/// 🔴 **금빛은 안 쓴다**(같은 날 사용자: 「눌렀을 때 노란색 빼고 실버로 다
/// 해라」). 고른 것은 **테가 도는 것**으로 알린다.
library;

import 'package:flutter/material.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../../core/widgets/silver_edge.dart';

/// 시트 바탕 — 거의 검정.
const Color kSheetInk = Color(0xFF0B0B0B);

/// 검은 면 위의 글자.
const Color kSheetOn = Color(0xFFFFFFFF);
const Color kSheetOnDim = Color(0x8AFFFFFF);

/// 줄·칸이 앉는 밝은 면 — 홈 아래 판과 같은 값이다.
const Color kSheetBox = kSheetPaper;

/// 밝은 면 위의 글자. 🔴 검은 화면용 흰 글자를 그대로 두면 안 보인다.
const Color kSheetBoxInk = Color(0xFF14161A);

/// 안 고른 것의 테 — 아주 얇게.
const Color kSheetEdge = Color(0x59C9D4D8);
const double kSheetEdgeWidth = 0.6;

/// 실버 한 벌의 출처. 🔴 값을 베껴 적지 않는다.
const Color kSheetSilver = SilverEdge.silver;

/// 「됐다」를 알리는 초록 — 이미 앉은 지인의 `✓ 자리` 같은 자리.
///
/// 🔴 **밝은 면([kSheetBox])용이다.** `AppTheme.seed`(`#70ED88`)는 검은
/// 화면용이라 이 면에서 대비가 2:1 도 안 나온다 — 1.27이 리포트에서 겪고
/// 내린 값을 그대로 쓴다.
const Color kSheetGreen = Color(0xFF1E7F45);

/// 시트의 바깥 틀 — 손잡이 · 머리말 · 닫기.
class SheetShell extends StatelessWidget {
  const SheetShell({
    super.key,
    required this.title,
    required this.child,
    this.heightFactor = 0.86,
  });

  final String title;
  final Widget child;
  final double heightFactor;

  @override
  Widget build(BuildContext context) => Container(
        height: MediaQuery.sizeOf(context).height * heightFactor,
        decoration: const BoxDecoration(
          color: kSheetInk,
          borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
        ),
        /* 🔴 **유리 안에 유리를 넣지 않는다**(`refractive_glass.dart`).
           시트는 알파만 쓴 면이고, 안쪽 줄들은 흐림 없이 색만 얹는다. */
        child: Column(
          children: [
            Container(
              width: 40,
              height: 4,
              margin: const EdgeInsets.only(top: 10, bottom: 6),
              decoration: BoxDecoration(
                color: kSheetOn.withValues(alpha: 0.22),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 6, 8, 8),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      title,
                      style: const TextStyle(
                        color: kSheetOn,
                        fontSize: 18,
                        fontWeight: FontWeight.w600,
                        letterSpacing: -0.2,
                      ),
                    ),
                  ),
                  IconButton(
                    tooltip: '닫기',
                    onPressed: () => Navigator.of(context).pop(),
                    icon: Icon(Icons.close,
                        color: kSheetOn.withValues(alpha: 0.7)),
                  ),
                ],
              ),
            ),
            Expanded(child: child),
          ],
        ),
      );
}

/// 밝은 면 위의 입력칸 꾸밈.
InputDecoration sheetInput(String hint) => InputDecoration(
      hintText: hint,
      hintStyle: TextStyle(color: kSheetBoxInk.withValues(alpha: 0.42)),
      isDense: true,
      contentPadding: const EdgeInsets.symmetric(vertical: 10),
      enabledBorder: UnderlineInputBorder(
        borderSide:
            BorderSide(color: kSheetBoxInk.withValues(alpha: 0.25)),
      ),
      focusedBorder: UnderlineInputBorder(
        borderSide: BorderSide(color: kSheetBoxInk.withValues(alpha: 0.6)),
      ),
    );

class SheetSpinner extends StatelessWidget {
  const SheetSpinner({super.key});

  @override
  Widget build(BuildContext context) => SizedBox(
        width: 22,
        height: 22,
        child: CircularProgressIndicator(
          strokeWidth: 2,
          color: kSheetOn.withValues(alpha: 0.4),
        ),
      );
}

class SheetMessage extends StatelessWidget {
  const SheetMessage({super.key, required this.title, required this.detail});

  final String title;
  final String detail;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              title,
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: kSheetOn,
                fontSize: 15,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 7),
            Text(
              detail,
              textAlign: TextAlign.center,
              style: TextStyle(
                color: kSheetOn.withValues(alpha: 0.5),
                fontSize: 13,
                height: 1.4,
              ),
            ),
          ],
        ),
      );
}
