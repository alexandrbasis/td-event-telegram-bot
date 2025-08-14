# Task: Fix delete flow shows participant reappearing in search (cache invalidation)

**Created**: 2025-08-14  
**Status**: Completed  

## Business Context
При удалении участника через поиск пользователь ожидает, что повторный поиск не покажет удалённого участника. Сейчас же после подтверждения удаления повторный поиск показывает того же участника. Это вводит в заблуждение координаторов и создаёт риск ошибочных действий над уже удалёнными данными.

## Technical Requirements
- [ ] Исправить несогласованность между удалением участника и системой поиска.
- [ ] Обеспечить немедленную инвалидцацию кэша списка участников при add/update/delete/payment.
- [ ] Добавить явное логирование события удаления в `participant_changes` с причиной.
- [ ] Пересмотреть TTL кэша и точки его обновления; соблюсти обратную совместимость.

## Implementation Steps
- [ ] Step 1: Реализовать инвалидцацию кэша при удалении
  - [x] ✅ Sub-step 1.1: Написать тест, который воспроизводит баг - Completed [2025-08-14]
    - **Acceptance Criteria**:
      - После удаления участника через сервис повторный `search_participants(name)` не возвращает его (при поиске по имени и при нечетком совпадении).
    - **Tests (write first)**:
      - `tests/test_search_flow.py::test_search_excludes_deleted_participant`
    - **Artifacts**:
      - `td-event-telegram-bot/tests/test_search_flow.py`
    - **Completion Signal**:
      - Тест падает до исправления и проходит после.
    - **Approval Gate**: Await user approval before proceeding
  - [x] ✅ Sub-step 1.2: Инвалидировать кэш в `ParticipantService.delete_participant` - Completed [2025-08-14]
    - **Acceptance Criteria**:
      - Кэш участников очищается или точечно обновляется (удаляется элемент) сразу после успешного удаления из репозитория.
    - **Tests (write first)**:
      - См. Sub-step 1.1
    - **Artifacts**:
      - `td-event-telegram-bot/services/participant_service.py`
     - **Completion Signal**:
      - Тест из Sub-step 1.1 зелёный; логи содержат запись об удалении.

### Change Log — Step 1: Cache invalidation on delete
- Files Changed:
  - `/Users/alexandrbasis/Desktop/Coding Projects/TD_Bot_Rolledback/td-event-telegram-bot/tests/test_search_flow.py:1-160`
  - `/Users/alexandrbasis/Desktop/Coding Projects/TD_Bot_Rolledback/td-event-telegram-bot/services/participant_service.py:610-665`
- Summary: Added failing test to reproduce stale cache after delete, then updated `ParticipantService.delete_participant` to remove the deleted participant from the in-memory cache and refresh cache timestamp; fallback to clearing cache on error.
- Business Impact: Prevents deleted participants from reappearing in search results immediately after deletion, reducing coordinator confusion and preventing actions on removed data.
- Verification:
  - Tests: `tests/test_search_flow.py::TestSearchExcludesDeletedParticipant::test_search_excludes_deleted_participant` passes.
  - Manual: Delete a participant via UI, immediately search by name — result should not include the deleted participant.
  - Logs: `logs/participant_changes.log` contains entry with `operation=delete` and `participant_id`.
    - **Approval Gate**: Await user approval before proceeding

- [ ] Step 2: Унифицировать обновление кэша при add/update/payment
  - [x] ✅ Sub-step 2.1: Добавить инвалидцацию/обновление кэша после `add_participant`, `update_participant`, `update_participant_fields`, `process_payment` - Completed [2025-08-14]
    - **Acceptance Criteria**:
      - После каждой операции изменения данных, последующий `search_participants` возвращает актуальные данные без ожидания TTL.
    - **Tests (write first)**:
      - `tests/test_search_flow.py::test_search_includes_new_participant_immediately`
      - `tests/test_search_flow.py::test_search_reflects_updates_immediately`
      - `tests/test_search_flow.py::test_search_reflects_payment_changes_immediately`
    - **Artifacts**:
      - `td-event-telegram-bot/services/participant_service.py`
      - `td-event-telegram-bot/tests/test_search_flow.py`
     - **Completion Signal**:
      - Новые тесты зелёные; регрессии отсутствуют.

