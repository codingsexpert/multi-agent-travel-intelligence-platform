# Development Plan: Multi-Agent AI Travel Intelligence & Dynamic Replanning Platform

This development plan breaks down the construction of the platform into **18 distinct, verifiable, and interview-ready phases**. Each phase is self-contained with concrete objectives, implementation tasks, target files/components, testing requirements, and measurable expected outputs.

---

## Phase Breakdown Matrix

| Phase | Title | Focus Area | Primary Deliverables |
|---|---|---|---|
| **Phase 0** | **Project Blueprint** | Architecture & Specification | Spec, Architecture, ADRs, Roadmap, Git repo |
| **Phase 1** | **Project Foundation** | Environment & Core Configuration | Python structure, dependencies, config loader, logger |
| **Phase 2** | **Streamlit UI Foundation** | Frontend Layout & State | Responsive UI shell, session state, navigation |
| **Phase 3** | **Supabase Integration** | Persistence, Auth & RLS | Database migrations, client wrapper, RLS policies |
| **Phase 4** | **LangGraph Core & Planner Agent** | Orchestration & Intent Parsing | Core graph engine, Pydantic schemas, Planner node |
| **Phase 5** | **Specialized Mock Agents** | Flight, Hotel, Activity, Weather | Mock engines, parallel graph fan-out nodes |
| **Phase 6** | **Budget Engine & Validator** | Deterministic Business Logic | Pure Python budget calculator, temporal validator |
| **Phase 7** | **MCP Integration** | Standardized Tool Layer | MCP client gateway, local MCP mock servers |
| **Phase 8** | **Real Travel APIs** | Live Data Feeds | Amadeus flights/hotels, OpenWeather, API error handling |
| **Phase 9** | **RAG & Supabase pgvector** | Static Domain Knowledge Base | Vector embeddings, destination knowledge, semantic search |
| **Phase 10** | **Live Web Search** | Fresh Information & Disruption Radar | Tavily/Brave search integration, query synthesizer |
| **Phase 11** | **Guardrails & Security** | Safety & Input/Output Protection | Injection detection, schema sanitization, PII filter |
| **Phase 12** | **Dynamic Replanning Engine** | Disruption Recovery & Delta State | Disruption triggers, surgical delta replanner, impact diff |
| **Phase 13** | **Human-in-the-Loop (HITL)** | User Approval Gates | LangGraph interrupt, interactive approval UI, resume |
| **Phase 14** | **LangSmith Observability** | Tracing, Telemetry & Metrics | Distributed run trees, token cost tracking, latency attribution |
| **Phase 15** | **Cost & Latency Optimization** | Performance Engineering | Prompt compression, model tiering, caching, parallelization |
| **Phase 16** | **Testing & Evaluation** | Quality Assurance & Benchmarks | Unit test suite, integration tests, LangGraph eval dataset |
| **Phase 17** | **Production UI Polish** | Enterprise Design & Visual Polish | Interactive timeline, card aesthetics, itinerary export (JSON/PDF) |
| **Phase 18** | **Deployment & Demo Runbook** | Production Readiness | Deployment guide, optional Dockerfile, interview script |

---

## Phase 0: Project Blueprint (Current Phase)
- **Objective**: Establish the conceptual, architectural, and version-control foundation of the project before writing application code.
- **Implementation Tasks**:
  1. Inspect local workspace and verify GitHub authentication.
  2. Create foundational documentation (`PROJECT_SPEC.md`, `ARCHITECTURE.md`, `ARCHITECTURE_DECISIONS.md`, `DEVELOPMENT_PLAN.md`, `README.md`).
  3. Create safe configuration template (`.env.example`) and security-first `.gitignore`.
  4. Initialize Git repository, link remote GitHub repository, create initial commit, and push.
- **Files / Components**:
  - `PROJECT_SPEC.md`, `ARCHITECTURE.md`, `ARCHITECTURE_DECISIONS.md`, `DEVELOPMENT_PLAN.md`, `README.md`, `.env.example`, `.gitignore`
- **Testing Requirements**:
  - Verify zero secrets in staging diff.
  - Verify clean markdown formatting and valid Mermaid diagrams.
  - Verify GitHub remote connectivity and repository creation.
- **Expected Output**:
  - Clean GitHub repository created and synchronized with foundational blueprint documents.

---

## Phase 1: Project Foundation & Configuration (Completed)
- **Objective**: Build a clean, maintainable Python foundation for the Multi-Agent Travel Intelligence Platform capable of starting in `DEMO_MODE` without external credentials.
- **Implementation Tasks**:
  1. Configured Python 3.11+ virtual environment (`.venv`) and pinned lightweight dependencies in `requirements.txt`.
  2. Implemented production-oriented project structure: `app/`, `agents/`, `graph/`, `models/`, `services/`, `repositories/`, `guardrails/`, `mcp/`, `rag/`, `evaluation/`, `tests/`, `config/`, and `utils/`.
  3. Implemented centralized configuration in `config/settings.py` using Pydantic Settings supporting `APP_ENV`, `DEMO_MODE`, Supabase, OpenAI, and LangSmith.
  4. Built structured logging utility in `utils/logger.py` with automated `SecretScrubbingFilter` to prevent accidental credential leakage in logs.
  5. Built structured application exception hierarchy in `utils/exceptions.py` (`AppError`, `ConfigurationError`, `ValidationError`, `ServiceError`, `GuardrailViolationError`).
  6. Implemented core domain models in `models/travel_request.py` (`TravelRequest`, `TravelerPreferences`, `TripConstraints`, `TripMetadata`) with Pydantic v2 date, travelers, and budget validations.
  7. Implemented Supabase client foundation in `services/supabase_service.py` with graceful `DEMO_MODE` fallback when credentials are not configured.
  8. Implemented non-network health check service in `services/health_service.py` evaluating environment and configuration readiness.
  9. Built minimal Phase 1 Streamlit dashboard entrypoint in `app/main.py` displaying environment status and an interactive Pydantic schema validation sandbox.
  10. Created exhaustive pytest test suite covering config loading, demo mode, model validations, health checks, and Supabase client behavior.
- **Files / Components**:
  - `requirements.txt`
  - `config/settings.py`, `config/__init__.py`
  - `utils/logger.py`, `utils/exceptions.py`, `utils/__init__.py`
  - `models/travel_request.py`, `models/__init__.py`
  - `services/supabase_service.py`, `services/health_service.py`, `services/__init__.py`
  - `app/main.py`, `app/__init__.py`
  - `agents/__init__.py`, `graph/__init__.py`, `repositories/__init__.py`, `guardrails/__init__.py`, `mcp/__init__.py`, `rag/__init__.py`, `evaluation/__init__.py`
  - `tests/test_config.py`, `tests/test_models.py`, `tests/test_health.py`, `tests/test_supabase.py`, `tests/test_logger_exceptions.py`
- **Testing Requirements**:
  - 15 unit tests passing with pytest (`pytest -v`).
  - Headless Streamlit launch test on port 8502 returning HTTP 200 OK without API keys.
- **Expected Output**:
  - Production-ready Python foundation verified and operational in offline `DEMO_MODE`.

---

