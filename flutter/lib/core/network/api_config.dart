/// FastAPI 백엔드(`fastapi/`, 계약은 `fastapi/docs/api-contract.md`) 주소.
///
/// 기본값은 `127.0.0.1`이다 — 실기기에서 USB로 붙여 테스트할 때는
/// `adb reverse tcp:8000 tcp:8000`으로 기기의 localhost:8000을 이 PC의
/// FastAPI(`uvicorn app.main:app --host 0.0.0.0 --port 8000`)로 그대로 이어준다.
///
/// 같은 Wi-Fi의 실기기에 무선으로 붙이거나 다른 환경을 쓸 때는 실행 시
/// 오버라이드한다:
///   flutter run --dart-define=API_BASE_URL=http://192.168.0.10:8000/api/v1
const String apiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://127.0.0.1:8000/api/v1',
);
