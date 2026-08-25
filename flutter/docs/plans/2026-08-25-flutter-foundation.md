# Super-Sub Flutter — 토대와 첫 플로우 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 실행되는 Flutter 앱에서 로그인 → 종목 선택 → 홈 → 프로필까지 이동할 수 있고, 리포지토리 계약 테스트가 통과하는 상태를 만든다.

**Architecture:** 기능별 수직 분할(feature-first). 화면은 리포지토리 인터페이스만 알고 구현체(Mock/API)는 모른다. Riverpod provider 한 줄이 교체 지점이다. 세션 상태는 `Notifier`가 들고, `go_router`가 `refreshListenable`로 그 변화를 받아 진입 경로를 분기한다.

**Tech Stack:** Flutter 3.44.2 / Dart 3.12.2 · flutter_riverpod · go_router · uuid · flutter_test

**Spec:** `flutter/docs/2026-08-25-flutter-app-design.md`

## Global Constraints

- **작업 경로는 `flutter/` 안으로 한정한다.** `jekyll/`, `_config.yml`, `_posts/`, `_layouts/`, `assets/`, 루트 `.gitignore`를 포함한 저장소 루트의 어떤 파일도 수정하지 않는다.
- 루트 `.gitignore`를 건드리지 않기 위해 Flutter의 무시 규칙은 `flutter/.gitignore`에 둔다.
- 백엔드가 없다. 네트워크 호출 코드를 작성하지 않는다. 모든 데이터는 `MockDb`에서 나온다.
- **모든 리포지토리 메서드는 `Future`를 반환한다.** 동기 반환이 하나라도 있으면 API 전환 시 그 화면을 다시 짠다.
- **Mock은 진짜처럼 굴어야 한다.** 모든 응답에 200~500ms 지연을 넣고, 실패와 빈 결과를 재현할 수 있어야 한다.
- 리포지토리 인터페이스는 도메인 모델로만 말한다. `Map<String, dynamic>`이나 DTO를 반환하지 않는다.
- **코드 생성(freezed/json_serializable)을 이 단계에서는 쓰지 않는다.** 스펙 2.2에서 권장했으나, 지금은 JSON이 존재하지 않으므로(Mock 전용) 직렬화 코드 생성은 근거 없는 선반영이다. 손으로 쓴 불변 클래스(`const` 생성자 + `copyWith` + `==`/`hashCode`)를 쓰고, 도입은 API 스펙이 정해지는 단계 7에서 재검토한다.
- 커밋은 각 태스크 끝에서 한다. 푸시는 하지 않는다 (사용자가 직접 한다).
- 모든 명령은 `flutter/` 디렉터리에서 실행한다.

---

## 파일 구조

이 계획이 만드는 파일이다.

```
flutter/
  pubspec.yaml                                     Task 1
  .gitignore                                       Task 1 (flutter create가 생성)
  lib/
    main.dart                                      Task 1  — ProviderScope + App
    app.dart                                       Task 1  — MaterialApp.router
    core/
      theme/app_theme.dart                         Task 1  — 색·타이포
      mock/mock_db.dart                            Task 3  — 인메모리 저장소 + 시드
      router/app_router.dart                       Task 5  — 라우트 + redirect 분기
      widgets/async_view.dart                      Task 6  — 로딩/빈/오류 공통 처리
      sport/current_sport.dart                     Task 8  — 종목 전역 컨텍스트
      sport/sport.dart                             Task 2  — Sport 모델
    features/
      auth/
        data/models/app_user.dart                  Task 2
        data/models/session.dart                   Task 4
        data/auth_repository.dart                  Task 4  — 인터페이스 + AuthException
        data/auth_repository_mock.dart             Task 4
        data/auth_providers.dart                   Task 4  — 교체 지점
        presentation/session_controller.dart       Task 5
        presentation/screens/login_screen.dart     Task 7
      team/
        data/models/team.dart                      Task 2
        data/models/team_member.dart               Task 2
      onboarding/
        presentation/screens/sport_screen.dart     Task 8
      home/
        presentation/screens/home_screen.dart      Task 9
      profile/
        presentation/screens/profile_screen.dart   Task 10
  test/
    contract/auth_repository_contract.dart         Task 4  — Mock/API 공용 계약
    features/auth/auth_repository_mock_test.dart   Task 4
    features/team/team_member_test.dart            Task 2
    core/mock_db_test.dart                         Task 3
    features/auth/session_controller_test.dart     Task 5
    core/async_view_test.dart                      Task 6
    features/auth/login_screen_test.dart           Task 7
    features/onboarding/sport_screen_test.dart     Task 8
    features/home/home_screen_test.dart            Task 9
    features/profile/profile_screen_test.dart      Task 10
```

---

### Task 1: 프로젝트 생성과 앱 뼈대

**Files:**
- Create: `flutter/pubspec.yaml`, `flutter/.gitignore`, `flutter/lib/main.dart`, `flutter/lib/app.dart`, `flutter/lib/core/theme/app_theme.dart`
- Test: `flutter/test/smoke_test.dart`

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces: `SuperSubApp` (StatelessWidget), `AppTheme.light` (`ThemeData`), `main()` — 이후 모든 태스크가 `SuperSubApp`을 진입점으로 쓴다.

- [ ] **Step 1: Flutter 프로젝트를 현재 디렉터리에 생성한다**

`flutter/docs/`가 이미 있으므로 비어 있지 않은 디렉터리에 생성하는 형태다. `flutter create`는 기존 파일을 덮어쓰지 않는다.

```bash
cd flutter
flutter create --org cloud.supersub --project-name super_sub --platforms=android,ios .
```

- [ ] **Step 2: 의존성을 추가한다**

버전을 손으로 적지 않는다. `pub add`가 설치된 Flutter SDK와 호환되는 최신 버전을 고르게 한다.

```bash
cd flutter
flutter pub add flutter_riverpod go_router uuid
flutter pub add dev:flutter_lints
```

- [ ] **Step 3: 실패하는 스모크 테스트를 쓴다**

`flutter create`가 만든 `test/widget_test.dart`는 삭제하고 아래를 만든다.

```bash
rm -f flutter/test/widget_test.dart
```

`flutter/test/smoke_test.dart`:

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:super_sub/app.dart';

void main() {
  testWidgets('앱이 뜨고 앱 이름이 보인다', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: SuperSubApp()));
    await tester.pumpAndSettle();
    expect(find.text('Super-Sub'), findsOneWidget);
  });
}
```

- [ ] **Step 4: 테스트를 돌려 실패를 확인한다**

```bash
cd flutter && flutter test test/smoke_test.dart
```

기대: `app.dart`가 없어 컴파일 실패 (`Target of URI doesn't exist`).

- [ ] **Step 5: 테마를 만든다**

`flutter/lib/core/theme/app_theme.dart`:

```dart
import 'package:flutter/material.dart';

class AppTheme {
  const AppTheme._();

  static const seed = Color(0xFF1B5E20);

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
```

- [ ] **Step 6: 앱 위젯과 진입점을 만든다**

`flutter/lib/app.dart` — 이 단계에서는 아직 라우터가 없으므로 `MaterialApp`을 쓴다. Task 5에서 `MaterialApp.router`로 바꾼다.

```dart
import 'package:flutter/material.dart';

import 'core/theme/app_theme.dart';

class SuperSubApp extends StatelessWidget {
  const SuperSubApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Super-Sub',
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      home: const Scaffold(
        body: Center(child: Text('Super-Sub')),
      ),
    );
  }
}
```

`flutter/lib/main.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app.dart';

void main() {
  runApp(const ProviderScope(child: SuperSubApp()));
}
```

- [ ] **Step 7: 테스트가 통과하는지 확인한다**

```bash
cd flutter && flutter test test/smoke_test.dart && flutter analyze
```

기대: 테스트 PASS, analyze 이슈 0건.

- [ ] **Step 8: 커밋한다**

```bash
git add flutter/
git commit -m "feat(app): Flutter 프로젝트 셋업과 앱 뼈대"
```

---

### Task 2: 도메인 모델 (Sport · AppUser · Team · TeamMember)