## Phase 2: Streamlit UI Foundation (Completed)
- **Objective**: Build the initial production-quality Streamlit Travel Command Center, providing a modular 13-page architecture, session state management, and structured intake form.
- **Implementation Tasks**:
  1. Built modular Streamlit router and main entrypoint in `app/main.py`.
  2. Implemented clean session-state manager in `app/state/session.py` (`current_trip_request`, `current_trip_id`, `current_page`, `workflow_status`, `messages`, `recent_trips`).
  3. Created reusable UI components:
     - Navigation sidebar (`app/components/sidebar.py`) with 13 functional pages and DEMO_MODE badge
     - Structured travel request summary card (`app/components/trip_summary_card.py`)
  4. Implemented all 13 specialized pages in `app/pages/`:
     - `Dashboard`: Platform status, architecture readiness (LangGraph, MCP, RAG, Supabase, LangSmith), quick trip creator, and recent trip list
     - `New Trip`: Full Pydantic-validated travel intake form (Route, Dates, Travellers, Budget, Preferences, Style, Constraints)
     - `My Trips`: In-memory trip requests and history
     - `Conversation`: Interactive chat area with message history (LLM integration notice)
     - `Itinerary`: Day-by-day activity slot layouts (Morning, Afternoon, Evening) with transit, weather, and cost placeholders
     - `Flights`: Flight search and corridor analysis placeholder (Amadeus/MCP notice)
     - `Hotels`: Accommodation search and proximity clustering placeholder
     - `Activities`: Experience curation and pacing placeholder
     - `Weather`: 14-day forecast and outdoor hazard detection placeholder
     - `Budget`: Category expense breakdown grid (Flights, Hotels, Activities, Transit, Food, Misc, Contingency, Remaining Budget)
     - `Sources`: Citations and references placeholder (RAG, Web, APIs)
     - `Agent Trace`: 9 planned agents roster with status "Not started", telemetry metrics (latency, tool calls, token usage, cost)
     - `Settings`: Environment diagnostics, configuration presence indicators (secrets masked), and session controls
  5. Implemented comprehensive test suite in `tests/test_ui_form.py` and `tests/test_ui_state.py`.
- **Files / Components**:
  - `app/main.py`
  - `app/state/session.py`, `app/state/__init__.py`
  - `app/components/sidebar.py`, `app/components/trip_summary_card.py`, `app/components/__init__.py`
  - `app/pages/dashboard.py`, `app/pages/new_trip.py`, `app/pages/my_trips.py`, `app/pages/conversation.py`, `app/pages/itinerary.py`, `app/pages/flights.py`, `app/pages/hotels.py`, `app/pages/activities.py`, `app/pages/weather.py`, `app/pages/budget.py`, `app/pages/sources.py`, `app/pages/agent_trace.py`, `app/pages/settings.py`, `app/pages/__init__.py`
  - `tests/test_ui_form.py`, `tests/test_ui_state.py`
- **Testing Requirements**:
  - 24 unit tests passing with pytest (`pytest -v`).
  - Headless Streamlit launch test on port 8503 returning HTTP 200 OK without errors.
- **Expected Output**:
  - Interactive, modular Travel Command Center operational in DEMO_MODE.

---

## Phase 3: Supabase Integration (PostgreSQL, Auth & RLS) (Completed)
- **Objective**: Implement durable persistence, user authentication, and Row Level Security for trip data with seamless in-memory fallback in `DEMO_MODE`.
- **Implementation Tasks**:
  1. Wrote versioned SQL schema migration in `supabase/migrations/20260928000001_initial_schema.sql` covering `profiles`, `trips`, `trip_preferences`, `conversations`, `messages`, and `agent_runs` with indexes and triggers.
  2. Implemented strict Row Level Security (RLS) policies in `supabase/migrations/20260928000002_rls_policies.sql` ensuring authenticated users can only access their own data via `auth.uid()`.
  3. Built authentication service in `services/auth_service.py` integrating Supabase Auth (`sign_up`, `sign_in`, `sign_out`, `get_current_user`) with offline guest identity in `DEMO_MODE`.
  4. Implemented repository abstraction layer in `repositories/`:
     - `TripRepository`: CRUD for trips and preferences with strict user isolation
     - `ConversationRepository`: Thread creation and retrieval
     - `MessageRepository`: Chronological message persistence with role validation
     - `AgentRunRepository`: Execution telemetry and audit tracking
     - `MockDataStore`: Isolated in-memory fallback store tagging records as `demo: True`
  5. Connected Streamlit UI:
     - `New Trip`: Persists trip, preferences, conversation, and initial user message via repositories
     - `My Trips`: Displays user-isolated trips with "Open Trip" activation
     - `Conversation`: Loads and appends thread messages via repositories
     - `Settings`: Live sign in / sign up / sign out controls when configured, or clear DEMO MODE local guest identity banner
  6. Added comprehensive unit tests in `tests/test_repositories.py`, `tests/test_auth.py`, and `tests/test_schema_sql.py`.
- **Files / Components**:
  - `supabase/migrations/20260928000001_initial_schema.sql`, `supabase/migrations/20260928000002_rls_policies.sql`, `supabase/README.md`
  - `services/auth_service.py`
  - `repositories/base.py`, `repositories/mock_store.py`, `repositories/trip_repository.py`, `repositories/conversation_repository.py`, `repositories/message_repository.py`, `repositories/agent_run_repository.py`, `repositories/__init__.py`
  - `app/state/session.py`, `app/state/__init__.py`
  - `app/pages/new_trip.py`, `app/pages/my_trips.py`, `app/pages/conversation.py`, `app/pages/settings.py`
  - `tests/test_repositories.py`, `tests/test_auth.py`, `tests/test_schema_sql.py`
- **Testing Requirements**:
  - 32 unit tests passing with pytest (`pytest -v`).
  - Headless Streamlit smoke test on port 8504 returning HTTP 200 OK without errors.
- **Expected Output**:
  - Production-ready database schema, RLS policies, Supabase Auth integration, and repository layer operational with full DEMO_MODE fallback.

---

## Phase 4: LangGraph Core Engine & Planner Agent (Completed)
- **Objective**: Initialize the central LangGraph state graph, define state schemas with Pydantic v2, and implement the Planner Agent with clarification routing, structured output extraction, and loop protection.
- **Implementation Tasks**:
  1. Defined strongly-typed `TravelState` TypedDict and `WorkflowStatus` enum in `graph/state.py`.
  2. Built Pydantic schemas in `models/planner.py`: `NormalizedTravelRequest`, `ClarificationRequest`, and `PlannerResult`.
  3. Created LLM abstraction and deterministic fallback in `services/llm_service.py` (`LLMService` with `DemoPlannerExtractor`) supporting multilingual/Hinglish patterns and strict retry limits (`MAX_PLANNER_RETRIES = 2`).
  4. Implemented Planner reasoning node in `agents/planner.py` with deterministic validation and loop protection (`MAX_GRAPH_STEPS = 10`).
  5. Implemented Clarification node in `agents/clarification.py` to route incomplete or conflicting requirements to `NEEDS_CLARIFICATION`.
  6. Built and compiled the LangGraph StateGraph workflow in `graph/workflow.py`: `START -> planner -> [conditional router] -> clarification / END (READY_FOR_SPECIALIZED_AGENTS)`.
  7. Implemented planning execution API in `services/planning_service.py` (`run_travel_planning`), integrating trip context, conversation message history, session state sync, and `agent_runs` telemetry.
  8. Integrated with Streamlit UI in `app/pages/new_trip.py` and `app/pages/conversation.py`.
  9. Added comprehensive unit and integration tests across 5 test suites (`tests/test_planner_models.py`, `tests/test_demo_extractor.py`, `tests/test_llm_service.py`, `tests/test_langgraph_workflow.py`, `tests/test_planning_service.py`).
