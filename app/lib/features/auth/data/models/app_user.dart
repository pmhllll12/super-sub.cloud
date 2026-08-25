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
