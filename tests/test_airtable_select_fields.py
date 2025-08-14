import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from repositories.airtable_participant_repository import AirtableParticipantRepository
from models.participant import Participant


class FakeTable:
    def __init__(self):
        self.last_create = None
        self.last_update = None

    def create(self, fields):
        self.last_create = fields
        return {"id": "rec_test"}

    def update(self, rec_id, fields):
        self.last_update = (rec_id, fields)
        return {"id": rec_id}


def make_repo():
    repo = AirtableParticipantRepository()
    repo.table = FakeTable()
    return repo


def test_add_omits_department_when_empty_or_candidate(monkeypatch):
    monkeypatch.setenv("AIRTABLE_TOKEN", "test")
    monkeypatch.setenv("AIRTABLE_BASE_ID", "test")
    repo = make_repo()

    p = Participant(FullNameRU="X", Role="CANDIDATE", Department="")
    repo.add(p)

    assert "Department" not in repo.table.last_create


def test_update_fields_sets_department_null_when_empty(monkeypatch):
    monkeypatch.setenv("AIRTABLE_TOKEN", "test")
    monkeypatch.setenv("AIRTABLE_BASE_ID", "test")
    repo = make_repo()

    repo.update_fields("rec1", Department="")
    _, fields = repo.table.last_update

    assert "Department" in fields and fields["Department"] is None


def test_update_clears_department_when_role_is_candidate(monkeypatch):
    monkeypatch.setenv("AIRTABLE_TOKEN", "test")
    monkeypatch.setenv("AIRTABLE_BASE_ID", "test")
    repo = make_repo()

    # simulate full update of a participant switching to CANDIDATE
    p = Participant(FullNameRU="X", Role="CANDIDATE", Department="Worship")
    p.id = "rec1"
    repo.update(p)

    rec_id, fields = repo.table.last_update
    assert rec_id == "rec1"
    assert fields.get("Role") == "CANDIDATE"
    # Must explicitly clear Department with null
    assert "Department" in fields and fields["Department"] is None


def test_update_fields_role_candidate_clears_department_when_not_provided(monkeypatch):
    monkeypatch.setenv("AIRTABLE_TOKEN", "test")
    monkeypatch.setenv("AIRTABLE_BASE_ID", "test")
    repo = make_repo()

    # Only Role is provided; Department not provided and should be cleared
    repo.update_fields("rec2", Role="CANDIDATE")
    rec_id, fields = repo.table.last_update
    assert rec_id == "rec2"
    assert fields.get("Role") == "CANDIDATE"
    assert "Department" in fields and fields["Department"] is None