- **Files / Components**:
  - `graph/state.py`, `graph/workflow.py`, `graph/__init__.py`
  - `models/planner.py`, `models/__init__.py`
  - `agents/planner.py`, `agents/clarification.py`, `agents/__init__.py`
  - `services/llm_service.py`, `services/planning_service.py`
  - `app/pages/new_trip.py`, `app/pages/conversation.py`
  - `tests/test_planner_models.py`, `tests/test_demo_extractor.py`, `tests/test_llm_service.py`, `tests/test_langgraph_workflow.py`, `tests/test_planning_service.py`
- **Testing Requirements**:
  - 57 unit and integration tests passing (`pytest -v`).
  - Tested complete requests, missing parameters, date conflicts, negative budget, zero duration/travelers, loop protection, retry limits, and DEMO_MODE fallback.
- **Expected Output**:
  - Graph accepts natural language user input and outputs structured `PlannerResult` reaching `READY_FOR_SPECIALIZED_AGENTS` or `NEEDS_CLARIFICATION`.

---

## Phase 5: Specialized Mock Domain Agents (Completed)
- **Objective**: Implement Flight, Hotel, Activity, Weather, and Research agents with deterministic mock engines, parallel execution, failure isolation, and Pydantic schemas.
- **Implementation Tasks**:
  1. Built strongly typed Pydantic models in `models/specialized_options.py`: `FlightOption`, `HotelOption`, `ActivityOption`, `WeatherObservation`, `DestinationResearch`.
  2. Built standardized base agent execution wrapper in `agents/base_agent.py` (`execute_agent_safely`) providing uniform telemetry, timing, and failure isolation.
  3. Implemented 5 specialized domain agents in `agents/`:
     - `FlightAgent` (`agents/flight_agent.py`): Aviation route planning and fare estimation with mock catalog.
     - `HotelAgent` (`agents/hotel_agent.py`): Lodging discovery, neighborhood scoring, and nightly rates.
     - `ActivityAgent` (`agents/activity_agent.py`): Point-of-interest curation and dining experiences matching interests.
     - `WeatherAgent` (`agents/weather_agent.py`): Climatological forecasts, precipitation risks, and advisory warnings.
     - `ResearchAgent` (`agents/research_agent.py`): Destination overview, cultural etiquette, travel tips, and customs.
  4. Updated LangGraph state machine in `graph/workflow.py`: Planner conditionally fans out in parallel to Flight, Hotel, Activity, and Weather nodes, converging into the Research Agent before `END`.
  5. Implemented failure isolation: individual agent failures are safely caught, recorded as `FAILED` in `agent_runs`, appended to `warnings`, and transition workflow status to `PARTIAL_RESULTS` without crashing the graph.
  6. Updated Streamlit UI across `app/pages/flights.py`, `app/pages/hotels.py`, `app/pages/activities.py`, `app/pages/weather.py`, `app/pages/sources.py`, `app/pages/agent_trace.py`, and `app/pages/new_trip.py`.
  7. Added comprehensive test coverage across `tests/test_specialized_agents.py` and `tests/test_multi_agent_workflow.py`.
- **Files / Components**:
  - `models/specialized_options.py`, `models/__init__.py`
  - `agents/base_agent.py`, `agents/flight_agent.py`, `agents/hotel_agent.py`, `agents/activity_agent.py`, `agents/weather_agent.py`, `agents/research_agent.py`, `agents/__init__.py`
  - `graph/state.py`, `graph/workflow.py`
  - `services/planning_service.py`
  - `app/pages/flights.py`, `app/pages/hotels.py`, `app/pages/activities.py`, `app/pages/weather.py`, `app/pages/sources.py`, `app/pages/agent_trace.py`, `app/pages/new_trip.py`
  - `tests/test_specialized_agents.py`, `tests/test_multi_agent_workflow.py`
- **Testing Requirements**:
  - 70 unit and integration tests passing (`pytest -v`).
  - Verified parallel execution, failure isolation with `PARTIAL_RESULTS`, schema validation, demo markers, and telemetry.
- **Expected Output**:
  - Graph populates state with flight, hotel, activity, weather, and research deliverables, terminating with `READY_FOR_VALIDATION` or `PARTIAL_RESULTS`.

---

## Phase 6: Budget Engine & Validator/Safety Agent (Pure Python) (Completed)
- **Objective**: Implement deterministic financial aggregation and constraint validation in pure Python, preventing LLM arithmetic errors and detecting inconsistent or infeasible travel plans.
- **Implementation Tasks**:
  1. Built strongly typed Pydantic models in `models/budget.py` (`BudgetItemCategory`, `BudgetItem`, `BudgetBreakdown`, `BudgetStatus`, `BudgetSummary`) and `models/validation.py` (`ValidationSeverity`, `ValidationIssue`, `ValidationResult`).
  2. Implemented pure Python `BudgetEngine` in `engines/budget_engine.py`:
     - Calculates flights, hotels, activities, food allowances, local transit, and miscellaneous buffer.
     - Deterministic arithmetic: `total_estimated_cost = flights + hotels + activities + food + transport + misc`.
     - Strict budget mode: flags `OVER_BUDGET` when estimated > budget, calculating exact variance and utilization percentage.
     - Currency handling: assumes normalized figures and detects currency mismatches across line items.
  3. Implemented pure Python `ValidatorEngine` in `engines/validator_engine.py`:
     - Budget validation: verifies positive caps, non-negative line items, and over-budget warnings.
     - Dates validation: enforces start/end date presence, valid ISO parsing, non-inverted date sequences (`end_date >= start_date`), and flexible duration support.
     - Traveller validation: enforces positive traveler headcount (`travelers >= 1`).
     - Flight logistics: verifies flight departure strictly precedes arrival (`departure < arrival`).
     - Lodging consistency: verifies check-in/check-out validity and non-negative nightly rates.
     - Activity schedule: detects duplicate activity recommendations and evaluates travel-time buffer conflicts (`POSSIBLE_TIME_CONFLICT`).
     - Climatological integrity: detects Weather Agent failures and flags `WEATHER_UNAVAILABLE` as a non-fatal warning without inventing data.
  4. Integrated LangGraph workflow in `graph/workflow.py`:
     - Added `budget_engine` node (`agents/budget_agent.py`) and `validator` node (`agents/validator_agent.py`).
     - Connected convergence pipeline: `[flight, hotel, activity, weather] -> research -> budget_engine -> validator -> END`.
     - Updated workflow terminal statuses: `READY_FOR_ITINERARY`, `READY_WITH_WARNINGS`, and `VALIDATION_FAILED`.
  5. Updated Streamlit Command Center UI:
     - `Budget` page (`app/pages/budget.py`): top metric KPIs, feasibility banner, 6-category breakdown grid, itemized financial audit table, and currency disclaimer.
     - `Itinerary` page (`app/pages/itinerary.py`): deterministic feasibility & constraint audit checklist and detailed issues log.
     - `New Trip` page (`app/pages/new_trip.py`): 8-component execution checklist and deterministic feasibility audit chips.
     - `Agent Trace` page (`app/pages/agent_trace.py`): labels Budget Engine and Validator as `DETERMINISTIC` with live duration, status, and telemetry.
  6. Added comprehensive unit and integration test suite:
     - `tests/test_budget_engine.py`: 8 unit tests covering all budget feasibility scenarios.
     - `tests/test_validator_engine.py`: 11 validator unit tests + 3 LangGraph end-to-end integration tests.
