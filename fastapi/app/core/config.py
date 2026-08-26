"""환경설정.

환경변수 키 이름은 팀 저장소(super-sub.cloud)의 `.env.example`을 그대로 따른다.
그쪽이 정본이므로 여기서 이름을 바꾸지 않는다. 팀 파일에는 이 앱이 아직 쓰지 않는
키(IAM 인증, AWS 자격증명 등)도 있어서 `extra="ignore"`로 흘려보낸다.
"""

from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "local"

    # --- 인증 ---------------------------------------------------------------
    # 🔴 비어 있으면 토큰을 발급하지 않는다(503). 조용한 기본값을 두면 그 값으로
    #    서명된 토큰을 누구나 만들 수 있으므로, 없으면 크게 실패하는 편이 낫다.
    #    운영 값은 배포 환경의 비밀 저장소에서 주입한다.
    jwt_secret: str = ""

    # --- Aurora PostgreSQL (pgvector) ---
    rds_host: str = ""
    rds_port: int = 5432
    rds_db_name: str = ""
    rds_user: str = ""
    rds_password: str = ""
    rds_ssl_mode: str = "require"

    # 드라이버가 URL만 받는 경우 쓴다. 값이 있으면 위 항목보다 우선한다.
    database_url: str = ""

    @property
    def dsn(self) -> str:
        """PostgreSQL 접속 문자열.

        비밀번호에 `@`·`/` 같은 문자가 들어가면 URL이 깨지므로 인코딩한다.
        """
        if self.database_url:
            return self.database_url
        return (
            f"postgresql://{quote_plus(self.rds_user)}:{quote_plus(self.rds_password)}"
            f"@{self.rds_host}:{self.rds_port}/{self.rds_db_name}"
            f"?sslmode={self.rds_ssl_mode}"
        )

    @property
    def db_configured(self) -> bool:
        """접속 대상이 정해져 있는지. 아직 RDS 인스턴스가 없어 기본값은 False다."""
        return bool(self.database_url or self.rds_host)


settings = Settings()
