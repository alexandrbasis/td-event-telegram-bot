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
        return {'id': 'rec_test'}

    def update(self, rec_id, fields):
        self.last_update = (rec_id, fields)
        return {'id': rec_id}


def make_repo():
    repo = AirtableParticipantRepository()
    repo.table = FakeTable()
    return repo


def test_add_omits_paymentdate_when_empty(monkeypatch):
    monkeypatch.setenv("AIRTABLE_TOKEN", "test")
    monkeypatch.setenv("AIRTABLE_BASE_ID", "test")
    repo = make_repo()
    p = Participant(FullNameRU='X', PaymentDate='')
    repo.add(p)
    assert 'PaymentDate' not in repo.table.last_create


def test_add_normalizes_european_date(monkeypatch):
    monkeypatch.setenv("AIRTABLE_TOKEN", "test")
    monkeypatch.setenv("AIRTABLE_BASE_ID", "test")
    repo = make_repo()
    p = Participant(FullNameRU='X', PaymentDate='14/08/2025')
    repo.add(p)
    assert repo.table.last_create['PaymentDate'] == '2025-08-14'


def test_update_fields_clears_with_null_when_empty(monkeypatch):
    monkeypatch.setenv("AIRTABLE_TOKEN", "test")
    monkeypatch.setenv("AIRTABLE_BASE_ID", "test")
    repo = make_repo()
    repo.update_fields('rec1', PaymentDate='')
    _, fields = repo.table.last_update
    assert 'PaymentDate' in fields and fields['PaymentDate'] is None


def test_update_payment_normalizes_date(monkeypatch):
    monkeypatch.setenv("AIRTABLE_TOKEN", "test")
    monkeypatch.setenv("AIRTABLE_BASE_ID", "test")
    repo = make_repo()
    repo.update_payment('rec2', status='Paid', amount=100, date='14-08-2025')
    _, fields = repo.table.last_update
    assert fields['PaymentDate'] == '2025-08-14'


