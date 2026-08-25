import 'chat_repository.dart';

/// 규칙 몇 개로 답하는 가짜 에이전트.
///
/// **진짜처럼 굴어야 한다** — 지연을 넣고, 빈 물음은 예외를 던진다. 즉시
/// 답하면 화면이 기다리는 동안의 표시를 안 만들게 되고, API를 붙이는 날
/// 대화창을 다시 짠다.
class MockChatRepository implements ChatRepository {
  static const _delay = Duration(milliseconds: 700);

  /// 물음에 들어 있으면 그 답을 내놓는다. 위에서부터 먼저 맞는 것을 쓴다.
  static const _rules = <(List<String>, String)>[
    (
      ['안녕', '하이', 'hello'],
      '안녕하세요. 올리신 영상을 보고 실력과 성향을 정리해 드립니다. '
          '무엇이 궁금하신가요?',
    ),
    (
      ['포지션', '자리'],
      '영상에서 뽑은 활동 범위와 스프린트 구간을 보면 측면 쪽 움직임이 많습니다. '
          '지표가 쌓이면 종목별 포지션 정의에 맞춰 다시 짚어 드리겠습니다.',
    ),
    (
      ['실력', '점수', '평가', '어때'],
      '실력은 하나의 점수로 내지 않습니다. 수준·역할·성향 세 축을 따로 보여 '
          '드리는 것이 이 앱의 방식입니다. 영상을 올리시면 축별로 정리해 '
          '드리겠습니다.',
    ),
    (
      ['영상', '업로드', '올리'],
      '위 판을 눌러 바로 찍거나 앨범에서 고르시면 됩니다. 한 번 분석에 크레딧 '
          '1개가 듭니다.',
    ),
    (
      ['호칭', '카드'],
      '호칭은 기준을 넘긴 것만 드립니다. 못 받은 호칭은 아예 보여 드리지 '
          '않습니다 — 못 넘긴 표시가 남으면 그게 낙인이 되니까요.',
    ),
    (
      ['크레딧', '요금', '가격'],
      '분석 1건에 크레딧 1개가 차감됩니다. 남은 양은 하단 바 메뉴의 분석 '
          '크레딧에서 볼 수 있습니다.',
    ),
  ];

  @override
  Future<String> ask(String question) async {
    final q = question.trim();
    if (q.isEmpty) {
      throw const ChatException('물어볼 내용을 적어 주세요');
    }
    await Future<void>.delayed(_delay);
    for (final (keys, answer) in _rules) {
      if (keys.any(q.contains)) return answer;
    }
    return '아직 영상이 없어서 그 질문에는 근거를 댈 수 없습니다. '
        '영상을 올려 주시면 지표를 뽑아 답해 드리겠습니다.';
  }
}
