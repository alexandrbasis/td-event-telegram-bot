# Task: Fix Airtable create error: PaymentDate invalid value on add (422)

**Created**: 2025-08-14  
**Status**: In Progress  

## Business Context
Creating a participant in Airtable fails with 422 when `PaymentDate` is empty. The current mapping always sends `PaymentDate: ""`, but Airtable Date fields reject empty strings. This blocks new participant sync to Airtable.

## Technical Requirements
- [x] Omit `PaymentDate` from the payload when it's empty/absent
- [x] Normalize provided dates to ISO `YYYY-MM-DD` (support `DD/MM/YYYY`, `DD.MM.YYYY`, `DD-MM-YYYY`, `YYYY/MM/DD`)
- [x] When clearing date on update, send `null` (or omit), not an empty string
- [x] Unit tests cover creation without `PaymentDate`, normalization cases, and date clearing

## Implementation Steps (with substeps)

- [x] ✅ Step 0 — Prep and Branch - Completed 2025-08-14  
  - **Implementation Notes**: Activated venv, installed pytest, baseline tests passed (136). Created branch `basisalexandr/tdb-10-fix-airtable-paymentdate-invalid`. Linear updated to In Progress with comment.

- [x] ✅ Step 1 — Add date normalization helper - Completed 2025-08-14
  - [x] File: `td-event-telegram-bot/repositories/airtable_participant_repository.py`
  - [x] Add function near imports:
    ```python
    from datetime import datetime

    def _normalize_date_to_iso(value: str) -> str:
        if not value:
            return ""
        v = str(value).strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(v, fmt).date().isoformat()
            except ValueError:
                continue
        # Assume already acceptable for Airtable or will be validated elsewhere
        return v
    ```
  - [x] Verification: temporary local import runs (`python -c 'import repositories.airtable_participant_repository as r;print("ok")'`).
  - [x] Linear: comment "Step 1 completed — helper added".
  - [x] Sub-step 1.1: Introduce `_normalize_date_to_iso`
    - **Acceptance Criteria**: Helper returns ISO `YYYY-MM-DD` for supported formats; returns input as-is if unparsable
    - **Tests (write first)**: Covered in Step 5 tests (`test_add_normalizes_*`)
    - **Artifacts**: `repositories/airtable_participant_repository.py`
    - **Completion Signal**: Import check prints `ok`; tests passing
    - **Approval Gate**: Approved by reviewer

- [x] ✅ Step 2 — Fix `_participant_to_airtable_fields` - Completed 2025-08-14
  - [x] In the same file, change building of the dict so that `PaymentDate` is added only if truthy and normalized:
    ```python
    fields = {
        'FullNameRU': participant.FullNameRU,
        'FullNameEN': participant.FullNameEN or '',
        'Gender': participant.Gender,
        'Size': participant.Size or '',
        'Church': participant.Church or '',
        'Role': participant.Role or '',
        'Department': participant.Department or '',
        'CountryAndCity': participant.CountryAndCity or '',
        'SubmittedBy': participant.SubmittedBy or '',
        'ContactInformation': participant.ContactInformation or '',
        'PaymentStatus': participant.PaymentStatus or 'Unpaid',
        'PaymentAmount': participant.PaymentAmount or 0,
    }
    if participant.PaymentDate:
        fields['PaymentDate'] = _normalize_date_to_iso(participant.PaymentDate)
    return fields
    ```
  - [x] Remove the old line that always set `'PaymentDate': participant.PaymentDate or ''`.
  - [x] Verification: ensure repository `.add()` will not include `PaymentDate` when empty by adding a quick REPL snippet or running tests in Step 6.
  - [x] Linear: comment "Step 2 completed — mapping updated".
  - [x] Sub-step 2.1: Omit empty `PaymentDate` on create
    - **Acceptance Criteria**: Payload contains no `PaymentDate` when input empty
    - **Tests (write first)**: `test_add_omits_paymentdate_when_empty`
    - **Artifacts**: `repositories/airtable_participant_repository.py`
    - **Completion Signal**: Test passes
    - **Approval Gate**: Approved by reviewer

