"""Owner account details over HTTP: joined shape, additive only."""

from api_testsupport import create_user, login, setup_admin

DETAIL_KEYS = {
    "id",
    "email",
    "is_active",
    "created_at",
    "updated_at",
    "profile",
    "system_roles",
    "tenants",
}


def test_detail_joins_for_fresh_member(client):
    setup_admin(client, "admin@x.com")
    user_id = create_user(client, "plain@x.com")

    body = client.get(f"/api/users/{user_id}").json()

    assert set(body.keys()) == DETAIL_KEYS
    assert body["profile"] is None
    assert body["system_roles"] == []
    assert len(body["tenants"]) == 1
    assert body["tenants"][0]["roles"] == ["member"]


def test_detail_lists_system_roles(client, session_factory):
    from api.models import SystemRole, UserSystemRole

    setup_admin(client, "admin@x.com")
    user_id = create_user(client, "plain@x.com")
    with session_factory() as session:
        session.add(UserSystemRole(user_id=user_id, role=SystemRole.SYSTEM_OWNER))
        session.commit()

    body = client.get(f"/api/users/{user_id}").json()

    assert body["system_roles"] == ["system_owner"]
    # The tenant link is one per user until invites arrive; the shape stays a list.
    assert len(body["tenants"]) == 1


def test_detail_shows_owner_role_and_profile(client):
    admin_id = setup_admin(client, "admin@x.com")
    assert (
        client.put(f"/api/users/{admin_id}/profile", json={"display_name": "Owner"}).status_code
        == 200
    )

    body = client.get(f"/api/users/{admin_id}").json()

    assert body["system_roles"] == ["system_owner"]
    assert body["profile"]["display_name"] == "Owner"
    assert body["tenants"][0]["roles"] == ["admin", "member"]


def test_detail_unknown_user_404(client):
    setup_admin(client, "admin@x.com")
    assert client.get("/api/users/424242").status_code == 404


def test_profile_reach_other_only_through_detail(client):
    setup_admin(client, "admin@x.com")
    user_id = create_user(client, "plain@x.com")
    login(client, "plain@x.com")
    assert (
        client.put(f"/api/users/{user_id}/profile", json={"display_name": "P"}).status_code == 200
    )

    login(client, "admin@x.com")
    body = client.get(f"/api/users/{user_id}").json()

    assert body["profile"]["display_name"] == "P"