**Files:**
- Create: `flutter/lib/core/sport/sport.dart`, `flutter/lib/features/auth/data/models/app_user.dart`, `flutter/lib/features/team/data/models/team.dart`, `flutter/lib/features/team/data/models/team_member.dart`
- Test: `flutter/test/features/team/team_member_test.dart`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `Sport({required String code, required String name})`
  - `AppUser({required String id, required String email, required String nickname, required DateTime createdAt})`, `AppUser copyWith({String? nickname})`
  - `Team({required String id, required String sportCode, required String name, required String region})`
  - `enum TeamRole { member, manager }`
  - `TeamMember({required String id, required String teamId, required String userId, required TeamRole role, required DateTime joinedAt, DateTime? leftAt})`, `bool get isActive`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

ERD의 `team_member.left_at`은 소프트 삭제다. 이 불변식을 모델에 못박는다.

`flutter/test/features/team/team_member_test.dart`:

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/team/data/models/team_member.dart';

void main() {
  final joined = DateTime(2026, 3, 1);

  test('leftAt이 없으면 활성 소속이다', () {
    final m = TeamMember(
      id: 'tm1',
      teamId: 't1',
      userId: 'u1',
      role: TeamRole.member,
      joinedAt: joined,
    );
    expect(m.isActive, isTrue);
  });

  test('leftAt이 있으면 비활성 소속이다 (소프트 삭제)', () {
    final m = TeamMember(
      id: 'tm1',
      teamId: 't1',
      userId: 'u1',
      role: TeamRole.member,
      joinedAt: joined,
      leftAt: DateTime(2026, 6, 1),
    );
    expect(m.isActive, isFalse);
  });

  test('같은 값이면 동등하다', () {
    final a = TeamMember(
      id: 'tm1', teamId: 't1', userId: 'u1',
      role: TeamRole.manager, joinedAt: joined,
    );
    final b = TeamMember(
      id: 'tm1', teamId: 't1', userId: 'u1',
      role: TeamRole.manager, joinedAt: joined,
    );
    expect(a, equals(b));
  });
}
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

```bash
cd flutter && flutter test test/features/team/team_member_test.dart
```

기대: 컴파일 실패 (`team_member.dart` 없음).

- [ ] **Step 3: 모델 4개를 만든다**

`flutter/lib/core/sport/sport.dart`:

```dart
/// ERD `sport` 테이블. 현재 풋살·야구 2행.
class Sport {
  const Sport({required this.code, required this.name});

  final String code;
  final String name;

  @override
  bool operator ==(Object other) =>
      other is Sport && other.code == code && other.name == name;

  @override
  int get hashCode => Object.hash(code, name);
}
```

`flutter/lib/features/auth/data/models/app_user.dart`:

```dart
/// ERD `user` 테이블. Dart 코어의 이름과 겹치지 않도록 AppUser로 둔다.
class AppUser {
  const AppUser({
    required this.id,
    required this.email,
    required this.nickname,
    required this.createdAt,
  });

  final String id;
  final String email;
  final String nickname;
  final DateTime createdAt;

  AppUser copyWith({String? nickname}) => AppUser(
        id: id,
        email: email,
        nickname: nickname ?? this.nickname,
        createdAt: createdAt,
      );

  @override
  bool operator ==(Object other) =>
      other is AppUser &&
      other.id == id &&
      other.email == email &&
      other.nickname == nickname &&
      other.createdAt == createdAt;

  @override
  int get hashCode => Object.hash(id, email, nickname, createdAt);
}
```

`flutter/lib/features/team/data/models/team.dart`:

```dart
/// ERD `team` 테이블. 종목은 팀이 결정한다 (match에는 sport_code가 없다).
class Team {
  const Team({
    required this.id,
    required this.sportCode,
    required this.name,
    required this.region,
  });

  final String id;
  final String sportCode;
  final String name;
  final String region;

  @override
  bool operator ==(Object other) =>
      other is Team &&
      other.id == id &&
      other.sportCode == sportCode &&
      other.name == name &&
      other.region == region;

  @override
  int get hashCode => Object.hash(id, sportCode, name, region);
}
```

`flutter/lib/features/team/data/models/team_member.dart`:

```dart
enum TeamRole { member, manager }

/// ERD `team_member` 테이블.
///
/// 탈퇴는 행 삭제가 아니라 leftAt 기록이다(소프트 삭제). 경기·평가 이력이
/// 남아야 하기 때문이다. 재가입이 가능해 (team_id, user_id, joined_at)이
/// 유일키이므로, 한 사람이 같은 팀에 대해 여러 행을 가질 수 있다.
class TeamMember {
  const TeamMember({
    required this.id,
    required this.teamId,
    required this.userId,
    required this.role,
    required this.joinedAt,
    this.leftAt,
  });

  final String id;
  final String teamId;
  final String userId;
  final TeamRole role;
  final DateTime joinedAt;
  final DateTime? leftAt;

  bool get isActive => leftAt == null;

  @override
  bool operator ==(Object other) =>
      other is TeamMember &&
      other.id == id &&
      other.teamId == teamId &&
      other.userId == userId &&
      other.role == role &&
      other.joinedAt == joinedAt &&
      other.leftAt == leftAt;

  @override
  int get hashCode =>
      Object.hash(id, teamId, userId, role, joinedAt, leftAt);
}
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

```bash
cd flutter && flutter test test/features/team/team_member_test.dart && flutter analyze
```

기대: 3개 테스트 PASS.

- [ ] **Step 5: 커밋한다**

```bash
git add flutter/lib flutter/test
git commit -m "feat(app): Sport/AppUser/Team/TeamMember 도메인 모델"
```

---

### Task 3: MockDb — 인메모리 저장소와 시드 계정 3종

**Files:**
- Create: `flutter/lib/core/mock/mock_db.dart`
- Test: `flutter/test/core/mock_db_test.dart`

**Interfaces:**
- Consumes: Task 2의 `Sport`, `AppUser`, `Team`, `TeamMember`, `TeamRole`
- Produces:
  - `class MockDb` — 필드 `List<Sport> sports`, `List<AppUser> users`, `List<Team> teams`, `List<TeamMember> teamMembers`
  - 시드 상수 `MockDb.playerId`, `MockDb.managerId`, `MockDb.newbieId` (모두 `String`)
  - `AppUser? findUserByEmail(String email)`, `AppUser? findUserById(String id)`
  - `mockDbProvider` (`Provider<MockDb>`) — 모든 Mock 리포지토리가 공유한다

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`flutter/test/core/mock_db_test.dart`:

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/core/mock/mock_db.dart';
import 'package:super_sub/features/team/data/models/team_member.dart';

void main() {
  late MockDb db;

  setUp(() => db = MockDb());

  test('종목은 풋살과 야구 2개다', () {
    expect(db.sports.map((s) => s.code), containsAll(['futsal', 'baseball']));
  });

  test('시드 계정 3종이 있다', () {
    expect(db.findUserById(MockDb.playerId), isNotNull);
    expect(db.findUserById(MockDb.managerId), isNotNull);
    expect(db.findUserById(MockDb.newbieId), isNotNull);
  });

  test('이메일로 사용자를 찾는다', () {
    final u = db.findUserById(MockDb.playerId)!;
    expect(db.findUserByEmail(u.email), equals(u));
  });

  test('없는 이메일이면 null이다', () {
    expect(db.findUserByEmail('nobody@nowhere.test'), isNull);
  });

  test('팀 관리자만 manager 역할을 갖는다', () {
    final roles = db.teamMembers
        .where((m) => m.userId == MockDb.managerId)
        .map((m) => m.role);
    expect(roles, contains(TeamRole.manager));

    final playerRoles = db.teamMembers
        .where((m) => m.userId == MockDb.playerId)
        .map((m) => m.role);
    expect(playerRoles, isNot(contains(TeamRole.manager)));
  });

  test('신규 가입자는 팀 소속이 없다 (빈 상태 UI 검증용)', () {
    final mine = db.teamMembers.where((m) => m.userId == MockDb.newbieId);
    expect(mine, isEmpty);
  });
}
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

```bash
cd flutter && flutter test test/core/mock_db_test.dart
```

기대: 컴파일 실패 (`mock_db.dart` 없음).

- [ ] **Step 3: MockDb를 만든다**

`flutter/lib/core/mock/mock_db.dart`:

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../features/auth/data/models/app_user.dart';
import '../../features/team/data/models/team.dart';
import '../../features/team/data/models/team_member.dart';
import '../sport/sport.dart';

/// 모든 Mock 리포지토리가 공유하는 단일 인메모리 저장소.
///
/// feature마다 각자 가짜 데이터를 들면 서로 모순된다 — 존재하지 않는 팀을
/// 참조하는 경기 같은 것. ERD와 같은 구조로 한 곳에 담고 모두 여기서 읽는다.
class MockDb {
  MockDb() {
    _seed();
  }

  static const playerId = 'u-player';
  static const managerId = 'u-manager';
  static const newbieId = 'u-newbie';

  final List<Sport> sports = [];
  final List<AppUser> users = [];
  final List<Team> teams = [];
  final List<TeamMember> teamMembers = [];

  AppUser? findUserByEmail(String email) {
    for (final u in users) {
      if (u.email == email) return u;
    }
    return null;
  }

  AppUser? findUserById(String id) {
    for (final u in users) {
      if (u.id == id) return u;
    }
    return null;
  }

  void _seed() {
    sports.addAll(const [
      Sport(code: 'futsal', name: '풋살'),
      Sport(code: 'baseball', name: '야구'),
    ]);

    users.addAll([
      AppUser(
        id: playerId,
        email: 'player@supersub.test',
        nickname: '김용병',
        createdAt: DateTime(2026, 3, 2),
      ),
      AppUser(
        id: managerId,
        email: 'manager@supersub.test',
        nickname: '이감독',
        createdAt: DateTime(2026, 2, 10),
      ),
      AppUser(
        id: newbieId,
        email: 'newbie@supersub.test',
        nickname: '박신입',
        createdAt: DateTime(2026, 8, 24),
      ),
    ]);

    teams.addAll(const [
      Team(
        id: 't-thunder',
        sportCode: 'futsal',
        name: '번개 풋살클럽',
        region: '서울 강남',
      ),
      Team(
        id: 't-bears',
        sportCode: 'baseball',
        name: '동네 베어스',
        region: '서울 송파',
      ),
    ]);

    teamMembers.addAll([
      TeamMember(
        id: 'tm-1',
        teamId: 't-thunder',
        userId: managerId,
        role: TeamRole.manager,
        joinedAt: DateTime(2026, 2, 12),
      ),
      TeamMember(
        id: 'tm-2',
        teamId: 't-thunder',
        userId: playerId,
        role: TeamRole.member,
        joinedAt: DateTime(2026, 3, 5),
      ),
      // 소프트 삭제 사례 — 탈퇴 이력이 남아 있어야 한다.
      TeamMember(
        id: 'tm-3',
        teamId: 't-bears',
        userId: playerId,
        role: TeamRole.member,
        joinedAt: DateTime(2026, 3, 10),
        leftAt: DateTime(2026, 6, 30),
      ),
    ]);
    // 신규 가입자(newbieId)는 의도적으로 소속을 넣지 않는다.
    // 빈 상태 UI를 반드시 만들도록 강제하는 장치다.
  }
}

final mockDbProvider = Provider<MockDb>((ref) => MockDb());
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

```bash
cd flutter && flutter test test/core/mock_db_test.dart && flutter analyze
```

기대: 6개 테스트 PASS.

- [ ] **Step 5: 커밋한다**

```bash
git add flutter/lib flutter/test
git commit -m "feat(app): MockDb 인메모리 저장소와 시드 계정 3종"
```

---

### Task 4: AuthRepository — 인터페이스 · Mock · 계약 테스트

**Files:**
- Create: `flutter/lib/features/auth/data/models/session.dart`, `flutter/lib/features/auth/data/auth_repository.dart`, `flutter/lib/features/auth/data/auth_repository_mock.dart`, `flutter/lib/features/auth/data/auth_providers.dart`
- Test: `flutter/test/contract/auth_repository_contract.dart`, `flutter/test/features/auth/auth_repository_mock_test.dart`

**Interfaces:**
- Consumes: Task 2의 `AppUser`, Task 3의 `MockDb` · `mockDbProvider`
- Produces:
  - `class Session { const Session({required AppUser user}); final AppUser user; }`
  - `class AuthException implements Exception { const AuthException(String message); final String message; }`
  - `abstract class AuthRepository` — `Future<Session> login({required String email, required String password})`, `Future<Session> loginAs(String userId)`, `Future<void> logout()`, `Future<Session?> restoreSession()`
  - `class MockAuthRepository implements AuthRepository`
  - `authRepositoryProvider` (`Provider<AuthRepository>`) — **교체 지점**
  - `void runAuthRepositoryContract(String name, AuthRepository Function() build)` — Mock과 미래의 API 구현체가 함께 통과해야 하는 계약

- [ ] **Step 1: 계약 테스트를 쓴다**

이것이 "provider 한 줄 교체"를 실제로 보장하는 장치다. 인터페이스에 대해 한 번 쓰고, 지금은 Mock에 물리고, API가 나오면 같은 파일을 `ApiAuthRepository`에 물린다.

`flutter/test/contract/auth_repository_contract.dart`:

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/auth/data/auth_repository.dart';

/// AuthRepository의 모든 구현체가 지켜야 하는 계약.
///
/// [build]는 매 테스트마다 깨끗한 구현체를 만들어 돌려준다.
/// [knownEmail]은 그 구현체에 존재하는 계정의 이메일이다.
void runAuthRepositoryContract(
  String name,
  AuthRepository Function() build, {
  required String knownEmail,
  required String knownUserId,
}) {
  group('$name — AuthRepository 계약', () {
    late AuthRepository repo;

    setUp(() => repo = build());

    test('등록된 이메일로 로그인하면 세션을 돌려준다', () async {
      final session = await repo.login(email: knownEmail, password: 'any');
      expect(session.user.email, equals(knownEmail));
    });

    test('없는 이메일로 로그인하면 AuthException을 던진다', () async {
      expect(
        () => repo.login(email: 'nobody@nowhere.test', password: 'any'),
        throwsA(isA<AuthException>()),
      );
    });

    test('로그인 전에는 복원할 세션이 없다', () async {
      expect(await repo.restoreSession(), isNull);
    });

    test('로그인 후에는 세션이 복원된다', () async {
      await repo.login(email: knownEmail, password: 'any');
      final restored = await repo.restoreSession();
      expect(restored, isNotNull);
      expect(restored!.user.email, equals(knownEmail));
    });

    test('로그아웃하면 세션이 사라진다', () async {
      await repo.login(email: knownEmail, password: 'any');
      await repo.logout();
      expect(await repo.restoreSession(), isNull);
    });

    test('loginAs로 특정 사용자로 바로 진입한다', () async {
      final session = await repo.loginAs(knownUserId);
      expect(session.user.id, equals(knownUserId));
    });

    test('없는 사용자로 loginAs하면 AuthException을 던진다', () async {
      expect(
        () => repo.loginAs('u-does-not-exist'),
        throwsA(isA<AuthException>()),
      );
    });

    test('응답은 즉시 오지 않는다 (지연이 있다)', () async {
      final sw = Stopwatch()..start();
      await repo.login(email: knownEmail, password: 'any');
      sw.stop();
      expect(sw.elapsedMilliseconds, greaterThanOrEqualTo(100));
    });
  });
}
```

`flutter/test/features/auth/auth_repository_mock_test.dart`:

```dart
import 'package:super_sub/core/mock/mock_db.dart';
import 'package:super_sub/features/auth/data/auth_repository_mock.dart';

import '../../contract/auth_repository_contract.dart';

void main() {
  runAuthRepositoryContract(
    'MockAuthRepository',
    () => MockAuthRepository(MockDb()),
    knownEmail: 'player@supersub.test',
    knownUserId: MockDb.playerId,
  );
}
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

```bash
cd flutter && flutter test test/features/auth/auth_repository_mock_test.dart
```

기대: 컴파일 실패 (`auth_repository.dart` 없음).

- [ ] **Step 3: 세션 모델과 인터페이스를 만든다**

`flutter/lib/features/auth/data/models/session.dart`:

```dart
import 'app_user.dart';

