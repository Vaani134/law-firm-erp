"""
Tests for the Matter Search endpoint.

GET /api/matters
"""

from __future__ import annotations

import uuid

import pytest
from fastapi import status

from app.models.matter import Matter


def _mk_key(prefix: str = "SRCH") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _seed_matter(
    db,
    matter_key: str | None = None,
    client_id: str = "SRCH",
    client_name: str = "Search Client LLC",
    matter_name: str = "Search Matter",
    practice_area: str | None = "Litigation",
    matter_type: str = "General",
    matter_status: str = "open",
    primary_attorney: str | None = "Test Attorney",
):
    if matter_key is None:
        matter_key = _mk_key()
    existing = db.query(Matter).filter(Matter.matter_key == matter_key).first()
    if existing:
        return existing
    m = Matter(
        matter_key=matter_key,
        client_id=client_id,
        matter_id="001",
        client_name=client_name,
        matter_name=matter_name,
        matter_description="Search test matter",
        practice_area=practice_area,
        matter_type=matter_type,
        matter_status=matter_status,
        primary_attorney=primary_attorney,
    )
    db.add(m)
    db.flush()
    return m


# ---------------------------------------------------------------------------
# 1. GET /api/matters with no parameters
# ---------------------------------------------------------------------------
class TestNoParameters:
    def test_returns_200(self, client, db_session):
        resp = client.get("/api/matters")
        assert resp.status_code == status.HTTP_200_OK

    def test_response_structure(self, client, db_session):
        _seed_matter(db_session)
        db_session.commit()

        resp = client.get("/api/matters")
        body = resp.json()
        assert "total" in body
        assert "limit" in body
        assert "offset" in body
        assert "matters" in body
        assert isinstance(body["matters"], list)
        assert body["limit"] == 20
        assert body["offset"] == 0

    def test_pagination_fields_present(self, client, db_session):
        _seed_matter(db_session)
        db_session.commit()

        resp = client.get("/api/matters")
        body = resp.json()
        assert body["total"] >= 1
        assert body["limit"] == 20
        assert body["offset"] == 0


# ---------------------------------------------------------------------------
# 2. Search by matter_key
# ---------------------------------------------------------------------------
class TestSearchByMatterKey:
    def test_finds_match(self, client, db_session):
        unique = _mk_key("KEYSRCH")
        _seed_matter(db_session, matter_key=unique, client_name="Other Client 1")
        _seed_matter(db_session, client_name="Other Client 2")
        db_session.commit()

        resp = client.get(f"/api/matters?q={unique}")
        body = resp.json()
        keys = [m["matter_key"] for m in body["matters"]]
        assert unique in keys
        assert body["total"] >= 1

    def test_non_matching_query_returns_empty(self, client, db_session):
        _seed_matter(db_session, client_name="Some Client")
        db_session.commit()

        resp = client.get("/api/matters?q=zzzz-no-match-zzzz")
        body = resp.json()
        assert body["total"] == 0
        assert body["matters"] == []


# ---------------------------------------------------------------------------
# 3. Search by client_name
# ---------------------------------------------------------------------------
class TestSearchByClientName:
    def test_finds_match(self, client, db_session):
        unique_client = f"UniqueClientName-{uuid.uuid4().hex[:6]}"
        _seed_matter(db_session, client_name=unique_client, matter_name="Some Matter A")
        _seed_matter(db_session, client_name="Other Client Inc", matter_name="Some Matter B")
        db_session.commit()

        resp = client.get(f"/api/matters?q={unique_client}")
        body = resp.json()
        clients = [m["client_name"] for m in body["matters"]]
        assert any(c == unique_client for c in clients)


# ---------------------------------------------------------------------------
# 4. Search by matter_name
# ---------------------------------------------------------------------------
class TestSearchByMatterName:
    def test_finds_match(self, client, db_session):
        unique_matter = f"UniqueMatterName-{uuid.uuid4().hex[:6]}"
        _seed_matter(db_session, matter_name=unique_matter)
        _seed_matter(db_session, matter_name="Other Matter")
        db_session.commit()

        resp = client.get(f"/api/matters?q={unique_matter}")
        body = resp.json()
        names = [m["matter_name"] for m in body["matters"]]
        assert any(n == unique_matter for n in names)


# ---------------------------------------------------------------------------
# 5. Case-insensitive search
# ---------------------------------------------------------------------------
class TestCaseInsensitive:
    def test_uppercase_query_finds_lowercase_data(self, client, db_session):
        unique_client = f"lowerclient{uuid.uuid4().hex[:6]}"
        _seed_matter(db_session, client_name=unique_client)
        db_session.commit()

        resp = client.get(f"/api/matters?q={unique_client.upper()}")
        body = resp.json()
        assert any(m["client_name"] == unique_client for m in body["matters"])

    def test_lowercase_query_finds_uppercase_data(self, client, db_session):
        unique_key = f"lowerkey-{uuid.uuid4().hex[:6]}"
        _seed_matter(db_session, matter_key=unique_key.upper())
        db_session.commit()

        resp = client.get(f"/api/matters?q={unique_key}")
        body = resp.json()
        keys = [m["matter_key"] for m in body["matters"]]
        assert unique_key.upper() in keys


