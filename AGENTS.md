---
alwaysApply: true
---
# AI Coder Agent Instructions - Tres Dias Israel Telegram Bot

**Version**: 1.1  
**Last Updated**: August 13, 2025
**Document Purpose**: Comprehensive guidelines for AI Coder agents working on the Tres Dias Israel Telegram Bot project

---

## 📋 Table of Contents
- [Development Workflow](#development-workflow)
- [Core Development Principles](#core-development-principles)
- [Pre-Implementation Requirements](#pre-implementation-requirements)
- [Implementation Guidelines](#implementation-guidelines)
- [Post-Implementation Requirements](#post-implementation-requirements)
- [Documentation Standards](#documentation-standards)
- [Code Quality Standards](#code-quality-standards)
- [Testing Requirements](#testing-requirements)
- [Architecture Compliance](#architecture-compliance)

---

## Development Workflow

### **MANDATORY 5-Step Development Process**

All development tasks MUST follow this structured workflow:

#### **Step 1: Task Assignment**
- User provides task description and requirements
- AI Coder agent acknowledges task and begins analysis

#### **Step 2: Technical Decomposition**
- **MANDATORY**: AI Coder agent creates technical decomposition document
- **Location**: `tasks/` directory 
- **Filename**: `task-YYYY-MM-DD-[brief-description].md`
- **Content**: Detailed technical breakdown including:
  - Task overview and business context
  - Technical requirements analysis
  - Implementation steps with checkboxes
  - Dependencies and risks
  - Testing strategy
  - Documentation update plan
  - Estimated effort and timeline

**Technical Decomposition Template:**
```markdown
# Task: [Task Name]

**Created**: [Date]  
**Status**: Draft | Under Review | Approved | In Progress | Completed  
**Estimated Effort**: [Hours/Days]

## Business Context
[Why this task is needed, business value, user impact]

## Technical Requirements
- [ ] Requirement 1
- [ ] Requirement 2
- [ ] Requirement 3

## Implementation Steps
### Phase 1: [Phase Name]
- [ ] Step 1.1: [Description]
- [ ] Step 1.2: [Description]

### Phase 2: [Phase Name]  
- [ ] Step 2.1: [Description]
- [ ] Step 2.2: [Description]

## Dependencies
- [Dependency 1]
- [Dependency 2]

## Risks & Mitigation
- **Risk**: [Description] → **Mitigation**: [Strategy]

## Testing Strategy
- [ ] Unit tests for [component]
- [ ] Integration tests for [workflow]
- [ ] Manual testing scenarios

## Documentation Updates Required
- [ ] Update `patterns.md` (if new patterns)
- [ ] Update `business-requirements.md` (if business rules change)
- [ ] Update `tests-structure.md` (always)
- [ ] Update `project-structure.md` (if structure changes)

## Success Criteria
- [ ] Criteria 1
- [ ] Criteria 2
- [ ] All tests pass
- [ ] Documentation updated
```

#### **Step 3: Decomposition Review**
- **MANDATORY**: User reviews technical decomposition
- User can request changes, additions, or clarifications
- Process iterates until decomposition is approved
- **Status Update**: Change status from "Draft" to "Approved"

#### **Step 4: Implementation**
- **MANDATORY**: AI Coder agent updates decomposition document throughout implementation
- Mark completed steps with ✅ and timestamp
- Add implementation notes and decisions
- Update status to "In Progress" → "Completed"
- Follow TDD approach: tests first, then implementation
- Maintain real-time progress tracking in the decomposition document

**Progress Tracking Format:**
```markdown
- [x] ✅ Step 1.1: [Description] - Completed [Timestamp]
  - **Implementation Notes**: [Key decisions, challenges, solutions]
- [x] ✅ Step 1.2: [Description] - Completed [Timestamp]
- [ ] Step 1.3: [Description] - In Progress
```

#### **Step 5: Documentation Updates**
- **MANDATORY**: Update all relevant documentation files
- Follow post-implementation requirements
- Update version numbers and dates
- Cross-reference with completed task in decomposition document

### **Workflow Enforcement Rules**

1. **No Implementation Without Decomposition**: Never start coding without an approved technical decomposition
2. **Real-Time Updates**: Update task decomposition throughout implementation, not at the end
3. **Single Source of Truth**: The task decomposition document is the authoritative source for task status
4. **Approval Gate**: Implementation cannot begin until decomposition is explicitly approved by user
5. **Progress Visibility**: User should be able to see progress at any time by checking the task decomposition file

### **Task Decomposition File Management**

- **Archive Completed Tasks**: Move completed task files to `tasks/completed/` subdirectory
- **Naming Convention**: `task-YYYY-MM-DD-[brief-description].md`
- **Status Tracking**: Always maintain current status in document header
- **Cross-References**: Link related tasks and reference relevant documentation
- **Directory Structure**:
  ```
  tasks/
  ├── task-2024-12-19-example-feature.md     # Active/In-Progress tasks
  ├── task-2024-12-20-another-task.md        # Active/In-Progress tasks
  └── completed/                              # Completed tasks archive
      ├── task-2024-12-15-completed-task.md
      └── task-2024-12-18-finished-feature.md
  ```

---

## Core Development Principles

### 1. Documentation-First Development
- **Always read existing documentation** before making changes
- **Update documentation immediately** after implementation
- **Document business decisions** and architectural choices
- **Maintain version control** for all documentation files

### 2. Test-Driven Development
- Write tests before implementing features
- Ensure comprehensive test coverage (>85%)
- Update test documentation after adding new tests
- Follow established testing patterns from `tests-structure.md`

### 3. Architecture Consistency
- Follow established patterns documented in `patterns.md`
- Maintain clean architecture principles
- Ensure proper separation of concerns
- Use dependency injection and repository patterns

### 4. Business-First Approach
- Understand business requirements from `business-requirements.md`
- Implement features that align with business goals
- Document business rule changes
- Consider user experience and business impact

---

## Pre-Implementation Requirements

### 1. Documentation Review (MANDATORY)
Before starting any implementation, **MUST** read and understand:

1. **Business Requirements** (`business-requirements.md`)
   - Understand the business context and requirements
   - Identify affected business processes
   - Note any constraints or assumptions

2. **Project Structure** (`project-structure.md`)
   - Understand current architecture
   - Identify where new code should be placed
   - Follow established file organization patterns

3. **Design Patterns** (`patterns.md`)
   - Identify applicable existing patterns
   - Plan how new code fits existing architecture
   - Determine if new patterns are needed

4. **Test Structure** (`tests-structure.md`)
   - Understand testing patterns and conventions
   - Plan test coverage for new features
   - Identify existing test utilities to reuse

### 2. Impact Assessment
- Identify all components that will be affected
- Plan backward compatibility considerations
- Assess performance implications
- Consider security implications

### 3. Implementation Planning
- Break down complex tasks into smaller, testable units
- Plan the order of implementation (tests first)
- Identify dependencies and integration points
- Plan rollback strategy if needed

---

## Implementation Guidelines

### 1. Code Organization
- Place code in appropriate layers (presentation, business, data)
- Follow existing naming conventions
- Use established directory structure
- Maintain consistent import organization

### 2. Error Handling
- Use established exception hierarchy (`utils/exceptions.py`)
- Implement graceful error recovery
- Provide user-friendly error messages
- Log errors appropriately for debugging

### 3. Logging and Monitoring
- Use established logging patterns (`utils/user_logger.py`)
- Log all significant user actions
- Include performance metrics where appropriate
- Follow structured logging format (JSON)

### 4. Configuration Management
- Use existing configuration patterns (`config.py`)
- Support environment-based configuration
- Maintain backward compatibility
- Document new configuration options

---

## Post-Implementation Requirements

### MANDATORY: Documentation Updates (After Every Implementation)

#### 1. Update `patterns.md` (If Applicable)
**When to Update:**
- New design patterns introduced
- Existing patterns modified or extended
- New architectural decisions made

**What to Include:**
- Pattern description and purpose
- Implementation examples
- Benefits and trade-offs
- Integration with existing patterns

**Template for New Pattern:**
```markdown
### X. [Pattern Name]

**Version Added**: [Version] - [Date]  
**Purpose**: [Brief description]

**Implementation**:
[Code examples and explanation]

**Benefits**:
- [Benefit 1]
- [Benefit 2]

**Example**:
```python
[Code example]
```
```

#### 2. Update `business-requirements.md` (If Applicable)
**When to Update:**
- New business rules implemented
- Business processes modified
- User roles or permissions changed
- Data requirements updated

**What to Include:**
- Updated business rules
- Modified processes
- New constraints or assumptions
- Impact on existing requirements

#### 3. Update `tests-structure.md` (ALWAYS)
**What to Include:**
- New test files and their purpose
- New testing patterns used
- Updated test coverage metrics
- New test utilities or fixtures

**Template for New Tests:**
```markdown
#### [Test File Name] (`test_[component].py`)
- **[X] lines of tests** covering:
  - [Test category 1]
  - [Test category 2]
  - [Edge cases and error handling]
```

#### 4. Update `project-structure.md` (If Structure Changed)
**When to Update:**
- New files or directories added
- File purposes changed
- Architecture modifications
- New dependencies introduced

**What to Include:**
- Updated directory structure
- New file descriptions
- Modified architectural patterns
- Updated dependency information

### Version Control for Documentation
Each updated document MUST have its version incremented and date updated:

```markdown
**Version**: [X.Y]  
**Last Updated**: [Month Day, Year]
```

---

## Documentation Standards

### 1. Version Control
- Increment version number for significant updates
- Update "Last Updated" date for all changes
- Document what changed in each version

### 2. Structure Consistency
- Follow established document templates
- Use consistent heading structures
- Maintain table of contents
- Include code examples where appropriate

### 3. Code Documentation
- Document all public APIs
- Include docstrings for all functions and classes
- Provide usage examples
- Document business rules in code comments

### 4. Business Documentation
- Use business terminology
- Explain "why" not just "what"
- Include business impact assessment
- Document user experience considerations

---

## Code Quality Standards

### 1. Code Style
- Follow PEP 8 Python style guidelines
- Use meaningful variable and function names
- Keep functions focused and small
- Use type hints where appropriate

### 2. Architecture Compliance
- Follow established layered architecture
- Use dependency injection
- Implement proper separation of concerns
- Follow SOLID principles

### 3. Performance Considerations
- Consider caching for expensive operations
- Optimize database queries
- Handle large datasets efficiently
- Monitor memory usage

### 4. Security Requirements
- Implement proper access control
- Validate all input data
- Log security-relevant events
- Handle sensitive data appropriately

---

## Testing Requirements

### 1. Test Coverage
- **Minimum 85% overall coverage**
- **95%+ for core business logic**
- **90%+ for data layer**
- **80%+ for async operations**

### 2. Test Types Required
- **Unit Tests**: Test individual components
- **Integration Tests**: Test component interactions
- **Async Tests**: Test bot operations and flows
- **Database Tests**: Test data persistence

### 3. Test Organization
- One test file per source module
- Use descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)
- Use appropriate test fixtures and mocks

### 4. Test Documentation
- Document test purpose and scope
- Explain complex test scenarios
- Update test structure documentation
- Include performance test results

---

## Architecture Compliance

### 1. Layered Architecture
- **Presentation Layer**: Telegram handlers (`main.py`)
- **Business Logic**: Services (`services/`)
- **Data Access**: Repositories (`repositories/`)
- **Infrastructure**: Utilities (`utils/`)

### 2. Design Patterns
- **Repository Pattern**: For data access abstraction
- **Service Layer**: For business logic orchestration
- **Decorator Pattern**: For cross-cutting concerns
- **Strategy Pattern**: For algorithm variations

### 3. Dependency Management
- Use dependency injection
- Depend on abstractions, not concretions
- Follow dependency inversion principle
- Maintain loose coupling

### 4. Error Handling
- Use established exception hierarchy
- Implement graceful degradation
- Provide meaningful error messages
- Log errors with appropriate detail

---

## Quick Implementation Checklist

### **Step 1: Task Assignment**
- [ ] User provides clear task description and requirements
- [ ] AI Coder agent acknowledges and begins analysis

### **Step 2: Technical Decomposition** 
- [ ] Read relevant documentation files (`business-requirements.md`, `patterns.md`, `tests-structure.md`, `project-structure.md`)
- [ ] Understand business requirements and impact
- [ ] Create technical decomposition document in `tasks/` directory
- [ ] Use proper naming convention: `task-YYYY-MM-DD-[brief-description].md`
- [ ] Include all required sections: Business Context, Technical Requirements, Implementation Steps, Dependencies, Risks, Testing Strategy, Documentation Updates, Success Criteria
- [ ] Set status to "Draft"
- [ ] Present decomposition to user for review

### **Step 3: Decomposition Review**
- [ ] User reviews technical decomposition
- [ ] Address any feedback or requested changes
- [ ] Iterate until user approves decomposition
- [ ] Update status to "Approved"

### **Step 4: Implementation**
- [ ] Update task status to "In Progress" 
- [ ] Follow TDD approach: write tests first
- [ ] Implement in phases as defined in decomposition
- [ ] **MANDATORY**: Update decomposition document with real-time progress
- [ ] Mark completed steps with ✅ and timestamp
- [ ] Add implementation notes for key decisions
- [ ] Follow established patterns and code quality standards
- [ ] Maintain test coverage requirements
- [ ] Update status to "Completed" when done

### **Step 5: Documentation Updates**
- [ ] **Update `patterns.md`** (if new patterns added)
- [ ] **Update `business-requirements.md`** (if business rules changed)  
- [ ] **Update `tests-structure.md`** (always)
- [ ] **Update `project-structure.md`** (if structure changed)
- [ ] Update version numbers and dates in all modified documents
- [ ] Cross-reference completed task in decomposition document
- [ ] Verify test coverage meets requirements
- [ ] Run full test suite
- [ ] Move completed task file to `tasks/completed/` directory

### **Workflow Validation**:
- [ ] No implementation started without approved decomposition
- [ ] Task decomposition document maintained as single source of truth
- [ ] Real-time progress updates throughout implementation
- [ ] All documentation updated post-implementation
- [ ] Task properly archived upon completion

---

## Emergency Procedures

### If Implementation Breaks Existing Functionality:
1. **Immediate**: Revert changes if possible
2. **Investigate**: Identify root cause
3. **Fix**: Address issue following these guidelines
4. **Test**: Verify fix doesn't introduce new issues
5. **Document**: Update relevant documentation

### If Documentation Gets Out of Sync:
1. **Audit**: Review all documentation files
2. **Update**: Bring documentation current with code
3. **Verify**: Ensure consistency across all documents
4. **Version**: Update version numbers and dates

---

## Success Metrics

### Code Quality:
- Test coverage >85%
- No critical security vulnerabilities
- Performance within acceptable limits
- Architecture compliance maintained

### Documentation Quality:
- All documents current and accurate
- Version control properly maintained
- Business requirements clearly documented
- Technical decisions properly recorded

### Business Value:
- Features align with business requirements
- User experience improved or maintained
- System reliability maintained or improved
- Performance acceptable for business needs

---

## Contact and Escalation

### For Questions About:
- **Business Requirements**: Review `business-requirements.md`
- **Technical Architecture**: Review `patterns.md` and `project-structure.md`
- **Testing Approach**: Review `tests-structure.md`
- **Implementation Details**: Review existing code and documentation

### Escalation Path:
1. **Self-Service**: Review existing documentation
2. **Code Review**: Analyze existing implementations
3. **Documentation**: Ensure all documents are consulted
4. **Implementation**: Follow established patterns and guidelines

---

**Remember**: This project serves a religious community with real people depending on accurate participant management. Every line of code and every documentation update contributes to the success of meaningful spiritual events. Take pride in maintaining high standards of quality, documentation, and business alignment.

---

*This document is a living guide that should evolve with the project. When in doubt, prioritize business value, code quality, and comprehensive documentation.*