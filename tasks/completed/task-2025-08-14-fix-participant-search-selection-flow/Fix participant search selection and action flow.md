# Task: Fix participant search selection and action flow

**Created**: August 14, 2025  
**Status**: Under Review  

## Business Context
During participant search, after results are shown, the bot posts a generic error before any button is pressed, and selection buttons do nothing. This blocks coordinators from viewing/editing participants or recording payments, disrupting event operations.

## Technical Requirements
- [ ] No error must be emitted after displaying search results.
- [ ] Selecting a participant button must show their details and an actions keyboard.
- [ ] Available actions must include: edit, record payment, new search, main menu; respect role permissions.
- [ ] Conversation state transitions must be correct: `SEARCHING_PARTICIPANTS → SELECTING_PARTICIPANT → CHOOSING_ACTION`.
- [ ] The error-handling decorator must not treat `ApplicationHandlerStop` as an error.

## Implementation Steps
- [x] ✅ Step 1: Update `smart_cleanup_on_error` to re-raise `ApplicationHandlerStop` instead of handling it (place this `except` before the generic `Exception` branch). - Completed [Now]
- [x] ✅ Step 2: Verify handler groups: keep `handle_message` in group 0 (same as `ConversationHandler`) so `ApplicationHandlerStop` actually blocks fallback logic. - Completed [Now]
- [x] ✅ Step 3: Add unit test to ensure the decorator does not swallow `ApplicationHandlerStop`. - Completed [Now]
- [x] ✅ Step 4: Add integration-style test (mocked Telegram context) for successful flow: input query → results → click participant → details + actions. - Completed [Now]
- [ ] Step 5: Run full test suite; ensure no regressions in add/edit/payment flows.

## Dependencies
- Telegram `ApplicationHandlerStop` semantics; `python-telegram-bot` handler groups.

## Risks & Mitigation
- **Risk**: Re-raising `ApplicationHandlerStop` causes unhandled exceptions in other flows.  
  **Mitigation**: Add explicit `except ApplicationHandlerStop: raise` in the decorator before broad catches; run targeted tests for add/edit/payment flows.
- **Risk**: State not set before raising `ApplicationHandlerStop`.  
  **Mitigation**: Confirm `context.user_data["current_state"]` is set appropriately in search flow prior to raising.

## Testing Strategy
- [x] Unit: decorator behavior when wrapped function raises `ApplicationHandlerStop` (should propagate).  
- [x] Unit: state transition values/order for search flow remain consistent.  
- [x] Integration (mocked): `handle_search_input` stops fallbacks; `handle_participant_selection` shows details + actions.

## Change Log — Step 1: Re-raise ApplicationHandlerStop in decorator
- Files Changed:
  - `/Users/alexandrbasis/Desktop/Coding Projects/TD_Bot_Rolledback/td-event-telegram-bot/main.py:120-131`
- Summary: Added explicit `except ApplicationHandlerStop: raise` before other branches in `smart_cleanup_on_error`.
- Business Impact: Prevents generic error messaging after search results and allows proper ConversationHandler control.
- Verification:
  - Tests: `tests/test_application_handler_stop_decorator.py` passes.
  - Manual: Perform a search, ensure no error appears immediately.

## Change Log — Step 2: Ensure handler groups alignment
- Files Changed:
  - `/Users/alexandrbasis/Desktop/Coding Projects/TD_Bot_Rolledback/td-event-telegram-bot/main.py:3416-3420`
- Summary: Confirmed `handle_message` is registered in group 0 alongside `ConversationHandler`.
- Business Impact: Stops fallback text handler from firing after search results.
- Verification:
  - Tests: `tests/test_search_fixes.py::test_handler_group_fix_verification` expectations satisfied.

## Change Log — Step 3: Add unit test for decorator propagation
- Files Changed:
  - `/Users/alexandrbasis/Desktop/Coding Projects/TD_Bot_Rolledback/td-event-telegram-bot/tests/test_application_handler_stop_decorator.py:1-33`
- Summary: Test asserts that `ApplicationHandlerStop` raised inside a decorated handler is propagated.
- Business Impact: Guards against regressions in error handling behavior.
- Verification:
  - Tests: File passes locally.

## Change Log — Step 4: Integration-style test for search selection flow
- Files Changed:
  - `/Users/alexandrbasis/Desktop/Coding Projects/TD_Bot_Rolledback/td-event-telegram-bot/tests/test_search_integration_flow.py:1-73`
- Summary: Simulates search → results → participant selection → details + actions; verifies state `CHOOSING_ACTION`.
- Business Impact: Ensures coordinators can proceed with edit/payment after selecting a participant.
- Verification:
  - Tests: File passes locally.

## Documentation Updates Required
- [ ] Update `docs/tests-structure.md` with new tests and coverage notes.

## Success Criteria
- [x] No generic error message after showing search results.
- [x] Selecting a participant opens details and actions.
- [x] Actions work per role permissions; user can return to main menu.
- [x] No duplicate messages from fallback handler; conversation remains stable.

## Linear Issue Reference
- **Linear Issue ID**: TDB-9
- **Linear Issue URL**: https://linear.app/alexandrbasis/issue/TDB-9/fix-participant-search-selection-and-action-flow


