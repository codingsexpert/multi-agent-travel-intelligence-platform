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

## Phase 5: Specialized Mock Domain Agents
- **Objective**: Implement Flight, Hotel, Activity, Weather, and Research agents with deterministic mock engines for offline development and testing.
- **Implementation Tasks**:
  1. Build realistic deterministic data generators in `src/mock_data/` (flights, hotels, activities, weather datasets).
  2. Implement Flight Agent (`src/agents/flight_agent.py`) returning candidate flight options.
  3. Implement Hotel Agent (`src/agents/hotel_agent.py`) selecting accommodations matching location and budget.
  4. Implement Activity Agent (`src/agents/activity_agent.py`) curating itinerary experiences.
  5. Implement Weather Agent (`src/agents/weather_agent.py`) retrieving climate forecasts.
  6. Wire nodes in parallel fan-out inside `src/graph/workflow.py`.
- **Files / Components**:
  - `src/mock_data/flights.json`, `src/mock_data/hotels.json`, `src/mock_data/activities.json`, `src/mock_data/weather.json`
  - `src/agents/flight_agent.py`, `src/agents/hotel_agent.py`, `src/agents/activity_agent.py`, `src/agents/weather_agent.py`
  - `tests/test_domain_agents.py`
- **Testing Requirements**:
  - Verify parallel execution of domain agents in the graph state machine without race conditions.
- **Expected Output**:
  - Graph populates state with flight, hotel, activity, and weather candidates.

---

## Phase 6: Budget Engine & Validator/Safety Agent (Pure Python)
- **Objective**: Implement deterministic financial aggregation and constraint validation in pure Python, preventing LLM arithmetic errors.
- **Implementation Tasks**:
  1. Build `src/engines/budget_engine.py`:
     - Calculates total trip cost (flights + hotels + activities + food allowance + contingency).
     - Calculates category percentages and currency conversions.
     - Detects budget overrun and flags violation magnitude.
  2. Build `src/engines/validator_engine.py`:
     - Temporal validation: Flight arrival < Hotel check-in; Activity intervals >= travel buffers.
     - Pacing check: Flag daily schedules exceeding 10 active hours (fatigue index).
     - Weather hazard check: Flag outdoor activities during forecasted storm days.
  3. Add `BudgetNode` and `ValidationNode` to `src/graph/workflow.py`.
- **Files / Components**:
  - `src/engines/budget_engine.py`, `src/engines/validator_engine.py`
  - `src/graph/nodes/budget_node.py`, `src/graph/nodes/validator_node.py`
  - `tests/test_engines.py`
- **Testing Requirements**:
  - Unit tests with edge cases (leap days, midnight flight arrivals, negative numbers, extreme budget overruns).
- **Expected Output**:
  - Verified math and feasibility enforcement with zero hallucination risk.

---

## Phase 7: Model Context Protocol (MCP) Integration
- **Objective**: Decouple tool logic into standardized Model Context Protocol (MCP) clients and servers.
- **Implementation Tasks**:
  1. Implement local MCP server `src/mcp_servers/travel_tools_server.py` exposing tool definitions via JSON-RPC.
  2. Implement MCP client gateway `src/services/mcp_client.py` connecting domain agents to MCP servers.
  3. Bind MCP tools to Flight, Hotel, and Weather agents.
  4. Support transparent fallback to in-memory mocks when external MCP processes are not spawned.
- **Files / Components**:
  - `src/mcp_servers/travel_tools_server.py`, `src/services/mcp_client.py`
  - `tests/test_mcp.py`
- **Testing Requirements**:
  - Verify tool discovery, parameter schema validation, and tool invocation via MCP client protocol.
- **Expected Output**:
  - Agents invoke tools using the standardized Model Context Protocol.

---

## Phase 8: Real External APIs Integration
- **Objective**: Connect real-world travel APIs for live data retrieval, wrapped in robust error handling.
- **Implementation Tasks**:
  1. Implement Amadeus API client (`src/services/amadeus_service.py`) for live flight and hotel pricing.
  2. Implement OpenWeather API client (`src/services/weather_service.py`) for live 14-day forecasts.
  3. Implement circuit breaker and fallback logic: if API fails, timeout occurs, or rate limit hit, gracefully fall back to mock data with UI notification.
- **Files / Components**:
  - `src/services/amadeus_service.py`, `src/services/weather_service.py`
  - `src/services/api_resilience.py`
  - `tests/test_external_apis.py`
- **Testing Requirements**:
  - Mock HTTP 429, 500, and timeout responses; verify seamless fallback without application crash.
- **Expected Output**:
  - Live data fetching when credentials provided, with zero-crash resilience.

---

## Phase 9: RAG Knowledge Base & Supabase pgvector
- **Objective**: Implement semantic retrieval over curated destination guides, visa rules, and local customs using `pgvector`.
- **Implementation Tasks**:
  1. Implement vector migration in `supabase/migrations/003_pgvector_setup.sql` with HNSW cosine index.
  2. Build document ingestion script `scripts/ingest_knowledge.py` to chunk and embed curated travel guides.
  3. Implement RAG retrieval service `src/services/rag_service.py` with metadata filtering (country, category).
  4. Connect Research Agent to RAG service.
