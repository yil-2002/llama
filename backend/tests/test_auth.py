import time

import pytest

from app.telegram_auth import InitDataError, sign_init_data, validate_init_data


def test_valid_init_data():
    s = sign_init_data({"auth_date": int(time.time()), "user": {"id": 42, "first_name": "Ali"}}, "tok")
    data = validate_init_data(s, "tok")
    assert data["user"]["id"] == 42


def test_wrong_token_rejected():
    s = sign_init_data({"auth_date": int(time.time()), "user": {"id": 42}}, "tok")
    with pytest.raises(InitDataError):
        validate_init_data(s, "other")


def test_expired_rejected():
    s = sign_init_data({"auth_date": int(time.time()) - 200000, "user": {"id": 42}}, "tok")
    with pytest.raises(InitDataError):
        validate_init_data(s, "tok")
