"""user/adapter/inbound/api/v1/positions_router.py — 계약 문서 3-3절.

읽기 전용 참조 데이터. 스텁의 목록이 마이그레이션 값과 같은지는
`test_sport_position_db.py` 가 실물로 대조한다.
"""

from uuid import uuid4

from app.core.security import issue_access_token
from tests.conftest import V1, error_code


def _headers():
    return {"Authorization": f"Bearer {issue_access_token(uuid4())}"}


class TestListPositions:
    def test_인증이_필요하다(self, client):
        assert client.get(f"{V1}/positions").status_code == 401

    def test_전_종목을_준다(self, client):
        rows = client.get(f"{V1}/positions", headers=_headers()).json()
        sports = {r["sport_code"] for r in rows}
        assert sports == {"football", "baseball", "basketball"}
        assert {"code", "label", "sport_code"} == set(rows[0])

    def test_종목으로_거른다(self, client):
        rows = client.get(
            f"{V1}/positions?sport_code=football", headers=_headers()
        ).json()
        assert {r["code"] for r in rows} == {"GK", "DF", "MF", "FW"}
        assert all(r["sport_code"] == "football" for r in rows)

    def test_종목_안에서만_유일한_약칭이_그대로_온다(self, client):
        """🔴 야구 `C`(포수)와 농구 `C`(센터)는 다른 것 — 둘 다 온다."""
        rows = client.get(f"{V1}/positions", headers=_headers()).json()
        cs = [(r["sport_code"], r["label"]) for r in rows if r["code"] == "C"]
        assert ("baseball", "포수") in cs
        assert ("basketball", "센터") in cs

    def test_없는_종목은_422_다(self, client):
        """빈 배열이면 오타와 "포지션이 아직 없다"가 같아 보인다."""
        res = client.get(
            f"{V1}/positions?sport_code=quidditch", headers=_headers()
        )
        assert res.status_code == 422
        assert error_code(res) == "UNKNOWN_SPORT"
