# AGENTS Playbook

## 1. Project Overview
This repository contains a Telegram bot for managing participants of the "Tres Dias Israel" event. The bot parses free-form text or template messages to add participants, checks for duplicates, enforces role-based access for coordinators and viewers, and provides commands to list, add and manage participants.

## 2. Setup
Follow these steps to prepare a development environment:

```bash
# Clone the repository
git clone <repository-url>
cd td-event-telegram-bot

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

1. Create a `.env` file in the repository root and set the bot token:
   ```
   BOT_TOKEN=your_telegram_bot_token_here
   ```
2. Update `config.py` with your Telegram user IDs in `COORDINATOR_IDS` and `VIEWER_IDS`.
3. Initialize the SQLite database by running:
   ```bash
   python3 database.py
   ```

## 3. Build & Test
Run the full test suite using Python's built-in `unittest` framework:

```bash
python3 -m unittest discover tests
```

The tests cover the participant parser (`test_parser.py`), database operations (`test_database.py`), confirmation template parsing (`test_confirmation_template.py`), and field normalization (`test_normalize_field_value.py`).

## 4. Coding Standards
- **Style**: Follow PEP 8. Use a formatter such as `black` for consistency.
- **Commit messages**: Use conventional commits (`feat:`, `fix:`, `docs:`, `test:` etc.).
- **Branch naming**: `<type>/<ticket-id>-<short-description>` (e.g., `feat/TDI-15-add-export-feature`).

## 5. Secrets Policy
- Do **not** commit secrets. The bot token belongs in a local `.env` file which is ignored by git.
- SQLite database files (`*.db`) are also ignored and should not be committed.

## 6. Gotchas / Pitfalls
- **In-memory cache**: `utils/cache.py` loads reference data (departments and cities) once on startup; restart the bot if these lists change.
- **Database initialization**: `participants.db` is not created automatically when running `main.py`. Execute `python3 database.py` before first use.
- **Role-based access**: User IDs are hardcoded in `config.py`. Changing roles requires modifying the file and redeploying.
- **State management**: Conversation states are defined in `states.py`. Ensure handlers respect the current state when extending conversation flows.

## 7. Logging Guidelines
- Every new command **must** log its usage with `UserActionLogger` at start and end.
- Updates to business logic should include corresponding log entries.
- When adding participant fields, ensure their changes are logged through `ParticipantService`.
- Use `UserActionLogger` exclusively for user actions.

### Log Structure
All logs are stored in the `logs/` directory:
- `logs/bot.log` - General application logs
- `logs/errors.log` - All errors with context
- `logs/user_actions.log` - User actions (JSON format)
- `logs/participant_changes.log` - Participant CRUD operations (JSON format)
- `logs/performance.log` - Performance metrics (JSON format)
- `logs/sql.log` - SQL queries (errors only)

### Monitoring Commands
```bash
# Quick monitoring
./scripts/monitor.sh stats              # Today's statistics
./scripts/monitor.sh live-users         # Real-time user actions
./scripts/monitor.sh live-errors        # Real-time errors
./scripts/monitor.sh user 12345         # Specific user actions
./scripts/monitor.sh report             # Generate HTML report

# Log cleanup
./scripts/log_cleanup.sh                # Archive old logs
```

### Examples
```python
user_logger.log_user_action(user_id, "command_start", {"command": "/add"})
user_logger.log_participant_operation(user_id, "update", data, participant_id)
```

### Mandatory logging
- Command start and completion
- CRUD operations on participants
- Conversation state transitions
- Errors with full context

### PR Checklist
- [ ] Commands log start/end via `UserActionLogger`
- [ ] `ParticipantService` logs all data changes
- [ ] State handlers use `@log_state_transitions`
- [ ] Tests cover logging when applicable
- [ ] Check logs are written to `logs/` directory
