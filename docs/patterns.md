# Design Patterns Documentation

**Version**: 1.0  
**Last Updated**: August 13, 2025  

## Overview

This document describes the design patterns and architectural patterns implemented in the Tres Dias Israel Telegram Bot project. These patterns ensure maintainability, testability, extensibility, and separation of concerns throughout the codebase.

## Table of Contents

1. [Architectural Patterns](#architectural-patterns)
2. [Structural Patterns](#structural-patterns)
3. [Behavioral Patterns](#behavioral-patterns)
4. [Creational Patterns](#creational-patterns)
5. [Cross-cutting Concern Patterns](#cross-cutting-concern-patterns)
6. [Integration Patterns](#integration-patterns)
7. [Data Processing Patterns](#data-processing-patterns)
8. [Pattern Interactions](#pattern-interactions)

---

## Architectural Patterns

### 1. Layered Architecture

**Purpose**: Organizes the application into horizontal layers with clear responsibilities and dependencies flowing downward.

**Implementation**:
```
Presentation Layer    → main.py (Telegram handlers)
Business Logic Layer → services/ (ParticipantService)
Data Access Layer    → repositories/ (Repository implementations)
Infrastructure Layer → utils/, database.py
```

**Benefits**:
- Clear separation of concerns
- Easy to test individual layers
- Technology-agnostic business logic
- Maintainable and scalable architecture

**Example**:
```python
# Presentation Layer (main.py)
@require_role("coordinator")
async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Delegates to business layer
    result = participant_service.add_participant(data, user_id)

# Business Layer (services/participant_service.py)
def add_participant(self, data: Dict, user_id: Optional[int] = None) -> Participant:
    # Business logic: validation, duplicate checking
    existing = self.check_duplicate(data.get("FullNameRU", ""), user_id)
    # Delegates to data layer
    new_id = self.repository.add(new_participant)
```

### 2. Clean Architecture

**Purpose**: Ensures dependencies point inward toward the domain, making the core business logic independent of external concerns.

**Implementation**:
```
Domain Models (center) ← services/ ← repositories/ ← external APIs
```

**Key Principles**:
- Domain models (`Participant`) have no external dependencies
- Business logic in services doesn't depend on infrastructure
- Repository interfaces defined in business layer, implemented in infrastructure

**Example**:
```python
# Domain Model (models/participant.py) - No external dependencies
@dataclass
class Participant:
    FullNameRU: str
    Gender: str = "F"
    # ... other fields

# Business Layer defines interface (repositories/participant_repository.py)
class AbstractParticipantRepository(ABC):
    @abstractmethod
    def add(self, participant: Participant) -> Union[int, str]:
        pass

# Infrastructure implements interface (repositories/participant_repository.py)
class SqliteParticipantRepository(BaseParticipantRepository):
    def add(self, participant: Participant) -> int:
        # SQLite-specific implementation
```

### 3. Domain-Driven Design (DDD)

**Purpose**: Places the domain model and business logic at the center of the application design.

**Implementation**:
- **Entities**: `Participant` dataclass represents the core domain entity
- **Value Objects**: Enums for Gender, Role, Size, Department
- **Repositories**: Abstract data access for domain entities
- **Services**: Domain services for complex business operations
- **Aggregates**: Participant as aggregate root

**Example**:
```python
# Domain Entity
@dataclass
class Participant:
    FullNameRU: str  # Identity field
    # ... other attributes

# Value Objects
class Gender(Enum):
    MALE = "M"
    FEMALE = "F"

# Domain Service
class ParticipantService:
    def check_duplicate(self, full_name_ru: str) -> Optional[Participant]:
        # Domain logic for duplicate detection
```

---

## Structural Patterns

### 1. Repository Pattern

**Purpose**: Abstracts data access logic and provides a uniform interface for accessing domain objects.

**Implementation**:
- Abstract base class: `AbstractParticipantRepository`
- Concrete implementations: `SqliteParticipantRepository`, `AirtableParticipantRepository`
- Base class with shared functionality: `BaseParticipantRepository`

**Benefits**:
- Data source abstraction
- Easy testing with mock repositories
- Swappable data storage backends
- Consistent data access interface

**Example**:
```python
# Abstract Repository Interface
class AbstractParticipantRepository(ABC):
    @abstractmethod
    def add(self, participant: Participant) -> Union[int, str]:
        pass
    
    @abstractmethod
    def get_by_id(self, participant_id: Union[int, str]) -> Optional[Participant]:
        pass

# SQLite Implementation
class SqliteParticipantRepository(BaseParticipantRepository):
    def add(self, participant: Participant) -> int:
        participant_data = asdict(participant)
        return add_participant(participant_data)

# Airtable Implementation  
class AirtableParticipantRepository(BaseParticipantRepository):
    def add(self, participant: Participant) -> str:
        record_data = self._participant_to_airtable_fields(participant)
        return self.client.create_record(record_data)
```

### 2. Adapter Pattern

**Purpose**: Allows incompatible interfaces to work together by wrapping external APIs.

**Implementation**:
- `AirtableClient` adapts the pyairtable library to project needs
- `AirtableParticipantRepository` adapts Airtable records to `Participant` objects
- Field mapping between domain model and external API schema

**Example**:
```python
class AirtableParticipantRepository(BaseParticipantRepository):
    def _participant_to_airtable_fields(self, participant: Participant) -> Dict:
        """Adapts Participant domain object to Airtable field format."""
        return {
            "Full Name (RU)": participant.FullNameRU,
            "Gender": participant.Gender,
            # ... field mapping
        }
    
    def _airtable_record_to_participant(self, record: Dict) -> Participant:
        """Adapts Airtable record to Participant domain object."""
        fields = record.get("fields", {})
        return Participant(
            id=record["id"],
            FullNameRU=fields.get("Full Name (RU)", ""),
            # ... field mapping
        )
```

### 3. Facade Pattern

**Purpose**: Provides a simplified interface to complex subsystems.

**Implementation**:
- `ParticipantService` acts as a facade for complex participant operations
- Simplifies interactions between presentation layer and multiple subsystems
- Hides complexity of parsing, validation, duplicate checking, and persistence

**Example**:
```python
class ParticipantService:
    """Facade for complex participant operations."""
    
    def add_participant(self, data: Dict, user_id: Optional[int] = None) -> Participant:
        # Coordinates multiple subsystems:
        # 1. Validation
        valid, error = validate_participant_data(data)
        if not valid:
            raise ValidationError(error)
        
        # 2. Duplicate checking
        existing = self.check_duplicate(data.get("FullNameRU", ""), user_id)
        if existing:
            raise DuplicateParticipantError(...)
        
        # 3. Persistence
        new_participant = Participant(**data)
        new_id = self.repository.add(new_participant)
        
        # 4. Logging
        self._log_participant_change(user_id, "add", data, participant_id=new_id)
        
        return new_participant
```

---

## Behavioral Patterns

### 1. Strategy Pattern

**Purpose**: Defines a family of algorithms, encapsulates each one, and makes them interchangeable.

**Implementation**:

#### Parsing Strategies
Different strategies for parsing participant data:
```python
# Strategy interface (implicit)
def parse_participant_data(text: str) -> Dict:
    if is_template_format(text):
        return parse_template_format(text)  # Template strategy
    else:
        return parse_unstructured_text(text)  # Free-form strategy

# Template parsing strategy
def parse_template_format(text: str) -> Dict:
    # Structured parsing logic
    
# Free-form parsing strategy  
def parse_unstructured_text(text: str) -> Dict:
    # Unstructured parsing logic
```

#### Repository Strategies
Different strategies for data persistence:
```python
def create_participant_repository():
    """Factory that selects repository strategy based on configuration."""
    if config.DATABASE_TYPE == "airtable":
        return AirtableParticipantRepository()  # Cloud strategy
    else:
        return SqliteParticipantRepository()    # Local strategy
```

### 2. State Pattern

**Purpose**: Allows an object to alter its behavior when its internal state changes.

**Implementation**:
- Telegram bot conversation states defined in `states.py`
- `ConversationHandler` manages state transitions
- Different handlers for different states

**Example**:
```python
# State definitions
COLLECTING_DATA = 1
FILLING_MISSING_FIELDS = 2
CONFIRMING_DATA = 3
CONFIRMING_DUPLICATE = 4
RECOVERING = 5

# State machine configuration
add_conv = ConversationHandler(
    entry_points=[CommandHandler("add", add_command)],
    states={
        COLLECTING_DATA: [
            MessageHandler(filters.TEXT, handle_partial_data)
        ],
        CONFIRMING_DATA: [
            CallbackQueryHandler(handle_save_confirmation, pattern="^confirm_save$"),
            CallbackQueryHandler(edit_field_callback, pattern="^edit_"),
        ],
        CONFIRMING_DUPLICATE: [
            CallbackQueryHandler(handle_duplicate_callback, pattern="^dup_"),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel_command)]
)
```

### 3. Template Method Pattern

**Purpose**: Defines the skeleton of an algorithm in a base class, letting subclasses override specific steps.

**Implementation**:
- `AbstractParticipantRepository` defines the interface template
- `BaseParticipantRepository` provides common validation logic
- Concrete repositories implement specific database operations

**Example**:
```python
class BaseParticipantRepository(AbstractParticipantRepository):
    """Template with shared validation logic."""
    
    def _validate_fields(self, **fields) -> None:
        """Common validation template method."""
        valid_fields = set(Participant.__annotations__.keys())
        invalid_fields = set(fields.keys()) - valid_fields
        if invalid_fields:
            raise ValueError(f"Invalid fields for Participant: {invalid_fields}")

class SqliteParticipantRepository(BaseParticipantRepository):
    """Concrete implementation following the template."""
    
    def update_fields(self, participant_id: int, **fields) -> bool:
        self._validate_fields(**fields)  # Uses template method
        # SQLite-specific implementation
```

### 4. Observer Pattern

**Purpose**: Defines a one-to-many dependency between objects so that when one object changes state, all dependents are notified.

**Implementation**:
- `UserActionLogger` observes and logs all user actions
- Service layer methods notify loggers of state changes
- Multiple loggers can observe the same events

**Example**:
```python
class ParticipantService:
    def __init__(self, repository: AbstractParticipantRepository):
        self.repository = repository
        # Observers
        self.logger = logging.getLogger("participant_changes")
        self.performance_logger = logging.getLogger("performance")
        self.user_action_logger = UserActionLogger()
    
    def add_participant(self, data: Dict, user_id: Optional[int] = None) -> Participant:
        # Perform operation
        new_id = self.repository.add(new_participant)
        
        # Notify observers
        self._log_participant_change(user_id, "add", data, participant_id=new_id)
        self.performance_logger.info(json.dumps({
            "operation": "add_participant",
            "duration": duration,
            "user_id": user_id
        }))
```

---

## Creational Patterns

### 1. Factory Pattern

**Purpose**: Creates objects without specifying their exact classes.

**Implementation**:
- `create_participant_repository()` factory function
- Runtime decision based on configuration
- Returns appropriate repository implementation

**Example**:
```python
def create_participant_repository():
    """Factory function to create the appropriate participant repository."""
    if config.DATABASE_TYPE == "airtable":
        logger.info("Using Airtable as database backend")
        return AirtableParticipantRepository()
    else:
        logger.info("Using SQLite as database backend") 
        return SqliteParticipantRepository()

# Usage in main()
participant_repository = create_participant_repository()
participant_service = ParticipantService(repository=participant_repository)
```

### 2. Dependency Injection

**Purpose**: Provides dependencies to an object rather than having it create them itself.

**Implementation**:
- `ParticipantService` receives repository through constructor injection
- Services don't create their own dependencies
- Enables easy testing and flexibility

**Example**:
```python
class ParticipantService:
    def __init__(self, repository: AbstractParticipantRepository):
        """Dependency injection - repository provided externally."""
        self.repository = repository
        self.logger = logging.getLogger("participant_changes")

# Injection at application startup
def main():
    repository = create_participant_repository()
    service = ParticipantService(repository=repository)  # Inject dependency
```

### 3. Singleton Pattern

**Purpose**: Ensures a class has only one instance and provides global access to it.

**Implementation**:
- Cache instance in `utils/cache.py`
- Logger instances are effectively singletons
- Configuration loaded once at startup

**Example**:
```python
# Cache singleton
class SimpleCache:
    def __init__(self):
        self._cache = {}
    
    def get(self, key):
        return self._cache.get(key)

# Global cache instance
cache = SimpleCache()

# Logger singleton pattern
class UserActionLogger:
    def __init__(self) -> None:
        self.logger = logging.getLogger("user_action")
        if not self.logger.handlers:  # Ensure single handler
            # Setup handler only once
```

---

## Cross-cutting Concern Patterns

### 1. Decorator Pattern

**Purpose**: Adds behavior to objects dynamically without altering their structure.

**Implementation**:
- `@require_role` decorator for authorization
- `@wraps` for preserving function metadata
- Cross-cutting security concerns

**Example**:
```python
def require_role(required_role):
    """Decorator to check user role for a command."""
    def decorator(func):
        @wraps(func)
        async def wrapper(update, context):
            user_id = update.effective_user.id
            
            if required_role == "coordinator" and user_id not in COORDINATOR_IDS:
                await update.message.reply_text(
                    "❌ Только координаторы могут выполнять эту команду.")
                return
                
            return await func(update, context)
        return wrapper
    return decorator

# Usage
@require_role("coordinator")
async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Command logic here
```

### 2. Middleware Pattern

**Purpose**: Provides a way to filter, process, or modify requests/responses in a pipeline.

**Implementation**:
- Telegram bot middleware for logging all updates
- Request processing pipeline
- Cross-cutting logging and debugging

**Example**:
```python
async def log_all_updates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Middleware to log all incoming updates."""
    user_id = update.effective_user.id if update.effective_user else "unknown"
    message_text = getattr(update.message, "text", "") if update.message else ""
    
    logger.info(f"Update from user {user_id}: {message_text}")

# Middleware registration
application.add_handler(
    MessageHandler(filters.ALL, log_all_updates), group=-1
)
```

### 3. Logging Pattern

**Purpose**: Provides structured, consistent logging across the application.

**Implementation**:
- `UserActionLogger` for structured user action logging
- Multiple specialized loggers for different concerns
- JSON-formatted logs for easy parsing

**Example**:
```python
class UserActionLogger:
    """Structured logger for user-related actions."""
    
    def log_user_action(self, user_id: int, action: str, details: Dict[str, Any], 
                       result: str = "success") -> None:
        data = {
            "event": "user_action",
            "user_id": user_id,
            "action": action,
            "details": details,
            "result": result,
        }
        self._log(self.USER_ACTION_LEVEL, data)
    
    def _log(self, level: int, data: Dict[str, Any]) -> None:
        self.logger.log(level, json.dumps(data, ensure_ascii=False))
```

### 4. Caching Pattern

**Purpose**: Stores frequently accessed data in memory to improve performance.

**Implementation**:
- Reference data caching (departments, cities)
- Participant data caching with TTL
- Cache invalidation strategies

**Example**:
```python
class ParticipantService:
    def __init__(self, repository: AbstractParticipantRepository):
        self._participants_cache = None
        self._cache_timestamp = 0
        self._cache_ttl = 300  # 5 minutes
    
    def _get_cached_participants(self):
        now = time.time()
        if (self._participants_cache is None or 
            now - self._cache_timestamp > self._cache_ttl):
            logger.debug("Refreshing participants cache")
            self._participants_cache = self.get_all_participants()
            self._cache_timestamp = now
        return self._participants_cache
```

---

## Integration Patterns

### 1. Gateway Pattern

**Purpose**: Encapsulates access to external systems behind a simplified interface.

**Implementation**:
- `AirtableClient` as gateway to Airtable API
- Telegram bot API abstraction
- External service integration

**Example**:
```python
class AirtableClient:
    """Gateway to Airtable API."""
    
    def __init__(self):
        self.token = config.AIRTABLE_TOKEN
        self.base_id = config.AIRTABLE_BASE_ID
        self.table_name = config.AIRTABLE_TABLE_NAME
    
    def test_connection(self) -> bool:
        """Test connection to Airtable API."""
        try:
            # Test API connectivity
            return True
        except Exception as e:
            logger.error(f"Airtable connection test failed: {e}")
            return False
```

### 2. Circuit Breaker Pattern

**Purpose**: Prevents cascading failures by stopping calls to failing services.

**Implementation**:
- Graceful fallback from Airtable to SQLite
- Configuration-based service switching
- Error handling with fallback strategies

**Example**:
```python
# Configuration fallback logic
if DATABASE_TYPE == 'airtable':
    if not AIRTABLE_TOKEN or not AIRTABLE_BASE_ID:
        print("⚠️ Airtable не настроен полностью. Переключаемся на локальную базу данных.")
        DATABASE_TYPE = 'local'  # Circuit breaker activation

# Runtime fallback in factory
def create_participant_repository():
    try:
        if config.DATABASE_TYPE == "airtable":
            client = AirtableClient()
            if not client.test_connection():
                print("❌ ERROR: Cannot connect to Airtable!")
                return SqliteParticipantRepository()  # Fallback
            return AirtableParticipantRepository()
    except Exception as e:
        logger.error(f"Airtable repository creation failed: {e}")
        return SqliteParticipantRepository()  # Fallback
```

### 3. Retry Pattern

**Purpose**: Automatically retries failed operations with configurable strategies.

**Implementation**:
- Session recovery for interrupted bot conversations
- Automatic state restoration
- User-friendly recovery options

**Example**:
```python
async def handle_session_recovery(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles recovery of interrupted sessions."""
    recovery_keyboard = [
        [InlineKeyboardButton("🔄 Продолжить", callback_data="recover_confirmation")],
        [InlineKeyboardButton("🆕 Начать заново", callback_data="recover_input")],
        [InlineKeyboardButton("❌ Отмена", callback_data="main_add")]
    ]
    
    await update.message.reply_text(
        "🔄 Обнаружена прерванная сессия добавления участника.\n"
        "Хотите продолжить с того места, где остановились?",
        reply_markup=InlineKeyboardMarkup(recovery_keyboard)
    )
```

---

## Data Processing Patterns

### 1. Parser Pattern

**Purpose**: Processes and transforms input data into structured formats.

**Implementation**:
- Multiple parsing strategies for different input formats
- Template format parser vs free-form text parser
- Extensible parsing architecture

**Example**:
```python
def parse_participant_data(text: str) -> Dict:
    """Main parser dispatcher."""
    if is_template_format(text):
        return parse_template_format(text)
    else:
        return parse_unstructured_text(text)

def parse_template_format(text: str) -> Dict:
    """Parses structured template format."""
    # Template: "Имя (рус): Мария Иванова\nПол: F\n..."
    
def parse_unstructured_text(text: str) -> Dict:
    """Parses free-form text."""
    # Free-form: "Анна Козлова женский S Благодать команда воршип от Петра anna@mail.ru"
```

### 2. Normalizer Pattern

**Purpose**: Standardizes data into consistent formats.

**Implementation**:
- `FieldNormalizer` class for data standardization
- Confidence-based normalization results
- Extensible normalization rules

**Example**:
```python
class FieldNormalizer:
    """Unified normalizer for participant fields."""
    
    def normalize_gender(self, value: str) -> NormalizationResult:
        """Normalizes gender field with confidence scoring."""
        value_upper = value.upper().strip()
        
        if value_upper in self.GENDER_MAPPINGS["M"]:
            return NormalizationResult("M", 1.0, f"Mapped '{value}' to 'M'")
        elif value_upper in self.GENDER_MAPPINGS["F"]:
            return NormalizationResult("F", 1.0, f"Mapped '{value}' to 'F'")
        
        return NormalizationResult(value, 0.0, f"Could not normalize gender: {value}")

@dataclass
class NormalizationResult:
    value: str
    confidence: float
    explanation: str
    
    def is_confident(self) -> bool:
        return self.confidence >= 0.8
```

### 3. Validator Pattern

**Purpose**: Ensures data meets business rules and constraints.

**Implementation**:
- Multi-level validation (presentation, business, data layers)
- Specific validators for different data types
- Comprehensive error reporting

**Example**:
```python
def validate_participant_data(data: Dict) -> Tuple[bool, str]:
    """Validates participant data against business rules."""
    
    # Required field validation
    if not data.get("FullNameRU", "").strip():
        return False, "Имя участника обязательно для заполнения"
    
    # Gender validation
    gender = data.get("Gender", "")
    if gender and gender not in ["M", "F"]:
        return False, f"Неверное значение пола: {gender}. Ожидается M или F"
    
    # Contact validation
    contact = data.get("ContactInformation", "")
    if contact and not is_valid_contact(contact):
        return False, f"Неверный формат контактной информации: {contact}"
    
    return True, "Validation passed"
```

---

## Pattern Interactions

### Layered Architecture + Repository + Service Layer
```
Telegram Handler (Presentation)
    ↓ calls
ParticipantService (Business Logic)
    ↓ uses
AbstractParticipantRepository (Data Access Interface)
    ↓ implemented by
SqliteParticipantRepository | AirtableParticipantRepository
```

### Strategy + Factory + Dependency Injection
```python
# Factory creates strategy based on config
repository = create_participant_repository()  # Factory Pattern

# Strategy injected into service
service = ParticipantService(repository=repository)  # Dependency Injection

# Service uses strategy polymorphically
service.add_participant(data)  # Strategy Pattern
```

### Decorator + Middleware + Observer
```python
@require_role("coordinator")  # Decorator Pattern
async def add_command(update, context):
    # Middleware logs all requests
    # Observer logs user actions
    result = participant_service.add_participant(data, user_id)
```

### State + Template Method + Observer
```python
# State Pattern manages conversation flow
ConversationHandler(
    states={
        CONFIRMING_DATA: [handlers...]  # State-specific handlers
    }
)

# Template Method in base repository
class BaseParticipantRepository:
    def update_fields(self, **fields):
        self._validate_fields(**fields)  # Template method
        # Concrete implementation in subclass

# Observer logs state transitions
user_action_logger.log_state_transition(user_id, from_state, to_state, context)
```

## Benefits of This Pattern Architecture

### Maintainability
- Clear separation of concerns through layered architecture
- Single responsibility principle enforced by pattern usage
- Easy to locate and modify specific functionality

### Testability
- Repository pattern enables easy mocking of data layer
- Dependency injection facilitates unit testing
- Strategy pattern allows testing different algorithms independently

### Extensibility
- New data sources easily added through repository implementations
- New parsing strategies can be plugged in
- Additional cross-cutting concerns can be added via decorators

### Reliability
- Circuit breaker pattern prevents cascading failures
- Observer pattern ensures comprehensive logging
- Validation patterns catch errors early

### Performance
- Caching patterns reduce database load
- Strategy patterns optimize for different use cases
- Lazy loading in repositories improves startup time

This comprehensive pattern implementation makes the Tres Dias Israel Telegram Bot a robust, maintainable, and extensible system that can evolve with changing requirements while maintaining code quality and architectural integrity.