- **Files / Components**:
  - `models/budget.py`, `models/validation.py`, `models/__init__.py`
  - `engines/budget_engine.py`, `engines/validator_engine.py`, `engines/__init__.py`
  - `agents/budget_agent.py`, `agents/validator_agent.py`, `agents/base_agent.py`, `agents/__init__.py`
  - `graph/state.py`, `graph/workflow.py`
  - `services/planning_service.py`
  - `app/pages/budget.py`, `app/pages/itinerary.py`, `app/pages/new_trip.py`, `app/pages/agent_trace.py`
  - `tests/test_budget_engine.py`, `tests/test_validator_engine.py`
- **Testing Requirements**:
  - 93 unit and integration tests passing (`pytest -v`).
  - Verified exact math, budget overage detection, time conflict detection, partial agent degradation, and Streamlit execution.
- **Expected Output**:
  - Exact financial arithmetic and constraint validation with zero LLM math or hallucination risk.

---

## Phase 7: Model Context Protocol (MCP) Integration (Completed)
- **Objective**: Introduce a production-grade Model Context Protocol (MCP) architecture decoupling agents from provider APIs through typed tools, least privilege permissions, security sandboxing, and full observability.
- **Implementation Tasks**:
  1. Built strongly typed Pydantic models under `models/mcp.py`:
     - Infrastructure & Telemetry: `ToolExecutionStatus`, `ToolExecutionError`, `MCPToolCall`, `MCPToolResult`.
     - Flight MCP: `SearchFlightsInput`, `SearchFlightsOutput`, `CompareFlightsInput`, `CompareFlightsOutput`, `GetFlightDetailsInput`, `GetFlightDetailsOutput`.
     - Hotel MCP: `SearchHotelsInput`, `SearchHotelsOutput`, `GetHotelDetailsInput`, `GetHotelDetailsOutput`.
     - Maps MCP: `PlaceItem`, `SearchPlacesInput`, `SearchPlacesOutput`, `CalculateRouteInput`, `CalculateRouteOutput`, `EstimateTravelTimeInput`, `EstimateTravelTimeOutput`.
     - Weather MCP: `GetCurrentWeatherInput`, `GetCurrentWeatherOutput`, `GetForecastInput`, `GetForecastOutput`, `GetWeatherAlertsInput`, `GetWeatherAlertsOutput`.
     - Search MCP: `SearchResultItem`, `WebSearchInput`, `WebSearchOutput`, `FetchPageInput`, `FetchPageOutput`, `SearchNewsInput`, `SearchNewsOutput`.
     - Currency MCP: `GetExchangeRateInput`, `GetExchangeRateOutput`.
  2. Implemented `MCPSecurityManager` in `mcp/security.py`:
     - Least-privilege enforcement via `AGENT_TOOL_PERMISSIONS` allowlist.
     - URL validation & SSRF prevention blocking localhost, loopbacks, and RFC-1918 private subnets.
     - Untrusted data isolation: marks all web/search outputs as `untrusted=True` and strips prompt injection attack vectors.
     - Secret scrubbing in telemetry: masks `api_key`, `secret`, `token`, `password`, `authorization`.
  3. Implemented MCP Tool Registry in `mcp/registry.py`:
     - `MCPToolDescriptor` binding tool name, description, schemas, and invocation handler.
     - Registers all 14 domain tools across Flight, Hotel, Maps, Weather, Search, and Currency domains.
  4. Implemented `MCPClient` in `mcp/client.py`:
     - Centralized gateway enforcing permission checks, Pydantic input validation, execution retries, timeouts, and recent call auditing (`get_recent_calls()`).
  5. Updated all specialized agents and calculation engines to invoke tools via `MCPClient`:
     - Flight Agent -> Flight MCP (`search_flights`, `compare_flights`)
     - Hotel Agent -> Hotel MCP (`search_hotels`)
     - Activity Agent -> Maps MCP (`search_places`, `estimate_travel_time`)
     - Weather Agent -> Weather MCP (`get_forecast`, `get_weather_alerts`)
     - Research Agent -> Search MCP (`web_search`, `search_news`)
     - Budget Engine -> Currency MCP (`get_exchange_rate`)
  6. Updated `TravelState` in `graph/state.py` with `Annotated[List[Dict[str, Any]], operator.add]` for concurrent tool call reduction.
  7. Updated Streamlit Travel Command Center (`app/pages/agent_trace.py`):
     - Displays hierarchical routing tree (Agent -> MCP Server -> Tools).
     - Live MCP Tool telemetry table showing status chips, latencies, retries, mode, and errors.
     - Security and least-privilege policy summary matrix.
  8. Created comprehensive test suite in `tests/test_mcp.py` (28 unit and integration tests covering all 20 required points).
- **Files / Components**:
  - `models/mcp.py`, `models/__init__.py`
  - `mcp/security.py`, `mcp/registry.py`, `mcp/client.py`, `mcp/__init__.py`
  - `mcp/tools/flight_tools.py`, `mcp/tools/hotel_tools.py`, `mcp/tools/maps_tools.py`, `mcp/tools/weather_tools.py`, `mcp/tools/search_tools.py`, `mcp/tools/currency_tools.py`, `mcp/tools/__init__.py`
  - `agents/flight_agent.py`, `agents/hotel_agent.py`, `agents/activity_agent.py`, `agents/weather_agent.py`, `agents/research_agent.py`, `agents/budget_agent.py`
  - `engines/budget_engine.py`, `graph/state.py`
  - `app/pages/agent_trace.py`
  - `tests/test_mcp.py`
- **Testing Requirements**:
  - 121 unit and integration tests passing (`pytest -v`).
  - Verified least privilege, SSRF prevention, untrusted content sanitization, retry behavior, demo marking, and agent integration.
- **Expected Output**:
  - Decoupled agent architecture communicating with standard MCP tools with least privilege and security boundaries.

---

## Phase 8: Real External APIs & Provider Integration (Completed)
- **Objective**: Replace mock/demo implementations with real external provider adapters behind the MCP tool boundary, ensuring agents never call external APIs directly while providing robust resiliency, rate limiting, and caching.
- **Architecture**:
  ```
  Agent  ──>  MCP Tool  ──>  Provider Adapter  ──>  External API
                                                        │
  Agent  <──  MCP Tool  <──  Normalized Model  <────────┘
  ```
