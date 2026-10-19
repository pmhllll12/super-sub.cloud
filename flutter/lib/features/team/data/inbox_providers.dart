import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/presentation/session_controller.dart';
import '../live_match.dart';
import 'candidate_providers.dart';
import 'match_providers.dart';
import 'models/contact.dart';
import 'models/match_candidate.dart';
import 'models/team_invitation.dart';

/// 🔴 **얼마마다 다시 묻는가.** 알림 채널(웹소켓·푸시)이 없어서 「몇 초마다
/// GET」이 유일한 길이다(계약 3-12절이 그렇게 정해 뒀다). 웹 알림함과 **같은
/// 값**을 쓴다 — 두 화면이 다른 속도로 도는 이유가 없다.
const Duration kInboxEvery = Duration(seconds: 15);

/// 알림함에 담기는 것 — **전부 서버에서 온다.**
///
/// 🔴 **이것이 웹과 앱을 잇는 자리다**(2026-09-25 사용자: 「진짜로 서로
/// 연결되어있어야 한다고」). 웹에서 보낸 초대·신청이 여기로 들어오고, 앱에서
/// 답한 것이 웹에 뜬다 — 가운데에 서버가 있기 때문이지 화면끼리 아는 것이
/// 아니다.
class Inbox {
  const Inbox({
    this.invitations = const [],
    this.contactRequests = const [],
    this.matchRequests = const [],
    this.liveMatch,
  });

  /// 나를 부른 팀들 — `GET /me/invitations`.
  final List<TeamInvitation> invitations;

  /// 나에게 온 지인 신청 — `GET /me/contacts/requests`.
  final List<ContactRequest> contactRequests;

  /// 우리 팀에게 온 경기 신청 — `GET /teams/{id}/match-requests` 중 **받은 것**.
  final List<TeamMatchRequest> matchRequests;

  /// 지금 잡혀 있는 경기. 🔴 판단은 `isLiveConfirmed` **한 곳**이다.
  final TeamMatchRequest? liveMatch;

  /// 사람이 **답해야 하는** 것의 수 — 머리칸 숫자가 이것이다.
  int get pending =>
      invitations.length + contactRequests.length + matchRequests.length;

  bool get isEmpty => pending == 0 && liveMatch == null;
}

/// 15초마다 서버에 묻는 알림함.
///
/// 🔴 **한 번 실패해도 멈추지 않는다** — 다음 주기에 다시 묻는다. 네 경로를
/// 따로 감싸는 것은 하나가 막혀도 나머지는 보이게 하려는 것이다(실제로
/// 실서버의 404 하나가 4.6초를 먹는 일이 있었다).
final inboxProvider = StreamProvider<Inbox>((ref) async* {
  /* 🔴 **세션을 지켜본다**(`read` 가 아니라 `watch`). 처음 한 번만 읽으면
     **로그인이 끝나기 전에** 물어보고 빈 채로 15초를 기다린다 — 켜자마자
     알림이 안 뜨는 것이 그 때문이었다. 로그인되면 이 흐름이 다시 시작된다. */
  final session = ref.watch(sessionControllerProvider);

  /* 🔴 **로그인 전에는 아예 안 묻는다.** 토큰이 없어 어차피 401 이고,
     타이머만 도는 것은 배터리와 시험 양쪽에 해롭다(시험은 「위젯 트리를
     버린 뒤에도 타이머가 남았다」로 깨진다). 로그인되면 위 `watch` 가
     이 흐름을 다시 시작한다. */
  if (session is! SessionLoggedIn) {
    yield const Inbox();
    return;
  }
  final teamId = session.user.ownedTeamId;

  Future<Inbox> look() async {

    final invites = ref.read(invitationRepositoryProvider);
    final contacts = ref.read(contactRepositoryProvider);
    final match = ref.read(matchRepositoryProvider);

    Future<T> safe<T>(Future<T> Function() f, T fallback) async {
      try {
        return await f();
      } catch (_) {
        return fallback;
      }
    }

    final mine = await safe(invites.myInvitations, const <TeamInvitation>[]);
    final asked =
        await safe(contacts.requests, const <ContactRequest>[]);

    var incoming = const <TeamMatchRequest>[];
    TeamMatchRequest? live;
    if (teamId != null) {
      final all = await safe(
        () => match.requests(teamId),
        const <TeamMatchRequest>[],
      );
      /* 🔴 **받은 것만 고른다** — 계약은 보낸 것과 받은 것을 함께 준다.
         안 가르면 내가 건 신청이 「답해 주세요」로 뜬다. */
      incoming = [
        for (final r in all)
          if (r.targetTeamId == teamId && r.isPending) r,
      ];
      live = firstLiveMatch(all, now: DateTime.now());
    }

    return Inbox(
      invitations: mine,
      contactRequests: asked,
      matchRequests: incoming,
      liveMatch: live,
    );
  }

  /* 🔴 **타이머를 직접 들고 끊는다.** `Stream.periodic` 을 `await for` 로
     돌면 화면이 사라진 뒤에도 타이머가 남아, 시험이 「위젯 트리를 버린
     뒤에도 타이머가 남았다」로 깨진다 — 실기기에서도 그만큼 요청이 계속
     나간다. */
  final out = StreamController<Inbox>();
  var closed = false;

  Future<void> tick() async {
    if (closed) return;
    final next = await look();
    if (!closed) out.add(next);
  }

  final timer = Timer.periodic(kInboxEvery, (_) => tick());
  ref.onDispose(() {
    closed = true;
    timer.cancel();
    out.close();
  });

  unawaited(tick());
  yield* out.stream;
});
