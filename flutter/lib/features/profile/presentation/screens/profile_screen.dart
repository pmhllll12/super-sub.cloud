import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../auth/data/models/app_user.dart';
import '../../../auth/data/models/team_membership.dart';
import '../../../auth/presentation/session_controller.dart';
import '../../../card/data/card_providers.dart';
import '../../../card/data/models/player_card.dart';
import '../../../card/presentation/card_editor_screen.dart';
import '../../../video/presentation/my_videos_controller.dart';
import '../../../video/presentation/screens/my_videos_screen.dart';
import '../widgets/player_card_view.dart';
import 'nickname_sheet.dart';

/// 내 프로필 — 웹 `/me`(`app/(app)/me/page.tsx`)를 폰 세로에 맞춰 옮긴 것이다.
///
/// 웹은 좌우 두 단(왼쪽 정보 · 오른쪽 영상)인데 **폰에는 옆으로 펼 자리가
/// 없어** 한 줄로 쌓는다(`www/docs/2026-08-31-앱-이식-지침.md` §2-2).
///
/// 웹의 **오른쪽 칸(영상)은 요약 블록 하나**로만 두고 본체는 밀고 들어가는
/// 전용 화면이다(`MyVideosScreen`) — 플레이어·스트립·리포트를 이 목록 안에
/// 다 쌓으면 프로필이 통째로 굴러야 하는 길이가 된다.
class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(sessionControllerProvider);
    if (session is! SessionLoggedIn) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    final user = session.user;
    final card = ref.watch(myCardProvider).value;

    return Scaffold(
      backgroundColor: _kBg,
      appBar: AppBar(
        backgroundColor: _kBg,
        foregroundColor: _kOn,
        title: const Text('MY PROFILE'),
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
        children: [
          _CardBlock(card: card, nickname: user.nickname),
          const SizedBox(height: 16),
          _TeamBlock(teams: user.teams),
          const SizedBox(height: 16),
          _InfoBlock(user: user),
          const SizedBox(height: 16),
          const _VideosBlock(),
          const SizedBox(height: 16),
          const _MatchesBlock(),
          const SizedBox(height: 16),
          _AccountBlock(user: user),
        ],
      ),
    );
  }
}

const Color _kBg = Color(0xFF14201A);
const Color _kOn = Color(0xFFFFFFFF);
const Color _kPanel = Color(0xFF1E3029);

/// 웹의 유리판 한 칸 — 제목 + 내용.
class _Block extends StatelessWidget {
  const _Block({required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: _kPanel,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(
                    color: _kOn,
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          child,
        ],
      ),
    );
  }
}

/// 내 카드 + 닉네임 + 꾸미기 입구.
class _CardBlock extends ConsumerWidget {
  const _CardBlock({required this.card, required this.nickname});

  final PlayerCard? card;
  final String nickname;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return _Block(
      title: '내 선수 카드',
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 🔴 카드가 없으면 빈 카드다 — 예외가 아니라 정상 상태다.
          if (card == null)
            const BlankPlayerCardView(width: 120)
          else
            PlayerCardView(
              width: 120,
              seed: card!.publicSlug,
              alias: aliasOf(card!),
              style: card!.style,
              photoUrl: card!.photoUrl,
            ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Flexible(
                      child: Text(
                        nickname,
                        style: const TextStyle(
                          color: _kOn,
                          fontSize: 22,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    IconButton(
                      key: const Key('profile-edit'),
                      icon: const Icon(Icons.edit, size: 18, color: _kOn),
                      tooltip: '닉네임 수정',
                      onPressed: () => showNicknameSheet(context, nickname),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                OutlinedButton(
                  key: const Key('profile-card-edit'),
                  onPressed: card == null
                      ? () => _createCard(context, ref)
                      : () => Navigator.of(context).push(
                            MaterialPageRoute<void>(
                              builder: (_) => CardEditorScreen(card: card!),
                            ),
                          ),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: _kOn,
                    side: BorderSide(color: _kOn.withValues(alpha: 0.4)),
                  ),
                  child: Text(card == null ? '카드 만들기' : '프로필 카드 수정'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  /// 🔴 카드는 **요청할 때** 생긴다(계약 `POST /me/card`) — 가입만으로는
  /// 안 생기고, 조회가 만들지도 않는다.
  ///
  /// 🔴 **첫 모습까지 저장한다** — 안 하면 앱에서 만든 카드가 웹에서 만든
  /// 것과 다르게 보인다(`createCardWithFirstLook`).
  Future<void> _createCard(BuildContext context, WidgetRef ref) async {
    try {
      await createCardWithFirstLook(ref.read(cardRepositoryProvider));
      ref.invalidate(myCardProvider);
    } catch (e) {
      if (context.mounted) _notReady(context, '$e');
    }
  }
}

void _notReady(BuildContext context, String what) {
  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(what)));
}

/// 소속 — 팀 이름 · 지역 · 종목.
class _TeamBlock extends StatelessWidget {
  const _TeamBlock({required this.teams});

  final List<TeamMembership> teams;

  @override
  Widget build(BuildContext context) {
    return _Block(
      title: '소속',
      child: teams.isEmpty
          ? const Text('아직 팀이 없습니다', style: TextStyle(color: _kOn))
          : Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (final t in teams)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                t.name,
                                style: const TextStyle(
                                  color: _kOn,
                                  fontSize: 16,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                              Text(
                                '${t.region} · ${t.sportCode}',
                                style: TextStyle(
                                  color: _kOn.withValues(alpha: 0.7),
                                  fontSize: 12,
                                ),
                              ),
                            ],
                          ),
                        ),
                        // 주장만 팀을 고칠 수 있다(계약 권한표).
                        if (t.isOwner)
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 8,
                              vertical: 2,
                            ),
                            decoration: BoxDecoration(
                              color: AppTheme.seed,
                              borderRadius: BorderRadius.circular(999),
                            ),
                            child: const Text(
                              '주장',
                              style: TextStyle(
                                color: Color(0xFF0B0B0B),
                                fontSize: 11,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),
              ],
            ),
    );
  }
}

/// 정보 — 이메일 · 함께한 날.
class _InfoBlock extends StatelessWidget {
  const _InfoBlock({required this.user});