- **Implementation Tasks**:
  1. Base Provider Infrastructure & Resiliency (`mcp/providers/base.py`):
     - `BaseProvider` using `httpx.Client` with bounded exponential backoff retries (`max_retries=2`).
     - Error classification hierarchy: `ProviderError`, `ProviderConfigurationError`, `ProviderAuthenticationError`, `ProviderRateLimitError` (HTTP 429 with `Retry-After`), `ProviderTimeoutError` (5-8s ceilings), `ProviderNetworkError` (5xx), `ProviderResponseValidationError`.
     - Header sanitization (`_sanitize_headers`) ensuring secrets and tokens are redacted.
     - `SourceAttribution` tracking provider provenance, source URL, timestamp, and mode.
     - Context variable (`_execution_mode_ctx`) propagating execution mode from `MCPClient` into provider adapters.
  2. In-Memory TTL Cache (`mcp/providers/cache.py`):
     - `ProviderCache` providing thread-safe caching with per-key expiration and hit/miss statistics.
  3. External Provider Adapters (`mcp/providers/`):
     - **Currency Provider** (`currency_provider.py`): Frankfurter API (live European Central Bank reference exchange rates, 1-hour caching, 1:1 identity optimization, deterministic mock fallback).
     - **Weather Provider** (`weather_provider.py`): Open-Meteo API (WMO standard meteorological data, geocoding resolution, live daily forecasts, storm alerts, 10-minute caching).
     - **Maps / Places Provider** (`maps_provider.py`): Photon (OpenStreetMap geocoding & POI search) and OSRM (route calculation & transit duration estimation, 1-hour caching).
     - **Search Provider** (`search_provider.py`): Tavily AI search and Wikipedia OpenSearch API with strict untrusted data isolation (`untrusted=True`), prompt injection stripping, and SSRF-blocked `fetch_page`.
     - **Flight Provider** (`flight_provider.py`): Amadeus GDS Aviation API with OAuth2 client credentials token caching, flight search, ranking, and `ProviderConfigurationError` when keys are unconfigured.
     - **Hotel Provider** (`hotel_provider.py`): Amadeus Hospitality API with city code mapping, lodging search, and amenity normalization.
  4. Tool Delegation (`mcp/tools/`):
     - Rewired all MCP domain tools (`flight_tools.py`, `hotel_tools.py`, `maps_tools.py`, `weather_tools.py`, `search_tools.py`, `currency_tools.py`) to delegate to provider adapters.
  5. Gateway Telemetry & UI (`mcp/client.py`, `app/pages/agent_trace.py`):
     - Updated `MCPClient` to capture provider provenance, execution mode, retries, and structured error codes.
     - Updated Streamlit Agent Trace page with provider routing tree (`Amadeus GDS`, `Open-Meteo WMO`, `Frankfurter (ECB)`, `Photon/OSRM`, `Wikipedia/Tavily`), Live vs Demo badges, latency benchmarks, and failure diagnostics.
  6. Configuration & Security (`config/settings.py`, `.env.example`):
     - Added provider credential fields (`amadeus_client_id`, `amadeus_client_secret`, `openweather_api_key`, `tavily_api_key`, `google_places_api_key`).
     - Kept `.env` gitignored with zero committed credentials.
  7. Comprehensive Testing (`tests/test_providers.py`):
     - 23 unit tests covering provider configuration, missing credentials, parsing, Pydantic validation, timeouts, retries, 429 rate limits, 5xx backoff, untrusted sanitization, and architectural boundary verification.
- **Files / Components**:
  - `config/settings.py`, `.env.example`
  - `mcp/providers/base.py`, `mcp/providers/cache.py`, `mcp/providers/currency_provider.py`, `mcp/providers/weather_provider.py`, `mcp/providers/maps_provider.py`, `mcp/providers/search_provider.py`, `mcp/providers/flight_provider.py`, `mcp/providers/hotel_provider.py`, `mcp/providers/__init__.py`
  - `mcp/tools/currency_tools.py`, `mcp/tools/flight_tools.py`, `mcp/tools/hotel_tools.py`, `mcp/tools/maps_tools.py`, `mcp/tools/weather_tools.py`, `mcp/tools/search_tools.py`
  - `mcp/client.py`, `models/mcp.py`, `graph/__init__.py`
  - `app/pages/agent_trace.py`
  - `tests/test_providers.py`
- **Testing Requirements**:
  - 144 unit and integration tests passing (`pytest -v`).
  - Verified mock and live parsing, failure isolation, retry policies, secret masking, and agent boundary preservation.
- **Expected Output**:
  - Legitimate live external API integrations with zero direct calls from agents, safe mock fallback in DEMO mode, and clear UI diagnostics.

---

## Phase 9: RAG Knowledge Base & Supabase pgvector (Completed)
- **Objective**: Implement a production-grade Retrieval-Augmented Generation (RAG) pipeline using Supabase PostgreSQL with `pgvector`, HNSW indexing, deterministic document chunking, metadata filtering, prompt injection defense, and agent integration.
- **Implementation Tasks**:
  1. Created migration `supabase/migrations/20260928000003_pgvector_rag.sql`:
     - Enabled `vector` extension.
     - Created `public.travel_documents` table with 1536-dim vector column, HNSW cosine index, and relational indexes.
     - Established Row Level Security (RLS) policies for public curated knowledge and user-private isolation.
     - Implemented `match_travel_documents` RPC function for combined semantic similarity and metadata filtering.
  2. Implemented RAG and pgvector domain models in `models/rag.py`:
     - `SourceTrustLevel` (`OFFICIAL`, `CURATED`, `REFERENCE`, `UNKNOWN`).
     - `DocumentMetadata`, `DocumentChunk`, `RAGRetrievalQuery`, `RetrievedChunk`, `RAGRetrievalResult`.
     - Prompt injection defenses: `sanitize_retrieved_content` and `format_retrieved_context_defensively`.
  3. Created vector embedding abstraction in `rag/embeddings.py`:
     - `BaseEmbeddingService`, `OpenAIEmbeddingService` (model: `text-embedding-3-small`, dim: 1536).
     - `MockEmbeddingService`: Deterministic unit-normalized 1536-dim float vectors for offline `DEMO_MODE=true`.
     - `EmbeddingConfigurationError` raised when live credentials are missing in production mode.
  4. Implemented document ingestion pipeline in `rag/ingestion.py`:
     - Formats supported: Markdown (.md), Plain Text (.txt), JSON (.json).
     - Text cleaning, control character stripping, and whitespace normalization.
     - Deterministic chunking preserving paragraph/sentence boundaries (`rag_chunk_size=500`, `rag_chunk_overlap=80`).
     - SHA-256 content hash deduplication avoiding redundant chunk creation and embedding costs.
  5. Created curated baseline seed knowledge base under `rag/seed_data/`:
     - Tokyo cultural customs guide and landmark experiences guide.
     - Paris cultural etiquette, museum guidelines, and dining norms.
     - London transportation and escalator rules guide.
     - New York City neighborhoods, tipping, and subway customs guide.
     - Delhi heritage monuments and temple manners guide.
     - Rome Vatican dress code and historic fountain rules guide.
  6. Implemented reusable retrieval service in `rag/retriever.py`:
     - `TravelKnowledgeRetriever` supporting hybrid semantic similarity + metadata filters (`destination`, `country`, `category`, `source_trust`, `is_public`/`user_id`).
     - Live Supabase pgvector RPC search with fallback to in-memory `MockKnowledgeStore` in DEMO_MODE.
     - Defensively tags all retrieved chunks as `untrusted: True`.
  7. Integrated RAG into specialized agents:
     - `ActivityAgent`: Queries curated attractions and cultural heritage, enriching activity descriptions and attaching verified citations.
     - `ResearchAgent`: Queries local customs, etiquette, and travel tips, attaching RAG citations to `sources`.
     - Added `rag_retrievals` telemetry to `TravelState` in `graph/state.py`.
  8. Updated Streamlit Travel Command Center:
     - `app/pages/sources.py`: Interactive RAG Sandbox with vector similarity search, destination/category filters, and knowledge base explorer.
     - `app/pages/agent_trace.py`: Live RAG Knowledge Retrieval audit table and execution metrics.
  9. Built comprehensive test suite in `tests/test_rag.py` (21 unit and integration tests covering all 22 required points).
