import os

os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app import main


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    main.Base.metadata.create_all(engine)
    test_sessions = sessionmaker(engine, expire_on_commit=False)

    def override_db():
        with test_sessions() as session:
            yield session

    def override_user(session=Depends(main.db)):
        return session.get(main.User, 1)

    with test_sessions() as session:
        session.add(main.User(id=1, email="test@example.com", password_hash="unused"))
        session.add(main.Conversation(id=1, user_id=1, title="Test conversation"))
        session.commit()

    main.app.dependency_overrides[main.db] = override_db
    main.app.dependency_overrides[main.current_user] = override_user
    try:
        with TestClient(main.app) as test_client:
            yield test_client
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()
