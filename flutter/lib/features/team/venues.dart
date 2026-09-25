/// **경기장 목록** — 신청할 때 고르는 구장.
///
/// 🔴 **지어낸 이름이 아니다.** 서울시 공공서비스예약(yeyak.seoul.go.kr)
/// 열린데이터에서 뽑은 실제 시설이고, 웹 `www/src/lib/venues.ts` 의 축구·
/// 풋살 항목을 **이름과 자치구만** 옮긴 것이다. 예약 시간대·링크는 앱이
/// 아직 안 쓰므로 안 옮겼다 — 필요해지면 그쪽에서 마저 가져온다.
///
/// 🔴 **우리가 예약을 중개하지 않는다**(미결 7번, 2026-09-04 박민호). 여기
/// 이름은 「어디서 만날까」를 적는 값일 뿐이다.
///
/// ⚠️ 서버가 주는 참조 데이터가 아니다 — 계약에 경로가 없어 양쪽에 붙박이로
/// 둔다. 경로가 생기면 **웹과 이 파일을 같이** 갈아 끼운다.
library;

class Venue {
  const Venue({required this.id, required this.name, required this.region});

  final String id;
  final String name;

  /// `서울 마포구` — 지역 목록(`regions.dart`)과 **같은 표기**여야 한다.
  final String region;
}

const List<Venue> kVenues = [
  Venue(id: 'mapo-01', name: '서울특별시 산악문화체험센터 난지천인조잔디축구장', region: '서울 마포구'),
  Venue(id: 'mapo-02', name: '서울특별시 산악문화체험센터 난지천 공원 풋살장', region: '서울 마포구'),
  Venue(id: 'songpa-01', name: '잠실종합운동장 풋살경기장', region: '서울 송파구'),
  Venue(id: 'songpa-02', name: '잠실종합운동장 제2풋살경기장', region: '서울 송파구'),
  Venue(id: 'yeongdeungpo-01', name: '영등포공원 풋살경기장', region: '서울 영등포구'),
  Venue(id: 'dongjak-01', name: '보라매공원 관리사무소. 인조잔디축구장', region: '서울 동작구'),
  Venue(id: 'gangdong-03', name: '광나루한강공원 축구장 2', region: '서울 강동구'),
  Venue(id: 'gangdong-05', name: '광나루한강공원 축구장 3', region: '서울 강동구'),
  Venue(id: 'gwangjin-03', name: '뚝섬한강공원 축구장 1', region: '서울 광진구'),
  Venue(id: 'gwangjin-04', name: '뚝섬한강공원 축구장 2', region: '서울 광진구'),
  Venue(id: 'seocho-01', name: '잠원한강공원 축구장', region: '서울 서초구'),
  Venue(id: 'seocho-03', name: '반포한강공원 축구장', region: '서울 서초구'),
  Venue(id: 'yongsan-01', name: '이촌한강공원 축구장', region: '서울 용산구'),
  Venue(id: 'yongsan-02', name: '이촌한강공원 풋살경기장(옥수역하부)', region: '서울 용산구'),
  Venue(id: 'yeongdeungpo-02', name: '양화한강공원 축구장', region: '서울 영등포구'),
  Venue(id: 'mapo-04', name: '망원한강공원 축구장', region: '서울 마포구'),
  Venue(id: 'guro-01', name: '계남근린공원 인조잔디축구장', region: '서울 구로구'),
  Venue(id: 'guro-02', name: '안양천 체육시설 풋살경기장(구일역 하부)', region: '서울 구로구'),
  Venue(id: 'seongdong-01', name: '중랑물재생센터 축구장', region: '서울 성동구'),
  Venue(id: 'yangcheon-01', name: '서서울호수공원', region: '서울 양천구'),
  Venue(id: 'mapo-08', name: '서울월드컵경기장 보조구장', region: '서울 마포구'),
  Venue(id: 'gwangjin-06', name: '서울어린이대공원 잔디축구장', region: '서울 광진구'),
  Venue(id: 'mapo-09', name: '서울월드컵경기장 풋살구장', region: '서울 마포구'),
  Venue(id: 'guro-03', name: '고척스카이돔', region: '서울 구로구'),
  Venue(id: 'seocho-05', name: '인재개발원 축구장', region: '서울 서초구'),
  Venue(id: 'seocho-06', name: '방배배수지체육공원', region: '서울 서초구'),
  Venue(id: 'mapo-10', name: '망원유수지 풋살장 망원유수지 풋살구장', region: '서울 마포구'),
  Venue(id: 'seocho-07', name: '양재근린공원 축구장', region: '서울 서초구'),
  Venue(id: 'dongjak-02', name: '노들나루공원(노들배수지공원)', region: '서울 동작구'),
];

/// 고른 지역의 구장을 **앞으로** 보낸 목록.
///
/// 🔴 목록에서 빼지는 않는다 — 우리 동네에 구장이 없을 수도 있고, 그때
/// 고를 것이 하나도 없으면 신청 자체를 못 한다.
List<Venue> venuesFor(List<String> regions) {
  final mine = <Venue>[];
  final rest = <Venue>[];
  for (final v in kVenues) {
    (regions.contains(v.region) ? mine : rest).add(v);
  }
  return [...mine, ...rest];
}