- **Files / Components**:
  - `supabase/migrations/20260928000003_pgvector_rag.sql`
  - `config/settings.py`, `utils/exceptions.py`
  - `models/rag.py`, `models/__init__.py`
  - `rag/embeddings.py`, `rag/ingestion.py`, `rag/retriever.py`, `rag/__init__.py`
  - `rag/seed_data/tokyo_customs.md`, `rag/seed_data/tokyo_attractions.md`, `rag/seed_data/paris_culture.md`
  - `rag/seed_data/london_transport_culture.md`, `rag/seed_data/new_york_guide.md`, `rag/seed_data/delhi_heritage.md`, `rag/seed_data/rome_heritage.md`
  - `agents/activity_agent.py`, `agents/research_agent.py`, `graph/state.py`
  - `app/pages/sources.py`, `app/pages/agent_trace.py`
  - `tests/test_rag.py`
- **Testing Requirements**:
  - 165 unit and integration tests passing (`pytest -v`).
  - Verified pgvector schema, embedding dimensions, document ingestion, chunking, deduplication, metadata filtering, prompt injection defense, private document isolation, and DEMO_MODE.
- **Expected Output**:
  - Stable, curated travel knowledge grounded in pgvector and delivered safely to reasoning agents with authentic source attribution.

---

## Phase 10: Web Search & Fresh Information Research *(Completed)*
- **Objective**: Implement a production-oriented fresh web research layer through the existing Search MCP boundary, retrieving current facts (festivals, temporary attraction closures, transport strikes, travel advisories, and recent headlines) that must not come from static RAG.
- **Completed Implementation**:
  1. Extended Search MCP schemas in `models/mcp.py` and `models/research.py`:
     - `WebSearchInput` & `WebSearchOutput`: added `destination`, `recency` (`today`, `24h`, `7d`, `30d`, `all`), `language`, `allowed_domains`.
     - `SearchResultItem`: added `source_type`, `published_at`, `retrieved_at`, `relevance_score`, `untrusted=True`.
     - `FetchPageInput` & `FetchPageOutput`: sandboxed HTML retrieval with `headings`, `source_domain`, `source_type`.
     - `SearchNewsInput` & `SearchNewsOutput`: specialized regional discovery for current events and disruptions.
     - `SourceTrustCategory` (`OFFICIAL`, `NEWS`, `REFERENCE`, `COMMUNITY`, `UNKNOWN`) and `classify_domain_trust()` classifier.
     - `ResearchFinding`, `ConflictingClaim`, and `FreshWebResearchResult`.
  2. Implemented Search MCP provider adapter in `mcp/providers/search_provider.py`:
     - `web_search`: Queries Tavily AI Search, Brave Search, or keyless Wikipedia OpenSearch API in LIVE mode; deterministic rich mock in DEMO mode.
     - `fetch_page`: Enforces SSRF defense, bounded timeout (5s), response size cap (< 500KB), and clean text extraction.
     - `search_news`: Queries regional headlines, disruptions, and festivals with domain trust classification.
     - Thread-safe TTL caching (`ProviderCache`) and HTTP 429 rate limit handling with `Retry-After`.
     - Explicit `ProviderConfigurationError` raised when live credentials are required but missing.
  3. Hardened security boundaries in `mcp/security.py`:
     - Strict SSRF defense blocking loopback (`localhost`, `127.0.0.1`, `[::1]`), private subnets (`10.x`, `192.168.x`, `172.16-31.x`), IPv6 unique local (`fc00::`, `fe80::`), and cloud metadata (`169.254.169.254`, `metadata.google.internal`).
     - Protocol validation: blocks `file://`, `ftp://`, and malformed URLs.
     - Domain allowlist enforcement for targeted page fetches.
     - Prompt injection defense: all retrieved content tagged `untrusted: True`; regex neutralizers defang instruction overrides.
     - Bounded HTML text extraction: strips `<script>`, `<style>`, `<nav>`, `<header>`, `<footer>`, `<aside>`, and tracking tags.
  4. Built research orchestration layer in `services/research_service.py`:
     - `InformationRouter`: Deterministic routing separating Curated RAG, Operational MCP APIs, and Fresh Web Search.
     - `ResearchService`: Orchestrates `search_news` -> `web_search` -> `fetch_page` on official portals.
     - Authoritative verification: Requires `OFFICIAL` sources for visa and entry mandates, warning if incomplete.
     - Conflict detection: Captures `ConflictingClaim` records when independent sources report contradictory facts.
  5. Integrated with Research Agent (`agents/research_agent.py`):
     - Merges curated RAG cultural intelligence with fresh web search findings.
     - Populates `DestinationResearch` with `fresh_findings`, `conflicts`, and `official_verified`.
     - Returns `fresh_research` in state delta and records tool calls for telemetry.
  6. Updated Streamlit Travel Command Center:
     - `app/pages/sources.py`: Interactive Fresh Web Research sandbox with recency filters, source trust badges, conflict alerts, and source-selection diagram.
     - `app/pages/agent_trace.py`: Live Search MCP execution telemetry.
  7. Built comprehensive test suite in `tests/test_search.py`:
     - 30 unit and integration tests covering all specified requirements.
- **Files / Components**:
  - `models/research.py`, `models/mcp.py`, `models/__init__.py`, `models/specialized_options.py`
  - `mcp/security.py`, `mcp/providers/search_provider.py`, `mcp/tools/search_tools.py`
  - `services/research_service.py`, `agents/research_agent.py`, `graph/state.py`
  - `app/pages/sources.py`, `app/pages/agent_trace.py`
  - `tests/test_search.py`
- **Testing Requirements**:
  - 195/195 tests passing across entire repo (`pytest -v`).
  - Verified schemas, recency, source classification, SSRF protection, prompt injection defense, conflict detection, DEMO/LIVE mode, and routing.
- **Expected Output**:
  - Secure, production-oriented fresh web research layer delivering grounded, time-sensitive travel intelligence.

---

## Phase 11: Production Guardrails & Security Implementation (COMPLETED)
- **Objective**: Build a centralized, Zero-Trust production security layer protecting user inputs, agent reasoning, tool invocations, RAG contexts, web contents, outputs, and runtime limits.
- **Implementation Tasks**:
  1. Build `guardrails/input.py`: Validate user inputs, detect prompt injection / jailbreak patterns, validate travel parameters (dates, budgets, currencies, traveler counts), and sanitize PII.
  2. Build `guardrails/tools.py`: Enforce least-privilege role allowlists, argument validation, and autonomously block high-risk actions (booking, payments, cancellations).
  3. Build `guardrails/output.py`: Validate agent outputs against Pydantic schemas, verify positive value bounds, and check fact/source metadata attribution.
  4. Build `guardrails/security.py`: Implement `SecretRedactor` (continuous masking of credentials/tokens), `PIISanitizer`, `RateLimiter` (sliding-window limit), `WorkflowCircuitBreaker` (step/tool/retry/timeout ceilings), and `SecurityAuditor`.
  5. Integrate into LangGraph (`graph/workflow.py`), MCP Client (`mcp/client.py`), and Streamlit UI (`app/pages/agent_trace.py` & `app/pages/settings.py`).
  6. Build comprehensive test suite `tests/test_guardrails.py` covering all 36 specified security scenarios.
- **Files / Components**:
  - `guardrails/input.py`, `guardrails/tools.py`, `guardrails/output.py`, `guardrails/security.py`, `guardrails/__init__.py`
  - `tests/test_guardrails.py`
  - Updates: `config/settings.py`, `utils/exceptions.py`, `mcp/client.py`, `graph/state.py`, `graph/workflow.py`, `services/planning_service.py`, `app/pages/agent_trace.py`, `app/pages/settings.py`
