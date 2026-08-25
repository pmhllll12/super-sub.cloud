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
