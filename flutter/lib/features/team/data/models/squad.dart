/// 스쿼드에 등재된 한 명.
class SquadMember {
  const SquadMember({
    required this.id,
    required this.playerCardId,
    required this.nickname,
    required this.positionCode,
    required this.positionLabel,
    required this.accepted,
    this.cardPublicSlug,
    this.gridCol,
    this.gridRow,
  });

  factory SquadMember.fromJson(Map<String, dynamic> json) => SquadMember(
        id: json['id'] as String,
        playerCardId: json['player_card_id'] as String,
        // 🔴 내부 id 를 밖에 내보내지 않는 것이 카드와 같은 원칙이라, 남의
        //    카드로 가는 길은 이 슬러그뿐이다. `null` 도 정상이다.
        cardPublicSlug: json['card_public_slug'] as String?,
        nickname: json['nickname'] as String,
        positionCode: json['position_code'] as String,
        positionLabel: json['position_label'] as String,
        gridCol: json['grid_col'] as int?,
        gridRow: json['grid_row'] as int?,
        /* 🔴 **칸이 아예 없으면 수락된 것으로 본다.** 옛 응답에는 이 칸이
           없었고 그때는 팀원만 앉을 수 있어 앉은 것이 곧 온 것이었다. 새
           응답에서 `null` 로 **와 있으면** 그때는 정말 대기중이다.

           ⚠️ 이 필드는 계약 문서 3-7절에 아직 안 적혀 있다(계약 60으로
           들어왔는데 문서 반영이 덜 됐다). 웹도 같은 판단을 하고 있고,
           정어진에게 문서 보강을 요청해 두었다. */
        accepted:
            !json.containsKey('accepted_at') || json['accepted_at'] != null,
      );

  final String id;
  final String playerCardId;

  /// 그 사람의 공개 카드로 가는 길(`GET /cards/{slug}`). `null` 일 수 있다.
  final String? cardPublicSlug;

  final String nickname;

  /// 🔴 **종목 안에서 찾는 값이다** — 약칭이 종목을 넘나든다(야구 `C` 는 포수,
  /// 농구 `C` 는 센터). 앱이 약칭으로 자리 이름을 **지어내지 않는다.**
  final String positionCode;

  /// 서버가 준 사람이 읽을 이름(「골키퍼」). 지어내지 않고 이걸 그린다.
  final String positionLabel;

  final int? gridCol;
  final int? gridRow;

  /// 이 사람이 **오기로 했는가**. 대기중이면 판에서 흐리게 그린다.
  final bool accepted;

  /// 판 칸에 올라가 있는가. 🔴 **둘은 함께 있거나 함께 없다**(계약).
  bool get hasSeat => gridCol != null && gridRow != null;

  /// 🔴 **아직 서버의 등재가 아니다** — 초대만 보내고 화면이 먼저 앉혀 둔
  /// 자리다(`squadWithSeatInvited`). [id] 는 `squad_member.id` 가 아니라
  /// **초대 id** 이고, [playerCardId] 는 모르는 값이라 비어 있다.
  ///
  /// 🔴 **이런 등재를 서버로 보내면 404 「등재를 찾을 수 없습니다」다**
  /// (2026-09-25 실기기에서 실제로 떴다) — 자리 박기·옮기기·빼기가 전부
  /// 이 값을 먼저 본다.
  bool get isPendingInvite => playerCardId.isEmpty;
}

/// 팀 하나의 스쿼드 — **팀 단위 카드 묶음**이다.
///
/// 경로가 `/teams/{id}/squad` **단수**이고 생성이 멱등이라 애플리케이션은 팀당
/// 하나로 다룬다(스키마는 여러 개를 허용하지만 이름 컬럼이 없어 구별할 수 없다).
class Squad {
  const Squad({
    required this.id,
    required this.teamId,
    required this.publicSlug,
    required this.members,
    this.formation,
  });

  factory Squad.fromJson(Map<String, dynamic> json) => Squad(
        id: json['id'] as String,
        teamId: json['team_id'] as String,
        publicSlug: json['public_slug'] as String,
        /* ⚠️ **`null` 을 만날 수 있다** — 2026-09-18 이전에 만들어진 스쿼드다.
           그전에는 크기 단추를 눌러 바꿀 때만 저장했는데 화면이 값 없이도
           기본 판을 켜진 것처럼 그려서 아무도 안 눌렀고, 실제 DB 가 거의 전부
           null 이었다. 읽는 쪽은 「모르는 값이면 기본 판으로 연다」를 지킨다. */
        formation: json['formation'] as String?,
        members: ((json['members'] as List<dynamic>?) ?? const [])
            .map((e) => SquadMember.fromJson(e as Map<String, dynamic>))
            .toList(growable: false),
      );

  final String id;
  final String teamId;

  /// 누구나 읽을 수 있는 판 주소(`GET /squads/{public_slug}`). 96비트 난수라
  /// 그 자체가 접근 통제다(SEC-005).
  final String publicSlug;

  /// 판 크기 — `"3:3"`·`"5:5"`·`"7:7"`. `null` 일 수 있다(위 주석).
  final String? formation;

  final List<SquadMember> members;
}