  final AppUser user;

  @override
  Widget build(BuildContext context) {
    final d = user.createdAt;
    final joined =
        '${d.year}.${d.month.toString().padLeft(2, '0')}'
        '.${d.day.toString().padLeft(2, '0')}부터';
    return _Block(
      title: '정보',
      child: Column(
        children: [
          _row('이메일', user.email),
          const SizedBox(height: 8),
          _row('함께한 날', joined),
        ],
      ),
    );
  }

  Widget _row(String label, String value) => Row(
    children: [
      SizedBox(
        width: 76,
        child: Text(
          label,
          style: TextStyle(color: _kOn.withValues(alpha: 0.7), fontSize: 13),
        ),
      ),
      Expanded(
        child: Text(value, style: const TextStyle(color: _kOn, fontSize: 13)),
      ),
    ],
  );
}

/// 내 영상 — **요약만.** 본체는 밀고 들어가는 전용 화면이다.
///
/// 🔴 **갈래별 편수를 적는다.** 웹은 편수를 안 적지만(영상 아래 `1 / N` 이
/// 이미 말한다) 여기엔 그 줄이 없어서, 편수마저 없으면 **들어가 보기 전에는
/// 영상이 있는지조차 모른다.**
class _VideosBlock extends ConsumerWidget {
  const _VideosBlock();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncVideos = ref.watch(myVideosProvider);

    return _Block(
      title: '내 영상',
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          key: const Key('profile-videos'),
          onTap: () => Navigator.of(context).push(
            MaterialPageRoute<void>(builder: (_) => const MyVideosScreen()),
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Row(
              children: [
                Expanded(
                  child: asyncVideos.when(
                    loading: () => Text(
                      '불러오는 중…',
                      style: TextStyle(color: _kOn.withValues(alpha: 0.6)),
                    ),
                    /* 🔴 **오류를 「없음」으로 그리지 않는다** — 로그인이
                       풀렸는데 「아직 올린 영상이 없습니다」로 보이면 사람은
                       자기 영상이 사라진 줄 안다. */
                    error: (e, _) => Text(
                      '영상을 불러오지 못했습니다',
                      style: TextStyle(color: _kOn.withValues(alpha: 0.6)),
                    ),
                    data: (all) {
                      final split = splitVideos(all);
                      if (all.isEmpty) {
                        return const Text(
                          '아직 올린 영상이 없습니다',
                          style: TextStyle(color: _kOn),
                        );
                      }
                      return Text(
                        '분석 ${split.analyzed.length} · 업로드 ${split.uploaded.length}',
                        style: const TextStyle(color: _kOn, fontSize: 15),
                      );
                    },
                  ),
                ),
                Icon(
                  Icons.chevron_right,
                  color: _kOn.withValues(alpha: 0.6),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _MatchesBlock extends StatelessWidget {
  const _MatchesBlock();

  @override
  Widget build(BuildContext context) {
    // ⚠️ 경기 경로(`GET /teams/{id}/matches`)는 아직 안 붙였다 — 웹도 팀이
    //    없으면 같은 문구를 보여 준다.
    return const _Block(
      title: '내 경기',
      child: Text('다가오는 경기가 없습니다.', style: TextStyle(color: _kOn)),
    );
  }
}

/// 계정 — 지인 검색 노출 · 로그아웃.
class _AccountBlock extends ConsumerWidget {
  const _AccountBlock({required this.user});

  final AppUser user;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return _Block(
      title: '계정',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          /* 🔴 **`Material` 로 감싼다.** `ListTile` 은 바탕과 잉크를 가장 가까운
             Material 에 그리는데, 색 있는 상자 안에 그냥 두면 그 상자가 효과를
             가린다고 프레임워크가 경고를 던진다(시험이 그걸로 깨졌다). */
          Material(
            color: Colors.transparent,
            child: SwitchListTile(
              key: const Key('profile-searchable'),
              contentPadding: EdgeInsets.zero,
              value: user.isNicknameSearchable,
              activeThumbColor: AppTheme.seed,
              title: const Text(
                '지인 검색에 나를 보이기',
                style: TextStyle(color: _kOn, fontSize: 14),
              ),
              subtitle: Text(
                '닉네임으로 나를 찾아 지인 신청을 보낼 수 있습니다.',
                style: TextStyle(
                  color: _kOn.withValues(alpha: 0.6),
                  fontSize: 12,
                ),
              ),
              onChanged: (v) async {
                try {
                  await ref
                      .read(sessionControllerProvider.notifier)
                      .setNicknameSearchable(v);
                } catch (e) {
                  if (context.mounted) _notReady(context, '$e');
                }
              },
            ),
          ),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              TextButton(
                key: const Key('profile-logout'),
                onPressed: () =>
                    ref.read(sessionControllerProvider.notifier).logout(),
                style: TextButton.styleFrom(foregroundColor: _kOn),
                child: const Text('로그아웃'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