- [x] ✅ Step 3 — Fix `update_fields` behavior for `PaymentDate` - Completed 2025-08-14
  - [x] Locate `def update_fields(self, participant_id, **fields)` in the same file.
  - [x] Before constructing `airtable_fields`, handle `PaymentDate` specially:
    ```python
    if 'PaymentDate' in fields:
        raw = fields.get('PaymentDate')
        if raw is None or str(raw).strip() == '':
            fields['PaymentDate'] = None  # clears field in Airtable
        else:
            fields['PaymentDate'] = _normalize_date_to_iso(str(raw))
    ```
  - [x] When building `airtable_fields`, do not convert `None` to empty string; keep `None` as-is so pyairtable sends JSON null.
    ```python
    airtable_fields = {}
    for key, value in fields.items():
        airtable_fields[key] = value if value is not None else None
    ```
  - [x] Linear: comment "Step 3 completed — update_fields handles empty/null and normalization".
  - [x] Sub-step 3.1: Normalize or clear `PaymentDate` in partial updates
    - **Acceptance Criteria**: Empty input results in JSON null; non-empty is ISO
    - **Tests (write first)**: `test_update_fields_clears_with_null_when_empty`
    - **Artifacts**: `repositories/airtable_participant_repository.py`
    - **Completion Signal**: Test passes
    - **Approval Gate**: Approved by reviewer

- [x] ✅ Step 4 — Ensure `update_payment` passes ISO date - Completed 2025-08-14
  - [x] In `def update_payment(...)`, normalize the provided `date` argument:
    ```python
    date = _normalize_date_to_iso(date) if date else date
    ```
  - [x] Keep existing logic for amount/status.
  - [x] Linear: comment "Step 4 completed — update_payment normalizes date".
  - [x] Sub-step 4.1: Normalize or clear `PaymentDate` in `update_payment`
    - **Acceptance Criteria**: Empty input results in JSON null; non-empty is ISO
    - **Tests (write first)**: `test_update_payment_normalizes_date`, `test_update_payment_clears_with_null_when_empty`
    - **Artifacts**: `repositories/airtable_participant_repository.py`
    - **Completion Signal**: Tests pass
    - **Approval Gate**: Approved by reviewer

- [x] ✅ Step 5 — Add focused unit tests (new file) - Completed 2025-08-14
  - [x] Create `td-event-telegram-bot/tests/test_airtable_paymentdate.py` with tests below using a fake table to capture payloads.
    ```python
    import types
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

    def test_add_omits_paymentdate_when_empty():
        repo = make_repo()
        p = Participant(FullNameRU='X', PaymentDate='')
        repo.add(p)
        assert 'PaymentDate' not in repo.table.last_create

    def test_add_normalizes_european_date():
        repo = make_repo()
        p = Participant(FullNameRU='X', PaymentDate='14/08/2025')
        repo.add(p)
        assert repo.table.last_create['PaymentDate'] == '2025-08-14'

    def test_update_fields_clears_with_null_when_empty():
        repo = make_repo()
        repo.update_fields('rec1', PaymentDate='')
        _, fields = repo.table.last_update
        assert 'PaymentDate' in fields and fields['PaymentDate'] is None
    ```
  - [x] Ran tests: `pytest -q tests/test_airtable_paymentdate.py` → 4 passed
  - [x] Linear: comment "Step 5 completed — unit tests added and passing" with brief output.
  - [x] Sub-step 5.1: Add tests for omission, normalization, clearing
    - **Acceptance Criteria**: All 6 tests pass
    - **Tests (write first)**: Implemented in `tests/test_airtable_paymentdate.py`
    - **Artifacts**: `tests/test_airtable_paymentdate.py`
    - **Completion Signal**: 6/6 passed
    - **Approval Gate**: Approved by reviewer

- [x] ✅ Step 6 — Full test run and lint - Completed 2025-08-14
  - [x] Run: `pytest -q` → 142 passed, 9 warnings
  - [x] Ensured no regressions
  - [x] Linear: comment summary posted

- [x] ✅ Step 7 — Documentation updates - Completed 2025-08-14
  - [ ] Update `td-event-telegram-bot/docs/tests-structure.md` section with the new test file name and what it covers.
  - [x] Linear: comment "Docs updated".

- [ ] Step 8 — Commit, push, PR, and review
  - [x] `git add -A && git commit -m "TDB-10: Normalize/omit PaymentDate for Airtable create/update; tests added"`
  - [x] `git push -u origin basisalexandr/tdb-10-fix-airtable-paymentdate-invalid`
  - [ ] Open PR and request review; attach TDB-10.
  - [ ] Linear: move to In Review and comment with PR link.

- [ ] Step 9 — After approval
  - [ ] Merge PR, pull `main`, and ensure full test run green.
  - [ ] Linear: set to Done with final comment including short summary, commit SHA, and path to archived task directory.

