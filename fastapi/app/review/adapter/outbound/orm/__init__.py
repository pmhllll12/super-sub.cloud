"""SQLAlchemy ORM 모델. 부록 D 도메인 ⑤ (평가·신뢰).

⚠️ 새 모델을 만들면 `alembic/env.py` 에도 등록한다. 빠뜨리면 `--autogenerate` 가
그 테이블을 "DB 에만 있는 것"으로 보고 `DROP TABLE` 을 만든다
(`tests/test_architecture.py` 의 `TestOrmRegistration`).

🔴 **이 다섯은 2026-09-04 에 마이그레이션보다 늦게 왔다.** 박민호가 스키마를
먼저 내고(`2649dd9`) 애플리케이션 계층은 확인을 기다리며 멈춰 있었는데, 그 사이
`main` 에 마이그레이션만 들어가 **`alembic check` 가 DROP TABLE 을 만들어 CI 가
깨졌다.** 마이그레이션과 ORM 은 같이 가야 한다.
"""
