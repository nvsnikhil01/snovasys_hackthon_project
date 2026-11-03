import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models  # noqa: F401
from app.database import Base
from app.models import Document, Permission, User
from app.permissions import can


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        yield session


def make_user(db, email, role="user"):
    user = User(email=email, password_hash="x", role=role)
    db.add(user)
    db.commit()
    return user


def make_doc(db, owner):
    doc = Document(owner_id=owner.id, filename="a.pdf", stored_path="x", size=1)
    db.add(doc)
    db.commit()
    return doc


def grant(db, doc, user, level):
    db.add(Permission(document_id=doc.id, user_id=user.id, level=level))
    db.commit()


def test_owner_can_do_everything(db):
    owner = make_user(db, "owner@x.com")
    doc = make_doc(db, owner)
    for action in ("read", "edit", "share", "delete"):
        assert can(db, owner, doc, action)


def test_stranger_has_no_access(db):
    owner = make_user(db, "owner@x.com")
    stranger = make_user(db, "stranger@x.com")
    doc = make_doc(db, owner)
    for action in ("read", "edit", "share", "delete"):
        assert not can(db, stranger, doc, action)


def test_read_grant_can_only_read(db):
    owner = make_user(db, "owner@x.com")
    reader = make_user(db, "reader@x.com")
    doc = make_doc(db, owner)
    grant(db, doc, reader, "read")
    assert can(db, reader, doc, "read")
    assert not can(db, reader, doc, "edit")
    assert not can(db, reader, doc, "share")
    assert not can(db, reader, doc, "delete")


def test_edit_grant_can_read_and_edit_only(db):
    owner = make_user(db, "owner@x.com")
    editor = make_user(db, "editor@x.com")
    doc = make_doc(db, owner)
    grant(db, doc, editor, "edit")
    assert can(db, editor, doc, "read")
    assert can(db, editor, doc, "edit")
    assert not can(db, editor, doc, "share")
    assert not can(db, editor, doc, "delete")


def test_admin_without_grant_cannot_read_contents(db):
    owner = make_user(db, "owner@x.com")
    admin = make_user(db, "admin@x.com", role="admin")
    doc = make_doc(db, owner)
    assert not can(db, admin, doc, "read")


def test_unknown_action_is_denied(db):
    owner = make_user(db, "owner@x.com")
    doc = make_doc(db, owner)
    assert not can(db, owner, doc, "fly")
def test_invalid_grant_level_is_denied(db):
    owner = make_user(db, "owner@x.com")
    other = make_user(db, "other@x.com")
    doc = make_doc(db, owner)
    grant(db, doc, other, "owner")  # bad data: should NOT give access
    for action in ("read", "edit", "share", "delete"):
        assert not can(db, other, doc, action)


def test_admin_with_read_grant_can_read_only(db):
    owner = make_user(db, "owner@x.com")
    admin = make_user(db, "admin@x.com", role="admin")
    doc = make_doc(db, owner)
    grant(db, doc, admin, "read")
    assert can(db, admin, doc, "read")
    assert not can(db, admin, doc, "edit")
    assert not can(db, admin, doc, "share")
    assert not can(db, admin, doc, "delete")


def test_owner_with_a_grant_is_still_owner(db):
    owner = make_user(db, "owner@x.com")
    doc = make_doc(db, owner)
    grant(db, doc, owner, "read")
    for action in ("read", "edit", "share", "delete"):
        assert can(db, owner, doc, action)