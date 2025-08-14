# Payment Functionality Documentation

**Version**: 1.0  
**Last Updated**: January 25, 2025  
**Related Task**: [TDB-1](https://linear.app/alexandrbasis/issue/TDB-1/dobavlenie-funkcionala-o-vnesenie-oplaty)

## Overview

This document provides a comprehensive overview of the payment functionality implemented in the Tres Dias Israel Telegram Bot. The payment system allows coordinators to track participant payments in Israeli Shekels (₪) through a unified interface.

## Key Features

### 💰 Universal Payment Entry
- **Single Button Interface**: "💰 Внести оплату" button available in all contexts
- **Unified Flow**: Button → Amount Entry → Validation → Confirmation → Save
- **Context Availability**: 
  - During participant addition
  - During participant search/viewing
  - During participant editing
  - Via dedicated `/payment` command

### 🔢 Strict Integer Validation
- **Currency**: Israeli Shekels (₪) only
- **Amount Format**: Integers only (no decimals)
- **Validation**: Positive numbers greater than 0
- **Display Format**: Always shows "₪" symbol (e.g., "500 ₪")

### 📊 Payment Status Management
- **Statuses**: Unpaid, Paid, Partial, Refunded
- **Display Mapping**: Russian language with emoji indicators
- **Auto Date**: Automatic date setting when status changes to "Paid"
- **Logging**: All payment operations are logged for audit

## Data Model

### Payment Fields
```python
@dataclass
class Participant:
    # ... existing fields ...
    
    # Payment fields - added for TDB-1
    PaymentStatus: str = "Unpaid"        # Status enum value
    PaymentAmount: int = 0               # Amount in shekels (integers only)
    PaymentDate: str = ""                # ISO format date string
```

### Payment Status Enum
```python
class PaymentStatus(Enum):
    UNPAID = "Unpaid"
    PAID = "Paid"
    PARTIAL = "Partial"
    REFUNDED = "Refunded"
```

## User Interface

### Payment Entry Flow
1. **Initiation**: User clicks "💰 Внести оплату" button
2. **Amount Input**: System prompts for integer amount in shekels
3. **Validation**: Strict integer validation with error messages
4. **Confirmation**: Shows participant name, amount, and confirmation buttons
5. **Save**: Updates payment status, amount, and date

### Display Formats
- **Search Results**: Shows payment status with emoji indicators
- **Participant Details**: Full payment information display
- **List Command**: Payment status for all participants

## Technical Implementation

### Service Layer
- `ParticipantService.process_payment()` - Main payment processing
- `ParticipantService.get_payment_statistics()` - Payment reporting
- `ParticipantService.validate_payment_data()` - Data validation

### Repository Layer
- `update_payment()` - Update payment information
- `get_unpaid_participants()` - Retrieve unpaid participants
- `get_payment_summary()` - Generate payment statistics

### Parser Integration
- Payment field parsing from unstructured text
- Support for Russian payment status terms
- Amount parsing with shekel symbols

## Commands

### `/payment` Command
- **Usage**: `/payment` or `/payment [participant name]`
- **Access**: Available to all users
- **Functionality**: 
  - Interactive search mode when no name provided
  - Direct payment entry when participant found
  - Integration with existing search handlers

## Testing Coverage

Comprehensive test suite in `test_payment_functionality.py`:
- **465+ lines of tests** covering all payment functionality
- **Unit Tests**: Model validation, enum handling, data validation
- **Integration Tests**: Service layer, repository operations, database CRUD
- **End-to-End Tests**: Full payment workflows
- **Parser Tests**: Payment field extraction from text

## Business Rules

1. **Currency**: All payments are in Israeli Shekels (₪)
2. **Amount Format**: Only positive integers accepted
3. **Status Tracking**: Automatic date setting on payment
4. **Access Control**: Payment modification available to all users
5. **Audit Trail**: All payment operations are logged
6. **Display Language**: Russian interface with emoji indicators

## Security Considerations

- **Input Validation**: Strict validation of all payment data
- **Audit Logging**: All payment operations logged with user ID
- **Data Integrity**: Proper database constraints and validation
- **Error Handling**: Graceful error recovery with user feedback

## Future Enhancements

Planned features for future iterations:
- **Batch Payment Processing**: Handle multiple payments at once
- **Payment Reporting**: `/payment_report` command for statistics
- **Payment Import**: Import payment data from external files
- **Advanced Filtering**: Filter participants by payment criteria

---

## Quick Reference

### Payment Status Display
- ✅ Оплачено (Paid)
- ❌ Не оплачено (Unpaid)
- 🔶 Частично оплачено (Partial)
- 🔄 Возвращено (Refunded)

### Key Files
- **Models**: `models/participant.py`
- **Constants**: `constants.py` (PaymentStatus enum)
- **Service**: `services/participant_service.py`
- **Repository**: `repositories/participant_repository.py`
- **Parser**: `parsers/participant_parser.py`
- **Tests**: `tests/test_payment_functionality.py`

### Related Documentation
- [Business Requirements](.cursor/rules/business-requirements.mdc)
- [Architectural Patterns](.cursor/rules/architectural-patterns.mdc)
- [Test Structure](docs/tests-structure.md)
- [Task Documentation](tasks/completed/task-2025-01-24-payment-functionality.md)

---

*This documentation reflects the completed implementation of payment functionality as of January 25, 2025. All features are production-ready and fully tested.*
