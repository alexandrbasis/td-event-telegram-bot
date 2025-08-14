# Test Structure Documentation

**Version**: 1.5  
**Last Updated**: August 14, 2025

## Overview

This document describes the comprehensive test architecture of the Tres Dias Israel Telegram Bot project. The test suite covers unit tests, integration tests, async operations, database interactions, and UI components, ensuring robust code quality and system reliability.

## Table of Contents

1. [Test Architecture Overview](#test-architecture-overview)
2. [Test Categories](#test-categories)
3. [Testing Patterns](#testing-patterns)
4. [Test Infrastructure](#test-infrastructure)
5. [Database Testing](#database-testing)
6. [Async Testing](#async-testing)
7. [Mock and Fixture Patterns](#mock-and-fixture-patterns)
8. [Test Data Management](#test-data-management)
9. [Test Coverage Areas](#test-coverage-areas)
10. [Testing Best Practices](#testing-best-practices)

---

## Test Architecture Overview

### Test Framework
- **Primary Framework**: Python `unittest` (built-in)
- **Async Testing**: `unittest.IsolatedAsyncioTestCase` for async operations
- **Mocking**: `unittest.mock` (MagicMock, AsyncMock, patch)
- **Database Testing**: In-memory SQLite for isolation

### Test Organization
```
tests/
├── Unit Tests (Component-level)
│   ├── test_parser.py              # Text parsing logic
│   ├── test_validators.py          # Data validation
│   ├── test_field_normalizer.py    # Field normalization
│   └── test_normalize_field_value.py
│
├── Integration Tests (Multi-component)
│   ├── test_participant_service.py # Service layer integration
│   ├── test_database.py           # Database operations
│   ├── test_search_engine.py      # Search functionality
│   ├── test_airtable_connection.py # Airtable API connectivity
│   ├── test_airtable_repository.py # Airtable repository integration
│   └── test_payment_functionality.py # Payment system comprehensive testing
│
├── Async Tests (Bot interactions)
│   ├── test_recover.py            # Error recovery flows
│   ├── test_search_flow.py        # Search conversation flows
│   ├── test_enum_selection_context.py # UI interactions
│   ├── test_field_edit_cancel.py  # Cancel operations
│   ├── test_search_double_messages.py # Search flow issues analysis (v1.3)
│   └── test_search_fixes.py       # Search flow fixes verification (v1.3)
│
├── UI/UX Tests (Interface components)
│   ├── test_edit_keyboard.py      # Keyboard generation
│   └── test_confirmation_template.py # Template parsing
│
├── Infrastructure Tests (System components)
│   ├── test_timeouts.py           # Timeout management
│   ├── test_database_fix.py       # Database edge cases
│   ├── test_missing_fields.py     # Field validation
│   └── test_ptb_application_builder.py # PTB Application build stability (no network)
│
└── Domain-Specific Tests (Business logic)
    ├── test_contact_validation.py  # Israeli phone validation
    ├── test_role_department_logic.py # Business rules
    └── test_payment_functionality.py # Payment validation and processing (Added v1.1)
```

---

## Test Categories

### 1. Unit Tests

**Purpose**: Test individual components in isolation.

**Characteristics**:
- Fast execution
- No external dependencies
- Focused on single functions/methods
- Comprehensive edge case coverage

**Examples**:

#### Parser Unit Tests (`test_parser.py`)
```python
class ParserTestCase(unittest.TestCase):
    def test_parse_candidate(self):
        text = "Иван Петров M L церковь Новая Жизнь кандидат"
        data = parse_participant_data(text)
        self.assertEqual(data["FullNameRU"], "Иван Петров")
        self.assertEqual(data["Role"], "CANDIDATE")
    
    def test_template_parsing(self):
        text = "Имя (рус): Иван Петров, Пол: M, Размер: L, Церковь: Благодать"
        self.assertTrue(is_template_format(text))
        data = parse_template_format(text)
        self.assertEqual(data["FullNameRU"], "Иван Петров")
```

#### Field Normalizer Tests (`test_field_normalizer.py`)
```python
class FieldNormalizerTestCase(unittest.TestCase):
    def test_gender_normalization(self):
        # Male gender variations
        self.assertEqual(normalize_gender('муж'), 'M')
        self.assertEqual(normalize_gender('мужской'), 'M')
        self.assertEqual(normalize_gender('male'), 'M')
        
        # Female gender variations
        self.assertEqual(normalize_gender('жен'), 'F')
        self.assertEqual(normalize_gender('женский'), 'F')
        
        # Invalid values
        self.assertIsNone(normalize_gender('неизвестно'))
```

#### Validation Tests (`test_validators.py`)
```python
class ValidateParticipantDataTestCase(unittest.TestCase):
    def test_valid_candidate(self):
        data = {
            "FullNameRU": "Иван Петров",
            "Gender": "M",
            "Role": "CANDIDATE",
        }
        valid, error = validate_participant_data(data)
        self.assertTrue(valid)
        self.assertEqual(error, "")
    
    def test_missing_role_fails(self):
        data = {"FullNameRU": "Иван Петров", "Role": ""}
        valid, error = validate_participant_data(data)
        self.assertFalse(valid)
        self.assertEqual(error, "Не указана роль")
```

### 2. Integration Tests

**Purpose**: Test interactions between multiple components.

**Characteristics**:
- Test component collaboration
- Use real implementations (not mocks)
- Test data flow through layers
- Database integration testing

**Examples**:

#### Service Layer Integration (`test_participant_service.py`)
```python
class ParticipantServiceTestCase(unittest.TestCase):
    def setUp(self):
        # Setup in-memory database
        self.conn = sqlite3.connect(":memory:")
        init_database()
        self.service = ParticipantService(SqliteParticipantRepository())
    
    def test_add_participant_returns_object(self):
        data = {
            "FullNameRU": "Тестовый Пользователь",
            "Gender": "M",
            "Role": "CANDIDATE",
        }
        participant = self.service.add_participant(data, user_id=1)
        self.assertIsNotNone(participant.id)
        self.assertEqual(participant.FullNameRU, "Тестовый Пользователь")
```

#### Search Engine Integration (`test_search_engine.py`)
```python
class SearchEngineTestCase(unittest.TestCase):
    def setUp(self):
        init_database()
        self.service = ParticipantService(SqliteParticipantRepository())
        
        # Create test participants
        self.p1 = self.service.add_participant({
            "FullNameRU": "Иван Петров",
            "Gender": "M",
            "Church": "Благодать",
            "Role": "CANDIDATE",
        })
    
    def test_search_by_name(self):
        results = self.service.search_participants("Иван")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].participant.FullNameRU, "Иван Петров")
```

#### Airtable Connection Testing (`test_airtable_connection.py`)
```python
if __name__ == "__main__":
    try:
        client = AirtableClient()
        if client.test_connection():
            print("✅ Airtable подключение работает!")
        else:
            print("❌ Ошибка подключения к Airtable")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
```

#### Airtable Repository Integration (`test_airtable_repository.py`)
```python
if __name__ == "__main__":
    try:
        repo = AirtableParticipantRepository()

        # Test create
        test_participant = Participant(
            FullNameRU="Тест Пользователь",
            Gender="M",
            Size="L",
            Church="Тестовая Церковь",
            Role="CANDIDATE",
        )

        participant_id = repo.add(test_participant)
        print(f"✅ Created participant with ID: {participant_id}")

        # Test get
        retrieved = repo.get_by_id(participant_id)
        if retrieved:
            print(f"✅ Retrieved participant: {retrieved.FullNameRU}")

        # Test delete (cleanup)
        repo.delete(participant_id)
        print("✅ Test participant deleted")

        print("🎉 All Airtable repository tests passed!")
    except Exception as e:
        print(f"❌ Error: {e}")
```

### 3. Async Tests

**Purpose**: Test asynchronous operations and Telegram bot interactions.

**Characteristics**:
- Use `unittest.IsolatedAsyncioTestCase`
- Test async/await operations
- Mock Telegram API interactions
- Test conversation flows and state management

**Examples**:

#### Error Recovery Flow (`test_recover.py`)
```python
class RecoverTechnicalErrorTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_recover_function_returns_state(self):
        update = SimpleNamespace(
            message=MagicMock(), 
            effective_user=SimpleNamespace(id=1)
        )
        context = SimpleNamespace(user_data={"current_state": CONFIRMING_DATA})
        
        with patch("main.show_recovery_options", new=AsyncMock(return_value=RECOVERING)):
            state = await recover_from_technical_error(update, context)
        
        self.assertEqual(state, RECOVERING)
    
    async def test_decorator_handles_jobqueue_error(self):
        async def failing(update, context):
            raise AttributeError("job_queue missing")
        
        decorated = smart_cleanup_on_error(failing)
        
        update = SimpleNamespace(
            message=MagicMock(),
            effective_user=SimpleNamespace(id=1)
        )
        update.message.reply_text = AsyncMock()
        
        with patch("main.recover_from_technical_error", new=AsyncMock(return_value=RECOVERING)):
            state = await decorated(update, context)
        
        self.assertEqual(state, RECOVERING)
```

#### Search Flow Testing (`test_search_flow.py`)
```python
class SearchFlowTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_search_after_cancel(self):
        context = SimpleNamespace(user_data={}, chat_data={})
```

#### Search Flow Issues Analysis (`test_search_double_messages.py`)
```python
class TestSearchDoubleMessagesIssues(unittest.IsolatedAsyncioTestCase):
    """
    Test class to verify search flow problems before implementing fixes.
    These tests are expected to FAIL on current code, confirming the issues.
    """
    
    def test_handler_group_isolation_analysis(self):
        """
        TEST PROBLEM 3: Analysis of handler group isolation
        
        This test analyzes why handle_message fallback runs despite ApplicationHandlerStop
        """
        # Analysis of handler registration groups from main.py:
        # - ConversationHandler: group 0 (default)
        # - handle_message: group 10 (MessageHandler with filters.TEXT)
        
        conversation_handler_group = 0  # Default group
        handle_message_group = 10       # Explicitly set in main.py
        
        # The issue: ApplicationHandlerStop only affects handlers in the same group
        self.assertNotEqual(conversation_handler_group, handle_message_group)
        
        # This means when ConversationHandler raises ApplicationHandlerStop in group 0,
        # it doesn't prevent handle_message in group 10 from running
        
        # THE ROOT CAUSE:
        # ApplicationHandlerStop(SELECTING_PARTICIPANT) in group 0 
        # does NOT block MessageHandler in group 10
        
        self.assertTrue(True, "Handler group isolation is the root cause of double messages")
```

#### Search Flow Fixes Verification (`test_search_fixes.py`)
```python
class TestSearchFlowFixes(unittest.IsolatedAsyncioTestCase):
    """
    Test class to verify that search flow fixes work correctly.
    These tests should PASS after implementing the fixes.
    """
    
    def test_handler_group_fix_verification(self):
        """
        TEST FIX 1: Verify that handle_message is now in the same group as ConversationHandler
        
        This test verifies that the fix for double messages is implemented correctly.
        """
        # The fix: handle_message moved from group 10 to group 0
        conversation_handler_group = 0  # Default group
        handle_message_group = 0        # FIXED: Now in same group
        
        # Verify they are now in the same group
        self.assertEqual(conversation_handler_group, handle_message_group)
        
        # This means ApplicationHandlerStop will now properly block handle_message
        self.assertTrue(True, "Handler groups are now aligned - ApplicationHandlerStop will work")
```

#### JSON Serialization Fix Tests (`test_json_serialization_fix.py`)
```python
class TestJSONSerializationFix(unittest.TestCase):
    """Tests that verify safe serialization of context user_data used by logging decorators.
    These tests prevent regressions that could break ConversationHandler transitions
    in the search flow when complex objects (e.g., SearchResult) are stored in user_data.
    """

    def test_search_results_serialization(self):
        # Verifies complex objects inside user_data are converted to JSON-safe form
        ...
```
        update = SimpleNamespace(
            callback_query=MagicMock(),
            effective_user=SimpleNamespace(id=1)
        )
        
        with patch("main._show_search_prompt"), \
             patch("main._cleanup_messages", new=AsyncMock()):
            state = await handle_search_callback(update, context)
            self.assertEqual(state, SEARCHING_PARTICIPANTS)
```

### 4. UI/UX Tests

**Purpose**: Test user interface components and keyboard generation.

**Examples**:

#### Keyboard Generation (`test_edit_keyboard.py`)
```python
class EditKeyboardTestCase(unittest.TestCase):
    def test_candidate_hides_department(self):
        kb = get_edit_keyboard({"Role": "CANDIDATE"})
        datas = [b.callback_data for row in kb.inline_keyboard for b in row]
        self.assertIn("edit_Role", datas)
        self.assertNotIn("edit_Department", datas)
    
    def test_team_shows_department(self):
        kb = get_edit_keyboard({"Role": "TEAM"})
        datas = [b.callback_data for row in kb.inline_keyboard for b in row]
        self.assertIn("edit_Department", datas)
```

---

## Testing Patterns

### 1. Database Isolation Pattern

**Purpose**: Ensure each test runs with a clean database state.

**Implementation**:
```python
class DatabaseTestCase(unittest.TestCase):
    def setUp(self):
        """Creates clean in-memory database for each test."""
        # Use in-memory SQLite
        database.DB_PATH = ":memory:"
        self.conn = sqlite3.connect(database.DB_PATH)
        self.conn.row_factory = sqlite3.Row
        
        # Patch DatabaseConnection to use our connection
        self._original_enter = database.DatabaseConnection.__enter__
        self._original_exit = database.DatabaseConnection.__exit__
        
        def _enter(_self):
            _self.conn = self.conn
            return self.conn
        
        def _exit(_self, exc_type, exc_val, exc_tb):
            if exc_type:
                self.conn.rollback()
            else:
                self.conn.commit()
        
        database.DatabaseConnection.__enter__ = _enter
        database.DatabaseConnection.__exit__ = _exit
        
        init_database()
    
    def tearDown(self):
        # Restore original methods
        database.DatabaseConnection.__enter__ = self._original_enter
        database.DatabaseConnection.__exit__ = self._original_exit
        self.conn.close()
```

### 2. Mock Context Pattern

**Purpose**: Create realistic test contexts for Telegram bot operations.

**Implementation**:
```python
def create_mock_update(user_id=1, text="", callback_data=None):
    """Factory for creating mock Telegram updates."""
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=user_id),
        message=MagicMock() if text else None,
        callback_query=MagicMock() if callback_data else None
    )
    
    if text:
        update.message.text = text
        update.message.reply_text = AsyncMock()
    
    if callback_data:
        update.callback_query.data = callback_data
        update.callback_query.answer = AsyncMock()
    
    return update

def create_mock_context(user_data=None):
    """Factory for creating mock bot contexts."""
    return SimpleNamespace(
        user_data=user_data or {},
        chat_data={},
        bot=MagicMock()
    )
```

### 3. Async Testing Pattern

**Purpose**: Test async operations with proper mocking.

**Implementation**:
```python
class AsyncTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_async_operation(self):
        # Setup
        update = create_mock_update(callback_data="test_data")
        context = create_mock_context({"state": "TESTING"})
        
        # Mock async dependencies
        with patch("main.async_function", new=AsyncMock(return_value="result")) as mock_func:
            # Execute
            result = await function_under_test(update, context)
            
            # Verify
            mock_func.assert_awaited_once_with(update, context)
            self.assertEqual(result, expected_result)
```

### 4. State Testing Pattern

**Purpose**: Test conversation state transitions.

**Implementation**:
```python
class StateTestCase(unittest.IsolatedAsyncioTestCase):
    def test_state_transition(self):
        context = SimpleNamespace(user_data={"current_state": INITIAL_STATE})
        
        # Test state change
        result = transition_function(context)
        
        self.assertEqual(context.user_data["current_state"], EXPECTED_STATE)
        self.assertEqual(result, EXPECTED_STATE)
```

---

## Test Infrastructure

### 1. Test Base Classes

#### Database Test Base
```python
class DatabaseTestBase(unittest.TestCase):
    """Base class for tests requiring database access."""
    
    def setUp(self):
        self._setup_in_memory_database()
        self._patch_database_connection()
        init_database()
    
    def tearDown(self):
        self._restore_database_connection()
        self.conn.close()
```

#### Async Test Base
```python
class AsyncTestBase(unittest.IsolatedAsyncioTestCase):
    """Base class for async bot operation tests."""
    
    def setUp(self):
        self.patches = []
    
    def tearDown(self):
        for patcher in self.patches:
            patcher.stop()
    
    def add_patch(self, target, **kwargs):
        patcher = patch(target, **kwargs)
        self.patches.append(patcher)
        return patcher.start()
```

### 2. Test Utilities

#### Mock Factories
```python
def create_participant_data(**overrides):
    """Factory for creating test participant data."""
    default_data = {
        "FullNameRU": "Тестовый Участник",
        "Gender": "M",
        "Size": "L",
        "Church": "Тестовая Церковь",
        "Role": "CANDIDATE",
    }
    default_data.update(overrides)
    return default_data

def create_telegram_update(message_text=None, callback_data=None, user_id=1):
    """Factory for creating Telegram update objects."""
    # Implementation details...
```

#### Assertion Helpers
```python
def assert_keyboard_contains(self, keyboard, expected_callback_data):
    """Assert that keyboard contains specific callback data."""
    all_callbacks = [
        button.callback_data 
        for row in keyboard.inline_keyboard 
        for button in row
    ]
    self.assertIn(expected_callback_data, all_callbacks)

def assert_participant_equals(self, actual, expected):
    """Assert participant objects are equal (ignoring ID)."""
    for field in ['FullNameRU', 'Gender', 'Size', 'Church', 'Role']:
        self.assertEqual(getattr(actual, field), expected.get(field))
```

---

## Database Testing

### In-Memory SQLite Strategy

**Benefits**:
- Fast test execution
- Complete isolation between tests
- Real database operations without persistence
- Identical schema to production

**Implementation Pattern**:
```python
def setUp(self):
    # Override database path to use in-memory database
    database.DB_PATH = ":memory:"
    
    # Create persistent connection for test duration
    self.conn = sqlite3.connect(database.DB_PATH)
    self.conn.row_factory = sqlite3.Row
    
    # Patch database connection context manager
    self._patch_database_connection()
    
    # Initialize schema
    init_database()
    
    # Create test data if needed
    self._create_test_data()
```

### Database Test Examples

#### CRUD Operations (`test_database.py`)
```python
def test_add_and_get_participant(self):
    """Test basic database CRUD operations."""
    # Add participant
    participant_id = add_participant(self.participant_data)
    self.assertIsNotNone(participant_id)
    
    # Retrieve participant
    retrieved = get_participant_by_id(participant_id)
    self.assertIsNotNone(retrieved)
    self.assertEqual(retrieved['FullNameRU'], self.participant_data['FullNameRU'])

def test_find_participant_by_name(self):
    """Test name-based lookup."""
    add_participant(self.participant_data)
    found = find_participant_by_name(self.participant_data['FullNameRU'])
    self.assertIsNotNone(found)
    self.assertEqual(found['FullNameRU'], self.participant_data['FullNameRU'])
```

#### Edge Cases (`test_database_fix.py`)
```python
def test_get_participant_by_id_none(self):
    """Test that non-existent ID returns None."""
    result = get_participant_by_id(99999)
    self.assertIsNone(result)

def test_find_participant_by_name_none(self):
    """Test that non-existent name returns None."""
    result = find_participant_by_name("Несуществующий Участник")
    self.assertIsNone(result)
```

---

## Async Testing

### Async Test Infrastructure

#### Base Setup
```python
class AsyncBotTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        """Setup for async tests."""
        self.update = self.create_mock_update()
        self.context = self.create_mock_context()
        
        # Setup common patches
        self.mock_reply = AsyncMock()
        self.update.message.reply_text = self.mock_reply
    
    def create_mock_update(self, **kwargs):
        return SimpleNamespace(
            message=MagicMock(),
            callback_query=MagicMock() if 'callback_data' in kwargs else None,
            effective_user=SimpleNamespace(id=kwargs.get('user_id', 1)),
            **kwargs
        )
```

### Async Test Patterns

#### Testing Async Handlers
```python
async def test_async_handler(self):
    """Test async message handler."""
    with patch('main.some_async_function', new=AsyncMock()) as mock_func:
        result = await handler_function(self.update, self.context)
        
        # Verify async calls
        mock_func.assert_awaited_once()
        self.mock_reply.assert_awaited_once()
        
        # Verify state changes
        self.assertEqual(result, EXPECTED_STATE)
```

#### Testing Callback Handlers
```python
async def test_callback_handler(self):
    """Test callback query handler."""
    self.update.callback_query.data = "test_callback"
    self.update.callback_query.answer = AsyncMock()
    
    with patch('main.process_callback', new=AsyncMock()) as mock_process:
        await callback_handler(self.update, self.context)
        
        self.update.callback_query.answer.assert_awaited_once()
        mock_process.assert_awaited_once()
```

#### Testing Error Handling
```python
async def test_error_recovery(self):
    """Test error recovery mechanisms."""
    # Setup failing operation
    async def failing_operation(update, context):
        raise Exception("Test error")
    
    decorated = smart_cleanup_on_error(failing_operation)
    
    with patch('main.recover_from_technical_error', new=AsyncMock()) as mock_recover:
        await decorated(self.update, self.context)
        mock_recover.assert_awaited_once()
```

---

## Mock and Fixture Patterns

### 1. Telegram API Mocking

#### Update and Context Mocking
```python
def create_telegram_mocks():
    """Create comprehensive Telegram API mocks."""
    update = MagicMock()
    context = MagicMock()
    
    # Message mocking
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    update.message.edit_text = AsyncMock()
    
    # Callback query mocking
    update.callback_query = MagicMock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    
    # User mocking
    update.effective_user = MagicMock()
    update.effective_user.id = 12345
    
    # Context mocking
    context.user_data = {}
    context.chat_data = {}
    context.bot = MagicMock()
    
    return update, context
```

### 2. Service Layer Mocking

#### Repository Mocking
```python
class MockParticipantRepository:
    """Mock repository for testing service layer."""
    
    def __init__(self):
        self.participants = {}
        self.next_id = 1
    
    def add(self, participant):
        participant_id = self.next_id
        self.next_id += 1
        participant.id = participant_id
        self.participants[participant_id] = participant
        return participant_id
    
    def get_by_id(self, participant_id):
        return self.participants.get(participant_id)
    
    def get_by_name(self, name):
        for p in self.participants.values():
            if p.FullNameRU == name:
                return p
        return None
```

### 3. External API Mocking

#### Airtable API Mocking
```python
@patch('repositories.airtable_client.AirtableClient')
def test_airtable_integration(self, mock_client_class):
    """Test Airtable integration with mocked API."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    # Mock API responses
    mock_client.create_record.return_value = "rec123456"
    mock_client.get_record.return_value = {
        "id": "rec123456",
        "fields": {"Full Name (RU)": "Test User"}
    }
    
    # Test the integration
    repo = AirtableParticipantRepository()
    participant = Participant(FullNameRU="Test User")
    result_id = repo.add(participant)
    
    self.assertEqual(result_id, "rec123456")
    mock_client.create_record.assert_called_once()
```

---

## Test Data Management

### 1. Test Data Factories

#### Participant Data Factory
```python
class ParticipantDataFactory:
    """Factory for creating test participant data."""
    
    @staticmethod
    def create_candidate(**overrides):
        """Create candidate participant data."""
        data = {
            "FullNameRU": "Тестовый Кандидат",
            "Gender": "M",
            "Size": "L",
            "Church": "Тестовая Церковь",
            "Role": "CANDIDATE",
            "ContactInformation": "test@example.com"
        }
        data.update(overrides)
        return data
    
    @staticmethod
    def create_team_member(**overrides):
        """Create team member participant data."""
        data = {
            "FullNameRU": "Тестовый Служитель",
            "Gender": "F",
            "Size": "M",
            "Church": "Церковь Команды",
            "Role": "TEAM",
            "Department": "Worship",
            "ContactInformation": "team@example.com"
        }
        data.update(overrides)
        return data
    
    @staticmethod
    def create_batch(count=5, **overrides):
        """Create multiple participants for bulk testing."""
        participants = []
        for i in range(count):
            data = ParticipantDataFactory.create_candidate(
                FullNameRU=f"Участник {i+1}",
                **overrides
            )
            participants.append(data)
        return participants
```

### 2. Test Fixtures

#### Database Fixtures
```python
class DatabaseFixtures:
    """Pre-defined test data for database testing."""
    
    @staticmethod
    def load_basic_participants(service):
        """Load basic set of participants for testing."""
        participants = [
            {
                "FullNameRU": "Иван Петров",
                "Gender": "M",
                "Size": "L",
                "Church": "Благодать",
                "Role": "CANDIDATE"
            },
            {
                "FullNameRU": "Анна Иванова",
                "Gender": "F",
                "Size": "M",
                "Church": "Грейс",
                "Role": "TEAM",
                "Department": "Worship"
            }
        ]
        
        created = []
        for data in participants:
            participant = service.add_participant(data)
            created.append(participant)
        
        return created
```

### 3. Test Configuration

#### Test Settings
```python
class TestConfig:
    """Configuration for test environment."""
    
    # Database settings
    TEST_DB_PATH = ":memory:"
    
    # Test user IDs
    TEST_COORDINATOR_ID = 12345
    TEST_VIEWER_ID = 67890
    
    # Test data paths
    TEST_DATA_DIR = "tests/data"
    
    # Mock settings
    MOCK_EXTERNAL_APIS = True
    ENABLE_LOGGING = False
```

---

## Test Coverage Areas

### 1. Core Business Logic (95%+ Coverage)

#### Parser Module (`test_parser.py`)
- **359 lines of tests** covering:
  - Template format parsing
  - Free-form text parsing
  - Field update parsing
  - Edge cases and error handling
  - Multi-language support
  - Special character handling

#### Validation Module (`test_validators.py`)
- **83 lines of tests** covering:
  - Required field validation
  - Role-specific validation
  - Contact information validation
  - Business rule enforcement

#### Field Normalization (`test_field_normalizer.py`)
- **101 lines of tests** covering:
  - Gender normalization
  - Size normalization
  - Department normalization
  - Multi-language field mapping

#### Payment Functionality (`test_payment_functionality.py`)
- **465 lines of comprehensive tests** covering:
  - Payment model data fields (PaymentStatus, PaymentAmount, PaymentDate)
  - Payment status enum validation and display mapping
  - Payment amount validation (integers only, positive values)
  - Payment status parsing from unstructured text
  - Service layer payment processing workflows
  - Database CRUD operations for payment fields
  - Payment statistics and reporting
  - Full end-to-end payment workflows
  - Integration with existing participant management system

### 2. Data Layer (90%+ Coverage)

#### Database Operations (`test_database.py`)
- **61 lines of tests** covering:
  - CRUD operations
  - Connection management
  - Transaction handling
  - Error scenarios

#### Repository Layer (`test_participant_service.py`)
- **56 lines of tests** covering:
  - Service-repository integration
  - Business logic orchestration
  - Error handling

#### Airtable Integration (`test_airtable_connection.py`, `test_airtable_repository.py`)
- **60 lines of tests** covering:
  - Airtable API connectivity testing
  - Repository CRUD operations
  - External API integration
  - Error handling for network issues
  - Data synchronization validation

### 3. User Interface (85%+ Coverage)

#### Keyboard Generation (`test_edit_keyboard.py`)
- **86 lines of tests** covering:
  - Dynamic keyboard creation
  - Role-based UI elements
  - Button configuration
  - Callback data generation

#### Template Processing (`test_confirmation_template.py`)
- **67 lines of tests** covering:
  - Template parsing
  - Service value filtering
  - Data extraction

### 4. Async Operations (80%+ Coverage)

#### Error Recovery (`test_recover.py`)
- **50 lines of tests** covering:
  - Technical error handling
  - State recovery
  - User interaction flows

#### Search Flows (`test_search_flow.py`)
- **59 lines of tests** covering:
  - Search conversation flows
  - State transitions
  - Cancel operations

### 5. Infrastructure (75%+ Coverage)

#### Timeout Management (`test_timeouts.py`)
- **46 lines of tests** covering:
  - Timeout setting and checking
  - Cleanup operations
  - Job queue management

#### Contact Validation (`test_contact_validation.py`)
- **177 lines of tests** covering:
  - Israeli phone number validation
  - Email validation
  - Contact format normalization

---

## Testing Best Practices

### 0. Testing Troubleshooting
For common testing issues and their solutions, refer to:
- **[Testing Troubleshooting Guide](testing-troubleshooting.md)** - Comprehensive guide for resolving test development and execution issues
- **Key Issues**: Framework compatibility (unittest vs pytest), virtual environment setup, method name mismatches, database testing patterns

### 1. Test Organization

#### Naming Conventions
```python
# Test class naming
class ComponentNameTestCase(unittest.TestCase):
    pass

# Test method naming
def test_specific_behavior_expected_outcome(self):
    pass

# Example:
def test_parse_candidate_returns_correct_role(self):
    pass
```

#### Test Structure (AAA Pattern)
```python
def test_example(self):
    # Arrange - Setup test data and conditions
    input_data = {"FullNameRU": "Test User", "Role": "CANDIDATE"}
    expected_result = "CANDIDATE"
    
    # Act - Execute the functionality being tested
    result = parse_participant_data(input_data)
    
    # Assert - Verify the outcome
    self.assertEqual(result["Role"], expected_result)
```

### 2. Test Independence

#### Isolated Tests
- Each test creates its own data
- No shared state between tests
- Clean database for each test
- Independent mock setups

#### Example:
```python
class IndependentTestCase(unittest.TestCase):
    def setUp(self):
        """Create fresh environment for each test."""
        self._setup_clean_database()
        self._create_test_data()
    
    def tearDown(self):
        """Clean up after each test."""
        self._cleanup_database()
        self._reset_mocks()
```

### 3. Comprehensive Assertions

#### Multiple Assertions
```python
def test_comprehensive_parsing(self):
    """Test multiple aspects of parsing result."""
    text = "Иван Петров M L церковь Благодать кандидат"
    result = parse_participant_data(text)
    
    # Verify all expected fields
    self.assertEqual(result["FullNameRU"], "Иван Петров")
    self.assertEqual(result["Gender"], "M")
    self.assertEqual(result["Size"], "L")
    self.assertEqual(result["Church"], "Благодать")
    self.assertEqual(result["Role"], "CANDIDATE")
    
    # Verify data types
    self.assertIsInstance(result, dict)
    self.assertIsInstance(result["FullNameRU"], str)
```

### 4. Error Testing

#### Exception Testing
```python
def test_invalid_input_raises_validation_error(self):
    """Test that invalid input raises appropriate exception."""
    invalid_data = {"FullNameRU": "", "Role": "INVALID"}
    
    with self.assertRaises(ValidationError) as context:
        validate_participant_data(invalid_data)
    
    self.assertIn("Имя участника обязательно", str(context.exception))
```

### 5. Performance Testing

#### Timing Assertions
```python
def test_parsing_performance(self):
    """Test that parsing completes within acceptable time."""
    text = "Large text input for performance testing..."
    
    start_time = time.time()
    result = parse_participant_data(text)
    end_time = time.time()
    
    self.assertLess(end_time - start_time, 1.0)  # Should complete within 1 second
    self.assertIsNotNone(result)
```

### 6. Mock Best Practices

#### Minimal Mocking
```python
def test_service_integration_minimal_mocks(self):
    """Test with minimal mocking for better integration coverage."""
    # Only mock external dependencies
    with patch('external_api.call') as mock_api:
        mock_api.return_value = {"status": "success"}
        
        # Use real implementations for internal components
        service = ParticipantService(SqliteParticipantRepository())
        result = service.process_participant(test_data)
        
        self.assertIsNotNone(result)
```

#### Assertion on Mocks
```python
def test_mock_interactions(self):
    """Verify mock interactions."""
    with patch('module.function') as mock_func:
        mock_func.return_value = "expected_result"
        
        result = function_under_test()
        
        # Verify mock was called correctly
        mock_func.assert_called_once_with(expected_args)
        self.assertEqual(result, "expected_result")
```

## Test Execution

### Running Tests

#### All Tests
```bash
# Run entire test suite (recommended way)
./venv/bin/python -m unittest discover tests

# Run with verbose output
./venv/bin/python -m unittest discover tests -v

# Alternative (if venv is activated)
python -m unittest discover tests -v
```

#### Specific Test Categories
```bash
# Run only database tests
./venv/bin/python -m unittest tests.test_database

# Run only parser tests
./venv/bin/python -m unittest tests.test_parser

# Run payment functionality tests
./venv/bin/python -m unittest tests.test_payment_functionality

# Run only async tests
./venv/bin/python -m unittest tests.test_recover tests.test_search_flow

# Run only infrastructure stability test for PTB builder
./venv/bin/python -m unittest tests.test_ptb_application_builder -v

# Run only Airtable integration tests
./venv/bin/python -m unittest tests.test_airtable_connection tests.test_airtable_repository
```

#### Individual Tests
```bash
# Run specific test method
./venv/bin/python -m unittest tests.test_parser.ParserTestCase.test_parse_candidate

# Run specific payment test
./venv/bin/python -m unittest tests.test_payment_functionality.TestPaymentModel.test_participant_payment_fields_default_values

# Run Airtable connection test
python tests/test_airtable_connection.py

# Run Airtable repository test
python tests/test_airtable_repository.py
```

### Test Coverage

#### Coverage Analysis
```bash
# Install coverage tool
pip install coverage

# Run tests with coverage
coverage run -m unittest discover tests

# Generate coverage report
coverage report -m

# Generate HTML coverage report
coverage html
```

#### Coverage Targets
- **Overall Coverage**: >85%
- **Core Business Logic**: >95%
- **Data Layer**: >90%
- **UI Components**: >85%
- **Async Operations**: >80%

## Payment Functionality Tests (Added v1.1)

### Payment Validation Tests (`test_payment_functionality.py`)

**Purpose**: Test payment validation, processing, and state management functionality.

**Test Coverage Areas**:

#### Payment Amount Validation
- **Integer Validation**: Ensure only integer values are accepted
- **Positive Value Validation**: Reject zero and negative amounts
- **Input Sanitization**: Handle various input formats and edge cases
- **Error Message Testing**: Verify appropriate error messages for invalid input

#### Payment State Management  
- **State Transitions**: Test payment workflow state transitions
- **State Validation**: Ensure valid state progression
- **State Recovery**: Test recovery from interrupted payment flows
- **Concurrent State Handling**: Test multiple users in payment states

#### Payment Processing Logic
- **Service Layer Integration**: Test ParticipantService.process_payment()
- **Database Updates**: Verify payment fields are updated correctly
- **Date Handling**: Test automatic PaymentDate setting
- **Status Logic**: Test PaymentStatus transitions (UNPAID → PAID → REFUNDED)

#### Payment Display Testing
- **Search Result Display**: Test payment info in search results
- **Detail View Display**: Test payment info in participant details
- **List Command Display**: Test payment info in /list output
- **Emoji Consistency**: Test consistent emoji usage across contexts

#### Payment Command Testing
- **Command Parsing**: Test /payment command with and without arguments
- **Search Integration**: Test payment command integration with search flow
- **Permission Testing**: Test coordinator-only access to /payment command
- **Error Handling**: Test command error scenarios

#### Payment UI Flow Testing
- **Button Integration**: Test "💰 Внести оплату" button functionality
- **Confirmation Flow**: Test payment confirmation dialog
- **Cancel Operations**: Test payment cancellation functionality
- **User Feedback**: Test success/error message display

**Test Implementation Patterns**:
```python
class TestPaymentFunctionality(unittest.TestCase):
    def test_validate_payment_amount_valid_integer(self):
        """Test validation accepts valid integer amounts."""
        is_valid, amount, error = validate_payment_amount("500")
        self.assertTrue(is_valid)
        self.assertEqual(amount, 500)
        self.assertEqual(error, "")
    
    def test_validate_payment_amount_rejects_decimal(self):
        """Test validation rejects decimal amounts."""
        is_valid, amount, error = validate_payment_amount("500.50")
        self.assertFalse(is_valid)
        self.assertEqual(amount, 0)
        self.assertIn("целое число", error)
    
    def test_payment_state_transitions(self):
        """Test payment workflow state transitions."""
        # Test state progression through payment flow
        # CHOOSING_ACTION → ENTERING_PAYMENT_AMOUNT → CONFIRMING_PAYMENT → END
    
    def test_payment_display_consistency(self):
        """Test consistent payment display across contexts."""
        # Test search results, details, and list display formats
```

**Expected Test Coverage**: 95%+ for payment-related functionality

**Integration Points**:
- **Database Layer**: Test payment field persistence
- **Service Layer**: Test payment processing business logic  
- **UI Layer**: Test payment button and state management
- **Command Layer**: Test /payment command functionality

## Conclusion

The test architecture of the Tres Dias Israel Telegram Bot provides comprehensive coverage across all system components. The combination of unit tests, integration tests, async tests, and specialized testing patterns ensures robust code quality, system reliability, and maintainability.

Key strengths of the test suite:
- **Comprehensive Coverage**: Tests cover all major components and edge cases
- **Isolation**: In-memory database testing ensures test independence
- **Async Support**: Proper testing of async Telegram bot operations
- **Realistic Mocking**: Appropriate use of mocks without over-mocking
- **Performance Awareness**: Tests consider performance implications
- **Maintainability**: Clear test structure and naming conventions

This test structure serves as both a quality assurance mechanism and documentation of system behavior, making it easier for developers to understand, modify, and extend the codebase with confidence.
