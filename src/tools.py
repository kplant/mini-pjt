"""도메인 도구: 일정, 바쁨, 후보 시간, 승인, 프로필, 담당 관계를 다룹니다.

권한은 프롬프트가 아니라 이 파일의 도구가 직접 검사합니다(ADR 0003).
- 요청자는 도구 인자가 아니라 Ctx로 바깥에서 주입합니다. LLM이 요청자를 바꿀 수 없습니다.
- 권한이 없으면 예외 대신 {"denied": True, "reason": ...}를 돌려줍니다.
  Agent는 이 결과를 보고 거절 이유를 설명하고, 응답 trace의 refused가 됩니다.
- 찾는 대상이 없으면 {"not_found": True} 또는 {"no_answer": True}를 돌려줍니다.

시간은 모두 KST이며 'YYYY-MM-DDTHH:MM' 문자열로 주고받습니다.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from src.db import DEFAULT_DB, connect

# 근무 시간과 조율 기본값(CONTEXT.md의 근무 시간, SERVICE.md 3번)
WORK_START_HOUR = 9
WORK_END_HOUR = 18
LUNCH = (12, 13)
SLOT_STEP_MIN = 30
DEFAULT_DURATION_MIN = 60
MAX_CANDIDATES = 3
DEFAULT_RANGE_BUSINESS_DAYS = 5

EXTERNAL_NOTICE = "외부 참석자의 일정은 회사가 알 수 없어 따로 확인이 필요합니다."


# ---------------------------------------------------------------------------
# 요청자와 실행 맥락
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Requester:
    """요청을 보낸 사람. 역할은 사용자 목록(people)에서 정합니다."""

    id: str
    name: str
    role: str                   # 임원 / 비서 / 관리자
    executive: str | None       # 임원은 자기 id, 비서는 담당 임원 id, 관리자는 None


@dataclass(frozen=True)
class Ctx:
    """도구 실행 맥락. 요청마다 새로 만듭니다."""

    requester: Requester
    base_date: date
    db_path: Path = DEFAULT_DB

    def conn(self) -> sqlite3.Connection:
        """일정 DB 연결을 엽니다."""
        return connect(self.db_path)


def load_requester(user_id: str, db_path: Path | str = DEFAULT_DB) -> Requester | None:
    """user_id로 요청자를 찾습니다. 임원·비서·관리자가 아니면 None입니다."""
    conn = connect(db_path)
    try:
        row = conn.execute("SELECT * FROM people WHERE id = ?", (user_id,)).fetchone()
        if row is None or row["role"] not in ("임원", "비서", "관리자"):
            return None
        executive = None
        if row["role"] == "임원":
            executive = row["id"]
        elif row["role"] == "비서":
            a = conn.execute(
                "SELECT executive FROM assignments WHERE secretary = ?", (user_id,)
            ).fetchone()
            executive = a["executive"] if a else None
        return Requester(row["id"], row["name"], row["role"], executive)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 공통 도우미
# ---------------------------------------------------------------------------

def _denied(reason: str, **extra) -> dict:
    """권한 거절 결과를 만듭니다."""
    return {"denied": True, "reason": reason, **extra}


def _fmt(dt: datetime) -> str:
    """datetime을 'YYYY-MM-DDTHH:MM'으로 바꿉니다."""
    return dt.strftime("%Y-%m-%dT%H:%M")


def _parse_dt(text: str) -> datetime:
    """'YYYY-MM-DDTHH:MM' 또는 'YYYY-MM-DD HH:MM'을 datetime으로 바꿉니다."""
    return datetime.fromisoformat(text.strip().replace(" ", "T"))


def _parse_range(date_from: str, date_to: str | None) -> tuple[datetime, datetime]:
    """조회 범위를 [시작, 끝)으로 바꿉니다. 날짜만 주면 그날 하루 전체입니다."""
    def start_of(text: str) -> datetime:
        return _parse_dt(text) if "T" in text or " " in text.strip() else datetime.fromisoformat(text.strip())

    def end_of(text: str) -> datetime:
        if "T" in text or " " in text.strip():
            return _parse_dt(text)
        return datetime.fromisoformat(text.strip()) + timedelta(days=1)

    return start_of(date_from), end_of(date_to or date_from)


def _label(row: sqlite3.Row) -> str:
    """사람을 '성명 직책'으로 부릅니다(예: 강민준 부사장)."""
    return f"{row['name']} {row['title']}"


def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    """두 시간 구간이 겹치는지 봅니다. 끝과 시작이 맞닿는 것은 겹침이 아닙니다."""
    return a_start < b_end and b_start < a_end


def resolve_person(conn: sqlite3.Connection, text: str) -> list[sqlite3.Row]:
    """'강민준 부사장님', '강민준', 'exec-kang' 같은 표현으로 사람을 찾습니다.

    성명 전체가 들어 있어야 찾습니다. 성+직책(예: 강 부사장)으로는 찾지 않습니다.
    """
    text = (text or "").strip().replace("님", "")
    row = conn.execute("SELECT * FROM people WHERE id = ?", (text,)).fetchone()
    if row:
        return [row]
    return [p for p in conn.execute("SELECT * FROM people") if p["name"] in text]


def _one_person(conn: sqlite3.Connection, text: str) -> sqlite3.Row | dict:
    """사람 한 명을 찾고, 없거나 여러 명이면 그 사실을 돌려줍니다."""
    found = resolve_person(conn, text)
    if not found:
        return {"not_found": True, "no_answer": True, "reason": f"'{text}'에 해당하는 사람을 찾을 수 없습니다."}
    if len(found) > 1:
        return {"ambiguous": True, "reason": f"'{text}'에 해당하는 사람이 여러 명입니다.",
                "matches": [_label(p) for p in found]}
    return found[0]


def _active_attendees(conn: sqlite3.Connection, event_id: str) -> list[sqlite3.Row]:
    """불참이 아닌 참석자를 사람 정보와 함께 돌려줍니다."""
    return conn.execute(
        "SELECT p.*, a.status FROM attendees a JOIN people p ON p.id = a.person_id "
        "WHERE a.event_id = ? AND a.status != '불참'",
        (event_id,),
    ).fetchall()


def _can_act_for(req: Requester, executive_id: str) -> bool:
    """요청자가 그 임원의 일정을 다룰 수 있는지 봅니다(본인 또는 담당 비서)."""
    return req.role in ("임원", "비서") and req.executive == executive_id


def _can_view(conn: sqlite3.Connection, req: Requester, ev: sqlite3.Row) -> bool:
    """요청자가 일정 내용을 볼 수 있는지 봅니다.

    비공개 일정은 주최 임원 본인만, 그 밖의 일정은 참석 임원 본인과 담당 비서만 봅니다.
    """
    if req.role not in ("임원", "비서"):
        return False
    if ev["private"]:
        return req.role == "임원" and req.id == ev["host"]
    exec_ids = {p["id"] for p in _active_attendees(conn, ev["id"]) if p["role"] == "임원"}
    return req.executive in exec_ids


def _busy_blocks(conn: sqlite3.Connection, person_id: str) -> list[tuple[datetime, datetime, str | None]]:
    """사람의 바쁨 구간. 승인 대기 일정도 바쁨으로 막습니다. (시작, 끝, 일정 id)"""
    rows = conn.execute(
        "SELECT e.id, e.start, e.end FROM events e JOIN attendees a ON a.event_id = e.id "
        "WHERE a.person_id = ? AND a.status != '불참'",
        (person_id,),
    ).fetchall()
    blocks = [(_parse_dt(r["start"]), _parse_dt(r["end"]), r["id"]) for r in rows]
    for r in conn.execute("SELECT start, end FROM employee_busy WHERE person = ?", (person_id,)):
        blocks.append((_parse_dt(r["start"]), _parse_dt(r["end"]), None))
    return blocks


def _event_view(conn: sqlite3.Connection, req: Requester, ev: sqlite3.Row) -> dict:
    """요청자 권한에 맞춰 일정을 보여 줍니다. 볼 수 없으면 바쁨으로만 보입니다."""
    if not _can_view(conn, req, ev):
        return {"start": ev["start"], "end": ev["end"], "status": "바쁨"}
    host = conn.execute("SELECT * FROM people WHERE id = ?", (ev["host"],)).fetchone()
    return {
        "event_id": ev["id"],
        "title": ev["title"],
        "start": ev["start"],
        "end": ev["end"],
        "host": _label(host),
        "attendees": [f"{_label(p)}({p['status']})" for p in _active_attendees(conn, ev["id"])],
        "agenda": ev["agenda"] or "",
        "private": bool(ev["private"]),
    }


def _new_id(prefix: str) -> str:
    """새 행의 id를 만듭니다."""
    return f"{prefix}-{uuid.uuid4().hex[:6]}"


def _add_approval(conn, kind: str, event_id: str, approver: str, requested_by: str,
                  change: dict | None = None) -> str:
    """승인 대기 건을 만듭니다(ADR 0002)."""
    ap_id = _new_id("ap")
    conn.execute(
        "INSERT INTO approvals (id, kind, event_id, approver, requested_by, change) VALUES (?, ?, ?, ?, ?, ?)",
        (ap_id, kind, event_id, approver, requested_by, json.dumps(change or {}, ensure_ascii=False)),
    )
    return ap_id


def _get_event(conn: sqlite3.Connection, event_id: str) -> sqlite3.Row | None:
    """일정 하나를 찾습니다."""
    return conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()


def _not_host_reason(conn, req: Requester, ev: sqlite3.Row) -> dict:
    """주최 임원 쪽이 아닐 때의 거절 결과. 참석 중이면 불참을 안내합니다."""
    attending = req.executive in {p["id"] for p in _active_attendees(conn, ev["id"])}
    if attending and not ev["private"]:
        return _denied("일정의 시간 변경과 취소는 주최 임원 쪽만 할 수 있습니다. 대신 불참으로 처리할 수 있습니다.",
                       suggestion="불참")
    return _denied("이 일정을 바꿀 권한이 없습니다.")


# ---------------------------------------------------------------------------
# 조회: 일정, 바쁨
# ---------------------------------------------------------------------------

def list_events(ctx: Ctx, executive: str, date_from: str, date_to: str | None = None) -> dict:
    """임원 한 명의 기간 내 일정을 권한에 맞춰 돌려줍니다(브리핑·조회)."""
    req = ctx.requester
    if req.role == "관리자":
        return _denied("관리자는 일정을 볼 수 없습니다.")
    conn = ctx.conn()
    try:
        person = _one_person(conn, executive)
        if isinstance(person, dict):
            return person
        if person["role"] != "임원":
            return _denied("일정은 임원 기준으로만 조회할 수 있습니다.")
        start, end = _parse_range(date_from, date_to)
        rows = [
            ev for ev in conn.execute(
                "SELECT e.* FROM events e JOIN attendees a ON a.event_id = e.id "
                "WHERE a.person_id = ? AND a.status != '불참' ORDER BY e.start",
                (person["id"],),
            )
            if _overlaps(_parse_dt(ev["start"]), _parse_dt(ev["end"]), start, end)
        ]
        items = [_event_view(conn, req, ev) for ev in rows]
        if not _can_act_for(req, person["id"]):
            return _denied(f"{_label(person)}의 일정 내용은 담당 비서와 본인만 볼 수 있습니다. 바쁨만 안내합니다.",
                           busy=[{"start": i["start"], "end": i["end"]} for i in items])
        if items and all(i.get("status") == "바쁨" for i in items):
            return _denied("비공개 일정이라 내용은 볼 수 없습니다. 바쁨만 안내합니다.",
                           busy=[{"start": i["start"], "end": i["end"]} for i in items])
        return {"executive": _label(person), "range": [_fmt(start), _fmt(end)], "events": items}
    finally:
        conn.close()


def get_event_at(ctx: Ctx, executive: str, at: str) -> dict:
    """특정 시각에 임원이 참석하는 일정의 내용을 돌려줍니다. 볼 수 없으면 바쁨만 안내합니다."""
    at_dt = _parse_dt(at)
    result = list_events(ctx, executive, _fmt(at_dt), _fmt(at_dt + timedelta(minutes=1)))
    if result.get("denied") or result.get("not_found") or result.get("ambiguous"):
        return result
    if not result["events"]:
        return {"no_event": True, "reason": f"{at}에 일정이 없습니다."}
    return result


def get_busy(ctx: Ctx, people: list[str], date_from: str, date_to: str | None = None) -> dict:
    """여러 사람의 바쁨(내용 없이 시간만)을 돌려줍니다. 외부 인물은 바쁨이 없습니다."""
    if ctx.requester.role == "관리자":
        return _denied("관리자는 일정 업무를 할 수 없습니다.")
    conn = ctx.conn()
    try:
        start, end = _parse_range(date_from, date_to)
        out, external = {}, []
        for name in people:
            person = _one_person(conn, name)
            if isinstance(person, dict):
                return person
            if person["role"] == "외부 인물":
                external.append(_label(person))
                continue
            out[_label(person)] = [
                {"start": _fmt(s), "end": _fmt(e)}
                for s, e, _ in sorted(_busy_blocks(conn, person["id"]))
                if _overlaps(s, e, start, end)
            ]
        result = {"busy": out}
        if external:
            result["external_attendees"] = external
            result["notice"] = EXTERNAL_NOTICE
        return result
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 조율: 후보 시간, 등록
# ---------------------------------------------------------------------------

def _business_days_after(base: date, count: int) -> tuple[date, date]:
    """기준일 다음 날부터 영업일 count일의 [첫날, 마지막 날]."""
    days, d = [], base
    while len(days) < count:
        d += timedelta(days=1)
        if d.weekday() < 5:
            days.append(d)
    return days[0], days[-1]


def find_candidates(ctx: Ctx, attendees: list[str], duration_min: int = DEFAULT_DURATION_MIN,
                    date_from: str | None = None, date_to: str | None = None) -> dict:
    """참석자 모두가 비어 있는 후보 시간을 최대 3개 찾습니다.

    근무 시간(평일 09~18시, 점심 12~13시 제외) 안에서 30분 단위로 찾고,
    가능하면 서로 다른 날로 나눠 제안합니다.
    """
    if ctx.requester.role == "관리자":
        return _denied("관리자는 일정 업무를 할 수 없습니다.")
    if date_from is None:
        first, last = _business_days_after(ctx.base_date, DEFAULT_RANGE_BUSINESS_DAYS)
    else:
        first = date.fromisoformat(date_from[:10])
        last = date.fromisoformat((date_to or date_from)[:10])
    conn = ctx.conn()
    try:
        blocks, external, names = [], [], []
        for name in attendees:
            person = _one_person(conn, name)
            if isinstance(person, dict):
                return person
            names.append(_label(person))
            if person["role"] == "외부 인물":
                external.append(_label(person))
            else:
                blocks += [(s, e) for s, e, _ in _busy_blocks(conn, person["id"])]
    finally:
        conn.close()

    length = timedelta(minutes=duration_min)
    slots_by_day: dict[date, list[datetime]] = {}
    d = first
    while d <= last:
        if d.weekday() < 5:
            t = datetime(d.year, d.month, d.day, WORK_START_HOUR)
            day_end = datetime(d.year, d.month, d.day, WORK_END_HOUR)
            lunch = (datetime(d.year, d.month, d.day, LUNCH[0]), datetime(d.year, d.month, d.day, LUNCH[1]))
            while t + length <= day_end:
                if not _overlaps(t, t + length, *lunch) and all(
                    not _overlaps(t, t + length, s, e) for s, e in blocks
                ):
                    slots_by_day.setdefault(d, []).append(t)
                t += timedelta(minutes=SLOT_STEP_MIN)
        d += timedelta(days=1)

    # 날마다 첫 빈 시간을 먼저 고르고, 모자라면 이른 시간부터 채웁니다.
    picked = [slots[0] for slots in slots_by_day.values()][:MAX_CANDIDATES]
    for slots in slots_by_day.values():
        for t in slots[1:]:
            if len(picked) >= MAX_CANDIDATES:
                break
            picked.append(t)
    picked.sort()

    result = {
        "attendees": names,
        "duration_min": duration_min,
        "range": [first.isoformat(), last.isoformat()],
        "candidates": [{"no": i + 1, "start": _fmt(t), "end": _fmt(t + length)} for i, t in enumerate(picked)],
    }
    if external:
        result["external_attendees"] = external
        result["notice"] = EXTERNAL_NOTICE
    if not picked:
        result["no_answer"] = True
        result["reason"] = "근무 시간 안에 참석자 모두가 비어 있는 시간이 없습니다."
    return result


def register_event(ctx: Ctx, title: str, start: str, end: str, attendees: list[str],
                   private: bool = False, agenda: str = "") -> dict:
    """일정을 등록합니다. 주최 임원은 요청자 본인 또는 담당 임원입니다.

    주최 임원의 캘린더에는 바로 등록하고, 다른 임원에게는 참석 요청(승인 대기)으로 넣습니다.
    """
    req = ctx.requester
    if req.role not in ("임원", "비서") or req.executive is None:
        return _denied("일정은 임원과 담당 비서만 등록할 수 있습니다.")
    start_dt, end_dt = _parse_dt(start), _parse_dt(end)
    if end_dt <= start_dt:
        return {"error": "끝나는 시간이 시작 시간보다 늦어야 합니다."}
    conn = ctx.conn()
    try:
        people = {req.executive: conn.execute("SELECT * FROM people WHERE id = ?", (req.executive,)).fetchone()}
        for name in attendees:
            person = _one_person(conn, name)
            if isinstance(person, dict):
                return person
            people[person["id"]] = person
        execs = [p for p in people.values() if p["role"] == "임원"]
        if private and not (req.role == "임원" and len(execs) == 1):
            return _denied("비공개 일정은 임원 본인이, 참석 임원이 한 명일 때만 만들 수 있습니다.")

        conflicts = [
            _label(p) for p in people.values() if p["role"] in ("임원", "직원")
            and any(_overlaps(start_dt, end_dt, s, e) for s, e, _ in _busy_blocks(conn, p["id"]))
        ]
        if conflicts:
            return {"conflict": True, "reason": "이미 바쁜 참석자가 있어 등록하지 않았습니다.",
                    "busy_attendees": conflicts}

        ev_id = _new_id("ev")
        conn.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ev_id, title, _fmt(start_dt), _fmt(end_dt), req.executive, int(private), agenda),
        )
        pending = []
        for pid, p in people.items():
            status = "확정"
            if p["role"] == "임원" and pid != req.executive:
                status = "승인 대기"
                _add_approval(conn, "참석 요청", ev_id, pid, req.id)
                pending.append(pid)
            conn.execute("INSERT INTO attendees VALUES (?, ?, ?)", (ev_id, pid, status))
        conn.commit()
        external = [_label(p) for p in people.values() if p["role"] == "외부 인물"]
        result = {
            "event_id": ev_id, "title": title, "start": _fmt(start_dt), "end": _fmt(end_dt),
            "registered_for": [req.executive], "pending_approval_for": pending,
        }
        if external:
            result["external_attendees"] = external
            result["notice"] = EXTERNAL_NOTICE
        return result
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 변경: 시간 변경, 취소, 불참
# ---------------------------------------------------------------------------

def _apply_time_change(conn, ev: sqlite3.Row, start: str, end: str, requested_by: str) -> list[str]:
    """주최 쪽의 시간 변경을 반영합니다. 다른 참석 임원에게는 승인 대기로 다시 들어갑니다."""
    conn.execute("UPDATE events SET start = ?, end = ? WHERE id = ?", (start, end, ev["id"]))
    pending = []
    for p in _active_attendees(conn, ev["id"]):
        if p["role"] == "임원" and p["id"] != ev["host"]:
            conn.execute(
                "UPDATE attendees SET status = '승인 대기' WHERE event_id = ? AND person_id = ?",
                (ev["id"], p["id"]),
            )
            _add_approval(conn, "시간 변경", ev["id"], p["id"], requested_by, {"start": start, "end": end})
            pending.append(p["id"])
    return pending


def _delete_event(conn, event_id: str) -> None:
    """일정과 딸린 참석·승인 정보를 지웁니다."""
    conn.execute("DELETE FROM approvals WHERE event_id = ?", (event_id,))
    conn.execute("DELETE FROM attendees WHERE event_id = ?", (event_id,))
    conn.execute("DELETE FROM events WHERE id = ?", (event_id,))


def update_event(ctx: Ctx, event_id: str, new_start: str, new_end: str | None = None) -> dict:
    """일정 시간을 바꿉니다. 주최 임원 쪽만 할 수 있습니다.

    임원 본인이 바꾸면 바로 반영하고, 비서가 바꾸면 담당 임원의 승인을 기다립니다.
    new_end를 비우면 원래 일정 길이를 그대로 둡니다.
    """
    req = ctx.requester
    if req.role not in ("임원", "비서"):
        return _denied("일정은 임원과 담당 비서만 바꿀 수 있습니다.")
    conn = ctx.conn()
    try:
        ev = _get_event(conn, event_id)
        if ev is None:
            return {"not_found": True, "reason": f"일정 {event_id}을(를) 찾을 수 없습니다."}
        start_dt = _parse_dt(new_start)
        if new_end:
            end_dt = _parse_dt(new_end)
        else:
            end_dt = start_dt + (_parse_dt(ev["end"]) - _parse_dt(ev["start"]))
        if end_dt <= start_dt:
            return {"error": "끝나는 시간이 시작 시간보다 늦어야 합니다."}
        if not _can_act_for(req, ev["host"]):
            return _not_host_reason(conn, req, ev)
        clash = [s for s, e, eid in _busy_blocks(conn, ev["host"])
                 if eid != ev["id"] and _overlaps(start_dt, end_dt, s, e)]
        if clash:
            return {"conflict": True, "reason": "주최 임원이 그 시간에 바쁩니다."}
        if req.role == "비서":
            _add_approval(conn, "변경", ev["id"], ev["host"], req.id,
                          {"start": _fmt(start_dt), "end": _fmt(end_dt)})
            conn.commit()
            return {"event_id": ev["id"], "title": ev["title"], "applied": False,
                    "pending_approval_for": [ev["host"]],
                    "reason": "비서의 변경은 담당 임원이 승인해야 확정됩니다."}
        pending = _apply_time_change(conn, ev, _fmt(start_dt), _fmt(end_dt), req.id)
        conn.commit()
        return {"event_id": ev["id"], "title": ev["title"], "applied": True,
                "start": _fmt(start_dt), "end": _fmt(end_dt), "pending_approval_for": pending}
    finally:
        conn.close()


def cancel_event(ctx: Ctx, event_id: str) -> dict:
    """일정을 취소합니다. 주최 임원 쪽만 할 수 있고, 비서의 취소는 승인이 필요합니다."""
    req = ctx.requester
    if req.role not in ("임원", "비서"):
        return _denied("일정은 임원과 담당 비서만 취소할 수 있습니다.")
    conn = ctx.conn()
    try:
        ev = _get_event(conn, event_id)
        if ev is None:
            return {"not_found": True, "reason": f"일정 {event_id}을(를) 찾을 수 없습니다."}
        if not _can_act_for(req, ev["host"]):
            return _not_host_reason(conn, req, ev)
        if req.role == "비서":
            _add_approval(conn, "취소", ev["id"], ev["host"], req.id)
            conn.commit()
            return {"event_id": ev["id"], "title": ev["title"], "applied": False,
                    "pending_approval_for": [ev["host"]],
                    "reason": "비서의 취소는 담당 임원이 승인해야 확정됩니다."}
        _delete_event(conn, ev["id"])
        conn.commit()
        return {"event_id": ev["id"], "title": ev["title"], "applied": True, "pending_approval_for": []}
    finally:
        conn.close()


def mark_absent(ctx: Ctx, event_id: str) -> dict:
    """요청자 쪽 임원을 일정에서 불참 처리합니다. 주최 임원은 불참할 수 없습니다."""
    req = ctx.requester
    if req.role not in ("임원", "비서") or req.executive is None:
        return _denied("불참은 임원과 담당 비서만 처리할 수 있습니다.")
    conn = ctx.conn()
    try:
        ev = _get_event(conn, event_id)
        if ev is None:
            return {"not_found": True, "reason": f"일정 {event_id}을(를) 찾을 수 없습니다."}
        if req.executive not in {p["id"] for p in _active_attendees(conn, ev["id"])}:
            return _denied("담당 임원이 참석하는 일정이 아닙니다.")
        if req.executive == ev["host"]:
            return _denied("주최 임원은 불참할 수 없습니다. 일정을 취소해야 합니다.", suggestion="취소")
        if req.role == "비서":
            _add_approval(conn, "불참", ev["id"], req.executive, req.id)
            conn.commit()
            return {"event_id": ev["id"], "title": ev["title"], "applied": False,
                    "pending_approval_for": [req.executive],
                    "reason": "비서의 불참 처리는 담당 임원이 승인해야 확정됩니다."}
        conn.execute("UPDATE attendees SET status = '불참' WHERE event_id = ? AND person_id = ?",
                     (ev["id"], req.executive))
        conn.commit()
        return {"event_id": ev["id"], "title": ev["title"], "applied": True, "pending_approval_for": []}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 승인
# ---------------------------------------------------------------------------

# 비서가 대신 승인할 수 있는 종류. 다른 임원 쪽에서 들어온 요청뿐입니다.
SECRETARY_DECIDABLE = ("참석 요청", "시간 변경")


def list_pending_approvals(ctx: Ctx) -> dict:
    """요청자 쪽 임원에게 들어온 승인 대기 목록을 돌려줍니다."""
    req = ctx.requester
    if req.role not in ("임원", "비서") or req.executive is None:
        return _denied("승인 대기 목록은 임원과 담당 비서만 볼 수 있습니다.")
    conn = ctx.conn()
    try:
        rows = conn.execute(
            "SELECT ap.*, e.title, e.start, e.end, p.name, p.title AS ptitle "
            "FROM approvals ap JOIN events e ON e.id = ap.event_id JOIN people p ON p.id = ap.requested_by "
            "WHERE ap.approver = ? AND ap.status = '대기' ORDER BY e.start",
            (req.executive,),
        ).fetchall()
        items = [{
            "approval_id": r["id"], "kind": r["kind"], "event_id": r["event_id"],
            "event_title": r["title"], "start": r["start"], "end": r["end"],
            "requested_by": f"{r['name']} {r['ptitle']}", "change": json.loads(r["change"]),
            "can_decide": req.role == "임원" or r["kind"] in SECRETARY_DECIDABLE,
        } for r in rows]
        return {"pending": items}
    finally:
        conn.close()


def decide_approval(ctx: Ctx, approval_id: str, approve: bool) -> dict:
    """승인 대기 건을 승인하거나 거절합니다.

    - 참석 요청·시간 변경: 승인하면 참석 확정, 거절하면 그 임원만 불참
    - 변경: 승인하면 시간 변경 반영, 거절하면 그대로
    - 취소: 승인하면 일정 삭제, 거절하면 그대로
    - 불참: 승인하면 불참, 거절하면 그대로
    비서 자신의 변경·취소·불참은 담당 임원 본인만 승인할 수 있습니다.
    """
    req = ctx.requester
    if req.role not in ("임원", "비서") or req.executive is None:
        return _denied("승인은 임원과 담당 비서만 할 수 있습니다.")
    conn = ctx.conn()
    try:
        ap = conn.execute("SELECT * FROM approvals WHERE id = ? AND status = '대기'", (approval_id,)).fetchone()
        if ap is None:
            return {"not_found": True, "reason": f"승인 대기 건 {approval_id}을(를) 찾을 수 없습니다."}
        if ap["approver"] != req.executive:
            return _denied("요청자 쪽 임원에게 들어온 승인 건이 아닙니다.")
        if req.role == "비서" and ap["kind"] not in SECRETARY_DECIDABLE:
            return _denied("비서의 변경·취소·불참 처리는 담당 임원 본인만 승인할 수 있습니다.")
        ev = _get_event(conn, ap["event_id"])
        kind, who = ap["kind"], ap["approver"]
        if kind in ("참석 요청", "시간 변경"):
            status = "확정" if approve else "불참"
            conn.execute("UPDATE attendees SET status = ? WHERE event_id = ? AND person_id = ?",
                         (status, ev["id"], who))
        elif approve and kind == "변경":
            change = json.loads(ap["change"])
            _apply_time_change(conn, ev, change["start"], change["end"], ap["requested_by"])
        elif approve and kind == "불참":
            conn.execute("UPDATE attendees SET status = '불참' WHERE event_id = ? AND person_id = ?",
                         (ev["id"], who))
        conn.execute("UPDATE approvals SET status = ? WHERE id = ?", ("승인" if approve else "거절", ap["id"]))
        if approve and kind == "취소":
            _delete_event(conn, ev["id"])
        conn.commit()
        return {"approval_id": ap["id"], "kind": kind, "event_title": ev["title"], "approved": approve}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 프로필
# ---------------------------------------------------------------------------

def get_profile(ctx: Ctx, name: str) -> dict:
    """참석자 한 명의 프로필을 돌려줍니다. 연락처는 가리지 않습니다(ADR 0004)."""
    if ctx.requester.role not in ("임원", "비서"):
        return _denied("프로필은 임원과 비서만 볼 수 있습니다.")
    conn = ctx.conn()
    try:
        person = _one_person(conn, name)
        if isinstance(person, dict):
            return person
        return {k: person[k] for k in ("id", "name", "title", "role", "org", "phone", "email", "memo")}
    finally:
        conn.close()


def register_external_profile(ctx: Ctx, name: str, title: str, org: str,
                              phone: str = "", email: str = "", memo: str = "") -> dict:
    """외부 인물의 프로필을 등록합니다. 같은 성명·소속이 있으면 기존 프로필을 돌려줍니다."""
    if ctx.requester.role not in ("임원", "비서"):
        return _denied("외부 인물은 임원과 비서만 등록할 수 있습니다.")
    conn = ctx.conn()
    try:
        row = conn.execute("SELECT * FROM people WHERE name = ? AND org = ?", (name, org)).fetchone()
        if row:
            return {"already_exists": True, "id": row["id"], "name": row["name"], "org": row["org"]}
        pid = _new_id("ext")
        conn.execute("INSERT INTO people VALUES (?, ?, ?, '외부 인물', ?, ?, ?, ?)",
                     (pid, name, title, org, phone, email, memo))
        conn.commit()
        return {"created": True, "id": pid, "name": name, "title": title, "org": org}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 담당 관계 (관리자 전용)
# ---------------------------------------------------------------------------

def list_assignments(ctx: Ctx) -> dict:
    """비서와 담당 임원 목록을 돌려줍니다."""
    if ctx.requester.role != "관리자":
        return _denied("담당 관계는 관리자만 관리합니다.")
    conn = ctx.conn()
    try:
        rows = conn.execute(
            "SELECT s.name AS sn, s.title AS st, e.name AS en, e.title AS et FROM assignments a "
            "JOIN people s ON s.id = a.secretary JOIN people e ON e.id = a.executive ORDER BY e.name"
        ).fetchall()
        return {"assignments": [{"secretary": f"{r['sn']} {r['st']}", "executive": f"{r['en']} {r['et']}"}
                                for r in rows]}
    finally:
        conn.close()


def set_assignment(ctx: Ctx, secretary: str, executive: str) -> dict:
    """비서의 담당 임원을 바꿉니다."""
    if ctx.requester.role != "관리자":
        return _denied("담당 관계는 관리자만 관리합니다.")
    conn = ctx.conn()
    try:
        sec, exe = _one_person(conn, secretary), _one_person(conn, executive)
        for p in (sec, exe):
            if isinstance(p, dict):
                return p
        if sec["role"] != "비서" or exe["role"] != "임원":
            return {"error": "비서와 임원을 지정해야 합니다."}
        conn.execute(
            "INSERT INTO assignments VALUES (?, ?) ON CONFLICT(secretary) DO UPDATE SET executive = excluded.executive",
            (sec["id"], exe["id"]),
        )
        conn.commit()
        return {"secretary": _label(sec), "executive": _label(exe), "updated": True}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# LangChain 도구 묶음
# ---------------------------------------------------------------------------

def build_tools(ctx: Ctx) -> dict[str, list]:
    """하위 Agent별 도구 묶음을 만듭니다. 요청자는 ctx로 고정되어 LLM이 바꿀 수 없습니다.

    반환: {"조율": [...], "일정": [...], "관리": [...]}
    결과는 JSON 문자열이며, 응답 trace는 이 결과의 denied·candidates·pending_approval_for를 읽습니다.
    """
    from langchain_core.tools import tool

    def out(result: dict) -> str:
        return json.dumps(result, ensure_ascii=False)

    @tool
    def tool_find_candidates(attendees: list[str], duration_min: int = DEFAULT_DURATION_MIN,
                             date_from: str | None = None, date_to: str | None = None) -> str:
        """참석자 모두가 비어 있는 후보 시간을 최대 3개 찾습니다.
        attendees는 성명 전체(예: '강민준 부사장'). 날짜는 'YYYY-MM-DD'. 날짜를 비우면 기준일 다음 날부터 5영업일."""
        return out(find_candidates(ctx, attendees, duration_min, date_from, date_to))

    @tool
    def tool_get_busy(people: list[str], date_from: str, date_to: str | None = None) -> str:
        """여러 사람의 바쁨(내용 없이 시간만)을 조회합니다. '비어 있어?' 같은 질문에 씁니다."""
        return out(get_busy(ctx, people, date_from, date_to))

    @tool
    def tool_register_event(title: str, start: str, end: str, attendees: list[str],
                            private: bool = False, agenda: str = "") -> str:
        """일정을 등록합니다. start/end는 'YYYY-MM-DDTHH:MM'. 다른 임원은 참석 요청(승인 대기)으로 들어갑니다."""
        return out(register_event(ctx, title, start, end, attendees, private, agenda))

    @tool
    def tool_list_events(executive: str, date_from: str, date_to: str | None = None) -> str:
        """임원 한 명의 기간 내 일정을 조회합니다(브리핑). 볼 수 없는 일정은 바쁨으로만 나옵니다."""
        return out(list_events(ctx, executive, date_from, date_to))

    @tool
    def tool_get_event_at(executive: str, at: str) -> str:
        """특정 시각('YYYY-MM-DDTHH:MM')에 임원이 참석하는 일정의 내용을 조회합니다."""
        return out(get_event_at(ctx, executive, at))

    @tool
    def tool_update_event(event_id: str, new_start: str, new_end: str | None = None) -> str:
        """일정 시간을 바꿉니다. 주최 임원 쪽만 가능하며, 비서의 변경은 승인 대기가 됩니다.
        new_start/new_end는 'YYYY-MM-DDTHH:MM'. 끝 시각을 말하지 않았으면 new_end를 비워 원래 길이를 유지합니다."""
        return out(update_event(ctx, event_id, new_start, new_end))

    @tool
    def tool_cancel_event(event_id: str) -> str:
        """일정을 취소합니다. 주최 임원 쪽만 가능하며, 비서의 취소는 승인 대기가 됩니다."""
        return out(cancel_event(ctx, event_id))

    @tool
    def tool_mark_absent(event_id: str) -> str:
        """요청자 쪽 임원을 일정에서 불참 처리합니다. 비서의 불참 처리는 승인 대기가 됩니다."""
        return out(mark_absent(ctx, event_id))

    @tool
    def tool_list_pending_approvals() -> str:
        """요청자 쪽 임원에게 들어온 승인 대기 목록을 조회합니다."""
        return out(list_pending_approvals(ctx))

    @tool
    def tool_decide_approval(approval_id: str, approve: bool) -> str:
        """승인 대기 건을 승인(approve=true)하거나 거절(approve=false)합니다."""
        return out(decide_approval(ctx, approval_id, approve))

    @tool
    def tool_get_profile(name: str) -> str:
        """참석자의 프로필(소속, 직책, 연락처, 메모)을 조회합니다. 성명 전체로 찾습니다."""
        return out(get_profile(ctx, name))

    @tool
    def tool_register_external_profile(name: str, title: str, org: str,
                                       phone: str = "", email: str = "", memo: str = "") -> str:
        """외부 인물의 프로필을 등록합니다. name은 성명 전체입니다."""
        return out(register_external_profile(ctx, name, title, org, phone, email, memo))

    @tool
    def tool_list_assignments() -> str:
        """비서와 담당 임원 목록을 조회합니다(관리자 전용)."""
        return out(list_assignments(ctx))

    @tool
    def tool_set_assignment(secretary: str, executive: str) -> str:
        """비서의 담당 임원을 바꿉니다(관리자 전용)."""
        return out(set_assignment(ctx, secretary, executive))

    return {
        "조율": [tool_find_candidates, tool_get_busy, tool_register_event],
        "일정": [tool_list_events, tool_get_event_at, tool_update_event, tool_cancel_event,
                 tool_mark_absent, tool_list_pending_approvals, tool_decide_approval,
                 tool_get_profile, tool_register_external_profile],
        "관리": [tool_list_assignments, tool_set_assignment],
    }
