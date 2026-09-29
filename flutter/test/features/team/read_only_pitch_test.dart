import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/profile/presentation/widgets/player_card_view.dart';
import 'package:super_sub/features/team/data/models/squad.dart';
import 'package:super_sub/features/team/presentation/widgets/read_only_pitch.dart';

SquadMember _m(String nickname, String slug, String pos, int col, int row) =>
    SquadMember(
      id: 'm-$nickname',
      playerCardId: 'pc',
      cardPublicSlug: slug,
      nickname: nickname,
      positionCode: pos,
      positionLabel: pos,
      gridCol: col,
      gridRow: row,
      accepted: true,
    );

Future<void> _pump(WidgetTester tester, Widget pitch) async {
  tester.view.physicalSize = const Size(1080, 2340);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    MaterialApp(home: Scaffold(body: SizedBox(height: 500, child: pitch))),
  );
  await tester.pump();
}

void main() {
  final squad = Squad(
    id: 's',
    teamId: 't',
    publicSlug: 'p',
    formation: '5:5',
    members: [_m('정상호', 'ho-1', 'FW', 1, 0)],
  );

  /// 🔴 **진짜 카드가 먼저다** (2026-09-25 사용자 요청). 이름 상자는 못
  /// 읽었을 때의 물러남이지 기본형이 아니다.
  testWidgets('카드가 있으면 그 카드를 그린다', (tester) async {
    await _pump(
      tester,
      ReadOnlyPitch(
        title: '우리 팀',
        squad: squad,
        cardBuilder: (slug, w) => PlayerCardView(width: w, seed: slug),
      ),
    );

    expect(find.byType(PlayerCardView), findsOneWidget);
  });

  /// 못 읽었으면 **빈 카드에 이름** — 홈 판과 같다.
  testWidgets('카드가 없으면 빈 카드에 이름을 쓴다', (tester) async {
    await _pump(
      tester,
      ReadOnlyPitch(title: '우리 팀', squad: squad, cardBuilder: (_, _) => null),
    );

    expect(find.byType(BlankPlayerCardView), findsWidgets);
    expect(find.text('정상호'), findsOneWidget);
  });

  /// 🔴 **자리가 빈 칸에는 카드를 안 세운다** — 포지션만 옅게 둔다.
  testWidgets('빈 자리는 포지션만 남는다', (tester) async {
    await _pump(tester, const ReadOnlyPitch(title: '우리 팀'));

    expect(find.byType(BlankPlayerCardView), findsNothing);
    expect(find.text('GK'), findsOneWidget);
  });
}