# ---------------------------------------------------------------------------
# 6. Empty/whitespace q behaves as no filter
# ---------------------------------------------------------------------------
class TestEmptyOrWhitespaceQ:
    def test_empty_q_returns_all(self, client, db_session):
        _seed_matter(db_session, client_name=f"EmptyQClient-{uuid.uuid4().hex[:6]}")
        db_session.commit()

        resp = client.get("/api/matters?q=")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["total"] >= 1

    def test_whitespace_q_returns_all(self, client, db_session):
        _seed_matter(db_session, client_name=f"WsQClient-{uuid.uuid4().hex[:6]}")
        db_session.commit()

        resp = client.get("/api/matters?q=%20%20%20")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["total"] >= 1


# ---------------------------------------------------------------------------
# 7. status filter
# ---------------------------------------------------------------------------
class TestStatusFilter:
    def test_filters_by_status(self, client, db_session):
        open_token = f"Open-{uuid.uuid4().hex[:8]}"
        _seed_matter(db_session, matter_status="open", client_name=open_token)
        _seed_matter(db_session, matter_status="closed", client_name=f"Closed-{uuid.uuid4().hex[:8]}")
        db_session.commit()

        resp = client.get(f"/api/matters?status=open&q={open_token}")
        body = resp.json()
        assert body["total"] >= 1
        assert all(m["matter_status"] == "open" for m in body["matters"])
        assert any(m["client_name"] == open_token for m in body["matters"])

    def test_status_filter_with_no_match(self, client, db_session):
        _seed_matter(db_session, matter_status="open")
        db_session.commit()

        resp = client.get("/api/matters?status=suspended")
        assert resp.json()["total"] == 0


# ---------------------------------------------------------------------------
# 8. practice_area filter
# ---------------------------------------------------------------------------
class TestPracticeAreaFilter:
    def test_filters_by_practice_area(self, client, db_session):
        tax_token = f"Tax-{uuid.uuid4().hex[:8]}"
        _seed_matter(db_session, practice_area="Tax", client_name=tax_token)
        _seed_matter(db_session, practice_area="IP", client_name=f"IP-{uuid.uuid4().hex[:8]}")
        db_session.commit()

        resp = client.get(f"/api/matters?practice_area=Tax&q={tax_token}")
        body = resp.json()
        assert body["total"] >= 1
        assert all(m["practice_area"] == "Tax" for m in body["matters"])
        assert any(m["client_name"] == tax_token for m in body["matters"])


# ---------------------------------------------------------------------------
# 9. Combined filters
# ---------------------------------------------------------------------------
class TestCombinedFilters:
    def test_q_plus_status_plus_practice_area(self, client, db_session):
        unique = f"combo-{uuid.uuid4().hex[:6]}"
        _seed_matter(
            db_session,
            matter_key=_mk_key("CMB"),
            client_name=f"Client {unique}",
            matter_name=f"Matter {unique}",
            matter_status="open",
            practice_area="Tax",
        )
        _seed_matter(
            db_session,
            client_name=f"Client {unique}",
            matter_name=f"Matter {unique}",
            matter_status="closed",
            practice_area="Tax",
        )
        db_session.commit()

        resp = client.get(f"/api/matters?q={unique}&status=open&practice_area=Tax")
        body = resp.json()
        assert body["total"] >= 1
        for m in body["matters"]:
            assert m["matter_status"] == "open"
            assert m["practice_area"] == "Tax"


# ---------------------------------------------------------------------------
# 10. limit pagination
# ---------------------------------------------------------------------------
class TestLimitPagination:
    def test_limit_caps_results(self, client, db_session):
        for _ in range(3):
            _seed_matter(db_session, client_name=f"Limit-{uuid.uuid4().hex[:6]}")
        db_session.commit()

        resp = client.get("/api/matters?limit=2")
        body = resp.json()
        assert len(body["matters"]) <= 2
        assert body["limit"] == 2

    def test_default_limit_is_20(self, client, db_session):
        resp = client.get("/api/matters")
        assert resp.json()["limit"] == 20


# ---------------------------------------------------------------------------
# 11. offset pagination
# ---------------------------------------------------------------------------
class TestOffsetPagination:
    def test_offset_skips_records(self, client, db_session):
        m1 = _seed_matter(db_session, matter_key=f"OFFA-{uuid.uuid4().hex[:6]}")
        m2 = _seed_matter(db_session, matter_key=f"OFFB-{uuid.uuid4().hex[:6]}")
        m3 = _seed_matter(db_session, matter_key=f"OFFC-{uuid.uuid4().hex[:6]}")
        db_session.commit()

        all_keys = {m1.matter_key, m2.matter_key, m3.matter_key}

        total = client.get("/api/matters?limit=1").json()["total"]
        assert total >= 3

        first_page = client.get("/api/matters?limit=1&offset=0").json()["matters"]
        second_page = client.get("/api/matters?limit=1&offset=1").json()["matters"]

        assert len(first_page) == 1
        assert len(second_page) == 1
        assert first_page[0]["matter_key"] != second_page[0]["matter_key"]
        assert "offset" in client.get("/api/matters?limit=1&offset=5").json()