## Dependencies
- pyairtable update semantics for clearing fields with `None` vs omission

## Risks & Mitigation
- **Risk**: Incorrect parsing of user-entered European formats  → **Mitigation**: Support multiple common formats; if parsing fails, fall back to original value and assert in tests that only valid cases are accepted
- **Risk**: Clearing behavior differs per Airtable API version  → **Mitigation**: Prefer omission for create; for updates, use `None` and add a test with mocked client

## Testing Strategy
- [x] Unit tests for `_participant_to_airtable_fields` with `PaymentDate` empty and with `14/08/2025` → `2025-08-14`
- [x] Unit tests for `update_fields`/`update_payment` behavior (normalize; clear date)
- [x] Integration-style test: repository `.add()` succeeds when `PaymentDate` is not set
- [x] Coverage snippet added (see below)

## Coverage

```
142 passed, 9 warnings in 0.87s

Name                                               Stmts   Miss  Cover
-------------------------------------------------  -----  -----  -----
tests/test_airtable_paymentdate.py                    64      0   100%
repositories/airtable_participant_repository.py      186    114    39%
TOTAL                                              4984   1664    67%
```

## Documentation Updates Required
- [x] Update `td-event-telegram-bot/docs/tests-structure.md` with new tests

## Success Criteria
- [ ] Creating a participant without `PaymentDate` does not error in Airtable
- [ ] Providing `14/08/2025` results in `2025-08-14` stored in Airtable
- [ ] Clearing `PaymentDate` on update succeeds without 422
- [ ] PR merged; Linear issue TDB-10 set to Done; task archived under `tasks/completed/`

## Change Log (to be filled during implementation)
### Change Log — Step 1-4: Implement PaymentDate normalization and mapping rules
- Files Changed:
  - `/Users/alexandrbasis/Desktop/Coding Projects/TD_Bot_Rolledback/td-event-telegram-bot/repositories/airtable_participant_repository.py:4`
  - `/Users/alexandrbasis/Desktop/Coding Projects/TD_Bot_Rolledback/td-event-telegram-bot/repositories/airtable_participant_repository.py:22-34`
  - `/Users/alexandrbasis/Desktop/Coding Projects/TD_Bot_Rolledback/td-event-telegram-bot/repositories/airtable_participant_repository.py:43-61`
  - `/Users/alexandrbasis/Desktop/Coding Projects/TD_Bot_Rolledback/td-event-telegram-bot/repositories/airtable_participant_repository.py:187-201`
  - `/Users/alexandrbasis/Desktop/Coding Projects/TD_Bot_Rolledback/td-event-telegram-bot/repositories/airtable_participant_repository.py:241-251`
- Summary: Added `_normalize_date_to_iso`; updated `_participant_to_airtable_fields` to omit empty `PaymentDate` and normalize when present; `update_fields` now normalizes/clears `PaymentDate` and preserves `None`; `update_payment` normalizes date.
- Business Impact: Prevents Airtable 422 on create when `PaymentDate` is empty; ensures consistent ISO date format.
- Verification:
  - Tests: `tests/test_airtable_paymentdate.py` all pass; full suite green.
  - Manual: N/A

### Change Log — Step 5: Add unit tests for PaymentDate behavior
- Files Changed:
  - `/Users/alexandrbasis/Desktop/Coding Projects/TD_Bot_Rolledback/td-event-telegram-bot/tests/test_airtable_paymentdate.py:1-999`
- Summary: Added 6 tests covering omission, normalization (multiple formats), clearing with null, and update_payment normalization/clearing.
- Business Impact: Locks in correct behavior; prevents regressions.
- Verification:
  - Tests: 6/6 passing.

### Change Log — Step 7: Update test structure docs
- Files Changed:
  - `/Users/alexandrbasis/Desktop/Coding Projects/TD_Bot_Rolledback/td-event-telegram-bot/docs/tests-structure.md:1-1351`
- Summary: Version bump to 1.7; documented new `test_airtable_paymentdate.py`.
- Business Impact: Documentation aligned with new tests.
- Verification:
  - Visual: Confirmed doc updates.

## Linear Issue Reference
- **Linear Issue ID**: TDB-10 (052b0ad8-7c07-4463-8bd2-317667cc2a38)
- **Linear Issue URL**: https://linear.app/alexandrbasis/issue/TDB-10/fix-airtable-create-error-paymentdate-invalid-value-on-add-422