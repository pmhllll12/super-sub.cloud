"""ORM 메타데이터를 JSON 으로 뽑는다. fastapi/.venv 로 돌린다.

alembic/env.py 가 등록하는 ORM 전부를 같은 방식(모든 *_orm.py 임포트)으로 불러,
테이블마다 도메인(컨텍스트 폴더)·컬럼·키·외래키·삭제 규칙·유일 제약을 담는다.
"""

import importlib
import json
import pathlib
import sys

# 🔴 저장소 루트는 이 파일 위치에서 구한다 — 절대경로를 박지 않는다(`tools/README.md`).
ROOT = pathlib.Path(__file__).resolve().parents[2] / "fastapi"
sys.path.insert(0, str(ROOT))

from sqlalchemy import UniqueConstraint  # noqa: E402

from app.core.database import Base  # noqa: E402

owner = {}
for f in sorted((ROOT / "app").glob("*/adapter/outbound/orm/*_orm.py")):
    ctx = f.parts[len(ROOT.parts) + 1]
    mod = importlib.import_module(".".join(f.relative_to(ROOT).with_suffix("").parts))
    for obj in vars(mod).values():
        t = getattr(obj, "__tablename__", None)
        if isinstance(t, str) and getattr(obj, "__module__", "") == mod.__name__:
            owner[t] = ctx


from sqlalchemy.dialects import postgresql  # noqa: E402

_PG = postgresql.dialect()


def typename(col):
    try:
        s = col.type.compile(dialect=_PG).lower()
    except Exception:
        s = type(col.type).__name__.lower()
    s = s.replace("timestamp with time zone", "timestamptz").replace("timestamp without time zone", "timestamp")
    s = s.replace("time without time zone", "time").replace("character varying", "varchar").replace("boolean", "bool")
    s = s.replace("integer", "int").replace("double precision", "float8")
    return s


out = {}
for name, table in sorted(Base.metadata.tables.items()):
    if name not in owner:
        continue
    uniques = []
    for c in table.constraints:
        if isinstance(c, UniqueConstraint):
            uniques.append([col.name for col in c.columns])
    for c in table.columns:
        if c.unique:
            uniques.append([c.name])
    for idx in table.indexes:
        if idx.unique:
            uniques.append([col.name for col in idx.columns] + (["(부분)"] if idx.dialect_options.get("postgresql", {}).get("where") is not None else []))
    fks = []
    for fk in table.foreign_key_constraints:
        fks.append({
            "cols": [c.name for c in fk.columns],
            "target": fk.referred_table.name,
            "target_cols": [e.column.name for e in fk.elements],
            "ondelete": (fk.ondelete or "NO ACTION").upper(),
        })
    out[name] = {
        "context": owner[name],
        "columns": [
            {"name": c.name, "type": typename(c), "nullable": bool(c.nullable), "pk": bool(c.primary_key),
             "fk": [f"{fk.column.table.name}.{fk.column.name}" for fk in c.foreign_keys]}
            for c in table.columns
        ],
        "pk": [c.name for c in table.primary_key.columns],
        "uniques": uniques,
        "fks": fks,
    }

json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("tables", len(out))
