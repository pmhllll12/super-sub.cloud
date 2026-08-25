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
