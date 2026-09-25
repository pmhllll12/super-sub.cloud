import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/team/data/match_repository.dart';
import 'package:super_sub/features/team/match_prefs.dart';

/// MatchRepository 의 모든 구현체가 지켜야 하는 계약 —
/// 계약 3-13절(조건) · 「맞는 상대」 · 3-15절(팀 대 팀 신청).
///
/// 🔴 프로토콜의 성질만 둔다 — 구현체별 의무(Mock 의 지연·자동 수락, API 의
/// 요일 변환)는 각자의 테스트 파일로.
void runMatchRepositoryContract(
  String name,
  MatchRepository Function() build, {
  required String myTeamId,
  required String teamWithoutPrefs,
  required String knownRegion,
}) {
  group('$name — MatchRepository 계약', () {
    late MatchRepository repo;

    setUp(() => repo = build());

    test('지역 목록에는 id 와 이름이 함께 온다', () async {
      final regions = await repo.regions();

      expect(regions, isNotEmpty);
      expect(regions.every((r) => r.id.isNotEmpty && r.label.isNotEmpty), isTrue);
      expect(regions.any((r) => r.label == knownRegion), isTrue);
    });

    /// 🔴 **약칭이 아니라 id 가 있어야 한다** — 계약이 `position_ids` 를 받고,
    /// 약칭은 종목 안에서만 유일해서 그것만으로는 한 줄을 못 가리킨다.
    test('포지션 목록에는 id 가 온다', () async {
      final positions = await repo.positions('football');

      expect(positions, isNotEmpty);
      expect(positions.every((p) => p.id.isNotEmpty), isTrue);
    });

    /// 🔴 **아직 안 정했으면 `null`** 이다 — 빈 조건과 갈라야 「처음이라
    /// 물어야 하는가」가 정해진다.
    test('조건을 안 정했으면 null 이다', () async {
      expect(await repo.teamPrefs(teamWithoutPrefs), isNull);
    });

    test('조건을 저장하고 다시 읽는다', () async {
      const prefs = MatchPrefs(
        regions: [],
        times: [TimeSlot(day: 6, from: '10:00', to: '12:00')],
      );
      final saved = prefs.copyWith(regions: [knownRegion]);

      await repo.saveTeamPrefs(myTeamId, saved);
      final read = await repo.teamPrefs(myTeamId);

      expect(read, isNotNull);
      expect(read!.regions, [knownRegion]);
      expect(read.times, hasLength(1));
      expect(read.times.single.day, 6, reason: '요일이 밀리면 안 된다');
      expect(read.times.single.from, '10:00');
    });

    /// 🔴 **통째로 교체다**(계약) — 부분 수정이 아니다.
    test('다시 저장하면 앞의 것이 남지 않는다', () async {
      await repo.saveTeamPrefs(
        myTeamId,
        MatchPrefs(regions: [knownRegion], times: const [
          TimeSlot(day: 6, from: '10:00', to: '12:00'),
          TimeSlot(day: 0, from: '10:00', to: '12:00'),
        ]),
      );
      await repo.saveTeamPrefs(
        myTeamId,
        MatchPrefs(regions: [knownRegion], times: const [
          TimeSlot(day: 1, from: '18:00', to: '20:00'),
        ]),
      );

      final read = await repo.teamPrefs(myTeamId);
      expect(read!.times, hasLength(1));
      expect(read.times.single.day, 1);
    });

    /// 🔴 뒤집힌 시간은 겹침 계산에서 **늘 거짓**이라 조용히 아무것도 안
    /// 걸린다 — 서버가 422 로 막는 까닭이다.
    test('끝이 시작보다 빠르면 저장되지 않는다', () async {
      await expectLater(
        repo.saveTeamPrefs(
          myTeamId,
          MatchPrefs(regions: [knownRegion], times: const [
            TimeSlot(day: 6, from: '12:00', to: '10:00'),
          ]),
        ),
        throwsA(anything),
      );
    });

    test('맞는 상대 후보를 읽는다', () async {
      final list = await repo.candidates(myTeamId);

      expect(list, isNotEmpty);
      expect(list.every((t) => t.name.isNotEmpty), isTrue);
      expect(list.every((t) => t.regionLabel.isNotEmpty), isTrue);
    });

    /// 🔴 **근거는 서버가 준 사실값 문장 그대로**다 — 화면이 겹침을 다시
    /// 계산하지 않는다(계약의 「하지 말 것」). 빈 배열도 정상이다.
    test('근거가 비어 있어도 목록에 남는다', () async {
      final list = await repo.candidates(myTeamId);

      expect(list.every((t) => t.reasons.isNotEmpty), isFalse,
          reason: '근거 없는 후보도 하드 필터는 통과했다');
    });

    test('경기를 신청하면 대기중으로 돌아온다', () async {
      final list = await repo.candidates(myTeamId);

      final req = await repo.requestMatch(
        myTeamId,
        targetTeamId: list.first.teamId,
        playedAt: '2026-10-03T11:00:00+09:00',
        place: '강남 풋살장',
      );

      expect(req.targetTeamId, list.first.teamId);
      expect(req.isPending, isTrue);
      expect(req.matchId, isNull, reason: '수락 전에는 경기가 없다');
    });

    /// 🔴 같은 상대에 **겹쳐 걸 수 없다**(409) — 안 막으면 시연 중에 같은
    /// 팀에 신청이 쌓인다.
    test('같은 상대에 겹쳐 걸 수 없다', () async {
      final list = await repo.candidates(myTeamId);
      final target = list.first.teamId;

      await repo.requestMatch(myTeamId,
          targetTeamId: target,
          playedAt: '2026-10-03T11:00:00+09:00',
          place: '강남 풋살장');

      await expectLater(
        repo.requestMatch(myTeamId,
            targetTeamId: target,
            playedAt: '2026-10-04T11:00:00+09:00',
            place: '강남 풋살장'),
        throwsA(anything),
      );
    });

    /// 🔴 **문구를 앱에 박지 않는다** — 정본은 `GET /review-options` 이고,
    /// **배열 순서가 곧 노출 순서**다(계약). 알파벳순으로 정렬하면 「주의」가
    /// 맨 앞에 온다.
    test('평가 항목을 서버가 준 순서 그대로 읽는다', () async {
      final opts = await repo.reviewOptions();

      expect(opts, isNotEmpty);
      expect(opts.first.category, isNot('caution'),
          reason: '주의가 맨 앞에 오면 순서를 건드린 것이다');
      expect(opts.every((o) => o.code.isNotEmpty && o.label.isNotEmpty), isTrue);
      expect(opts.any((o) => o.category == 'caution'), isTrue);
    });

    /// 🔴 **점수가 없다**(계약) — 고른 항목만 보낸다.
    test('평가를 낸다', () async {
      await repo.submitReview(
        'm-1',
        revieweeId: 'u-1',
        optionCodes: const ['manner_time'],
      );
    });

    /// 🔴 **경기당 1회**(DB 유일 제약) — 두 번째는 409 다.
    test('같은 사람을 두 번 평가하지 못한다', () async {
      await repo.submitReview('m-1',
          revieweeId: 'u-1', optionCodes: const ['manner_time']);

      await expectLater(
        repo.submitReview('m-1',
            revieweeId: 'u-1', optionCodes: const ['manner_time']),
        throwsA(anything),
      );
    });

    /// 🔴 하나도 안 고르면 422 `NO_OPTION_SELECTED` — 빈 평가는 뜻이 없다.
    test('아무것도 안 고르면 못 낸다', () async {
      await expectLater(
        repo.submitReview('m-1', revieweeId: 'u-2', optionCodes: const []),
        throwsA(anything),
      );
    });

    /// 🔴 **걸어 둔 신청을 무를 수 있어야 한다** (2026-09-25, 사용자가
    /// 실기기에서 막혔다: 「3팀 다 수락 대기중에서 아무것도 안먹히는데」).
    /// 상대가 답을 안 하면 그 팀은 **영영 잠긴 채**로 남는다 — 계약도
    /// `DELETE …/match-requests/{id}` 를 그 자리에 뒀다.
    test('건 신청을 무른다', () async {
      final list = await repo.candidates(myTeamId);
      final made = await repo.requestMatch(
        myTeamId,
        targetTeamId: list.first.teamId,
        playedAt: '2026-10-03T11:00:00+09:00',
        place: '강남 풋살장',
      );

      await repo.cancelRequest(myTeamId, requestId: made.id);

      final after = await repo.requests(myTeamId);
      expect(after.where((r) => r.id == made.id).every((r) => r.isPending),
          isFalse, reason: '무른 신청은 대기중이 아니다');
    });

    /// 🔴 **무른 뒤에는 다시 걸 수 있다** — 안 그러면 무르는 뜻이 없다.
    test('무른 뒤 같은 팀에 다시 건다', () async {
      final list = await repo.candidates(myTeamId);
      final target = list.first.teamId;
      final made = await repo.requestMatch(myTeamId,
          targetTeamId: target,
          playedAt: '2026-10-03T11:00:00+09:00',
          place: '강남 풋살장');
      await repo.cancelRequest(myTeamId, requestId: made.id);

      await repo.requestMatch(myTeamId,
          targetTeamId: target,
          playedAt: '2026-10-04T11:00:00+09:00',
          place: '강남 풋살장');
    });

    test('신청의 답을 다시 읽을 수 있다', () async {
      final list = await repo.candidates(myTeamId);
      final made = await repo.requestMatch(
        myTeamId,
        targetTeamId: list.first.teamId,
        playedAt: '2026-10-03T11:00:00+09:00',
        place: '강남 풋살장',
      );

      final all = await repo.requests(myTeamId);
      expect(all.any((r) => r.id == made.id), isTrue);
    });
  });
}
