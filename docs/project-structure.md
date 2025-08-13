# Project Structure Documentation

**Version**: 1.0  
**Last Updated**: August 13, 2025  

## Project Overview

**Project Name**: Tres Dias Israel - Telegram Bot  
**Purpose**: Telegram bot for managing participants of the "Tres Dias Israel" event  
**Technology Stack**: Python 3.8+, python-telegram-bot, SQLite/Airtable, dataclasses  
**Architecture Pattern**: Layered architecture with Repository pattern and Service layer  

This system provides intelligent participant data parsing, duplicate detection, role-based access control, and comprehensive participant management capabilities through a Telegram bot interface.

## Root Directory Structure

```
td-event-telegram-bot/
├── 📁 Core Application Files
│   ├── main.py                    # Entry point, bot handlers, conversation flows
│   ├── states.py                  # Conversation state definitions
│   └── messages.py                # Bot message templates and responses
│
├── 📁 Configuration & Constants
│   ├── config.py                  # Environment configuration, database settings
│   ├── constants.py               # Enums, display mappings, validation constants
│   └── __init__.py                # Package initialization
│
├── 📁 Data Layer
│   ├── database.py                # SQLite database operations and schema
│   ├── models/                    # Data models and entities
│   └── repositories/              # Data access layer (Repository pattern)
│
├── 📁 Business Logic Layer
│   ├── services/                  # Business logic and domain services
│   └── parsers/                   # Text parsing and data extraction
│
├── 📁 Infrastructure Layer
│   └── utils/                     # Cross-cutting concerns and utilities
│
├── 📁 Testing Layer
│   └── tests/                     # Comprehensive test suite
│
├── 📁 Documentation & Scripts
│   ├── docs/                      # Project documentation
│   ├── scripts/                   # Operational scripts
│   └── tasks/                     # Development task documentation
│
└── 📁 Environment & Dependencies
    ├── requirements.txt           # Python dependencies
    ├── venv/                      # Virtual environment
    ├── logs/                      # Application logs
    └── participants.db            # SQLite database file
```

## Detailed Directory Breakdown

### Core Application Files

#### `main.py` (3021 lines)
- **Purpose**: Main application entry point and Telegram bot orchestration
- **Key Components**:
  - Telegram bot handlers and command processors
  - Conversation flow management using ConversationHandler
  - Role-based access control integration
  - Session recovery and timeout management
  - Application initialization and configuration
- **Dependencies**: telegram, config, services, repositories, utils
- **Architecture Role**: Presentation layer and application controller

#### `states.py` (17 lines)
- **Purpose**: Defines conversation states for bot interactions
- **Key Components**: State constants for conversation flow management
- **Architecture Role**: State management for user interactions

#### `messages.py` (48 lines)
- **Purpose**: Centralized message templates and bot responses
- **Key Components**: Predefined message templates for user communication
- **Architecture Role**: Presentation layer message management

### Configuration & Constants

#### `config.py` (48 lines)
- **Purpose**: Environment-based configuration management
- **Key Components**:
  - Bot token and username configuration
  - Database type selection (SQLite/Airtable)
  - User role definitions (coordinators, viewers)
  - Airtable integration settings
  - Debug and logging configuration
- **Features**: Automatic fallback to local database if Airtable unavailable
- **Architecture Role**: Configuration layer

#### `constants.py` (124 lines)
- **Purpose**: System constants, enums, and display mappings
- **Key Components**:
  - Gender, Role, Size, Department enums
  - Display name mappings for UI
  - Israeli cities reference data
  - Reverse lookup functions for parsing
- **Architecture Role**: Domain constants and reference data

### Data Layer

#### `database.py` (394 lines)
- **Purpose**: SQLite database operations and schema management
- **Key Components**:
  - Database initialization and schema creation
  - Low-level CRUD operations
  - Database connection management
  - Migration support
- **Architecture Role**: Data persistence layer

#### `models/participant.py` (21 lines)
- **Purpose**: Core domain model definition
- **Key Components**:
  - Participant dataclass with typed fields
  - Default values and field validation
  - Domain object representation
- **Architecture Role**: Domain model layer

#### `repositories/` Directory
- **Purpose**: Data access layer implementing Repository pattern
- **Architecture Role**: Data abstraction layer

##### `participant_repository.py` (296 lines)
- **Components**:
  - `AbstractParticipantRepository`: Abstract base class defining repository interface
  - `BaseParticipantRepository`: Shared validation helpers
  - `SqliteParticipantRepository`: SQLite-specific implementation
- **Key Features**:
  - CRUD operations with domain objects
  - Partial field updates
  - Existence checking
  - Error handling and logging

##### `airtable_participant_repository.py` (214 lines)
- **Purpose**: Airtable-specific repository implementation
- **Key Features**:
  - Airtable API integration
  - Field mapping between domain model and Airtable schema
  - Error handling for external API calls

