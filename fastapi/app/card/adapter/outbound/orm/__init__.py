"""SQLAlchemy ORM 모델.

여기 있는 클래스는 **테이블 모양**이지 도메인이 아니다. 도메인 엔티티는
`domain/entities/` 에 있고, 둘 사이 변환은 `../mappers/` 가 맡는다.

⚠️ 새 모델을 만들면 Alembic 이 아는 metadata 에 **반드시 등록한다.**
등록을 빠뜨리면 `--autogenerate` 가 그 테이블을 "DB 에만 있는 것"으로 보고
`DROP TABLE` 을 만든다.
"""