# ---------------------------------------------------------------------------
# 12. total is correct before pagination
# ---------------------------------------------------------------------------
class TestTotalBeforePagination:
    def test_total_reflects_all_matches(self, client, db_session):
        for _ in range(5):
            _seed_matter(db_session, client_name=f"Tot-{uuid.uuid4().hex[:6]}")
        db_session.commit()

        resp = client.get("/api/matters?limit=2")
        body = resp.json()
        assert body["total"] >= 5
        assert len(body["matters"]) <= 2

    def test_total_reflects_filtered_count(self, client, db_session):
        for _ in range(3):
            _seed_matter(db_session, matter_status="open", client_name=f"Tot2-{uuid.uuid4().hex[:6]}")
        _seed_matter(db_session, matter_status="closed", client_name=f"Tot2Closed-{uuid.uuid4().hex[:6]}")
        db_session.commit()

        resp = client.get("/api/matters?status=open&limit=1")
        body = resp.json()
        assert body["total"] >= 3
        assert len(body["matters"]) == 1


# ---------------------------------------------------------------------------
# 13-15. Validation errors
# ---------------------------------------------------------------------------
class TestValidation:
    def test_limit_above_100_returns_422(self, client, db_session):
        resp = client.get("/api/matters?limit=101")
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_limit_zero_returns_422(self, client, db_session):
        resp = client.get("/api/matters?limit=0")
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_negative_offset_returns_422(self, client, db_session):
        resp = client.get("/api/matters?offset=-1")
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_limit_100_is_allowed(self, client, db_session):
        resp = client.get("/api/matters?limit=100")
        assert resp.status_code == status.HTTP_200_OK

    def test_offset_zero_is_allowed(self, client, db_session):
        resp = client.get("/api/matters?offset=0")
        assert resp.status_code == status.HTTP_200_OK


# ---------------------------------------------------------------------------
# 16. Non-matching query
# ---------------------------------------------------------------------------
class TestNonMatching:
    def test_total_zero_and_empty_matters(self, client, db_session):
        _seed_matter(db_session, client_name="Some Real Client")
        db_session.commit()

        resp = client.get("/api/matters?q=zzzzz-no-such-string-anywhere-zzzzz")
        body = resp.json()
        assert body["total"] == 0
        assert body["matters"] == []


# ---------------------------------------------------------------------------
# 17. Deterministic ordering
# ---------------------------------------------------------------------------
class TestOrdering:
    def test_results_ordered_by_matter_key_ascending(self, client, db_session):
        keys = [f"ORD-{uuid.uuid4().hex[:8]}" for _ in range(3)]
        for k in keys:
            _seed_matter(db_session, matter_key=k)
        db_session.commit()

        resp = client.get("/api/matters?limit=100")
        body = resp.json()
        matter_keys = [m["matter_key"] for m in body["matters"]]
        assert matter_keys == sorted(matter_keys)

    def test_pagination_stable_across_calls(self, client, db_session):
        for _ in range(5):
            _seed_matter(db_session, matter_key=_mk_key("STAB"))
        db_session.commit()

        resp1 = client.get("/api/matters?limit=2&offset=0")
        resp2 = client.get("/api/matters?limit=2&offset=0")
        assert resp1.json()["matters"] == resp2.json()["matters"]


# ---------------------------------------------------------------------------
# 18. Read-only
# ---------------------------------------------------------------------------
class TestReadOnly:
    def test_does_not_modify_records(self, client, db_session):
        m = _seed_matter(
            db_session,
            client_name=f"ReadOnly-{uuid.uuid4().hex[:6]}",
            matter_name="Before Matter",
            matter_status="open",
        )
        db_session.commit()
        before_name = m.matter_name
        before_status = m.matter_status

        client.get("/api/matters?q=ReadOnly")
        client.get("/api/matters?status=open")
        client.get("/api/matters?limit=5")

        db_session.expire(m)
        reloaded = db_session.get(Matter, m.matter_key)
        assert reloaded.matter_name == before_name
        assert reloaded.matter_status == before_status


# ---------------------------------------------------------------------------
# 19. Existing matter detail endpoint still works
# ---------------------------------------------------------------------------
class TestDetailEndpointStillWorks:
    def test_detail_endpoint_returns_matter(self, client, db_session):
        m = _seed_matter(
            db_session,
            client_name="DetailWorks",
            matter_name="Detail Matter",
        )
        db_session.commit()

        resp = client.get(f"/api/matters/{m.matter_key}")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["matter"]["matter_key"] == m.matter_key

    def test_detail_endpoint_404_for_missing(self, client, db_session):
        resp = client.get("/api/matters/DOES-NOT-EXIST-999")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_collection_route_not_intercepted_as_detail(self, client, db_session):
        resp = client.get("/api/matters")
        assert resp.status_code == status.HTTP_200_OK
        assert "matters" in resp.json()
        assert "matter" not in resp.json()