class Session {
  const Session({required this.user});

  final AppUser user;

  @override
  bool operator ==(Object other) => other is Session && other.user == user;

  @override
  int get hashCode => user.hashCode;
}
```

`flutter/lib/features/auth/data/auth_repository.dart`:

```dart
import 'models/session.dart';

class AuthException implements Exception {
  const AuthException(this.message);

  final String message;

  @override
  String toString() => message;
}

/// 화면이 아는 유일한 인증 계약.
///
/// 구현체가 Mock인지 API인지 화면은 모른다. 교체는 authRepositoryProvider
/// 한 줄이다. 모든 메서드가 Future인 이유는, 동기 반환이 하나라도 있으면
/// API 전환 시 그 화면을 다시 짜야 하기 때문이다.
abstract class AuthRepository {
  Future<Session> login({required String email, required String password});

  /// 개발용 바로 진입. 릴리즈 빌드의 UI에서는 호출되지 않는다.
  Future<Session> loginAs(String userId);

  Future<void> logout();

  Future<Session?> restoreSession();
}
```

- [ ] **Step 4: Mock 구현체와 provider를 만든다**

`flutter/lib/features/auth/data/auth_repository_mock.dart`:

```dart
import '../../../core/mock/mock_db.dart';
import 'auth_repository.dart';
import 'models/session.dart';

class MockAuthRepository implements AuthRepository {
  MockAuthRepository(this._db);

  final MockDb _db;

  Session? _current;

  static const _delay = Duration(milliseconds: 300);

  @override
  Future<Session> login({
    required String email,
    required String password,
  }) async {
    await Future<void>.delayed(_delay);
    final user = _db.findUserByEmail(email);
    if (user == null) {
      throw const AuthException('등록되지 않은 이메일입니다');
    }
    return _current = Session(user: user);
  }

  @override
  Future<Session> loginAs(String userId) async {
    await Future<void>.delayed(_delay);
    final user = _db.findUserById(userId);
    if (user == null) {
      throw const AuthException('존재하지 않는 사용자입니다');
    }
    return _current = Session(user: user);
  }

  @override
  Future<void> logout() async {
    await Future<void>.delayed(_delay);
    _current = null;
  }

  @override
  Future<Session?> restoreSession() async {
    await Future<void>.delayed(_delay);
    return _current;
  }
}
```

`flutter/lib/features/auth/data/auth_providers.dart`:

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/mock/mock_db.dart';
import 'auth_repository.dart';
import 'auth_repository_mock.dart';

/// 백엔드 교체 지점.
///
/// API가 나오면 이 한 줄을 ApiAuthRepository로 바꾼다.
/// 화면·위젯·컨트롤러는 수정하지 않는다.
final authRepositoryProvider = Provider<AuthRepository>(
  (ref) => MockAuthRepository(ref.watch(mockDbProvider)),
);
```

- [ ] **Step 5: 테스트가 통과하는지 확인한다**

```bash
cd flutter && flutter test test/features/auth/ && flutter analyze
```

기대: 계약 테스트 8개 PASS.

- [ ] **Step 6: 커밋한다**

```bash
git add flutter/lib flutter/test
git commit -m "feat(app): AuthRepository 인터페이스와 Mock 구현, 계약 테스트"
```

---

### Task 5: 세션 컨트롤러와 라우터 분기

**Files:**
- Create: `flutter/lib/features/auth/presentation/session_controller.dart`, `flutter/lib/core/router/app_router.dart`
- Modify: `flutter/lib/app.dart` (MaterialApp → MaterialApp.router)
- Test: `flutter/test/features/auth/session_controller_test.dart`

**Interfaces:**
- Consumes: Task 4의 `AuthRepository`, `authRepositoryProvider`, `Session`, `AuthException`
- Produces:
  - `sealed class SessionState` — `SessionUnknown`, `SessionLoggedOut`, `SessionLoggedIn(AppUser user)`
  - `class SessionController extends Notifier<SessionState>` — `Future<void> login(String email, String password)`, `Future<void> loginAs(String userId)`, `Future<void> logout()`; 로그인 실패 시 `AuthException`을 그대로 던진다
  - `sessionControllerProvider` (`NotifierProvider<SessionController, SessionState>`)
  - `routerProvider` (`Provider<GoRouter>`) — 라우트 `/login`, `/onboarding/sport`, `/home`, `/profile`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`flutter/test/features/auth/session_controller_test.dart`:

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:super_sub/core/mock/mock_db.dart';
import 'package:super_sub/features/auth/data/auth_repository.dart';
import 'package:super_sub/features/auth/presentation/session_controller.dart';

void main() {
  late ProviderContainer container;

  setUp(() {
    container = ProviderContainer();
    addTearDown(container.dispose);
  });

  test('처음에는 세션 상태를 모른다', () {
    expect(container.read(sessionControllerProvider), isA<SessionUnknown>());
  });

  test('복원할 세션이 없으면 로그아웃 상태가 된다', () async {
    container.read(sessionControllerProvider);
    await Future<void>.delayed(const Duration(milliseconds: 500));
    expect(container.read(sessionControllerProvider), isA<SessionLoggedOut>());
  });

  test('로그인하면 로그인 상태가 된다', () async {
    await container
        .read(sessionControllerProvider.notifier)
        .login('player@supersub.test', 'any');
    final state = container.read(sessionControllerProvider);
    expect(state, isA<SessionLoggedIn>());
    expect((state as SessionLoggedIn).user.id, equals(MockDb.playerId));
  });

  test('로그인 실패는 AuthException으로 전달되고 상태는 로그아웃이다', () async {
    await expectLater(
      container
          .read(sessionControllerProvider.notifier)
          .login('nobody@nowhere.test', 'any'),
      throwsA(isA<AuthException>()),
    );
    expect(container.read(sessionControllerProvider), isA<SessionLoggedOut>());
  });

  test('loginAs로 팀 관리자로 진입한다', () async {
    await container
        .read(sessionControllerProvider.notifier)
        .loginAs(MockDb.managerId);
    final state = container.read(sessionControllerProvider);
    expect((state as SessionLoggedIn).user.id, equals(MockDb.managerId));
  });

  test('로그아웃하면 로그아웃 상태가 된다', () async {
    final c = container.read(sessionControllerProvider.notifier);
    await c.login('player@supersub.test', 'any');
    await c.logout();
    expect(container.read(sessionControllerProvider), isA<SessionLoggedOut>());
  });
}
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

```bash
cd flutter && flutter test test/features/auth/session_controller_test.dart
```

기대: 컴파일 실패 (`session_controller.dart` 없음).

- [ ] **Step 3: 세션 컨트롤러를 만든다**

`flutter/lib/features/auth/presentation/session_controller.dart`:

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/auth_providers.dart';
import '../data/models/app_user.dart';

sealed class SessionState {
  const SessionState();
}

/// 앱 시작 직후, 복원 시도가 끝나기 전 상태.
class SessionUnknown extends SessionState {
  const SessionUnknown();
}

class SessionLoggedOut extends SessionState {
  const SessionLoggedOut();
}

class SessionLoggedIn extends SessionState {
  const SessionLoggedIn(this.user);

  final AppUser user;
}

class SessionController extends Notifier<SessionState> {
  @override
  SessionState build() {
    _restore();
    return const SessionUnknown();
  }

  Future<void> _restore() async {
    final session = await ref.read(authRepositoryProvider).restoreSession();
    state = session == null
        ? const SessionLoggedOut()
        : SessionLoggedIn(session.user);
  }

  Future<void> login(String email, String password) async {
    try {
      final session = await ref
          .read(authRepositoryProvider)
          .login(email: email, password: password);
      state = SessionLoggedIn(session.user);
    } catch (_) {
      state = const SessionLoggedOut();
      rethrow;
    }
  }

