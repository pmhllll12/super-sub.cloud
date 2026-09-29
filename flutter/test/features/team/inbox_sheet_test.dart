import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/team/data/candidate_providers.dart';
import 'package:super_sub/features/team/data/contact_repository.dart';
import 'package:super_sub/features/team/data/inbox_providers.dart';
import 'package:super_sub/features/team/data/invitation_repository.dart';
import 'package:super_sub/features/team/data/models/contact.dart';
import 'package:super_sub/features/team/data/models/match_candidate.dart';
import 'package:super_sub/features/team/data/models/team_invitation.dart';
import 'package:super_sub/features/team/presentation/sheets/inbox_sheet.dart';

class _FakeInvites implements InvitationRepository {
  final accepted = <String>[];
  final rejected = <String>[];

  @override
  Future<List<TeamInvitation>> myInvitations() async => const [];
  @override
  Future<void> acceptInvitation(String id) async => accepted.add(id);
  @override
  Future<void> rejectInvitation(String id) async => rejected.add(id);
  @override
  Future<TeamInvitation> invite(String teamId,
          {required String userId, String? positionCode}) =>
      throw UnimplementedError();
}

class _FakeContacts implements ContactRepository {
  final accepted = <String>[];

  @override
  Future<void> accept(String contactId) async => accepted.add(contactId);
  @override
  Future<List<Contact>> contacts() async => const [];
  @override
  Future<List<ContactRequest>> requests() async => const [];
  @override
  Future<List<FoundUser>> search(String q) async => const [];
  @override
  Future<void> request(String targetUserId) async {}
}

const _inbox = Inbox(
  invitations: [
    TeamInvitation(
      id: 'inv-1',
      teamId: 't-bears',
      invitedUserId: 'u-me',
      status: 'pending',
      positionCode: 'MF',
      positionLabel: '미드필더',
      teamName: '베어스',
      teamRegion: '서울 송파구',
    ),
  ],
  contactRequests: [
    ContactRequest(id: 'ct-1', requesterUserId: 'u-x'),
  ],
  matchRequests: [
    TeamMatchRequest(
      id: 'tmr-in',
      requesterTeamId: 't-bears',
      targetTeamId: 't-thunder',
      status: 'pending',
      playedAt: '2026-10-05T11:00:00+09:00',
      place: '영등포공원 풋살경기장',
      requesterTeamName: '베어스',
    ),
  ],
);

Future<void> _open(
  WidgetTester tester, {
  Inbox inbox = _inbox,
  _FakeInvites? invites,
  _FakeContacts? contacts,
}) async {
  tester.view.physicalSize = const Size(1080, 2340);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        inboxProvider.overrideWith((ref) => Stream.value(inbox)),
        invitationRepositoryProvider
            .overrideWithValue(invites ?? _FakeInvites()),
        contactRepositoryProvider.overrideWithValue(contacts ?? _FakeContacts()),
      ],
      child: MaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (context) => ElevatedButton(
              onPressed: () => showInboxSheet(context, teamId: 't-thunder'),
              child: const Text('열기'),
            ),
          ),
        ),
      ),
    ),
  );

  await tester.tap(find.text('열기'));
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 500));
}

void main() {
  /// 🔴 **세 가지가 다 한 자리에 온다** — 팀 초대 · 지인 신청 · 경기 신청.
  /// 서버에서 오는 값이라, 웹에서 보낸 것이 그대로 여기 뜬다.
  testWidgets('받은 것 셋이 다 보인다', (tester) async {
    await _open(tester);

    expect(find.textContaining('베어스'), findsWidgets);
    expect(find.textContaining('지인'), findsWidgets);
    expect(find.textContaining('영등포공원'), findsOneWidget);
  });

  /// 🔴 **어느 자리로 부르는지 적는다** — 자리를 안 정한 초대도 정상이라
  /// 있을 때만 적는다.
  testWidgets('초대에 부르는 자리가 적힌다', (tester) async {
    await _open(tester);

    expect(find.textContaining('미드필더'), findsOneWidget);
  });

  testWidgets('팀 초대를 수락하면 저장소로 간다', (tester) async {
    final invites = _FakeInvites();
    await _open(tester, invites: invites);

    await tester.tap(find.byKey(const Key('inbox-accept-inv-1')));
    await tester.pump(const Duration(milliseconds: 500));

    expect(invites.accepted, ['inv-1']);
  });

  testWidgets('팀 초대를 거절할 수 있다', (tester) async {
    final invites = _FakeInvites();
    await _open(tester, invites: invites);

    await tester.tap(find.byKey(const Key('inbox-reject-inv-1')));
    await tester.pump(const Duration(milliseconds: 500));

    expect(invites.rejected, ['inv-1']);
  });

  testWidgets('지인 신청을 수락하면 저장소로 간다', (tester) async {
    final contacts = _FakeContacts();
    await _open(tester, contacts: contacts);

    await tester.tap(find.byKey(const Key('inbox-accept-ct-1')));
    await tester.pump(const Duration(milliseconds: 500));

    expect(contacts.accepted, ['ct-1']);
  });

  /// 🔴 **빈 알림함도 화면이 있어야 한다** — 아무것도 안 뜨면 고장으로 읽힌다.
  testWidgets('받은 것이 없으면 그렇게 적는다', (tester) async {
    await _open(tester, inbox: const Inbox());

    expect(find.textContaining('없습니다'), findsOneWidget);
  });
}