##### `airtable_client.py` (31 lines)
- **Purpose**: Airtable API client wrapper
- **Key Features**:
  - Connection testing
  - API abstraction
  - Configuration management

### Business Logic Layer

#### `services/participant_service.py` (780 lines)
- **Purpose**: Core business logic orchestration
- **Key Components**:
  - `ParticipantService`: Main service class
  - Duplicate detection logic
  - Data validation and normalization
  - Search functionality
  - Performance monitoring and caching
- **Architecture Role**: Business logic layer

#### `parsers/participant_parser.py` (1116 lines)
- **Purpose**: Intelligent text parsing and data extraction
- **Key Components**:
  - Template format parsing
  - Free-form text parsing
  - Field normalization
  - Hebrew text filtering
  - Data structure recognition
- **Key Features**:
  - Multiple parsing strategies
  - Robust error handling
  - Flexible data format support
- **Architecture Role**: Data transformation layer

### Infrastructure Layer

#### `utils/` Directory
- **Purpose**: Cross-cutting concerns and utility functions
- **Architecture Role**: Infrastructure and utility layer

##### Key Utility Modules:

**`decorators.py` (28 lines)**
- Role-based access control decorators
- Authorization middleware

**`validators.py` (51 lines)**
- Data validation functions
- Input sanitization

**`exceptions.py` (24 lines)**
- Custom exception hierarchy
- Error classification

**`field_normalizer.py` (333 lines)**
- Data normalization utilities
- Field value standardization

**`cache.py` (27 lines)**
- Caching mechanisms
- Reference data management

**`timeouts.py` (22 lines)**
- Session timeout management
- Cleanup utilities

**`session_recovery.py` (93 lines)**
- Session recovery utilities
- State restoration

**`user_logger.py` (132 lines)**
- User action logging
- Audit trail management

**`recognizers.py` (81 lines)**
- Pattern recognition utilities
- Text analysis helpers

### Testing Layer

#### `tests/` Directory (20 test files)
- **Purpose**: Comprehensive test coverage for all components
- **Test Categories**:
  - **Unit Tests**: Individual component testing
  - **Integration Tests**: Component interaction testing
  - **Parser Tests**: Text parsing validation
  - **Database Tests**: Data persistence testing
  - **Service Tests**: Business logic testing
  - **Validation Tests**: Data validation testing
  - **Airtable Integration Tests**: External API integration testing

**Key Test Files**:
- `test_parser.py` (359 lines) - Parser functionality
- `test_database.py` (61 lines) - Database operations
- `test_participant_service.py` (56 lines) - Service layer
- `test_validators.py` (83 lines) - Validation logic
- `test_contact_validation.py` (177 lines) - Contact validation
- `test_airtable_connection.py` (19 lines) - Airtable API connectivity
- `test_airtable_repository.py` (41 lines) - Airtable repository integration
- Additional specialized test files for specific features

### Documentation & Scripts

#### `docs/` Directory
- **Current Files**:
  - `MONITORING.md` - Operational monitoring guidelines
  - `project-structure.md` - This document

#### `scripts/` Directory
- **Purpose**: Operational and maintenance scripts
- **Files**:
  - `monitor.sh` (122 lines) - System monitoring script
  - `log_analyzer.py` (110 lines) - Log analysis utilities
  - `log_cleanup.sh` (27 lines) - Log maintenance script

#### `tasks/` Directory
- **Purpose**: Development task documentation and planning
- **Files**:
  - Task planning documents
  - Implementation specifications
  - Development workflows

## Architectural Patterns

### Repository Pattern Implementation
- **Abstract Interface**: `AbstractParticipantRepository` defines contract
- **Concrete Implementations**: 
  - `SqliteParticipantRepository` for local database
  - `AirtableParticipantRepository` for cloud database
- **Benefits**: Data source abstraction, testability, flexibility

### Service Layer Pattern
- **Implementation**: `ParticipantService` orchestrates business logic
- **Responsibilities**:
  - Business rule enforcement
  - Data validation and transformation
  - Duplicate detection
  - Performance optimization through caching
- **Benefits**: Business logic centralization, separation of concerns

### Decorator Pattern
- **Implementation**: Role-based access control decorators
- **Usage**: `@require_role` for method-level authorization
- **Benefits**: Cross-cutting concern implementation, clean code

### Strategy Pattern
- **Parsing Strategies**: Multiple text parsing approaches
  - Template format parsing
  - Free-form text parsing
  - Field-specific normalization
- **Database Strategies**: Multiple backend support
  - SQLite for local development
  - Airtable for cloud deployment

## Data Flow Architecture

```
1. Input Layer (Telegram Bot)
   ↓
2. Presentation Layer (main.py handlers)
   ↓
3. Business Logic Layer (services/)
   ↓
4. Data Access Layer (repositories/)
   ↓
5. Persistence Layer (database.py / Airtable API)
```