  Future<void> loginAs(String userId) async {
    final session = await ref.read(authRepositoryProvider).loginAs(userId);
    state = SessionLoggedIn(session.user);
  }

  Future<void> logout() async {
    await ref.read(authRepositoryProvider).logout();
    state = const SessionLoggedOut();
  }
}

final sessionControllerProvider =
    NotifierProvider<SessionController, SessionState>(SessionController.new);
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

```bash
cd flutter && flutter test test/features/auth/session_controller_test.dart
```

기대: 6개 테스트 PASS.

- [ ] **Step 5: 라우터를 만든다**

화면은 Task 7~10에서 만들므로, 지금은 자리표시 위젯으로 라우트만 연결한다. 각 태스크가 해당 자리표시를 실제 화면으로 교체한다.

`flutter/lib/core/router/app_router.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/presentation/session_controller.dart';

/// GoRouter를 provider가 매번 다시 만들면 내비게이션 스택이 날아간다.
/// 그래서 라우터는 한 번만 만들고, 세션 변화는 ValueNotifier로 흘려보내
/// refreshListenable이 redirect를 다시 돌리게 한다.
final routerProvider = Provider<GoRouter>((ref) {
  final refresh = ValueNotifier<SessionState>(const SessionUnknown());
  ref.onDispose(refresh.dispose);
  ref.listen<SessionState>(
    sessionControllerProvider,
    (_, next) => refresh.value = next,
    fireImmediately: true,
  );

  return GoRouter(
    initialLocation: '/home',
    refreshListenable: refresh,
    redirect: (context, state) {
      final session = refresh.value;
      final path = state.matchedLocation;

      // 복원 중에는 아무 데도 보내지 않는다.
      if (session is SessionUnknown) return null;

      final loggedIn = session is SessionLoggedIn;
      if (!loggedIn) return path == '/login' ? null : '/login';
      if (path == '/login') return '/home';
      return null;
    },
    routes: [
      GoRoute(
        path: '/login',
        builder: (_, __) => const _Placeholder('로그인'),
      ),
      GoRoute(
        path: '/onboarding/sport',
        builder: (_, __) => const _Placeholder('종목 선택'),
      ),
      GoRoute(
        path: '/home',
        builder: (_, __) => const _Placeholder('홈'),
      ),
      GoRoute(
        path: '/profile',
        builder: (_, __) => const _Placeholder('프로필'),
      ),
    ],
  );
});

class _Placeholder extends StatelessWidget {
  const _Placeholder(this.label);

  final String label;

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: Text(label)),
        body: Center(child: Text(label)),
      );
}
```

- [ ] **Step 6: app.dart를 라우터에 연결한다**

`flutter/lib/app.dart` 전체를 아래로 교체한다.

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/router/app_router.dart';
import 'core/theme/app_theme.dart';

class SuperSubApp extends ConsumerWidget {
  const SuperSubApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp.router(
      title: 'Super-Sub',
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      routerConfig: ref.watch(routerProvider),
    );
  }
}
```

`flutter/test/smoke_test.dart`를 아래로 교체한다. 이제 첫 화면은 로그인이다.

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:super_sub/app.dart';

void main() {
  testWidgets('로그인하지 않았으면 로그인 화면으로 간다', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: SuperSubApp()));
    await tester.pump(const Duration(milliseconds: 500));
    await tester.pumpAndSettle();
    expect(find.text('로그인'), findsWidgets);
  });
}
```

- [ ] **Step 7: 전체 테스트와 정적 분석을 돌린다**

```bash
cd flutter && flutter test && flutter analyze
```

기대: 전부 PASS, analyze 이슈 0건.

- [ ] **Step 8: 커밋한다**

```bash
git add flutter/lib flutter/test
git commit -m "feat(app): 세션 컨트롤러와 go_router 진입 분기"
```

---

### Task 6: 공통 비동기 상태 위젯

**Files:**
- Create: `flutter/lib/core/widgets/async_view.dart`
- Test: `flutter/test/core/async_view_test.dart`

**Interfaces:**
- Consumes: 없음 (Flutter/Riverpod만)
- Produces: `class AsyncView<T> extends StatelessWidget` — 생성자 `AsyncView({required AsyncValue<T> value, required Widget Function(T) data, bool Function(T)? isEmpty, String emptyMessage, VoidCallback? onRetry})`
- **소비 시점:** 이 계획의 화면들(로그인·온보딩·홈·프로필)은 세션 상태만 쓰므로 `AsyncView`를 직접 쓰지 않는다. 첫 소비처는 계획 2의 영상 목록이다. 지금 만드는 이유는, 목록 화면을 짜면서 급하게 만들면 화면마다 로딩·오류 처리가 제각각이 되기 때문이다. 검증은 Step 1의 위젯 테스트로 한다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

스펙 6절의 네 가지 상태(로딩·성공·빈 결과·오류)를 화면마다 다시 짜지 않기 위한 위젯이다.

`flutter/test/core/async_view_test.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:super_sub/core/widgets/async_view.dart';

Widget _wrap(Widget child) => MaterialApp(home: Scaffold(body: child));

void main() {
  testWidgets('로딩이면 인디케이터를 보여준다', (tester) async {
    await tester.pumpWidget(_wrap(
      AsyncView<List<String>>(
        value: const AsyncValue.loading(),
        data: (d) => Text(d.join()),
      ),
    ));
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
  });

  testWidgets('성공이면 내용을 보여준다', (tester) async {
    await tester.pumpWidget(_wrap(
      AsyncView<List<String>>(
        value: const AsyncValue.data(['가', '나']),
        data: (d) => Text(d.join()),
      ),
    ));
    expect(find.text('가나'), findsOneWidget);
  });

  testWidgets('빈 결과면 안내 문구를 보여준다', (tester) async {
    await tester.pumpWidget(_wrap(
      AsyncView<List<String>>(
        value: const AsyncValue.data([]),
        isEmpty: (d) => d.isEmpty,
        emptyMessage: '아직 영상이 없습니다',
        data: (d) => Text(d.join()),
      ),
    ));
    expect(find.text('아직 영상이 없습니다'), findsOneWidget);
  });

  testWidgets('오류면 사유와 재시도 버튼을 보여준다', (tester) async {
    var retried = false;
    await tester.pumpWidget(_wrap(
      AsyncView<List<String>>(
        value: AsyncValue.error('불러오지 못했습니다', StackTrace.empty),
        onRetry: () => retried = true,
        data: (d) => Text(d.join()),
      ),
    ));
    expect(find.text('불러오지 못했습니다'), findsOneWidget);
    await tester.tap(find.text('다시 시도'));
    expect(retried, isTrue);
  });
}
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

```bash
cd flutter && flutter test test/core/async_view_test.dart
```

기대: 컴파일 실패 (`async_view.dart` 없음).

- [ ] **Step 3: 위젯을 만든다**

`flutter/lib/core/widgets/async_view.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 비동기 화면의 네 가지 상태를 한 곳에서 처리한다.
///
/// Mock이 지연·실패·빈 목록을 실제로 만들어내므로(스펙 4.3) 이 네 상태는
/// 개발 중에 계속 눈에 띈다. 그것이 Mock을 진짜처럼 만드는 이유다.
class AsyncView<T> extends StatelessWidget {
  const AsyncView({
    super.key,
    required this.value,
    required this.data,
    this.isEmpty,
    this.emptyMessage = '표시할 내용이 없습니다',
    this.onRetry,
  });

  final AsyncValue<T> value;
  final Widget Function(T data) data;
  final bool Function(T data)? isEmpty;
  final String emptyMessage;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return value.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('$e', textAlign: TextAlign.center),
            if (onRetry != null) ...[
              const SizedBox(height: 12),
              FilledButton(onPressed: onRetry, child: const Text('다시 시도')),
            ],
          ],
        ),
      ),
      data: (d) {
        if (isEmpty?.call(d) ?? false) {
          return Center(child: Text(emptyMessage));
        }
        return data(d);
      },
    );
  }
}
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

```bash
cd flutter && flutter test test/core/async_view_test.dart && flutter analyze
```

