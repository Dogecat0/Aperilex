At the end of this message, I will ask you to do something. Please follow the "Explore, Review, Plan" workflow when you start.

# Explore
First, use parallel subagents to find and read files that may be useful for implementing the task/ticket.

**IMPORTANT: You MUST use subagents to read ANY file during exploration. DO NOT read files directly in the main thread.**

**PROHIBITED: Do NOT use grep, find, awk, sed, or any bash command tools for text searching or content extraction. Use file listing tools like glob to find files, then delegate actual file reading to subagents.**

**SUBAGENT GUIDANCE: Within subagents, always read files directly rather than using search tools. Extract information by reading the full file content and filtering programmatically.**

**READ TOOL: When using the Read tool, always read all lines of the file, do not read in sections.**

Design specific tasks for each subagent based on what you need to understand. Give focused missions like:
- "Extract authentication system interface and dependencies"
- "Find repository patterns and method signatures" 
- "Identify domain layer error handling patterns"
- "Map database schema for entities X, Y, Z"
- "Extract configuration and environment patterns"
- "Find API endpoint patterns and schemas"
- "Get coding style examples for feature X"

Subagents should return only task-relevant information, creating focused codemaps not exhaustive dumps. Target specific concepts: interface contracts, class hierarchies, configuration patterns, error handling, data flows, external integrations.

Always identify files to modify vs. reference examples.

Ignore test files during exploration - they will be examined in later phases if needed.

# Review
Before implementing the plan, it's important to conduct a comprehensive review of the existing codebase and any relevant documentation. This will help ensure that the implementation is consistent with the project's standards and practices.

**Architectural Analysis**: Think hard and write up the current state of the codebase, including:
- Relevant architectural decisions and design patterns in use
- Clean architecture layer separation and dependencies
- Domain-driven design patterns and domain boundaries
- CQRS implementation patterns (commands, queries, handlers)
- Repository patterns and data access strategies
- Service layer organization and dependency injection
- Error handling and validation approaches

**Technical Standards Review**: Analyze existing coding conventions:
- Type annotation patterns and MyPy compliance
- Pydantic schema design and validation patterns
- SQLAlchemy model patterns and database relationships
- Async/await usage patterns and concurrency approaches
- LLM integration patterns and provider abstractions
- Testing strategies and coverage expectations
- Code quality standards (formatting, linting, structure)

**Integration Patterns**: Review how the system handles:
- External service integrations (EdgarTools, OpenAI)
- Background task processing (Celery patterns)
- Caching strategies and Redis usage
- API endpoint design and response patterns
- Configuration management and environment handling

**Development Workflow**: Document relevant:
- Git branching strategies and commit patterns
- Development tool usage (Poetry, Docker, testing)
- Quality assurance processes and automation
- Documentation standards and requirements

# Plan
Next, think ultrahard and write up a detailed implementation plan. Consider all aspects necessary for a complete feature implementation:

**Core Implementation**: Break down the main development tasks:
- Domain layer changes (entities, value objects, domain services)
- Application layer updates (commands, queries, handlers, services)
- Infrastructure layer modifications (repositories, external services)
- Presentation layer changes (API endpoints, schemas, validation)

**Quality Assurance**: Plan comprehensive testing strategy:
- Unit tests for domain logic and business rules
- Integration tests for repository and service layers
- API endpoint testing with proper request/response validation
- End-to-end workflow testing where applicable
- Test data fixtures and mock strategies

**Documentation Requirements**: Identify documentation needs:
- API documentation updates (OpenAPI schema changes)
- Architecture documentation for new patterns
- Setup instructions for new dependencies
- Usage examples and integration guides

**Cross-Cutting Concerns**: Address system-wide impacts:
- Configuration updates and environment variables
- Database migration requirements (Alembic)
- Caching strategy updates and invalidation patterns
- Background task integration and queue management
- Error handling and logging enhancements
- Performance considerations and monitoring

If there are things you are not sure about, use parallel subagents to do some web research. They should only return useful information, no noise.

If there are things you still do not understand or questions you have for the user, pause here to ask them before continuing.

**VALIDATION**: Before proceeding, ensure the plan addresses:
- Consistency with existing architectural patterns
- Compliance with project coding standards
- Proper integration with existing infrastructure
- Comprehensive testing coverage
- Clear implementation sequence and dependencies
- Risk mitigation for complex changes

$ARGUMENTS