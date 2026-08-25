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
