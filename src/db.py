"""일정 저장소(SQLite)의 스키마 생성과 더미 데이터 초기화를 맡습니다.

교육용 더미 데이터(data/seed.json)를 읽어 DB를 처음 상태로 만듭니다.
평가할 때는 문항마다 reset_db()를 불러 같은 상태에서 시작합니다.
나중에 사내 일정 도구로 바꿀 때는 이 파일 대신 API 연결 계층을 둡니다.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "schedule.sqlite"
DEFAULT_SEED = ROOT / "data" / "seed.json"

SCHEMA = """
CREATE TABLE people (
    id     TEXT PRIMARY KEY,
    name   TEXT NOT NULL,
    title  TEXT NOT NULL,
    role   TEXT NOT NULL CHECK (role IN ('임원', '비서', '관리자', '직원', '외부 인물')),
    org    TEXT NOT NULL,
    phone  TEXT,
    email  TEXT,
    memo   TEXT
);

-- 비서 한 명은 임원 한 명만 담당합니다. 한 임원에게는 비서가 여러 명 있을 수 있습니다.
CREATE TABLE assignments (
    secretary TEXT PRIMARY KEY REFERENCES people(id),
    executive TEXT NOT NULL REFERENCES people(id)
);

CREATE TABLE events (
    id      TEXT PRIMARY KEY,
    title   TEXT NOT NULL,
    start   TEXT NOT NULL,          -- KST, 'YYYY-MM-DDTHH:MM'
    end     TEXT NOT NULL,
    host    TEXT NOT NULL REFERENCES people(id),   -- 주최 임원
    private INTEGER NOT NULL DEFAULT 0,
    agenda  TEXT
);

-- 참석 상태: 확정 / 승인 대기 / 불참
CREATE TABLE attendees (
    event_id  TEXT NOT NULL REFERENCES events(id),
    person_id TEXT NOT NULL REFERENCES people(id),
    status    TEXT NOT NULL DEFAULT '확정' CHECK (status IN ('확정', '승인 대기', '불참')),
    PRIMARY KEY (event_id, person_id)
);

-- 승인 대기 건. kind: 참석 요청 / 시간 변경 / 변경 / 취소 / 불참
CREATE TABLE approvals (
    id           TEXT PRIMARY KEY,
    kind         TEXT NOT NULL,
    event_id     TEXT NOT NULL REFERENCES events(id),
    approver     TEXT NOT NULL REFERENCES people(id),   -- 승인할 임원
    requested_by TEXT NOT NULL REFERENCES people(id),
    change       TEXT NOT NULL DEFAULT '{}',             -- 변경 내용(JSON)
    status       TEXT NOT NULL DEFAULT '대기' CHECK (status IN ('대기', '승인', '거절'))
);

-- 직원의 바쁨. 사내 캘린더에서 시간 정보만 가져오며 내용은 다루지 않습니다.
CREATE TABLE employee_busy (
    person TEXT NOT NULL REFERENCES people(id),
    start  TEXT NOT NULL,
    end    TEXT NOT NULL
);
"""


def connect(db_path: Path | str = DEFAULT_DB) -> sqlite3.Connection:
    """일정 DB에 연결합니다. 행은 컬럼 이름으로 꺼낼 수 있게 돌려줍니다."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def load_seed(conn: sqlite3.Connection, seed: dict) -> None:
    """시드 데이터를 비어 있는 DB에 넣습니다.

    참석 요청이 승인 대기 중인 임원은 참석 상태를 '승인 대기'로 둡니다.
    승인 전에도 그 시간은 바쁨으로 막혀야 하기 때문입니다.
    """
    conn.executemany(
        "INSERT INTO people VALUES (:id, :name, :title, :role, :org, :phone, :email, :memo)",
        seed["people"],
    )
    conn.executemany(
        "INSERT INTO assignments VALUES (:secretary, :executive)",
        seed["assignments"],
    )
    for ev in seed["events"]:
        conn.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ev["id"], ev["title"], ev["start"], ev["end"], ev["host"],
             int(ev["private"]), ev.get("agenda", "")),
        )
        conn.executemany(
            "INSERT INTO attendees (event_id, person_id) VALUES (?, ?)",
            [(ev["id"], pid) for pid in ev["attendees"]],
        )
    for ap in seed["approvals"]:
        conn.execute(
            "INSERT INTO approvals (id, kind, event_id, approver, requested_by, change) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (ap["id"], ap["kind"], ap["event_id"], ap["approver"], ap["requested_by"],
             json.dumps(ap.get("change", {}), ensure_ascii=False)),
        )
        if ap["kind"] == "참석 요청":
            conn.execute(
                "UPDATE attendees SET status = '승인 대기' WHERE event_id = ? AND person_id = ?",
                (ap["event_id"], ap["approver"]),
            )
    conn.executemany(
        "INSERT INTO employee_busy VALUES (:person, :start, :end)",
        seed["employee_busy"],
    )


TABLES = ("employee_busy", "approvals", "attendees", "events", "assignments", "people")


def reset_db(db_path: Path | str = DEFAULT_DB, seed_path: Path | str = DEFAULT_SEED) -> Path:
    """테이블을 모두 지우고 시드 데이터로 처음 상태를 다시 만듭니다.

    평가 문항마다 불러서, 앞 문항의 변경이 다음 문항에 영향을 주지 않게 합니다.
    파일을 지우지 않고 테이블만 다시 만듭니다. Windows에서는 다른 연결이 열려 있으면
    파일을 지울 수 없기 때문입니다.
    """
    db_path = Path(db_path)
    seed = json.loads(Path(seed_path).read_text(encoding="utf-8"))
    conn = connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        for table in TABLES:
            conn.execute(f"DROP TABLE IF EXISTS {table}")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMA)
        load_seed(conn, seed)
        conn.commit()
    finally:
        conn.close()
    return db_path


if __name__ == "__main__":
    print(f"초기화 완료: {reset_db()}")