- **Testing Requirements**:
  - 36 dedicated deterministic security tests covering input validation, prompt injection, tool authorization, high-risk blocking, SSRF, secret redaction, PII sanitization, rate limits, circuit breakers, RLS isolation, output schemas, and DEMO/LIVE consistency. All 231 tests pass.
- **Expected Output**:
  - Hardened execution pipeline safe against adversarial inputs, data exfiltration, runaway loops, and unauthorized tool calls.

---


## Phase 12: Dynamic Replanning Engine (COMPLETED)
- **Objective**: Build a deterministic Dynamic Replanning Engine that allows the multi-agent travel system to react to changing conditions (flight cancellations, weather alerts, hotel sold out, budget cuts, user revisions) without restarting the entire workflow.
- **Implementation Tasks**:
  1. Built strongly typed Pydantic models in `models/replanning.py`:
     - `ChangeEventType`: 15 categorical disruption types (`FLIGHT_CANCELLED`, `FLIGHT_DELAYED`, `WEATHER_ALERT`, `HOTEL_UNAVAILABLE`, `BUDGET_CHANGED`, etc.).
     - `ChangeEventSeverity`: `INFO`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.
     - `NodeExecutionAction`: `RERUN`, `REUSE`, `INVALIDATE`, `SKIP`.
     - `ChangeEvent`, `ImpactAnalysis`, `ItineraryVersion`, `ReplanningAuditRecord`.
  2. Built deterministic `ReplanningEngine` in `engines/replanning_engine.py`:
     - Explicit deterministic `DEPENDENCY_GRAPH` mapping nodes to dependent processes.
     - `EVENT_NODE_MAPPING` linking events to primary affected nodes, downstream reruns, affected days, and severity tiers.
     - `analyze_impact()`: Deduplicates events, detects recursion loops, computes minimal affected node set (`rerun_nodes`), reusable nodes (`reusable_nodes`), and synthesizes structured human-readable explanations strictly from event facts.
     - `execute_selective_replan()`: Selectively re-executes only affected nodes, preserves `last_valid_itinerary` on failure, deterministically re-runs Budget Engine and Validator Engine, increments itinerary version (`v1 -> v2`), and archives full version history.
     - `parse_user_replan_request()`: Deterministically converts natural language revision prompts into structured `ChangeEvent` instances.
  3. Integrated LangGraph StateGraph Replanning Workflow in `graph/workflow.py`:
     - Created `create_replanning_graph()`: `START -> detect_change -> impact_analysis -> selective_execution -> budget_engine -> validator -> itinerary_version -> output_guardrail -> END`.
     - Added replanning tracking state fields to `graph/state.py` (`itinerary_version`, `itinerary_history`, `last_valid_itinerary`, `agent_execution_modes`, `replan_count`, `replan_reasons`, `pending_change_events`, `processed_event_ids`).
  4. Built `ReplanningRepository` in `repositories/replanning_repository.py` and database migration `supabase/migrations/20260928000004_replanning_events.sql` with Row Level Security (RLS) guaranteeing tenant isolation.
  5. Built `ReplanningService` in `services/replanning_service.py` wrapping input guardrails, tenant authorization, impact analysis, selective execution, and immutable audit logging.
  6. Updated Streamlit UI:
     - `Itinerary` page (`app/pages/itinerary.py`): Dynamic Replanning & Changes section showing current version badge (`v2`), latest trigger, structured "Why did the itinerary change?", affected vs. reusable component breakdown, evolution timeline, and live disruption/user replan simulation form.
     - `Agent Trace` page (`app/pages/agent_trace.py`): Dynamic Replanning Telemetry section displaying selective execution badges (`RERUN ⚡`, `REUSED ✓`, `INVALIDATED ✗`, `SKIPPED ⏸️`) for all 7 domain nodes.
  7. Built comprehensive test suite in `tests/test_replanning.py` covering all 32 required scenarios.
- **Files / Components**:
  - `models/replanning.py`, `models/__init__.py`
  - `engines/replanning_engine.py`, `engines/__init__.py`
  - `repositories/replanning_repository.py`, `repositories/mock_store.py`, `repositories/__init__.py`
  - `supabase/migrations/20260928000004_replanning_events.sql`
  - `graph/state.py`, `graph/workflow.py`
  - `services/replanning_service.py`, `services/__init__.py`
  - `app/pages/itinerary.py`, `app/pages/agent_trace.py`
  - `tests/test_replanning.py`
- **Testing Requirements**:
  - 32 dedicated unit/integration tests passing (`pytest tests/test_replanning.py -v`).
  - Total test suite: 263/263 tests passing across all 12 phases with 0 failures.
- **Expected Output**:
  - Intelligent, surgical replanning that updates only affected schedule blocks, preserves confirmed plans, recalculates exact budgets, and guarantees safety.

---

## Phase 13: Human-in-the-Loop (HITL) Gateways (Completed)
- **Objective**: Implement a production-grade Human-in-the-Loop authorization gate that strictly governs high-impact, transactional operations (flight/hotel/activity bookings, cancellations, payments) while preserving autonomous read-only intelligence.
- **Implementation Tasks**:
  1. Implemented strongly typed Pydantic models in `models/approval.py` (`ActionProposal`, `ApprovalRequest`, `ApprovalDecision`, `ActionExecutionResult`, `ApprovalAuditEvent`, and `classify_action_risk`).
  2. Implemented Supabase migration `supabase/migrations/20260928000005_hitl_approvals.sql` with tables for proposals, requests, executions, and audit events protected by strict Row Level Security (RLS).
  3. Created safe mock transactional adapters in `mcp/transactional_providers.py` (`MockFlightBookingProvider`, `MockHotelBookingProvider`, `MockActivityBookingProvider`) clearly badged `DEMO / MOCK`.
  4. Implemented `ApprovalRepository` and updated `MockDataStore` in `repositories/approval_repository.py` and `repositories/mock_store.py`.
  5. Implemented `ApprovalService` in `services/approval_service.py` managing creation, pending retrieval, server-side expiry, state version matching, human decision recording, and audit logging.
  6. Implemented `ActionExecutionService` in `services/action_execution_service.py` enforcing idempotency, tool authorization, mock provider execution, and audit logging.
  7. Integrated Dynamic Replanning with HITL in `services/replanning_service.py` to automatically invalidate stale proposals when the itinerary version increments.
  8. Integrated LangGraph HITL gate in `graph/state.py` and `graph/workflow.py` (`approval_gate_node` and `resume_graph_after_approval`) pausing execution on unapproved high-impact operations.
  9. Implemented dedicated Streamlit Approvals page (`app/pages/approvals.py`), updated navigation in `app/main.py` and `app/components/sidebar.py`, and added HITL lifecycle tracking to `app/pages/agent_trace.py`.
  10. Built comprehensive test suite in `tests/test_hitl.py` covering all 24 required test scenarios.
- **Files / Components**:
  - `models/approval.py`, `models/__init__.py`
  - `supabase/migrations/20260928000005_hitl_approvals.sql`
  - `mcp/transactional_providers.py`, `mcp/__init__.py`
  - `repositories/approval_repository.py`, `repositories/mock_store.py`, `repositories/__init__.py`
  - `services/approval_service.py`, `services/action_execution_service.py`, `services/replanning_service.py`, `services/__init__.py`
  - `graph/state.py`, `graph/workflow.py`
  - `app/pages/approvals.py`, `app/pages/__init__.py`, `app/main.py`, `app/components/sidebar.py`, `app/pages/agent_trace.py`
  - `tests/test_hitl.py`
