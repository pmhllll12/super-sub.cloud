import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/candidate_providers.dart';
import '../../data/inbox_providers.dart';
import '../../data/match_providers.dart';
import '../../data/models/contact.dart';
import '../../data/models/match_candidate.dart';
import '../../data/models/team_invitation.dart';
import 'sheet_skin.dart';

/// 알림함 — **받은 것**에 답하는 자리.
///
/// 🔴 **여기 있는 것은 전부 서버에서 온다**(2026-09-25 사용자: 「진짜로 서로
/// 연결되어있어야 한다고」). 웹에서 보낸 초대·신청이 그대로 뜨고, 여기서
/// 답한 것이 웹에 뜬다 — 가운데에 서버가 있기 때문이지 화면끼리 아는 것이
/// 아니다.
Future<void> showInboxSheet(
  BuildContext context, {
  required String? teamId,
}) =>
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => _InboxSheet(teamId: teamId),
    );

class _InboxSheet extends ConsumerWidget {
  const _InboxSheet({required this.teamId});

  final String? teamId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(inboxProvider);

    return SheetShell(
      title: '알림',
      child: async.when(
        loading: () => const Center(child: SheetSpinner()),
        error: (e, _) => Center(
          child: SheetMessage(title: '알림을 불러오지 못했습니다', detail: '$e'),
        ),
        data: (inbox) => inbox.pending == 0
            ? const Center(
                child: SheetMessage(
                  title: '받은 것이 없습니다',
                  detail: '팀 초대 · 지인 신청 · 경기 신청이 오면 여기 뜹니다.',
                ),
              )
            : ListView(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 28),
                children: [
                  for (final i in inbox.invitations) _InvitationRow(invitation: i),
                  for (final c in inbox.contactRequests) _ContactRow(request: c),
                  for (final m in inbox.matchRequests)
                    _MatchRow(request: m, teamId: teamId),
                ],
              ),
      ),
    );
  }
}

/// 나를 부른 팀.
class _InvitationRow extends ConsumerWidget {
  const _InvitationRow({required this.invitation});

  final TeamInvitation invitation;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final repo = ref.read(invitationRepositoryProvider);
    return _Card(
      title: '${invitation.teamName} 에서 불렀습니다',
      /* 🔴 **자리는 있을 때만 적는다** — 자리를 안 정한 초대(「우리 팀에
         오세요」)가 정상이다(계약 3-3절). */
      detail: [
        if (invitation.teamRegion.isNotEmpty) invitation.teamRegion,
        if (invitation.positionLabel case final p?) '$p 자리',
      ].join(' · '),
      acceptKey: Key('inbox-accept-${invitation.id}'),
      rejectKey: Key('inbox-reject-${invitation.id}'),
      onAccept: () async {
        await repo.acceptInvitation(invitation.id);
        ref.invalidate(inboxProvider);
      },
      onReject: () async {
        await repo.rejectInvitation(invitation.id);
        ref.invalidate(inboxProvider);
      },
    );
  }
}

/// 나에게 온 지인 신청.
class _ContactRow extends ConsumerWidget {
  const _ContactRow({required this.request});

  final ContactRequest request;

  @override
  Widget build(BuildContext context, WidgetRef ref) => _Card(
        title: '지인 신청이 왔습니다',
        /* ⚠️ **누가 보냈는지는 이름이 안 온다** — 계약의
           `GET /me/contacts/requests` 는 `requester_user_id` 만 준다.
           닉네임을 얻을 경로가 없어서 지어내지 않는다. */
        detail: request.note ?? '',
        acceptKey: Key('inbox-accept-${request.id}'),
        onAccept: () async {
          await ref.read(contactRepositoryProvider).accept(request.id);
          ref
            ..invalidate(inboxProvider)
            ..invalidate(contactsProvider)
            ..invalidate(contactRequestsProvider);
        },
      );
}

/// 우리 팀에게 온 경기 신청.
class _MatchRow extends ConsumerWidget {
  const _MatchRow({required this.request, required this.teamId});

  final TeamMatchRequest request;
  final String? teamId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final repo = ref.read(matchRepositoryProvider);
    final at = DateTime.tryParse(request.playedAt);
    return _Card(
      title: '${request.requesterTeamName} 가 경기를 신청했습니다',
      detail: [
        if (at != null)
          '${at.month}월 ${at.day}일 '
              '${at.hour.toString().padLeft(2, '0')}:'
              '${at.minute.toString().padLeft(2, '0')}',
        request.place,
      ].join(' · '),
      acceptKey: Key('inbox-accept-${request.id}'),
      rejectKey: Key('inbox-reject-${request.id}'),
      onAccept: teamId == null
          ? null
          : () async {
              await repo.acceptRequest(teamId!, requestId: request.id);
              ref
                ..invalidate(inboxProvider)
                ..invalidate(liveRequestsProvider(teamId!));
            },
      onReject: teamId == null
          ? null
          : () async {
              await repo.rejectRequest(teamId!, requestId: request.id);
              ref.invalidate(inboxProvider);
            },
    );
  }
}

class _Card extends StatefulWidget {
  const _Card({
    required this.title,
    required this.detail,
    required this.acceptKey,
    required this.onAccept,
    this.rejectKey,
    this.onReject,
  });

  final String title;
  final String detail;
  final Key acceptKey;
  final Key? rejectKey;
  final Future<void> Function()? onAccept;
  final Future<void> Function()? onReject;

  @override
  State<_Card> createState() => _CardState();
}

class _CardState extends State<_Card> {
  bool _busy = false;

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: kSheetBox,
          borderRadius: BorderRadius.circular(16),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              widget.title,
              style: const TextStyle(
                color: kSheetBoxInk,
                fontSize: 15,
                fontWeight: FontWeight.w700,
              ),
            ),
            if (widget.detail.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 3),
                child: Text(
                  widget.detail,
                  style: TextStyle(
                    color: kSheetBoxInk.withValues(alpha: 0.65),
                    fontSize: 12.5,
                  ),
                ),
              ),
            const SizedBox(height: 12),
            Row(
              children: [
                _Button(
                  key: widget.acceptKey,
                  label: '수락',
                  strong: true,
                  onTap: _busy ? null : () => _run(widget.onAccept),
                ),
                if (widget.rejectKey case final k?) ...[
                  const SizedBox(width: 8),
                  _Button(
                    key: k,
                    label: '거절',
                    onTap: _busy ? null : () => _run(widget.onReject),
                  ),
                ],
              ],
            ),
          ],
        ),
      );

  Future<void> _run(Future<void> Function()? f) async {
    if (f == null) return;
    setState(() => _busy = true);
    try {
      await f();
    } catch (e) {
      if (!mounted) return;
      setState(() => _busy = false);
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text('$e')));
    }
  }
}

class _Button extends StatelessWidget {
  const _Button({
    super.key,
    required this.label,
    required this.onTap,
    this.strong = false,
  });

  final String label;
  final VoidCallback? onTap;
  final bool strong;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(999),
            color: strong ? kSheetGreen.withValues(alpha: 0.12) : null,
            border: Border.all(
              color: strong
                  ? kSheetGreen
                  : kSheetBoxInk.withValues(alpha: 0.28),
            ),
          ),
          child: Text(
            label,
            style: TextStyle(
              color: strong ? kSheetGreen : kSheetBoxInk.withValues(alpha: 0.8),
              fontSize: 13,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
      );
}