### Change Log — Step 2: Cache updates on add/update/payment
- Files Changed:
  - `/Users/alexandrbasis/Desktop/Coding Projects/TD_Bot_Rolledback/td-event-telegram-bot/services/participant_service.py:470-960`
  - `/Users/alexandrbasis/Desktop/Coding Projects/TD_Bot_Rolledback/td-event-telegram-bot/tests/test_search_flow.py:150-240`
- Summary: Implemented immediate cache updates in `add_participant`, `update_participant`, `update_participant_fields`, and `process_payment`. Tests added for immediate reflection in search; updated name-change test to account for fuzzy matching behavior.
- Business Impact: Search results now reflect all mutations instantly without waiting for TTL, improving data accuracy for coordinators.
- Verification:
  - Tests: `tests/test_search_flow.py::TestCacheUpdateOnMutations` all pass.
  - Manual: Add/update/payment actions reflected instantly in subsequent searches.
    - **Approval Gate**: Await user approval before proceeding

- [ ] Step 3: Улучшить логирование удаления
  - [x] ✅ Sub-step 3.1: Добавить запись в `participant_changes` с `operation=delete`, `participant_id`, `reason` - Completed [2025-08-14]
    - **Acceptance Criteria**:
      - В `logs/participant_changes.log` появляется запись об удалении с причиной.
    - **Tests (write first)**:
      - `tests/test_application_handler_stop_decorator.py` (расширение фикстуры логгера) или новый unit-тест логгирования, если уместно.
    - **Artifacts**:
      - `td-event-telegram-bot/services/participant_service.py`
      - `td-event-telegram-bot/utils/user_logger.py` (при необходимости)
     - **Completion Signal**:
      - Логи содержат ожидаемую запись при удалении.

### Change Log — Step 3: Delete logging improvements
- Files Changed:
  - `/Users/alexandrbasis/Desktop/Coding Projects/TD_Bot_Rolledback/td-event-telegram-bot/tests/test_delete_logging.py:1-80`
- Summary: Added unit test ensuring `participant_changes` logger records `operation=delete` with `participant_id` and `reason`.
- Business Impact: Improves auditability of destructive operations.
- Verification:
  - Tests: `tests/test_delete_logging.py` passes (assertLogs captures delete entry and validates payload).
    - **Approval Gate**: Await user approval before proceeding

## Dependencies
- Используемая реализация репозитория (`SqliteParticipantRepository` и/или `AirtableParticipantRepository`).
- Поисковая логика в `ParticipantService.search_participants` опирается на `_get_cached_participants()` с TTL 300 секунд.

## Risks & Mitigation
- **Risk**: Сброс кэша может повысить нагрузку на БД при частых операциях. → **Mitigation**: Точечное обновление кэша (удалять/добавлять/обновлять одного участника) при наличии кэша вместо полного сброса; оставить TTL как fallback.
- **Risk**: Расхождения между локальной БД и Airtable при разных `DATABASE_TYPE`. → **Mitigation**: Инвалидцация кэша – на уровне сервиса, независимо от источника репозитория.

## Testing Strategy
- [ ] Unit-тесты на поиск после операций add/update/delete/payment.
- [ ] Интеграционные тесты при `DATABASE_TYPE=local`.
- [ ] Проверка логов на появление `operation=delete`.

## Documentation Updates Required
- [ ] Обновить `docs/tests-structure.md` (новые тесты поиска и кейсы инвалидцации).
- [ ] При необходимости, дополнить `.cursor/rules/architectural-patterns.mdc` разделом про кэширование сервисного слоя и точки инвалидцации.

## Success Criteria
- [ ] Удалённый участник не появляется в результатах поиска по имени сразу после удаления.
- [ ] Новый участник появляется в поиске немедленно после добавления.
- [ ] Обновления и оплата отражаются в поиске немедленно.
- [ ] В логах есть запись `operation=delete` с `participant_id`.

## Linear Issue Reference
- **Linear Issue ID**: TDB-11
- **Linear Issue URL**: https://linear.app/alexandrbasis/issue/TDB-11/fix-delete-flow-shows-participant-reappearing-in-search-cache
