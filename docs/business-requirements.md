# Business Requirements - Tres Dias Israel Telegram Bot

**Version**: 1.0  
**Last Updated**: August 13, 2025

## 📋 Table of Contents
- [Project Overview](#project-overview)
- [Business Context](#business-context)
- [Core Business Entities](#core-business-entities)
- [User Roles & Permissions](#user-roles--permissions)
- [Business Processes](#business-processes)
- [Data Requirements](#data-requirements)
- [Integration Requirements](#integration-requirements)
- [Quality Requirements](#quality-requirements)
- [Constraints & Assumptions](#constraints--assumptions)
- [Future Enhancements](#future-enhancements)

## Project Overview

**Project Name**: Tres Dias Israel - Telegram Bot  
**Business Domain**: Event Management & Participant Registration  
**Primary Purpose**: Automate participant registration and management for Tres Dias Israel religious retreats  
**Target Users**: Event coordinators, administrators, and authorized viewers  

### Mission Statement
Provide an intelligent, user-friendly Telegram bot that streamlines participant registration for Tres Dias Israel events, eliminates manual data entry errors, prevents duplicate registrations, and maintains data integrity across multiple backend systems.

## Business Context

### What is Tres Dias?
Tres Dias is a Christian spiritual retreat movement that conducts 3-day intensive programs. The Israeli chapter requires:
- Careful participant screening and registration
- Role-based access control for sensitive participant data
- Multi-language support (Russian, English, Hebrew context)
- Integration with existing workflow tools (Airtable, local databases)

### Business Pain Points Addressed
1. **Manual Data Entry**: Coordinators previously copied participant data manually from messages
2. **Data Inconsistency**: Different formats and typos led to database inconsistencies  
3. **Duplicate Participants**: No automated checking for existing participants
4. **Access Control**: Need to restrict sensitive operations to authorized coordinators
5. **Multi-Backend Complexity**: Supporting both cloud (Airtable) and local databases
6. **Hebrew Text Issues**: Hebrew characters causing parsing errors in participant data

## Core Business Entities

### Participant
The central business entity representing a person applying for or participating in Tres Dias events.

**Core Attributes:**
- **FullNameRU** (Required): Full name in Russian/Cyrillic script
- **Gender** (Required): M (Male) / F (Female) - required for accommodation planning
- **Size** (Required): Clothing size (XS, S, M, L, XL, XXL, 3XL) - for event materials
- **Church** (Required): Home church/congregation - for community tracking
- **Role** (Required): CANDIDATE (first-time participant) / TEAM (returning helper)

**Optional Attributes:**
- **Department**: For TEAM role - specific service area (Kitchen, Worship, Administration, etc.)
- **FullNameEN**: English transliteration of name
- **CountryAndCity**: Location information (focus on Israeli cities)
- **SubmittedBy**: Name of person who referred/submitted this participant
- **ContactInformation**: Email, phone, or other contact details

**Business Rules:**
- FullNameRU is the primary identifier for duplicate detection
- Department is only applicable when Role = "TEAM"
- Gender determines accommodation assignments
- Size determines material distribution
- Church affiliation is tracked for community building

### User Roles
**Coordinator**: Full access - can add, edit, delete participants
**Viewer**: Read-only access - can view participant lists and statistics

## User Roles & Permissions

### Coordinator Role
**Who**: Event organizers, registration managers, senior volunteers  
**Permissions**:
- Add new participants (`/add` command)
- Edit existing participant data (`/edit` command - planned)
- Delete participants (`/delete` command - planned)  
- View all participant data (`/list` command)
- Export data (`/export` command - planned)
- Access all bot functionality

**Business Justification**: Coordinators handle sensitive personal data and make decisions about participant acceptance.

### Viewer Role  
**Who**: Junior volunteers, observers, reporting personnel  
**Permissions**:
- View participant lists (`/list` command)
- Access basic bot help (`/help`, `/start`)
- Export data (`/export` command - planned)

**Restrictions**:
- Cannot add, modify, or delete participant data
- Cannot access administrative functions

**Business Justification**: Allows broader team access for coordination while protecting data integrity.

### Unauthorized Users
**Behavior**: Denied access with clear error message  
**Business Justification**: Participant data is sensitive and requires explicit authorization.

## Business Processes

### 1. Participant Registration Process

**Trigger**: Coordinator receives participant information (via email, form, verbal communication)  
**Goal**: Accurately capture participant data in the system  

**Process Flow:**
1. **Initiation**: Coordinator uses `/add` command
2. **Data Input**: Coordinator pastes participant information in any supported format:
   - **Template Format**: Structured "Field: Value" format
   - **Free-form Text**: Natural language with participant details
   - **Mixed Format**: Combination of structured and unstructured data
3. **Intelligent Parsing**: System extracts structured data using AI-powered parsing
4. **Validation & Confirmation**: System displays parsed data for coordinator review
5. **Interactive Editing**: Coordinator can modify any field using inline keyboards
6. **Duplicate Detection**: System checks for existing participants by name
7. **Duplicate Resolution**: If duplicate found, coordinator chooses:
   - Create new entry (allow duplicate)
   - Cancel registration
   - Update existing participant data
8. **Final Confirmation**: Coordinator confirms final data
9. **Persistence**: Data saved to configured backend (SQLite or Airtable)
10. **Audit Trail**: Action logged for compliance

**Business Rules:**
- All required fields must be filled before saving
- Hebrew text is filtered out during parsing to prevent errors
- Names are used for duplicate detection (case-insensitive)
- Department field only required for TEAM role

### 2. Data Parsing & Normalization Process

**Business Need**: Coordinators receive participant data in various formats from different sources

**Supported Input Formats:**

**Template Format Example:**
```
Имя (рус): Мария Иванова  
Пол: F  
Размер: M  
Церковь: Новая Жизнь  
Роль: CANDIDATE  
Кто подал: Петр Сидоров  
Контакты: maria@mail.ru  
```

**Free-form Text Example:**
```
Анна Козлова женский S Благодать команда воршип от Петра anna@mail.ru
```

**Parsing Intelligence:**
- **Multi-language Recognition**: Handles Russian, English, and mixed text
- **Context-aware Field Detection**: Recognizes fields based on surrounding context
- **Flexible Value Mapping**: Maps display names to system values (e.g., "женский" → "F")
- **Smart Name Extraction**: Separates Russian and English names from mixed text
- **Contact Information Detection**: Extracts emails, phones automatically
- **Church Name Recognition**: Matches against known church database
- **City Recognition**: Identifies Israeli cities in multiple languages

### 3. Duplicate Management Process

**Business Problem**: Multiple coordinators might register the same participant

**Detection Logic:**
- Primary key: FullNameRU (case-insensitive comparison)
- Fuzzy matching for slight variations in spelling
- Real-time checking during registration

**Resolution Options:**
1. **Add as New**: Create duplicate entry (for different events or genuine different people)
2. **Cancel**: Abort registration process
3. **Replace**: Update existing participant with new data

**Business Value**: Prevents data pollution and maintains participant database integrity

### 4. Role-based Data Access Process

**Business Need**: Control access to sensitive participant information

**Implementation:**
- User ID-based role assignment in configuration
- Decorator-based permission checking on all sensitive operations
- Clear error messages for unauthorized access attempts

**Audit Requirements:**
- All user actions logged with timestamps
- User ID and action type recorded
- Failed authorization attempts logged

## Data Requirements

### Data Quality Standards
- **Completeness**: All required fields must be populated
- **Consistency**: Standardized values for enums (Gender, Role, Size, Department)
- **Accuracy**: Intelligent parsing reduces human input errors
- **Uniqueness**: Duplicate detection prevents data pollution
- **Integrity**: Referential integrity between Role and Department fields

### Data Security Requirements
- **Access Control**: Role-based access to sensitive operations
- **Audit Trail**: Complete logging of all data modifications
- **Data Retention**: Participant data retained per organizational policy
- **Privacy**: Personal information access limited to authorized users

### Data Integration Requirements
- **Multi-backend Support**: SQLite (local) and Airtable (cloud) backends
- **Graceful Fallback**: Automatic fallback to local database if cloud unavailable
- **Schema Consistency**: Identical data model across all backends
- **Migration Support**: Ability to transfer data between backends

## Integration Requirements

### Telegram Bot Platform
- **Bot Framework**: python-telegram-bot library
- **Conversation Management**: Multi-state conversation flows
- **Inline Keyboards**: Interactive data editing capabilities
- **Error Handling**: Graceful error recovery and user feedback

### Database Integration
**Primary Option - Airtable:**
- Cloud-based collaboration
- Web interface for non-technical users
- API integration for automated data sync
- Backup and recovery capabilities

**Fallback Option - SQLite:**
- Local development and testing
- Offline operation capability
- Simple deployment requirements
- No external dependencies

### External Data Sources
- **Church Database**: Cached list of known churches for validation
- **City Database**: Israeli cities in multiple languages for location parsing
- **Department Definitions**: Predefined service areas for TEAM participants

## Quality Requirements

### Performance Requirements
- **Response Time**: Bot responses within 2 seconds for normal operations
- **Parsing Speed**: Text parsing completed within 1 second
- **Concurrent Users**: Support for multiple coordinators simultaneously
- **Database Performance**: Efficient duplicate detection even with large datasets

### Reliability Requirements
- **Uptime**: 99.9% availability during event registration periods
- **Error Recovery**: Automatic session recovery after technical failures
- **Data Consistency**: ACID compliance for all database operations
- **Backup Strategy**: Regular automated backups of participant data

### Usability Requirements
- **Learning Curve**: New coordinators productive within 10 minutes
- **Input Flexibility**: Accept participant data in any reasonable format
- **Clear Feedback**: Immediate confirmation of all user actions
- **Error Messages**: Clear, actionable error messages in Russian
- **Mobile Friendly**: Optimized for mobile Telegram clients

### Security Requirements
- **Authentication**: Telegram user ID-based authentication
- **Authorization**: Role-based access control for all operations
- **Audit Logging**: Complete audit trail of all data modifications
- **Data Protection**: Secure handling of personal information

## Constraints & Assumptions

### Technical Constraints
- **Platform**: Must operate within Telegram Bot API limitations
- **Language**: Python 3.8+ required for development team familiarity
- **Database**: Must support both cloud and local deployment scenarios
- **Network**: Must handle intermittent internet connectivity gracefully

### Business Constraints
- **Budget**: Minimal infrastructure costs (favor free/low-cost solutions)
- **Timeline**: Rapid deployment required for upcoming events
- **Maintenance**: Solution must be maintainable by small technical team
- **Scalability**: Must handle peak registration periods (hundreds of participants)

### Regulatory Constraints
- **Data Privacy**: Compliance with personal data protection requirements
- **Religious Sensitivity**: Respectful handling of religious affiliation data
- **Multi-language**: Support for Russian-speaking user base in Israel

### Assumptions
- **User Device**: Coordinators have smartphones with Telegram installed
- **Internet Access**: Reliable internet access during registration periods
- **Training**: Basic training provided to coordinators on bot usage
- **Data Sources**: Participant data quality depends on original source accuracy

## Future Enhancements

### Planned Features (High Priority)
1. **Participant Editing**: Full CRUD operations for existing participants
2. **Advanced Search**: Search participants by multiple criteria
3. **Data Export**: CSV/Excel export functionality
4. **Bulk Operations**: Import multiple participants from spreadsheets
5. **Reporting Dashboard**: Statistics and analytics for coordinators

### Potential Features (Medium Priority)
1. **Notification System**: Alerts for registration deadlines
2. **Integration APIs**: Connect with other event management tools
3. **Mobile App**: Dedicated mobile application beyond Telegram
4. **Advanced Analytics**: Participant demographics and trends
5. **Multi-event Support**: Manage multiple Tres Dias events simultaneously

### Long-term Vision (Low Priority)
1. **AI-powered Insights**: Predictive analytics for participant management
2. **Automated Communications**: Personalized participant communications
3. **Integration Hub**: Central integration point for all event management tools
4. **Multi-organization**: Support for multiple Tres Dias chapters
5. **Advanced Workflow**: Complex approval processes and participant lifecycle management

---

## Quick Reference for AI Agents

### Key Business Rules
1. **Required Fields**: FullNameRU, Gender, Size, Church, Role must be filled
2. **Role Logic**: Department only required when Role = "TEAM"
3. **Duplicate Detection**: Based on FullNameRU (case-insensitive)
4. **Access Control**: Coordinators can modify data, Viewers can only read
5. **Data Parsing**: Support template format, free-form text, and mixed formats

### Critical Success Factors
1. **Data Quality**: Accurate parsing reduces coordinator workload
2. **User Experience**: Simple, intuitive interface for non-technical users  
3. **Reliability**: System must work consistently during registration periods
4. **Security**: Proper access control for sensitive participant data
5. **Flexibility**: Handle diverse input formats from various sources

### Common Integration Patterns
- Repository pattern for database abstraction
- Service layer for business logic
- Decorator pattern for access control
- Strategy pattern for parsing algorithms
- Observer pattern for audit logging

This document serves as the definitive business requirements reference for all AI agents working on the Tres Dias Israel Telegram Bot project.