- **Testing Requirements**:
  - 24 dedicated unit and integration tests passing (`pytest tests/test_hitl.py -v`).
  - Total test suite: 287/287 tests passing across all 13 phases with 0 failures.
- **Expected Output**:
  - Production-grade HITL governance ensuring no real money is spent, read-only intelligence remains autonomous, and all transactional actions require explicit human approval.

---

## Phase 14: LangSmith Observability & Production Tracing *(Completed)*
- **Objective**: Implement production-grade LangSmith distributed tracing, token usage tracking, exact model cost calculation, secret redaction, and performance observability across the entire multi-agent workflow with non-blocking failure isolation.
- **Completed Implementation**:
  1. LangSmith Configuration in `config/settings.py`:
     - Environment variables: `LANGSMITH_TRACING`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`, `LANGSMITH_ENDPOINT` (with `LANGCHAIN_*` alias compatibility).
     - Support for both `DEMO_MODE` and `LIVE_MODE`.
  2. Centralized Observability Layer in `services/observability_service.py`:
     - `TraceSanitizer`: Recursively scrubs secrets from dictionaries, lists, strings, Bearer tokens, and URL parameters (`api_key`, `token`, `password`, `secret`, `authorization`, `cookie`, `card_number`, `credential`).
     - `WorkflowTelemetryTracker`: Tracks operations, model calls, input/output tokens, estimated cost, MCP calls, search calls, RAG calls, retries, latency, spans, and errors.
     - `ObservabilityService`: Non-blocking LangSmith client and RunTree integration with graceful offline fallback.
  3. End-to-End Workflow Instrumentation:
     - `services/planning_service.py`: Root workflow tracker creation, agent span ingestion, model token tracking, and telemetry attachment to `TravelState`.
     - `mcp/client.py`: MCP tool execution tracing (`trace_mcp_tool`) capturing duration, status, retries, and sanitized arguments.
     - `rag/retriever.py`: RAG knowledge retrieval tracing (`trace_rag_retrieval`) recording query, retrieved chunk count, source IDs, and similarity score.
     - `mcp/tools/search_tools.py`: Web search tracing (`trace_web_search`) recording search query, provider, and result count.
     - `services/replanning_service.py`: Dynamic replan tracing (`trace_replanning_event`) logging affected, reused, and rerun nodes.
     - `services/action_execution_service.py`: HITL execution tracing (`trace_hitl_action`) logging proposals, risk levels, and confirmation codes.
  4. Streamlit Observability UI in `app/pages/agent_trace.py`:
     - WORKFLOW SUMMARY: Status, Workflow ID, Trip ID, Duration, Total operations, Model calls, Tool calls, Search calls, RAG calls, Retries, Estimated cost.
     - AGENT TRACE checklist: Visual status for all 11 nodes with badges (`LLM`, `DETERMINISTIC`, `MCP`, `RAG`, `WEB`, `HUMAN`, `MOCK`, `LIVE`).
     - TRACE DETAILS & TIMELINE: Detailed span breakdown with sanitized inputs, providers, and error summaries.
     - LangSmith Run link with safe URL or "Tracing unavailable" in offline mode.
  5. Built Comprehensive Test Suite in `tests/test_observability.py`:
     - 21 unit and integration tests covering configuration, tracing enable/disable, parent/child runs, secret sanitization, cost calculations, MCP/RAG/Search/Replanning/HITL tracing, and non-blocking failure isolation.
- **Files / Components**:
  - `config/settings.py`
  - `services/observability_service.py`, `services/__init__.py`
  - `services/planning_service.py`, `graph/state.py`
  - `mcp/client.py`, `mcp/tools/search_tools.py`, `rag/retriever.py`
  - `services/replanning_service.py`, `services/action_execution_service.py`
  - `app/pages/agent_trace.py`
  - `tests/test_observability.py`
- **Testing Requirements**:
  - 21 tests in `tests/test_observability.py` passing with 100% success.
- **Expected Output**:
  - Enterprise-grade LangSmith distributed tracing and observability layer with non-blocking failure resilience.

---

## Phase 15: Latency & Cost Optimization
- **Objective**: Slash end-to-end plan generation latency and optimize LLM token expenditures.
- **Implementation Tasks**:
  1. Implement prompt compression and token deduplication in agent prompts.
  2. Implement two-tier model routing: Route extraction and formatting to `gpt-4o-mini`, reserving `gpt-4o` for Planner and Replanner.
  3. Implement in-memory / Redis cache for repetitive tool and embedding queries (`src/core/cache.py`).
  4. Maximize parallel async execution across independent sub-agents in LangGraph.
- **Files / Components**:
  - `src/core/cache.py`, `src/agents/model_router.py`
  - `tests/test_optimization.py`
- **Testing Requirements**:
  - Benchmark execution time and token consumption before and after optimization.
- **Expected Output**:
  - >= 50% latency reduction and >= 60% token cost reduction.

---

## Phase 16: Comprehensive Testing & Evaluation
- **Objective**: Construct exhaustive test suites, automated evaluation datasets, and CI benchmarks.
- **Implementation Tasks**:
  1. Build comprehensive pytest suite covering unit, integration, and graph workflow tests.
  2. Create standard evaluation dataset `tests/eval_dataset.json` with 25 complex travel scenarios.
  3. Implement evaluation runner measuring:
     - Budget adherence rate (target: 100%)
     - Temporal conflict rate (target: 0%)
     - Hallucination / groundedness rate (target: < 2%)
- **Files / Components**:
  - `tests/eval_runner.py`, `tests/eval_dataset.json`
  - Full suite in `tests/`
- **Testing Requirements**:
  - Run `pytest --cov=src` achieving > 85% coverage on core engines and state machines.
- **Expected Output**:
  - Automated evaluation harness proving system reliability and interview readiness.

---

## Phase 17: Production UI Polish & Experience
- **Objective**: Elevate the user interface to an enterprise-grade, visually stunning standard.
- **Implementation Tasks**:
  1. Polish CSS styling: Sleek dark mode, custom typography (Inter/Outfit), micro-animations, glassmorphism cards.
  2. Build interactive day-by-day itinerary timeline with expandable activity cards and route maps.
  3. Build PDF / JSON itinerary export service (`src/services/export_service.py`).
  4. Add responsive trip comparison view.
- **Files / Components**:
  - `src/ui/assets/styles.css`, `src/ui/components/timeline_view.py`
  - `src/services/export_service.py`
- **Testing Requirements**:
  - Verify UI responsiveness across screen sizes and export generation fidelity.
- **Expected Output**:
  - Visually compelling, modern web application ready for live demos.

---

## Phase 18: Deployment & Interview Runbook
- **Objective**: Finalize production deployment documentation, optional containerization, and technical interview talking points.
- **Implementation Tasks**:
  1. Write comprehensive deployment guide (`DEPLOYMENT.md`) covering Streamlit Cloud, Supabase setup, and self-hosted options.
  2. Provide optional `Dockerfile` and `docker-compose.yml` for containerized environments.
  3. Write `INTERVIEW_TALKING_POINTS.md` highlighting architecture decisions, trade-offs, state graph design, and disaster recovery.
  4. Final end-to-end demo verification script.
- **Files / Components**:
  - `DEPLOYMENT.md`, `INTERVIEW_TALKING_POINTS.md`
  - Optional `Dockerfile`, `docker-compose.yml`
- **Testing Requirements**:
  - Perform clean-slate setup on a fresh environment following `DEPLOYMENT.md`.
- **Expected Output**:
  - Production-ready, fully documented repository with interview demo scripts.
