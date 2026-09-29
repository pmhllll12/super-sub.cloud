import '../../../core/network/api_client.dart';
import 'contact_repository.dart';
import 'models/contact.dart';

/// `fastapi/` 백엔드에 붙는 실제 구현. 계약은 `api-contract.md` 3-12절.
class ApiContactRepository implements ContactRepository {
  ApiContactRepository(this._api);

  final ApiClient _api;

  @override
  Future<List<Contact>> contacts() async {
    /* 🔴 **이 경로만 `items` 로 한 겹 감싸여 온다**(계약). 다른 목록처럼
       `getList` 로 읽으면 `type 'Map' is not a subtype of List` 로 터진다. */
    final body = await _api.get('/me/contacts');
    final items = (body['items'] as List?) ?? const [];
    return items
        .cast<Map<String, dynamic>>()
        .map(Contact.fromJson)
        .toList();
  }

  @override
  Future<List<ContactRequest>> requests() async =>
      (await _api.getList('/me/contacts/requests'))
          .map(ContactRequest.fromJson)
          .toList();

  @override
  Future<List<FoundUser>> search(String query) async {
    if (query.isEmpty) return const [];
    final q = Uri(queryParameters: {'q': query}).query;
    return (await _api.getList('/users/search?$q'))
        .map(FoundUser.fromJson)
        .toList();
  }

  @override
  Future<void> request(String targetUserId) async {
    try {
      await _api.post('/me/contacts', {'target_user_id': targetUserId});
    } on ApiException catch (e) {
      /* 🔴 **`ALREADY_REQUESTED` 만** 삼킨다. 원하던 상태가 이미 이뤄진
         것이라 오류로 보일 이유가 없다. 409 를 통째로 삼키면 나중에 다른
         409 가 생겼을 때 조용히 묻힌다 — `code` 로 가른다. */
      if (e.code == 'ALREADY_REQUESTED') return;
      rethrow;
    }
  }

  @override
  Future<void> accept(String contactId) =>
      _api.post('/me/contacts/${Uri.encodeComponent(contactId)}/accept', null);
}
