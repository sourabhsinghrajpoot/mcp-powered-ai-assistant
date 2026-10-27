from backend.app import main


def test_registration_creates_account_and_returns_login_token(client):
    response = client.post(
        "/api/auth/register",
        data={"username": "new-user@example.com", "password": "a-secure-password"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["user"]["email"] == "new-user@example.com"
    assert payload["access_token"]
    login = client.post(
        "/api/auth/login",
        data={"username": "new-user@example.com", "password": "a-secure-password"},
    )
    assert login.status_code == 200
    claims = main.jwt.decode(
        payload["access_token"],
        main.settings.jwt_secret,
        algorithms=["HS256"],
    )
    assert claims["sub"] == str(payload["user"]["id"])
