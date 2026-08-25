import 'app_user.dart';

class Session {
  const Session({required this.user});

  final AppUser user;

  @override
  bool operator ==(Object other) => other is Session && other.user == user;

  @override
  int get hashCode => user.hashCode;
}
