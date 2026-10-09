"""Users listing: paged body, filters, counts, clamp, and 422s.

Unit tests drive listing.list_page on a real session. HTTP tests pin
the router contract over the container database.
"""

from api import users
from api.users import listing
from api_testsupport import create_user

ROW_KEYS = {"id", "email", "is_active", "created_at", "updated_at"}


def test_escape_like_neutralizes_wildcards():
    assert listing.escape_like("100%_done\\") == "100\\%\\_done\\\\"


def test_list_page_clamps_counts_and_trims(session_factory):
    with session_factory() as db:
        users.register(db, "lu-b@x.com", "s3cret123")
        users.register(db, "lu-a@x.com", "s3cret123")

        page = listing.list_page(db, q="  lu-a  ", page=99, page_size=1)

        assert page.page == 1
        assert [u.email for u in page.items] == ["lu-a@x.com"]
        assert page.total == 1
        assert page.total_all == 2


def test_list_page_empty_database_answers_first_page(session_factory):
    with session_factory() as db:
        page = listing.list_page(db)

    assert page.items == []
    assert page.total == 0
    assert page.total_all == 0
    assert page.page == 1


def test_page_body_shape(admin_client):
    create_user(admin_client, "shape@x.com")
    body = admin_client.get("/api/users").json()
    assert set(body) == {"items", "total", "total_all", "page", "page_size"}
    assert all(set(row) == ROW_KEYS for row in body["items"])


def test_paging_slices_in_id_order(admin_client):
    for i in range(1, 26):
        create_user(admin_client, f"pg{i:02d}@x.com")

    first = admin_client.get("/api/users", params={"page_size": 10}).json()
    second = admin_client.get("/api/users", params={"page_size": 10, "page": 2}).json()
    third = admin_client.get("/api/users", params={"page_size": 10, "page": 3}).json()

    assert [u["email"] for u in first["items"]] == [
        "admin@x.com",
        *[f"pg{i:02d}@x.com" for i in range(1, 10)],
    ]
    assert [u["email"] for u in second["items"]] == [
        *[f"pg{i:02d}@x.com" for i in range(10, 20)],
    ]
    assert [u["email"] for u in third["items"]] == [
        *[f"pg{i:02d}@x.com" for i in range(20, 26)],
    ]
    assert first["total"] == second["total"] == third["total"] == 26


def test_filter_and_search_combine_with_paging(admin_client):
    for i in range(1, 13):
        create_user(admin_client, f"act{i:02d}@x.com")
    flips = []
    for i in range(1, 13):
        uid = create_user(admin_client, f"off{i:02d}@x.com")
        flip = admin_client.put(f"/api/users/{uid}/activation", json={"active": False})
        flips.append(flip.status_code)
    assert flips == [200] * 12

    first = admin_client.get(
        "/api/users", params={"status": "inactive", "q": "off", "page_size": 10}
    ).json()
    second = admin_client.get(
        "/api/users",
        params={"status": "inactive", "q": "off", "page_size": 10, "page": 2},
    ).json()

    assert first["total"] == 12
    assert first["total_all"] == 25
    assert [u["email"] for u in first["items"]] == [
        *[f"off{i:02d}@x.com" for i in range(1, 11)],
    ]
    assert [u["email"] for u in second["items"]] == ["off11@x.com", "off12@x.com"]
    assert all(u["is_active"] is False for u in first["items"] + second["items"])


def test_counts_split_filtered_and_all(admin_client):
    create_user(admin_client, "q-found@x.com")
    create_user(admin_client, "q-other@x.com")

    body = admin_client.get("/api/users", params={"q": "found"}).json()
    upper = admin_client.get("/api/users", params={"q": "FOUND"}).json()

    assert body["total"] == 1
    assert body["total_all"] == 3
    assert [u["email"] for u in upper["items"]] == ["q-found@x.com"]


def test_page_size_25_applies_and_echoes(admin_client):
    # 13 rows: the default 10 would answer 10, so the count has bite.
    for i in range(1, 13):
        create_user(admin_client, f"s25-{i:02d}@x.com")

    body = admin_client.get("/api/users", params={"page_size": 25}).json()

    assert body["page_size"] == 25
    assert len(body["items"]) == 13


def test_wildcards_match_literally(admin_client):
    create_user(admin_client, "a%b@x.com")
    create_user(admin_client, "a_z@x.com")
    create_user(admin_client, "plain@x.com")

    percent = admin_client.get("/api/users", params={"q": "a%b"}).json()
    underscore = admin_client.get("/api/users", params={"q": "a_z"}).json()

    assert [u["email"] for u in percent["items"]] == ["a%b@x.com"]
    assert [u["email"] for u in underscore["items"]] == ["a_z@x.com"]


def test_page_past_end_clamps_to_last(admin_client):
    for i in range(1, 13):
        create_user(admin_client, f"cl{i:02d}@x.com")

    body = admin_client.get("/api/users", params={"page": 999}).json()

    assert body["page"] == 2
    assert len(body["items"]) == 3
    assert body["total"] == 13


def test_no_matches_answers_empty_first_page(admin_client):
    create_user(admin_client, "only@x.com")

    body = admin_client.get("/api/users", params={"q": "ghost"}).json()

    assert body["items"] == []
    assert body["total"] == 0
    assert body["page"] == 1


def test_defaults_apply_without_params(admin_client):
    create_user(admin_client, "dflt@x.com")

    body = admin_client.get("/api/users").json()

    assert body["page"] == 1
    assert body["page_size"] == 10
    assert body["total"] == 2


def test_bad_query_params_answer_422(admin_client):
    cases = (
        {"page": 0},
        {"page": -1},
        {"page_size": 7},
        {"status": "bogus"},
        {"q": "x" * 201},
    )
    responses = [admin_client.get("/api/users", params=params) for params in cases]
    assert [resp.status_code for resp in responses] == [422] * len(cases)
