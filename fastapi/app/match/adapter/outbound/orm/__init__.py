"""SQLAlchemy ORM 모델.

⚠️ 새 모델을 만들면 `alembic/env.py` 에도 등록한다. 빠뜨리면 `--autogenerate` 가
그 테이블을 "DB 에만 있는 것"으로 보고 `DROP TABLE` 을 만든다
(`tests/test_architecture.py` 의 `TestOrmRegistration`).
"""
