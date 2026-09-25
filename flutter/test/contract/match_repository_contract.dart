import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/core/network/api_client.dart';
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

  /// **나에게 온** 신청의 id — 받은 쪽에서 답하는 갈래를 밟는다.
  required String incomingId,
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

    /// 🔴 **내 조건은 팀 조건과 저장소가 다르다**(계약 3-13절) — 같은 사람이
    /// 팀장이면서 팀원일 수 있어 **절대 안 섞는다.**
    test('내 조건을 안 정했으면 null 이다', () async {
      expect(await repo.myPrefs(), isNull);
    });

    /// 🔴 **내 조건에만 포지션이 있다** — 여기 올린 자리가 곧 남의 AI 추천
    /// 판에 뜨는 조건이다(계약).
    test('내 조건은 자리까지 저장한다', () async {
      final saved = MatchPrefs(
        regions: [knownRegion],
        times: const [TimeSlot(day: 6, from: '10:00', to: '12:00')],
        positions: const ['MF'],
      );

      await repo.saveMyPrefs(saved);
      final read = await repo.myPrefs();

      expect(read!.positions, ['MF']);
      expect(read.regions, [knownRegion]);
      expect(read.times.single.day, 6);
    });

    /// 🔴 **팀 조건과 안 섞인다** — 한쪽을 저장해도 다른 쪽은 그대로다.
    test('내 조건과 팀 조건이 안 섞인다', () async {
      await repo.saveMyPrefs(MatchPrefs(
        regions: [knownRegion],
        times: const [TimeSlot(day: 1, from: '18:00', to: '20:00')],
        positions: const ['GK'],
      ));

      expect(await repo.teamPrefs(teamWithoutPrefs), isNull);
    });

    /// 🔴 **팀 id 를 몰라도 되는 유일한 경로다**(계약) — 이것이 없으면 용병이
    /// 지원할 경기를 찾을 방법이 아예 없다.
    test('사람을 찾는 경기를 읽는다', () async {
      final list = await repo.openMatches();

      expect(list, isNotEmpty);
      expect(list.every((m) => m.teamName.isNotEmpty), isTrue);
    });

    /// 🔴 **어느 자리를 몇 명 찾는지가 함께 온다** — 그게 없으면 지원할지
    /// 판단할 수가 없다.
    test('찾는 자리가 실려 있다', () async {
      final list = await repo.openMatches();

      expect(list.any((m) => m.needs.isNotEmpty), isTrue);
    });

    /// 🔴 **종목 코드가 틀리면 빈 배열이 아니라 예외다**(계약) — 빈 배열로
    /// 답하면 오타와 「그 종목 경기가 없다」가 같아 보인다.
    test('없는 종목은 예외다', () async {
      await expectLater(
        repo.openMatches(sportCode: '없는종목'),
        throwsA(anything),
      );
    });

    /// ⚠️ 지역은 자유 문자열이라 검증할 대상이 없다 — 안 걸리면 빈 목록이다.
    test('안 걸리는 지역은 빈 목록이다', () async {
      expect(await repo.openMatches(region: '없는동네'), isEmpty);
    });

    /// 🔴 **받은 신청에 답할 수 있어야 한다** (2026-09-25 사용자: 「진짜로
    /// 서로 연결되어있어야 한다고」). 앱에서 수락한 것이 웹에 뜨는 길이
    /// 이것뿐이다.
    test('받은 신청을 수락하면 경기가 생긴다', () async {
      final got = await repo.acceptRequest(myTeamId, requestId: incomingId);

      expect(got.isAccepted, isTrue);
      expect(got.matchId, isNotNull, reason: '수락되면 경기가 생긴다');
    });

    test('받은 신청을 거절할 수 있다', () async {
      await repo.rejectRequest(myTeamId, requestId: incomingId);

      final after = await repo.requests(myTeamId);
      expect(after.where((r) => r.id == incomingId).every((r) => r.isPending),
          isFalse);
    });

    /// 🔴 **이미 답한 것은 다시 못 답한다**(409 `ALREADY_RESPONDED`).
    test('두 번 수락하지 못한다', () async {
      await repo.acceptRequest(myTeamId, requestId: incomingId);

      await expectLater(
        repo.acceptRequest(myTeamId, requestId: incomingId),
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

    /* 🔴 **사람을 찾는 경기에 지원한다** (계약 3-5절, 2026-09-25 사용자 요청:
       「사람을 찾는팀 지원 단추 하고」). 이 서비스가 하려던 일 자체 — 팀에
       없는 사람이 용병으로 들어가는 길 — 인데 앱에는 **길이 없었다.** */
    test('사람을 찾는 경기에 지원한다', () async {
      final open = await repo.openMatches();
      final made = await repo.apply(open.first.id);

      expect(made.matchId, open.first.id);
      /* 🔴 **아직 확정이 아니다** — 지원은 한쪽만 찬 것이고, 주장이 수락해야
         `confirmed` 가 참이 된다. 여기서 참이면 화면이 「자리를 얻었다」고
         잘못 말한다. */
      expect(made.confirmed, isFalse);
    });

    /// 🔴 **경기당 한 건이다**(계약 409 `ALREADY_APPLIED`).
    test('같은 경기에 두 번 지원하면 막는다', () async {
      final open = await repo.openMatches();
      await repo.apply(open.first.id);

      await expectLater(
        repo.apply(open.first.id),
        throwsA(
          isA<ApiException>().having((e) => e.code, 'code', 'ALREADY_APPLIED'),
        ),
      );
    });

    /// 🔴 **무른 뒤에는 다시 지원할 수 있다** — 안 그러면 무르는 뜻이 없다.
    test('지원을 무른 뒤 다시 지원한다', () async {
      final open = await repo.openMatches();
      final made = await repo.apply(open.first.id);

      await repo.withdraw(open.first.id, applicationId: made.id);

      await repo.apply(open.first.id);
    });
  });
}
