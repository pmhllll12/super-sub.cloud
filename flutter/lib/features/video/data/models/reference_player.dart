/// 견줄 **본보기 선수** — 계약 3-14절 `GET /reference-players`.
///
/// 🔴 **서버는 이름과 id 만 준다. 재생 주소는 안 준다.**
/// 선수 원본 영상이 S3 에 없어서다(EC2 역할에 `videos/` 접두사 쓰기 권한이 없다 —
/// 정어진이 2026-09-15 에 올리려다 막혔고, 계약 문서가 그 자리에
/// 「이번 범위에서 안 한 것 — 재생 주소」로 적어 두었다).
///
/// 그래서 **영상은 앱이 들고 다닌다**(`assets/compare/`). 웹도 같은 처지라
/// 자기 `public/compare/` 에 둔 사본을 튼다 — 같은 파일이다.
library;

/// 선수 한 명.
class ReferencePlayer {
  const ReferencePlayer({required this.id, required this.name});

  /// `rovelli` · `castanheira`. 🔴 **웹의 `COMPARE` 배열 id 와 같은 값이다** —
  /// 서버가 그렇게 맞춰 두었으니 앱도 이 값으로 영상을 찾는다.
  final String id;

  /// 화면에 적는 이름.
  ///
  /// 🔴 **지어낸 가상 인물이다** — 실존 선수 이름을 넣지 말 것(퍼블리시티권).
  /// 영상도 같은 까닭으로 Pexels 무료 클립이다(미결 `paik` 28번, 박민호 판단 대기).
  final String name;

  factory ReferencePlayer.fromJson(Map<String, dynamic> json) => ReferencePlayer(
    id: json['id'] as String,
    name: (json['name'] as String?) ?? '',
  );

  /// 이 선수의 **관절 에셋 경로** — 🔴 **서버가 준 응답을 그대로 담아 둔 것**
  /// 이라 `Skeleton.fromJson` 에 그대로 물린다. 없으면 `null`(서버에 묻는다).
  ///
  /// 🔴 **왜 들고 다니나.** 같은 값을 서버에 물으면 **0.67~11.5초**로 들쭉날쭉
  /// 하다(2026-09-25, 여덟 번 실측). 계약이 「관절은 DB 에 없고 요청마다 S3 의
  /// 리포트에서 읽는다」고 정해 두어서다. **선수 관절은 절대 안 바뀌는 값**이라
  /// 기기에 두면 그 변덕이 통째로 사라진다 — 영상을 들고 다니는 것과 같은 까닭.
  ///
  /// ⚠️ **정상호가 본보기를 다시 분석하면 여기도 다시 받아야 한다.** 그때는
  /// 아래 명령으로 덮는다(토큰은 `www/src/app/login/page.tsx` 의 심사위원 계정):
  ///
  /// ```
  /// curl -s "$BASE/reference-players/<id>/skeleton" -H "Authorization: Bearer <토큰>" \
  ///   -o flutter/assets/compare/<id>.skeleton.json
  /// ```
  String? get skeletonAsset => _skeletons[id];

  /// 이 선수의 **영상 에셋 경로**. 🔴 **없으면 `null`.**
  ///
  /// 서버가 우리가 안 들고 있는 선수를 새로 내줄 수 있다. 그때 화면은 뼈대
  /// 카드와 문장만 보여 주고 **영상 칸을 비운다** — 없는 에셋을 틀려고 하면
  /// 앱이 죽는다.
  String? get clipAsset => _clips[id];
}

/// 🔴 **여기 있는 것만 틀 수 있다.** 파일을 더하면 `pubspec.yaml` 의
/// `assets:` 에도 같이 넣어야 한다 — 안 그러면 **빌드는 되고 재생만 안 된다.**
const Map<String, String> _clips = {
  'rovelli': 'assets/compare/rovelli.mp4',
  'castanheira': 'assets/compare/castanheira.mp4',
};

/// 🔴 **[_clips] 와 짝이다** — 하나만 더하면 영상은 도는데 관절이 안 붙거나
/// 그 반대가 된다. 서버가 새 선수를 내주면 **둘 다 없어도 된다**(그때는
/// 영상 칸을 비우고 관절은 서버에 묻는다).
const Map<String, String> _skeletons = {
  'rovelli': 'assets/compare/rovelli.skeleton.json',
  'castanheira': 'assets/compare/castanheira.skeleton.json',
};