기대: 4개 테스트 PASS.

- [ ] **Step 5: 커밋한다**

```bash
git add flutter/lib flutter/test
git commit -m "feat(app): 로딩/빈/오류 공통 처리 위젯 AsyncView"
```

---

### Task 7: 로그인 화면과 개발용 바로 진입

**Files:**
- Create: `flutter/lib/features/auth/presentation/screens/login_screen.dart`
- Modify: `flutter/lib/core/router/app_router.dart` (`/login`의 `_Placeholder`를 `LoginScreen`으로 교체)
- Test: `flutter/test/features/auth/login_screen_test.dart`

**Interfaces:**
- Consumes: Task 5의 `sessionControllerProvider`, Task 4의 `AuthException`, Task 3의 `MockDb.playerId` · `MockDb.managerId` · `MockDb.newbieId`
- Produces: `class LoginScreen extends ConsumerStatefulWidget`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`flutter/test/features/auth/login_screen_test.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:super_sub/features/auth/presentation/screens/login_screen.dart';
import 'package:super_sub/features/auth/presentation/session_controller.dart';

Widget _wrap() => const ProviderScope(
      child: MaterialApp(home: LoginScreen()),
    );

void main() {
  testWidgets('이메일과 비밀번호 입력란이 있다', (tester) async {
    await tester.pumpWidget(_wrap());
    expect(find.byType(TextField), findsNWidgets(2));
  });

  testWidgets('개발용 바로 진입 계정 3종이 있다', (tester) async {
    await tester.pumpWidget(_wrap());
    expect(find.text('개인 사용자 (데이터 있음)'), findsOneWidget);
    expect(find.text('팀 관리자'), findsOneWidget);
    expect(find.text('신규 가입자 (데이터 0건)'), findsOneWidget);
  });

  testWidgets('없는 이메일로 로그인하면 오류 문구가 뜬다', (tester) async {
    await tester.pumpWidget(_wrap());
    await tester.enterText(find.byKey(const Key('login-email')), 'x@y.test');
    await tester.enterText(find.byKey(const Key('login-password')), 'pw');
    await tester.tap(find.byKey(const Key('login-submit')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 500));
    expect(find.text('등록되지 않은 이메일입니다'), findsOneWidget);
  });

  testWidgets('바로 진입 버튼을 누르면 세션이 생긴다', (tester) async {
    final container = ProviderContainer();
    addTearDown(container.dispose);

    await tester.pumpWidget(UncontrolledProviderScope(
      container: container,
      child: const MaterialApp(home: LoginScreen()),
    ));
    await tester.tap(find.text('팀 관리자'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 500));

    expect(container.read(sessionControllerProvider), isA<SessionLoggedIn>());
  });
}
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

```bash
cd flutter && flutter test test/features/auth/login_screen_test.dart
```

기대: 컴파일 실패 (`login_screen.dart` 없음).

- [ ] **Step 3: 로그인 화면을 만든다**

`flutter/lib/features/auth/presentation/screens/login_screen.dart`:

```dart
import 'package:flutter/foundation.dart' show kDebugMode;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/mock/mock_db.dart';
import '../session_controller.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _email = TextEditingController();
  final _password = TextEditingController();

  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _run(Future<void> Function() action) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await action();
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final controller = ref.read(sessionControllerProvider.notifier);

    return Scaffold(
      appBar: AppBar(title: const Text('로그인')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              key: const Key('login-email'),
              controller: _email,
              decoration: const InputDecoration(labelText: '이메일'),
              keyboardType: TextInputType.emailAddress,
            ),
            const SizedBox(height: 12),
            TextField(
              key: const Key('login-password'),
              controller: _password,
              decoration: const InputDecoration(labelText: '비밀번호'),
              obscureText: true,
            ),
            if (_error != null) ...[
              const SizedBox(height: 12),
              Text(
                _error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ],
            const SizedBox(height: 20),
            FilledButton(
              key: const Key('login-submit'),
              onPressed: _busy
                  ? null
                  : () => _run(
                        () => controller.login(_email.text, _password.text),
                      ),
              child: _busy
                  ? const SizedBox(
                      height: 18,
                      width: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('로그인'),
            ),
            if (kDebugMode) ...[
              const SizedBox(height: 32),
              const Divider(),
              const SizedBox(height: 8),
              Text(
                '개발용 바로 진입',
                style: Theme.of(context).textTheme.labelLarge,
              ),
              const SizedBox(height: 8),
              _DevLoginButton(
                label: '개인 사용자 (데이터 있음)',
                userId: MockDb.playerId,
                busy: _busy,
                onTap: (id) => _run(() => controller.loginAs(id)),
              ),
              _DevLoginButton(
                label: '팀 관리자',
                userId: MockDb.managerId,
                busy: _busy,
                onTap: (id) => _run(() => controller.loginAs(id)),
              ),
              _DevLoginButton(
                label: '신규 가입자 (데이터 0건)',
                userId: MockDb.newbieId,
                busy: _busy,
                onTap: (id) => _run(() => controller.loginAs(id)),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _DevLoginButton extends StatelessWidget {
  const _DevLoginButton({
    required this.label,
    required this.userId,
    required this.busy,
    required this.onTap,
  });

  final String label;
  final String userId;
  final bool busy;
  final void Function(String userId) onTap;

  @override
  Widget build(BuildContext context) {
    return OutlinedButton(
      onPressed: busy ? null : () => onTap(userId),
      child: Text(label),
    );
  }
}
```

- [ ] **Step 4: 라우터를 실제 화면에 연결한다**

`flutter/lib/core/router/app_router.dart`에서 `/login` 라우트를 교체하고 import를 추가한다.

```dart
import '../../features/auth/presentation/screens/login_screen.dart';
```

```dart
      GoRoute(
        path: '/login',
        builder: (_, __) => const LoginScreen(),
      ),
```

- [ ] **Step 5: 테스트가 통과하는지 확인한다**

```bash
cd flutter && flutter test && flutter analyze
```

기대: 로그인 화면 테스트 4개를 포함해 전부 PASS.

- [ ] **Step 6: 커밋한다**

```bash
git add flutter/lib flutter/test
git commit -m "feat(app): 로그인 화면과 개발용 바로 진입(kDebugMode)"
```

---

### Task 8: 종목 전역 컨텍스트와 온보딩 화면

**Files:**
- Create: `flutter/lib/core/sport/current_sport.dart`, `flutter/lib/features/onboarding/presentation/screens/sport_screen.dart`
- Modify: `flutter/lib/core/router/app_router.dart` (`/onboarding/sport` 연결 + redirect 규칙 추가)
- Test: `flutter/test/features/onboarding/sport_screen_test.dart`

**Interfaces:**
- Consumes: Task 3의 `mockDbProvider`(종목 목록), Task 5의 `SessionState`
- Produces:
  - `class CurrentSport extends Notifier<String?>` — `void select(String sportCode)`, `void clear()`
  - `currentSportProvider` (`NotifierProvider<CurrentSport, String?>`)
  - `class SportScreen extends ConsumerWidget`

> **스펙과의 차이 (기록):** ERD의 `user` 테이블에는 선호 종목 컬럼이 없다. 따라서 온보딩에서
> 고른 종목을 저장할 서버 자리가 현재 스키마에 없다. 이 단계에서는 앱 메모리에만 둔다.
> 영구 저장(기기 저장소 또는 스키마 추가)은 스펙 10절 미결 항목으로 넘긴다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`flutter/test/features/onboarding/sport_screen_test.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:super_sub/core/sport/current_sport.dart';
import 'package:super_sub/features/onboarding/presentation/screens/sport_screen.dart';

void main() {
  testWidgets('종목 2개가 보인다', (tester) async {
    await tester.pumpWidget(const ProviderScope(
      child: MaterialApp(home: SportScreen()),
    ));
    expect(find.text('풋살'), findsOneWidget);
    expect(find.text('야구'), findsOneWidget);
  });

  testWidgets('종목을 고르면 전역 컨텍스트에 반영된다', (tester) async {
    final container = ProviderContainer();
    addTearDown(container.dispose);

    await tester.pumpWidget(UncontrolledProviderScope(
      container: container,
      child: const MaterialApp(home: SportScreen()),
    ));

    expect(container.read(currentSportProvider), isNull);
    await tester.tap(find.text('야구'));
    await tester.pump();
    expect(container.read(currentSportProvider), equals('baseball'));
  });
}
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

```bash
cd flutter && flutter test test/features/onboarding/sport_screen_test.dart
```

기대: 컴파일 실패.

- [ ] **Step 3: 종목 컨텍스트를 만든다**

`flutter/lib/core/sport/current_sport.dart`:

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 종목 전역 컨텍스트.
///
/// ERD에서 metric_definition·title_definition·position이 모두 sport_code에
/// 매달려 있다. 즉 지표도 호칭도 포지션도 종목마다 다르다. 나중에 끼워넣으면
/// 거의 모든 화면을 고치게 되므로 처음부터 전역으로 둔다.
///
/// 주의: ERD의 user 테이블에는 선호 종목 컬럼이 없다. 지금은 앱 메모리에만
/// 두고, 영구 저장은 미결 항목이다.
class CurrentSport extends Notifier<String?> {
  @override
  String? build() => null;

  void select(String sportCode) => state = sportCode;

  void clear() => state = null;
}

final currentSportProvider =
    NotifierProvider<CurrentSport, String?>(CurrentSport.new);
```

- [ ] **Step 4: 온보딩 화면을 만든다**

`flutter/lib/features/onboarding/presentation/screens/sport_screen.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/mock/mock_db.dart';
import '../../../../core/sport/current_sport.dart';

class SportScreen extends ConsumerWidget {
  const SportScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final sports = ref.watch(mockDbProvider).sports;

    return Scaffold(
      appBar: AppBar(title: const Text('종목 선택')),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          Text(
            '어떤 종목을 하시나요?',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 16),
          for (final sport in sports)
            Card(
              child: ListTile(
                title: Text(sport.name),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => ref
                    .read(currentSportProvider.notifier)
                    .select(sport.code),
              ),
            ),
        ],
      ),
    );
  }
}
```

- [ ] **Step 5: 라우터에 연결하고 진입 규칙을 추가한다**

`flutter/lib/core/router/app_router.dart`에 import를 추가한다.

```dart
import '../../features/onboarding/presentation/screens/sport_screen.dart';
import '../sport/current_sport.dart';
```

`routerProvider` 안에서 종목 상태도 새로고침 대상에 넣는다. `refresh`를 두 값의 조합으로 바꾼다.

```dart
final routerProvider = Provider<GoRouter>((ref) {
  final refresh = ValueNotifier<int>(0);
  ref.onDispose(refresh.dispose);

  SessionState session = const SessionUnknown();
  String? sport;

  ref.listen<SessionState>(sessionControllerProvider, (_, next) {
    session = next;
    refresh.value++;
  }, fireImmediately: true);

  ref.listen<String?>(currentSportProvider, (_, next) {
    sport = next;
    refresh.value++;
  }, fireImmediately: true);

  return GoRouter(
    initialLocation: '/home',
    refreshListenable: refresh,
    redirect: (context, state) {
      final path = state.matchedLocation;

      if (session is SessionUnknown) return null;

      final loggedIn = session is SessionLoggedIn;
      if (!loggedIn) return path == '/login' ? null : '/login';

      // 로그인은 했는데 종목을 아직 안 골랐으면 온보딩으로.
      if (sport == null) {
        return path == '/onboarding/sport' ? null : '/onboarding/sport';
      }

      if (path == '/login' || path == '/onboarding/sport') return '/home';
      return null;
    },
    routes: [
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      GoRoute(
        path: '/onboarding/sport',
        builder: (_, __) => const SportScreen(),
      ),
      GoRoute(path: '/home', builder: (_, __) => const _Placeholder('홈')),
      GoRoute(
        path: '/profile',
        builder: (_, __) => const _Placeholder('프로필'),
      ),
    ],
  );
});
```

- [ ] **Step 6: 테스트가 통과하는지 확인한다**

```bash
cd flutter && flutter test && flutter analyze
```

기대: 전부 PASS.

- [ ] **Step 7: 커밋한다**

```bash
git add flutter/lib flutter/test
git commit -m "feat(app): 종목 전역 컨텍스트와 온보딩 화면"
```

---

### Task 9: 홈 화면

**Files:**
- Create: `flutter/lib/features/home/presentation/screens/home_screen.dart`
- Modify: `flutter/lib/core/router/app_router.dart` (`/home` 연결)
- Test: `flutter/test/features/home/home_screen_test.dart`

**Interfaces:**
- Consumes: Task 5의 `sessionControllerProvider` · `SessionLoggedIn`, Task 8의 `currentSportProvider`, Task 3의 `mockDbProvider`
- Produces: `class HomeScreen extends ConsumerWidget`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`flutter/test/features/home/home_screen_test.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:super_sub/core/mock/mock_db.dart';
import 'package:super_sub/core/sport/current_sport.dart';
import 'package:super_sub/features/auth/presentation/session_controller.dart';
import 'package:super_sub/features/home/presentation/screens/home_screen.dart';

Future<ProviderContainer> _pumpLoggedIn(WidgetTester tester) async {
  final container = ProviderContainer();
  addTearDown(container.dispose);
  await container
      .read(sessionControllerProvider.notifier)
      .loginAs(MockDb.playerId);
  container.read(currentSportProvider.notifier).select('futsal');

  await tester.pumpWidget(UncontrolledProviderScope(
    container: container,
    child: const MaterialApp(home: HomeScreen()),
  ));
  await tester.pumpAndSettle();
  return container;
}

void main() {
  testWidgets('닉네임과 현재 종목을 보여준다', (tester) async {
    await _pumpLoggedIn(tester);
    expect(find.textContaining('김용병'), findsOneWidget);
    expect(find.text('풋살'), findsOneWidget);
  });

  testWidgets('종목을 전환할 수 있다', (tester) async {
    final container = await _pumpLoggedIn(tester);
    await tester.tap(find.byKey(const Key('home-sport-switch')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('야구').last);
    await tester.pumpAndSettle();
    expect(container.read(currentSportProvider), equals('baseball'));
  });

  testWidgets('로그아웃 버튼이 있다', (tester) async {
    final container = await _pumpLoggedIn(tester);
    await tester.tap(find.byKey(const Key('home-logout')));
    await tester.pump(const Duration(milliseconds: 500));
    expect(container.read(sessionControllerProvider), isA<SessionLoggedOut>());
  });
}
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

```bash
cd flutter && flutter test test/features/home/home_screen_test.dart
```

기대: 컴파일 실패.

- [ ] **Step 3: 홈 화면을 만든다**

`flutter/lib/features/home/presentation/screens/home_screen.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/mock/mock_db.dart';
import '../../../../core/sport/current_sport.dart';
import '../../../../core/sport/sport.dart';
import '../../../auth/presentation/session_controller.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(sessionControllerProvider);
    final sportCode = ref.watch(currentSportProvider);
    final sports = ref.watch(mockDbProvider).sports;

    final nickname =
        session is SessionLoggedIn ? session.user.nickname : '';
    final sportName = sports
        .where((s) => s.code == sportCode)
        .map((s) => s.name)
        .join();

    return Scaffold(
      appBar: AppBar(
        title: const Text('홈'),
        actions: [
          IconButton(
            key: const Key('home-logout'),
            icon: const Icon(Icons.logout),
            tooltip: '로그아웃',
            onPressed: () =>
                ref.read(sessionControllerProvider.notifier).logout(),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            '$nickname 님, 안녕하세요',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 16),
          Card(
            child: ListTile(
              key: const Key('home-sport-switch'),
              title: Text(sportName),
              subtitle: const Text('종목 전환'),
              trailing: const Icon(Icons.swap_horiz),
              onTap: () => _showSportSheet(context, ref, sports),
            ),
          ),
          const SizedBox(height: 8),
          Card(
            child: ListTile(
              title: const Text('내 프로필'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => context.go('/profile'),
            ),
          ),
        ],
      ),
    );
  }

  void _showSportSheet(
    BuildContext context,
    WidgetRef ref,
    List<Sport> sports,
  ) {
    showModalBottomSheet<void>(
      context: context,
      builder: (sheetContext) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            for (final sport in sports)
              ListTile(
                title: Text(sport.name),
                onTap: () {
                  ref
                      .read(currentSportProvider.notifier)
                      .select(sport.code);
                  Navigator.of(sheetContext).pop();
                },
              ),
          ],
        ),
      ),
    );
  }
}
```

- [ ] **Step 4: 라우터에 연결한다**

`flutter/lib/core/router/app_router.dart`에 import를 추가하고 `/home` 라우트를 교체한다.

```dart
import '../../features/home/presentation/screens/home_screen.dart';
```

```dart
      GoRoute(path: '/home', builder: (_, __) => const HomeScreen()),
```

- [ ] **Step 5: 테스트가 통과하는지 확인한다**

```bash
cd flutter && flutter test && flutter analyze
```

기대: 전부 PASS.

- [ ] **Step 6: 커밋한다**

```bash
git add flutter/lib flutter/test
git commit -m "feat(app): 홈 화면 (종목 전환·로그아웃)"
```

---

### Task 10: 프로필 화면과 수정 바텀시트

**Files:**
- Create: `flutter/lib/features/profile/presentation/screens/profile_screen.dart`
- Modify: `flutter/lib/core/router/app_router.dart` (`/profile` 연결), `flutter/lib/features/auth/presentation/session_controller.dart` (`updateNickname` 추가)
- Test: `flutter/test/features/profile/profile_screen_test.dart`

**Interfaces:**
- Consumes: Task 5의 `sessionControllerProvider` · `SessionLoggedIn`, Task 2의 `AppUser.copyWith`
- Produces:
  - `SessionController.updateNickname(String nickname)` — 세션의 사용자 닉네임을 바꾼다
  - `class ProfileScreen extends ConsumerWidget`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`flutter/test/features/profile/profile_screen_test.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:super_sub/core/mock/mock_db.dart';
import 'package:super_sub/features/auth/presentation/session_controller.dart';
import 'package:super_sub/features/profile/presentation/screens/profile_screen.dart';

Future<ProviderContainer> _pump(WidgetTester tester, String userId) async {
  final container = ProviderContainer();
  addTearDown(container.dispose);
  await container.read(sessionControllerProvider.notifier).loginAs(userId);

  await tester.pumpWidget(UncontrolledProviderScope(
    container: container,
    child: const MaterialApp(home: ProfileScreen()),
  ));
  await tester.pumpAndSettle();
  return container;
}

void main() {
  testWidgets('닉네임과 이메일을 보여준다', (tester) async {
    await _pump(tester, MockDb.playerId);
    expect(find.text('김용병'), findsOneWidget);
    expect(find.text('player@supersub.test'), findsOneWidget);
  });

  testWidgets('바텀시트에서 닉네임을 바꾼다', (tester) async {
    final container = await _pump(tester, MockDb.playerId);

    await tester.tap(find.byKey(const Key('profile-edit')));
    await tester.pumpAndSettle();

    await tester.enterText(find.byKey(const Key('profile-nickname')), '김교체');
    await tester.tap(find.byKey(const Key('profile-save')));
    await tester.pumpAndSettle();

    final state = container.read(sessionControllerProvider) as SessionLoggedIn;
    expect(state.user.nickname, equals('김교체'));
    expect(find.text('김교체'), findsOneWidget);
  });
}
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

```bash
cd flutter && flutter test test/features/profile/profile_screen_test.dart
```

기대: 컴파일 실패.

- [ ] **Step 3: 세션 컨트롤러에 닉네임 변경을 추가한다**

`flutter/lib/features/auth/presentation/session_controller.dart`의 `SessionController` 안에 아래 메서드를 추가한다.

```dart
  void updateNickname(String nickname) {
    final current = state;
    if (current is! SessionLoggedIn) return;
    state = SessionLoggedIn(current.user.copyWith(nickname: nickname));
  }
```

- [ ] **Step 4: 프로필 화면을 만든다**

`flutter/lib/features/profile/presentation/screens/profile_screen.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../auth/presentation/session_controller.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(sessionControllerProvider);

    if (session is! SessionLoggedIn) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    final user = session.user;

    return Scaffold(
      appBar: AppBar(
        title: const Text('프로필'),
        actions: [
          IconButton(
            key: const Key('profile-edit'),
            icon: const Icon(Icons.edit),
            tooltip: '프로필 수정',
            onPressed: () => _showEditSheet(context, ref, user.nickname),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          ListTile(
            title: Text(
              user.nickname,
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            subtitle: Text(user.email),
          ),
          const Divider(),
          ListTile(
            title: const Text('가입일'),
            trailing: Text(
              '${user.createdAt.year}.${user.createdAt.month}.${user.createdAt.day}',
            ),
          ),
        ],
      ),
    );
  }

  void _showEditSheet(BuildContext context, WidgetRef ref, String current) {
    final controller = TextEditingController(text: current);

    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (sheetContext) => Padding(
        padding: EdgeInsets.only(
          left: 20,
          right: 20,
          top: 20,
          bottom: MediaQuery.of(sheetContext).viewInsets.bottom + 20,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('닉네임 수정'),
            const SizedBox(height: 12),
            TextField(
              key: const Key('profile-nickname'),
              controller: controller,
              decoration: const InputDecoration(labelText: '닉네임'),
            ),
            const SizedBox(height: 16),
            FilledButton(
              key: const Key('profile-save'),
              onPressed: () {
                ref
                    .read(sessionControllerProvider.notifier)
                    .updateNickname(controller.text);
                Navigator.of(sheetContext).pop();
              },
              child: const Text('저장'),
            ),
          ],
        ),
      ),
    );
  }
}
```

- [ ] **Step 5: 라우터에 연결하고 자리표시 위젯을 정리한다**

`flutter/lib/core/router/app_router.dart`에 import를 추가하고 `/profile` 라우트를 교체한다.

```dart
import '../../features/profile/presentation/screens/profile_screen.dart';
```

```dart
      GoRoute(path: '/profile', builder: (_, __) => const ProfileScreen()),
```

모든 라우트가 실제 화면에 연결되었으므로 `_Placeholder` 클래스를 파일에서 삭제한다.

- [ ] **Step 6: 전체 테스트와 정적 분석을 돌린다**

```bash
cd flutter && flutter test && flutter analyze
```

기대: 전부 PASS, analyze 이슈 0건.

- [ ] **Step 7: 시뮬레이터에서 직접 확인한다**

```bash
cd flutter && open -a Simulator && flutter run
```

확인할 것: 로그인 화면 진입 → "팀 관리자" 바로 진입 → 종목 선택 → 홈에 닉네임 표시 →
프로필 이동 → 닉네임 수정 → 로그아웃 시 로그인 화면 복귀.

- [ ] **Step 8: 커밋한다**

```bash
git add flutter/lib flutter/test
git commit -m "feat(app): 프로필 화면과 닉네임 수정 바텀시트"
```

---

## 완료 기준

- `cd flutter && flutter test` 전부 통과
- `cd flutter && flutter analyze` 이슈 0건
- 시뮬레이터에서 로그인 → 종목 선택 → 홈 → 프로필 → 로그아웃 왕복이 동작
- `flutter/` 밖의 파일이 하나도 수정되지 않음 (`git status`로 확인)
- `AuthRepository` 계약 테스트가 존재하며, 이후 `ApiAuthRepository`에 그대로 재사용 가능

## 다음 계획서

이 계획은 스펙 8절의 단계 0~1까지다. 이어지는 범위는 별도 계획서로 나눈다.

- 계획 2 — 영상 업로드·목록·분석 상태·리포트 (단계 2)
- 계획 3 — 선수 카드·호칭·공개 카드 딥링크 (단계 3)
- 계획 4 — 경기 탐색·지원·팀 관리자 매칭 (단계 4~5)
- 계획 5 — 평가·신고·불참, 크레딧·코치 (단계 6)