### Detailed Flow:
1. **User Input** → Telegram message received
2. **Handler Processing** → Route to appropriate command handler
3. **Authorization** → Role-based access control check
4. **Parsing** → Extract structured data from text
5. **Validation** → Business rule validation
6. **Service Logic** → Duplicate checking, data processing
7. **Repository** → Data persistence abstraction
8. **Storage** → Actual data storage (SQLite/Airtable)

## Key Design Principles

### SOLID Principles Implementation
- **Single Responsibility**: Each module has focused purpose
- **Open/Closed**: Extensible through interfaces (Repository pattern)
- **Liskov Substitution**: Repository implementations are interchangeable
- **Interface Segregation**: Focused interfaces for specific concerns
- **Dependency Inversion**: High-level modules depend on abstractions

### Domain-Driven Design
- **Domain Model**: `Participant` dataclass represents business entity
- **Repository**: Data access abstraction
- **Service**: Business logic orchestration
- **Value Objects**: Enums and constants for domain concepts

### Clean Architecture
- **Dependency Direction**: Dependencies point inward toward domain
- **Layer Separation**: Clear boundaries between layers
- **Testability**: Easy unit testing through dependency injection

## Configuration Management

### Environment-Based Configuration
- **Development**: Local SQLite database
- **Production**: Configurable backend (SQLite/Airtable)
- **Environment Variables**: Secure configuration through `.env`

### Feature Flags
- **Database Selection**: Runtime database backend selection
- **Debug Mode**: Configurable logging and debugging
- **Role Management**: Flexible user role assignment

### Multi-Backend Support
- **SQLite**: Local development and testing
- **Airtable**: Cloud-based production deployment
- **Graceful Fallback**: Automatic fallback to local if cloud unavailable

## Error Handling Strategy

### Exception Hierarchy
- **Base Exceptions**: `BotException`, `ValidationError`
- **Specific Exceptions**: `ParticipantNotFoundError`, `DuplicateParticipantError`
- **Database Exceptions**: `DatabaseError` for persistence issues

### Error Recovery
- **Graceful Degradation**: System continues operating with reduced functionality
- **User-Friendly Messages**: Clear error communication to users
- **Logging**: Comprehensive error logging for debugging

### Validation Strategy
- **Input Validation**: Early validation at presentation layer
- **Business Rule Validation**: Service layer validation
- **Data Integrity**: Repository layer validation

## Testing Strategy

### Test Coverage
- **Unit Tests**: Individual component testing with mocks
- **Integration Tests**: Component interaction testing
- **End-to-End Tests**: Full workflow testing
- **Performance Tests**: Load and performance validation

### Test Organization
- **Per-Component Tests**: Each module has corresponding test file
- **Shared Test Utilities**: Common test helpers and fixtures
- **Test Data**: Realistic test data for comprehensive coverage

### Continuous Testing
- **Automated Test Suite**: Full test suite execution
- **Test-Driven Development**: Tests guide implementation
- **Regression Testing**: Prevent functionality regression

## Operational Considerations

### Logging and Monitoring
- **Structured Logging**: JSON-formatted logs for analysis
- **Performance Monitoring**: Operation timing and metrics
- **User Action Auditing**: Complete audit trail of user actions
- **Error Tracking**: Comprehensive error logging and alerting

### Session Management
- **Timeout Handling**: Automatic session cleanup
- **State Recovery**: Recovery from interrupted sessions
- **Concurrent Sessions**: Multi-user session management

### Performance Optimization
- **Caching**: Reference data caching for performance
- **Database Optimization**: Efficient queries and indexing
- **Memory Management**: Efficient resource utilization

### Maintenance
- **Log Rotation**: Automated log cleanup and rotation
- **Database Maintenance**: Schema migrations and optimization
- **Monitoring Scripts**: Automated system health monitoring

## File Size and Complexity Metrics

### Large Files (>500 lines)
- `parsers/participant_parser.py` (1116 lines) - Complex parsing logic
- `services/participant_service.py` (780 lines) - Business logic orchestration
- `database.py` (394 lines) - Database operations
- `repositories/participant_repository.py` (296 lines) - Repository implementation

### Medium Files (100-500 lines)
- `repositories/airtable_participant_repository.py` (214 lines)
- `utils/field_normalizer.py` (333 lines)
- `utils/user_logger.py` (132 lines)
- `constants.py` (124 lines)
- `scripts/monitor.sh` (122 lines)
- `scripts/log_analyzer.py` (110 lines)

### Small Files (<100 lines)
- Configuration and utility files
- Model definitions
- Test files (individual components)
- Documentation files

This structure reflects a mature, well-architected system with clear separation of concerns, comprehensive testing, and robust operational capabilities.