- **Files / Components**:
  - `supabase/migrations/003_pgvector_setup.sql`, `scripts/ingest_knowledge.py`
  - `src/services/rag_service.py`, `src/agents/research_agent.py`
  - `data/knowledge_base/` (curated markdown guides)
  - `tests/test_rag.py`
- **Testing Requirements**:
  - Test vector similarity queries against mock destination guides; verify precision and relevance scoring.
- **Expected Output**:
  - Grounded destination insights retrieved and cited in agent recommendations.

---

## Phase 10: Live Web Search Integration
- **Objective**: Integrate web search to detect volatile real-time conditions (events, closures, strikes, seasonal anomalies).
- **Implementation Tasks**:
  1. Implement web search client `src/services/search_service.py` supporting Tavily / Brave Search API.
  2. Build query formulation agent prompt that constructs temporal, surgical search queries.
  3. Implement snippet cleaner: strips HTML, deduplicates, and limits token length.
  4. Combine RAG static knowledge + Live search findings in Research Agent synthesis.
- **Files / Components**:
  - `src/services/search_service.py`, `src/agents/research_agent.py`
  - `tests/test_search.py`
- **Testing Requirements**:
  - Verify query synthesis and clean markdown extraction from search results.
- **Expected Output**:
  - Up-to-the-minute real-world travel context integrated into trip planning.

---

## Phase 11: Guardrails & Security Implementation
- **Objective**: Enforce multi-layer safety across inputs, tool calls, and outputs.
- **Implementation Tasks**:
  1. Build `src/guardrails/input_guardrails.py`: Detect prompt injection, role hijacking, and illegal character payloads.
  2. Build `src/guardrails/tool_guardrails.py`: Verify tool permissions, enforce argument whitelisting, and block unauthorized commands.
  3. Build `src/guardrails/output_guardrails.py`: Strict Pydantic validation, fact-grounding check against tool observations, and PII masking.
  4. Attach guardrails to LangGraph entry and exit nodes.
- **Files / Components**:
  - `src/guardrails/input_guardrails.py`, `src/guardrails/tool_guardrails.py`, `src/guardrails/output_guardrails.py`
  - `tests/test_guardrails.py`
- **Testing Requirements**:
  - Pass adversarial injection prompts, malformed schemas, and PII; verify rejection or sanitization.
- **Expected Output**:
  - Hardened execution pipeline safe against adversarial inputs and hallucinations.

---

## Phase 12: Dynamic Replanning Engine
- **Objective**: Enable surgical delta-replanning in response to disruptions without regenerating the entire trip.
- **Implementation Tasks**:
  1. Define disruption event schema `src/schemas/disruption.py` (e.g. Flight Cancelled, Storm Alert, Hotel Unavailable, Budget Cut).
  2. Implement Replanner Agent `src/agents/replanner.py`:
     - Assesses disruption impact.
     - Identifies invalidated itinerary items while locking confirmed ones.
     - Generates targeted delta instructions for affected sub-agents.
  3. Add cyclic replanning edge in LangGraph with `replan_count` circuit breaker.
  4. Build Streamlit Disruption Simulator UI allowing users to trigger test events.
- **Files / Components**:
  - `src/schemas/disruption.py`, `src/agents/replanner.py`
  - `src/ui/components/disruption_simulator.py`
  - `tests/test_replanning.py`
- **Testing Requirements**:
  - Trigger simulated flight delay; verify hotel and downstream activities adjust while unaffected days remain intact.
- **Expected Output**:
  - Dynamic delta-replanning with visual before-and-after itinerary diffs.

---

## Phase 13: Human-in-the-Loop (HITL) Gateways
- **Objective**: Implement checkpoint interrupts requiring explicit human approval for sensitive financial or booking actions.
- **Implementation Tasks**:
  1. Implement `ApprovalGate` node in `src/graph/workflow.py` using LangGraph's `interrupt()`.
  2. Persist graph checkpoints in Supabase checkpointer.
  3. Implement Streamlit interactive approval modal (`src/ui/components/approval_modal.py`):
     - Displays itemized financial commitment, non-refundable policies, and confirmation button.
  4. Implement resume handler calling `graph.invoke(Command(resume=...))`.
- **Files / Components**:
  - `src/graph/nodes/approval_node.py`, `src/ui/components/approval_modal.py`
  - `tests/test_hitl.py`
- **Testing Requirements**:
  - Verify graph halts before booking, yields state to UI, and successfully resumes upon approval.
- **Expected Output**:
  - Controlled financial commitment flow with full human oversight.

---

## Phase 14: LangSmith Observability & Tracing
- **Objective**: Integrate end-to-end distributed tracing, token cost attribution, and latency profiling.
- **Implementation Tasks**:
  1. Configure LangSmith tracer in `src/core/telemetry.py` with custom project tags and run metadata.
  2. Instrument custom spans for deterministic engines (budget, validation) alongside LLM spans.
  3. Implement cost calculator aggregating token expenditure per agent and overall run.
  4. Create Streamlit observability panel displaying trace URLs and run performance.
- **Files / Components**:
  - `src/core/telemetry.py`, `src/ui/components/observability_panel.py`
  - `tests/test_telemetry.py`
- **Testing Requirements**:
  - Verify trace generation and correct hierarchical span structure in LangSmith test runs.
- **Expected Output**:
  - Production-grade visibility into latency, tokens, cost, and agent decision paths.

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
