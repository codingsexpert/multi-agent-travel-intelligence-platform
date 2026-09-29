# Multi-Agent AI Travel Intelligence & Dynamic Replanning Platform

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-orange.svg)](https://github.com/langchain-ai/langgraph)
[![MCP](https://img.shields.io/badge/Tools-Model%20Context%20Protocol-purple.svg)](https://modelcontextprotocol.io/)
[![Supabase](https://img.shields.io/badge/Database-Supabase%20%7C%20PostgreSQL%20%7C%20pgvector-green.svg)](https://supabase.com/)
[![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-red.svg)](https://streamlit.io/)
[![LangSmith](https://img.shields.io/badge/Observability-LangSmith-black.svg)](https://smith.langchain.com/)

An enterprise-grade, interview-ready multi-agent travel intelligence platform built with **Python, LangGraph, MCP, Supabase, pgvector, and Streamlit**. 

Unlike conventional travel chatbots that produce hallucinated, fragile, or mathematically broken itineraries, this platform treats trip planning as a **stateful, distributed decision-making workflow** powered by specialized AI agents, deterministic Python calculation engines, live disruption recovery, and human-in-the-loop safety gates.

---

## 🌟 Core Highlights

- 🧠 **Multi-Agent Orchestration**: 9 specialized agents coordinated through **LangGraph** with cyclic execution, parallel fan-out, and persistent state.
- 📐 **Strict Separation of Concerns**: **Agents Reason** (qualitative decisions, trade-offs, synthesis) while **Python Calculates** (deterministic financial math, temporal feasibility, and constraint validation). Zero LLM arithmetic errors.
- 🔌 **Standardized Tool Layer (MCP)**: Implements Anthropic's **Model Context Protocol** to cleanly decouple tool execution, sandboxing APIs and allowing instant mock swapping.
- 🔄 **Dynamic Replanning Engine**: Reacts to disruptions (flight delays, storm alerts, attraction closures) with surgical delta-replanning, altering only affected schedule blocks without destroying confirmed plans.
- 🛡️ **Multi-Layer Guardrails**: Input injection detection, tool execution privilege boundaries, and strict output schema validation via **Pydantic v2**.
- 👤 **Human-in-the-Loop (HITL)**: High-stakes operations (booking, payments, cancellations) pause the execution graph using LangGraph interrupts for explicit traveler authorization.
- 📚 **Hybrid Knowledge Fabric**: Curated destination intelligence stored in **Supabase pgvector RAG** combined with live **Web Search** for real-time freshness.
- 📊 **Enterprise Observability**: End-to-end distributed tracing, token attribution, latency profiling, and regression benchmarking with **LangSmith**.
- 🚀 **Offline-First Demo Mode (`DEMO_MODE=true`)**: Run 100% locally with deterministic mock data and tools—no expensive API keys or Docker required for evaluations.

---

## 🏛️ High-Level System Architecture

```mermaid
graph TD
    User([Traveler / Operator]) <--> UI[Streamlit UI Layer]
    UI <--> Auth[Supabase Auth - RLS Enforced]
    
    subgraph Orchestration [LangGraph State Engine]
        Planner[1. Planner Agent] --> SubAgents
        
        subgraph SubAgents [Domain Reasoning Agents]
            FlightAgent[2. Flight Agent]
            HotelAgent[3. Hotel Agent]
            ActivityAgent[4. Activity Agent]
            WeatherAgent[5. Weather Agent]
            ResearchAgent[6. Research Agent]
        end
        
        SubAgents --> DeterministicEngines
        
        subgraph DeterministicEngines [Deterministic Python Logic]
            BudgetEngine[7. Budget Engine - Pure Math]
            ValidatorEngine[8. Validator - Feasibility]
        end
        
        DeterministicEngines --> SynthesisNode[9. Itinerary Agent]
        DeterministicEngines -.->|Constraint Violation| Replanner[Replanning Node]
        Replanner --> SubAgents
        
        SynthesisNode --> ApprovalGate{Human Approval?}
        ApprovalGate -- Yes --> HITLInterrupt[Paused Execution State]
        ApprovalGate -- No --> FinalItinerary[Final Trip Plan]
        HITLInterrupt --> UI
    end
    
    subgraph KnowledgeAndTools [Knowledge & External Tools]
        SubAgents <--> MCPGateway[MCP Client Gateway]
        MCPGateway <--> MCPServers[MCP Tool Servers]
        ResearchAgent <--> pgvector[(Supabase pgvector RAG)]
        ResearchAgent <--> WebSearch[Live Web Search API]
    end
    
    subgraph Telemetry [Observability]
        Orchestration -.-> LangSmith[LangSmith Tracing & Evals]
    end
```

---

## 🤖 The 9 Specialized Agents

| # | Agent | Primary Role | Core Tools & Technologies |
|---|---|---|---|
| **1** | **Planner Agent** | Parses natural language travel desires into structured `TripRequirementSpec`; plans execution graph. | LLM Reasoning, Pydantic v2 |
| **2** | **Flight Agent** | Searches, filters, and ranks candidate flights matching schedules, transit tolerances, and class. | Flight MCP / Amadeus API / Mock Engine |
| **3** | **Hotel Agent** | Identifies accommodations matching traveler preferences, location radius, amenities, and price ceilings. | Hotel MCP / Booking API / Mock Engine |
| **4** | **Activity / Experience Agent** | Curates cultural, leisure, and dining experiences respecting travel pace and interest themes. | Places API / RAG Knowledge / Mock Engine |
| **5** | **Weather Agent** | Analyzes climate history and forecasts; alerts downstream agents to outdoor hazard windows. | Weather MCP / OpenWeather API / Mock Engine |
| **6** | **Research Agent** | Retrieves visa regulations, transit rules, seasonal advisories, and local customs. | Supabase pgvector RAG + Live Web Search |
| **7** | **Budget Agent** | Enforces hard financial limits; itemizes transport, lodging, activities, food, and contingency. | Pure Python Deterministic Engine |
| **8** | **Validator / Safety Agent** | Validates temporal feasibility, travel buffers, pacing scores, and safety advisories. | Pure Python Constraint Engine |
| **9** | **Itinerary Agent** | Synthesizes approved choices into an interactive, hour-by-hour visual itinerary. | LLM Narrative Synthesis + Structured JSON |

---

## 🛠️ Technology Stack

| Category | Technology | Rationale |
|---|---|---|
| **Language** | Python 3.11+ | Enterprise standard for AI/ML engineering, rich typing, and async runtime. |
| **Frontend UI** | Streamlit | Python-native reactive workspace with dynamic state monitoring and approval modals. |
| **Orchestration** | LangGraph | Stateful cyclic graphs, native human-in-the-loop interrupts, and checkpointing. |
| **Tool Protocol** | Model Context Protocol (MCP) | Industry standard protocol decoupling agent logic from external API implementations. |
| **Database** | Supabase PostgreSQL | Reliable ACID persistence, Row Level Security (RLS), and zero-friction operations. |
| **Vector Search** | Supabase pgvector | Relational data and semantic vector search in one database with HNSW indexing. |
| **Data Validation** | Pydantic v2 | Blazing-fast Rust-based schema validation and structured LLM tool schemas. |
| **Observability** | LangSmith | Distributed run trees, token/cost attribution, latency profiling, and automated evals. |
| **Live Search** | Tavily / Brave Search | Real-time freshness for events, advisories, and sudden travel disruptions. |

---

## 📁 Repository Structure

```
travel-intelligence-platform/
├── app/                          # Streamlit Travel Command Center
│   ├── __init__.py
│   ├── main.py                   # Main entrypoint & page router
│   ├── state/                    # Session state management (trip, user, conv)
│   │   ├── __init__.py
│   │   └── session.py            # Active trip, auth & navigation state
│   ├── components/               # Modular UI components
│   │   ├── __init__.py
│   │   ├── sidebar.py            # Navigation & environment indicators
│   │   └── trip_summary_card.py  # Structured TravelRequest summary cards
│   └── pages/                    # 13 dedicated command center views
│       ├── __init__.py
│       ├── dashboard.py          # Platform readiness & quick action
│       ├── new_trip.py           # Intake form with repository persistence
│       ├── my_trips.py           # Saved trips list with user data isolation
│       ├── conversation.py       # Thread & message persistence interface
│       ├── itinerary.py          # Day-by-day activity slot layouts
│       ├── flights.py            # Flight search & corridor analysis
│       ├── hotels.py             # Accommodation & lodging alternatives
│       ├── activities.py         # Experience curation & pacing
│       ├── weather.py            # 14-day forecasts & hazard radar
│       ├── budget.py             # Deterministic budget breakdown grid
│       ├── sources.py            # Citations (RAG, Web, APIs)
│       ├── agent_trace.py        # 9 agents execution telemetry
│       └── settings.py           # Supabase Auth controls & diagnostics
├── config/                       # Centralized settings & environment loading
│   ├── __init__.py
│   └── settings.py               # Pydantic Settings with DEMO_MODE defaults
├── models/                       # Pydantic v2 domain schemas & data validation
│   ├── __init__.py
│   └── travel_request.py         # TravelRequest, TravelerPreferences, Constraints
├── repositories/                 # Data access layer with DEMO_MODE fallback
│   ├── __init__.py
│   ├── base.py                   # Base repository
│   ├── mock_store.py             # Thread-safe in-memory store for DEMO_MODE
│   ├── trip_repository.py        # Trips and trip preferences CRUD
│   ├── conversation_repository.py# Conversation threads CRUD
│   ├── message_repository.py     # Chronological messages CRUD
│   └── agent_run_repository.py   # Agent run audit log & telemetry
├── services/                     # Backend services & integration abstractions
│   ├── __init__.py
│   ├── auth_service.py           # Supabase Auth with DEMO_MODE fallback
│   ├── health_service.py         # Non-blocking health & configuration verification
│   └── supabase_service.py       # Supabase client wrapper with DEMO_MODE fallback
├── supabase/                     # Database migrations & RLS policies
│   ├── README.md                 # Migration guide & CLI instructions
│   └── migrations/
│       ├── 20260928000001_initial_schema.sql # Core relational tables
│       └── 20260928000002_rls_policies.sql   # Strict Row Level Security
├── utils/                        # Logging & error handling foundations
│   ├── __init__.py
│   ├── exceptions.py             # Structured application exception hierarchy
│   └── logger.py                 # Structured logger with secret scrubbing filter
├── agents/                       # Specialized travel domain agents (Phases 4 & 5)
├── engines/                      # Pure Python deterministic math & validator engines (Phase 6)
│   ├── __init__.py
│   ├── budget_engine.py          # Deterministic financial math & category breakdowns
│   └── validator_engine.py       # Deterministic feasibility & time-conflict validation
├── graph/                        # LangGraph orchestration state machine (Phases 4, 5 & 6)
├── guardrails/                   # Input, tool & output safety guardrails (Phase 11)
├── mcp/                          # Model Context Protocol servers, adapters & clients (Phases 7 & 8)
│   ├── __init__.py
│   ├── client.py                 # MCPClient gateway with retries, timeouts, and auditing
│   ├── registry.py               # MCPToolRegistry with 14 typed descriptors
│   ├── security.py               # MCPSecurityManager (Least privilege, SSRF, sanitization)
│   ├── providers/                # External provider adapters & resiliency (Phase 8 - Completed)
│   │   ├── __init__.py
│   │   ├── base.py               # BaseProvider with backoff, timeouts, 429 Retry-After, and sanitization
│   │   ├── cache.py              # Thread-safe in-memory TTL ProviderCache
│   │   ├── currency_provider.py  # Frankfurter ECB live exchange rates & caching
│   │   ├── weather_provider.py   # Open-Meteo WMO daily forecasts & alert checks
│   │   ├── maps_provider.py      # Photon OSM geocoding/POI & OSRM transit routing
│   │   ├── search_provider.py    # Tavily & Wikipedia OpenSearch with untrusted content isolation
│   │   ├── flight_provider.py    # Amadeus GDS Flight Offers Search v2 & OAuth2
│   │   └── hotel_provider.py     # Amadeus Hospitality hotel discovery & details
│   └── tools/                    # Domain-specific MCP tools delegating to provider adapters
│       ├── flight_tools.py       # search_flights, compare_flights, get_flight_details
│       ├── hotel_tools.py        # search_hotels, get_hotel_details
│       ├── maps_tools.py         # search_places, calculate_route, estimate_travel_time
│       ├── weather_tools.py      # get_current_weather, get_forecast, get_weather_alerts
│       ├── search_tools.py       # web_search, fetch_page, search_news
│       └── currency_tools.py     # get_exchange_rate
├── rag/                          # pgvector RAG domain knowledge base (Phase 9)
├── evaluation/                   # Automated evaluation & benchmark datasets (Phase 16)
├── tests/                        # Comprehensive test suite (pytest - 144 tests)
│   ├── test_auth.py              # Supabase Auth and session tests
│   ├── test_budget_engine.py     # Deterministic budget calculation tests
│   ├── test_config.py            # Environment & settings loading tests
│   ├── test_demo_extractor.py    # Deterministic fallback parser tests
│   ├── test_health.py            # Health status & component checks
│   ├── test_langgraph_workflow.py# Core LangGraph orchestration tests
│   ├── test_llm_service.py       # LLM provider & fallback tests
│   ├── test_logger_exceptions.py # Secret scrubbing & exception hierarchy tests
│   ├── test_mcp.py               # Phase 7 MCP tools, validation, security, and client tests
│   ├── test_providers.py         # Phase 8 Real provider adapters, resiliency, 429, timeouts, caching
│   ├── test_models.py            # Pydantic travel schema validation tests
│   ├── test_multi_agent_workflow.py # Multi-agent workflow integration tests
│   ├── test_planner_models.py    # Structured planner model tests
│   ├── test_planning_service.py  # End-to-end planning service tests
│   ├── test_repositories.py      # Repository CRUD & user data isolation tests
│   ├── test_schema_sql.py        # SQL migration & RLS policy verification tests
│   ├── test_specialized_agents.py# Specialized domain agent tests
│   ├── test_supabase.py          # Supabase service & DEMO_MODE fallback tests
│   ├── test_ui_form.py           # Travel intake form validation tests
│   ├── test_ui_state.py          # Session state & navigation tests
│   └── test_validator_engine.py  # Feasibility & time conflict validation tests
├── requirements.txt              # Pinned, lightweight core dependencies
├── .env.example                  # Environment configuration template (zero secrets)
├── .gitignore                    # Version control exclusion rules
├── README.md                     # Project overview & architectural guide
├── PROJECT_SPEC.md               # Complete functional & technical specifications
├── ARCHITECTURE.md               # Detailed architectural deep-dive & schemas
├── ARCHITECTURE_DECISIONS.md     # Architectural Decision Records (ADRs)
└── DEVELOPMENT_PLAN.md           # 18-phase implementation roadmap
```

---

## 🚀 Quick Start & Local Development Guide

### 1. Prerequisites
- Python 3.11 or higher (Python 3.13 tested)
- Git

### 2. Create Virtual Environment
```bash
# Clone or navigate to the repository directory
cd travel-intelligence-platform

# Create Python virtual environment
python3 -m venv .venv

# Activate the virtual environment
# On macOS / Linux:
source .venv/bin/activate
# On Windows:
# .venv\Scripts\activate
```

### 3. Install Dependencies
```bash
# Install pinned dependencies
pip install -r requirements.txt
```

### 4. Configure Environment Variables
```bash
# Copy the template to create your local .env
cp .env.example .env

# By default, DEMO_MODE=true is configured.
# You do NOT need any API keys or credentials to run the platform locally!
```

### 5. Run the Streamlit Application
```bash
# Launch Streamlit in DEMO_MODE
streamlit run app/main.py
```
Open your browser at `http://localhost:8501`. You will see the system health dashboard and the interactive TravelRequest validation sandbox.

### 6. Run the Test Suite
```bash
# Run all unit tests with verbose reporting
pytest -v
```

---

## 💡 How `DEMO_MODE` Works

`DEMO_MODE` enables 100% offline, interview-ready evaluation without requiring live API keys, paid accounts, or Docker containers:
1. **Zero External Dependencies**: The application starts immediately without OpenAI keys, Supabase credentials, or flight/hotel subscriptions.
2. **Graceful Degradation**: Backend services (like `SupabaseService`) detect missing credentials, safely return `None` or in-memory mocks, and log informational notices rather than raising fatal errors.
3. **Deterministic Testing**: All core models, validations, and graph routing mechanics can be validated through `pytest` and the Streamlit UI deterministically.
4. **Instant Production Switching**: Setting `DEMO_MODE=false` in `.env` activates real credentials and live external integrations whenever you are ready.

---

## 🚦 Phased Development Status

The platform is developed in **18 distinct phases**:

- [x] **Phase 0: Project Blueprint** *(Completed)*
- [x] **Phase 1: Project Foundation & Configuration** *(Completed)*
- [x] **Phase 2: Streamlit UI Foundation** *(Completed)*
- [x] **Phase 3: Supabase Integration (PostgreSQL, Auth & RLS)** *(Completed)*
- [x] **Phase 4: LangGraph Core Engine & Planner Agent** *(Completed)*
- [x] **Phase 5: Specialized Mock Domain Agents** *(Completed)*
- [x] **Phase 6: Budget Engine & Validator/Safety Agent (Pure Python)** *(Completed)*
- [x] **Phase 7: Model Context Protocol (MCP) Integration** *(Completed)*
- [x] **Phase 8: Real External APIs & Provider Integration** *(Completed)*
- [x] **Phase 9: RAG Knowledge Base & Supabase pgvector** *(Completed)*
- [x] **Phase 10: Web Search & Fresh Information Research** *(Completed)*
- [x] **Phase 11: Production Guardrails & Security Layer** *(Completed)*
- [x] **Phase 12: Dynamic Replanning Engine** *(Completed)*
- [x] **Phase 13: Human-in-the-Loop (HITL) Gateways** *(Completed)*
- [x] **Phase 14: LangSmith Observability & Tracing** *(Completed)*
- [x] **Phase 15: Latency & Cost Optimization** *(Completed)*
- [x] **Phase 16: Comprehensive Testing & Evaluation** *(Completed)*
- [x] **Phase 17: Production Travel Command Center UI/UX** *(Completed)*
- [ ] **Phase 18: Deployment & Interview Runbook**

---

## 🛡️ Phase 11: Production Guardrails & Zero Trust Security Layer

Phase 11 implements a centralized, production-oriented security and guardrails architecture protecting the entire platform. Following a strict **Zero Trust** model, all incoming user inputs, retrieved RAG documents, scraped web pages, external API payloads, and LLM completions are treated as untrusted data (`untrusted: True`).

### Security Architecture & Flow

```
                 USER
                  ↓
            INPUT GUARDRAIL
                  ↓
              LANGGRAPH
                  ↓
               AGENT
                  ↓
            TOOL GUARDRAIL
                  ↓
            MCP / RAG / WEB
                  ↓
           OUTPUT GUARDRAIL
                  ↓
              VALIDATOR
                  ↓
              RESPONSE
```

### The 4 Centralized Guardrail Layers

1. **Input Guardrails (`guardrails/input.py`)**:
   - **Prompt Injection Defense**: Deterministic regex protection against instruction overrides (`ignore previous instructions`, `reveal system prompt`, `show api keys`, `bypass security`) and code execution syntax (`eval`, `__import__`, `<script>`).
   - **Travel Domain Validation**: Strictly validates destinations, positive budgets, realistic traveler counts (1–50), standard 3-letter ISO currencies, logical date sequences (return >= departure), and minimum 1-day trip duration.
   - **Input Length Bounds**: Hard bounds (`MAX_INPUT_CHARS=2000`) preventing token-exhaustion attacks.
   - **Automatic PII Sanitization**: Automatically masks credit cards, passport numbers, email addresses, and phone numbers.

2. **Tool Guardrails & Authorization (`guardrails/tools.py`)**:
   - **Role-Based Tool Allowlists**: Enforces least-privilege tool execution per agent role (e.g. Flight Agent cannot invoke hotel or weather tools).
   - **Autonomous High-Risk Action Blocker**: Unconditionally blocks autonomous execution of `booking`, `purchasing`, `payment`, `cancellation`, and `financial_transaction`.
   - **Argument Validation**: Validates geographic coordinates, bounds search queries, validates ISO dates, and checks numbers prior to dispatch.

3. **Output Guardrails & Fact Safety (`guardrails/output.py`)**:
   - **Pydantic Schema Validation**: Every agent deliverable is parsed and validated against strict schemas (`PlannerResult`, `FlightOption`, `HotelOption`, `ActivityOption`, `BudgetSummary`, `ValidationResult`).
   - **Bounds Verification**: Prevents negative pricing, negative budget totals, or invalid itineraries.
   - **Fact & Source Attribution**: Mandates authentic source attribution (`source`, `provider`, `retrieved_at`, `status`); prohibits fabricated citations.

4. **Runtime Security, Circuit Breakers & Auditing (`guardrails/security.py`)**:
   - **Secret Redactor**: Continuous regex engine masking API keys (`sk-...`, `tvly-...`), JWTs, Bearer tokens, postgres passwords, and Authorization headers across logs, traces, and UI.
   - **Workflow Circuit Breakers**: Configurable limits (`MAX_AGENT_STEPS=15`, `MAX_TOOL_CALLS=25`, `MAX_RETRIES=2`, `WORKFLOW_TIMEOUT_SECONDS=30.0`) preventing infinite LangGraph loops.
   - **Sliding-Window Rate Limiter**: Thread-safe in-memory rate limiting (`RATE_LIMIT_REQUESTS=60 / 60s`).
   - **Security Auditor**: Structured, redacted security event logging (`PROMPT_INJECTION_DETECTED`, `HIGH_RISK_ACTION_BLOCKED`, `TOOL_PERMISSION_DENIED`, etc.).
   - **Supabase Tenant Isolation**: Enforces database Row-Level Security (`auth.uid() = user_id`) across all tables.

---

## 🌐 Phase 10: Web Search & Fresh Information Research


Phase 10 introduces a production-oriented, secure web research layer operating through the **Search MCP** boundary. It enables reasoning agents to retrieve fresh, time-sensitive intelligence that must **not** come from static RAG or structured operational APIs.

### Grounding Source-Selection Matrix

```
                    USER REQUEST
                         ↓
                 INFORMATION TYPE
                         ↓
        ┌────────────────┼────────────────┐
        ↓                ↓                ↓
      RAG             MCP/API         WEB SEARCH
        ↓                ↓                ↓
 Stable Knowledge    Live Structured   Fresh Info
        └────────────────┼────────────────┘
                         ↓
                      AGENTS
                         ↓
                     VALIDATOR
```

### Strict Separation of Knowledge Sources

| Data Layer | Role & Scope | Typical Examples | Underlying Engine |
| :--- | :--- | :--- | :--- |
| **Curated RAG** | **Stable Knowledge** | Cultural customs, etiquette, monument history, general travel tips, transit norms | Supabase pgvector + HNSW |
| **Operational MCP / APIs** | **Structured Live Data** | Flight schedules, room availability, live weather forecasts, currency conversions | Amadeus GDS, Open-Meteo, Frankfurter |
| **Search MCP / Web Search** | **Fresh / Current Info** | Seasonal festivals, attraction closures, transport strikes, travel advisories, regional news | Tavily / Brave Search / Safe HTTP Fetcher |

### Search MCP Architecture

Agents interact **exclusively** with Search MCP tools—never directly calling search APIs:

```
Research Agent
      ↓
Search MCP
      ↓
Search Provider (Tavily / Brave / Safe Fetcher)
      ↓
Fresh Web Results
      ↓
Validation / Normalization / Security Sanitization
      ↓
Research Agent
```

#### MCP Tools Provided:
1. `web_search(query, destination, recency, max_results, allowed_domains)`: Structured web query returning sanitized snippets, domain classifications, and publication timestamps.
2. `search_news(query, destination, recency, limit)`: Specialized regional discovery for current events, transport disruptions, festivals, and advisories.
3. `fetch_page(url, max_length)`: Sandboxed, SSRF-protected HTTP page retrieval extracting clean headings and text while stripping scripts, styles, tracking tags, and navigation wrappers.

### Source Trust Classification

All retrieved sources are classified into explicit trust categories:
- **`OFFICIAL`**: Government portals, embassies, national tourism organizations (`.gov`, `travel.state.gov`, `japan.travel`, `metro.tokyo.jp`, `visitlondon.com`).
- **`NEWS`**: Established news organizations (`bbc.com`, `reuters.com`, `japantimes.co.jp`, `lemonde.fr`).
- **`REFERENCE`**: Curated travel encyclopedias (`wikipedia.org`, `wikivoyage.org`, `lonelyplanet.com`).
- **`COMMUNITY`**: Forums and social travel communities (`reddit.com`, `tripadvisor.com`, `flyertalk.com`).
- **`UNKNOWN`**: Unclassified external domains.

### Authoritative Verification for Sensitive Requirements
For critical legal and border requirements (visas, passport validity rules, immigration mandates, health certificates):
- The system **strictly prefers `OFFICIAL` government and embassy sources**.
- Random travel blogs are never used as sole authority for entry rules.
- If authoritative official verification is missing, the system explicitly reports **verification as incomplete** rather than fabricating requirements.

### Multi-Source Research & Conflict Handling
When multiple sources report contradictory facts (e.g. market closure days, renovation timelines, festival dates):
- The system **never silently chooses one source**.
- A `ConflictingClaim` record is populated with `claim_a`, `claim_b`, `source_a`, `source_b`, timestamps, and an explicit uncertainty advisory.

### Security Boundaries & Protections
1. **SSRF & Private Network Defense**:
   - Blocks loopback targets (`localhost`, `127.0.0.1`, `0.0.0.0`, `[::1]`).
   - Blocks private RFC 1918 subnets (`10.x`, `192.168.x`, `172.16-31.x`).
   - Blocks cloud metadata endpoints (`169.254.169.254`, `metadata.google.internal`).
   - Restricts protocols to `http://` and `https://` (prohibiting `file://`, `ftp://`).
2. **Prompt Injection Defense**:
   - Retrieved web pages are strictly treated as **UNTRUSTED DATA** (`untrusted: True`).
   - Pattern neutralizers scrub adversarial instruction overrides (`Ignore previous instructions`, `SYSTEM INSTRUCTIONS:`, `developer mode`).
   - Content cannot alter LangGraph state machine flow, grant permissions, or invoke tools.
3. **Resiliency & Performance**:
   - **Caching**: 15-minute in-memory cache for repeated queries and fetched pages.
   - **Rate Limiting**: Handles HTTP 429 with `Retry-After` header extraction and bounded exponential backoff.
   - **Bounded Retries**: Maximum 2 retries on 5xx network errors; no infinite loops.
   - **Size Limits**: Page downloads capped at 500KB with 5-second timeouts.
4. **DEMO vs LIVE Mode**:
   - `DEMO_MODE=true`: Deterministic, rich mock results marked `DEMO` with realistic dates and trust classifications.
   - `DEMO_MODE=false`: Real Tavily or Brave Search queries; raises explicit `ProviderConfigurationError` if credentials are missing.

---

## 📚 Phase 9: RAG Knowledge Base & Supabase pgvector

Phase 9 introduces an enterprise-grade **Retrieval-Augmented Generation (RAG)** pipeline using **Supabase PostgreSQL with pgvector**, HNSW indexing, and semantic similarity search to provide stable, curated travel knowledge to agents.

### Information Architecture Distinction

```
                USER QUERY
                     ↓
                  AGENT
                     ↓
              RAG RETRIEVER
                     ↓
             Supabase pgvector
                     ↓
          Semantic + Metadata Filter
                     ↓
             Relevant Chunks
                     ↓
                   AGENT
```

| Source Layer | Role & Scope | Examples | Engine |
| :--- | :--- | :--- | :--- |
| **RAG Knowledge Base** | **Stable / Curated Knowledge** | Local customs, temple manners, attraction history, transit rules, neighborhood guides | Supabase pgvector + HNSW index |
| **MCP / API Gateway** | **Structured Live Information** | Flight availability, hotel pricing, real-time weather forecasts, foreign exchange rates | Amadeus GDS, Open-Meteo, Frankfurter ECB |
| **Web Search (Phase 10)** | **Fresh / Current Information** | Transport strikes, festival dates, breaking travel advisories, emergency bulletins | Tavily / Brave Search API |

### Key RAG Implementation Details

1. **pgvector Storage**:
   - Dedicated table: `public.travel_documents` with 1536-dimensional vector column (`vector(1536)`).
   - High-performance HNSW index (`idx_travel_documents_embedding_hnsw`) with cosine similarity (`vector_cosine_ops`).
   - Stored procedure: `match_travel_documents` executing combined cosine distance and metadata filtering.
2. **Embedding Configuration**:
   - Default Model: OpenAI `text-embedding-3-small` (dimension: 1536, metric: cosine similarity).
   - Configurable via `config/settings.py` (`embedding_model`, `embedding_dimension`, `embedding_provider`).
   - Missing credentials in live mode raise explicit `EmbeddingConfigurationError`.
   - `MockEmbeddingService`: Generates deterministic, unit-normalized 1536-dimensional vectors from text hashes for complete offline evaluation during `DEMO_MODE=true`.
3. **Deterministic Ingestion & Deduplication**:
   - Supports Markdown (.md), Plain Text (.txt), and JSON (.json).
   - Cleans formatting, strips unprintable control characters, and collapses whitespace.
   - Deterministic chunking preserving paragraph and sentence boundaries with configurable window (`rag_chunk_size=500`, `rag_chunk_overlap=80`).
   - Deduplication tracking using SHA-256 content hashes to prevent duplicate chunks and unnecessary embedding costs.
4. **Hybrid Retrieval & Metadata Filtering**:
   - Combines vector cosine similarity with strict metadata filtering on `destination`, `country`, `category` (e.g. customs, attractions, food, transport), and `source_trust`.
5. **Private Document Isolation & RLS**:
   - Row Level Security ensures global curated guides (`is_public = true`) are visible to all users, while private documents (`is_public = false`) are strictly accessible only by their owning `user_id`.
6. **Prompt Injection Defense & Untrusted Data Sandboxing**:
   - All retrieved chunks are explicitly tagged with `untrusted: True`.
   - Defenses sanitize directive jailbreak phrases (`Ignore previous instructions`, `SYSTEM:`, `<script>`).
   - Context is injected into agent prompts within isolated `<curated_travel_knowledge>` blocks with clear developer instructions that content represents factual reference data, not system instructions.
7. **No Fabricated Citations**:
   - Chunks preserve exact source names, trust classifications (`OFFICIAL`, `CURATED`, `REFERENCE`, `UNKNOWN`), and canonical URLs. Internal documents without URLs are marked `[Curated Knowledge]` without fabricating web addresses.

---

## 🔄 Dynamic Replanning Engine (Phase 12)

The Dynamic Replanning Engine allows the travel platform to react to real-time disruptions (e.g. flight cancellations, severe weather alerts, hotel booking drops, and user budget updates) **without restarting the entire workflow**.

### Core Architecture Flow

```text
                 CHANGE EVENT
                      ↓
               IMPACT ANALYSIS
                      ↓
             DEPENDENCY GRAPH
                      ↓
              AFFECTED NODES
                 ↙    ↓    ↘
              RERUN  REUSE  INVALIDATE
                 ↘    ↓    ↙
                MERGE STATE
                     ↓
                BUDGET ENGINE
                     ↓
                  VALIDATOR
                     ↓
               ITINERARY vN
```

### Key Capabilities & Principles

1. **Selective Re-Execution Over Full Restart**:
   - The platform resolves explicit dependencies rather than prompting an LLM to "recreate the entire trip".
   - Only nodes directly impacted by the change event are re-executed (`RERUN`), while unaffected deliverables (`REUSED`) are preserved intact.
   - Example (Flight Cancelled): Flight Agent reruns and Day 1 activities adjust; Hotel, Weather, and Destination Research remain untouched and are marked `REUSED`.
   - Example (Weather Storm): Activity Agent swaps outdoor Day 3 excursions for indoor cultural landmarks; Flights and Hotels remain unchanged.

2. **Structured Change Events (`ChangeEvent`)**:
   - Strongly typed Pydantic models with 15 categorical disruption types: `FLIGHT_CANCELLED`, `FLIGHT_DELAYED`, `HOTEL_UNAVAILABLE`, `WEATHER_ALERT`, `BUDGET_CHANGED`, `TRIP_DATES_CHANGED`, `TRAVELLER_COUNT_CHANGED`, `PREFERENCE_CHANGED`, `DESTINATION_CHANGED`, etc.
   - Categorized by severity (`INFO`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) with metadata tracking.

3. **Deterministic Dependency Graph**:
   - Explicit mappings link upstream disruptions to affected components and days:
     - `Flight -> Day 1 Arrival & Activities, Hotel Check-in, Budget Engine`
     - `Hotel -> Lodging Location, Daily Transit Buffers, Budget Engine`
     - `Weather -> Outdoor Activities, Daily Schedule`
     - `Budget -> Budget Engine, Validator Engine`

4. **Result Reuse & Invalidation Rules**:
   - Every deliverable is fingerprint-tracked.
   - Deliverables depending on changed parameters are explicitly invalidated; unaffected components are safely reused.

5. **State & Itinerary Versioning (`ItineraryVersion`)**:
   - Every replan creates an immutable new version (`v1 -> v2 -> v3...`).
   - Maintains full history of previous plans, trigger events, and structured reasons.

6. **Structured Human Explanations**:
   - Synthesizes clear, factual explanations strictly from event data (e.g., *"Your Tokyo flight was cancelled by the carrier. The system automatically rescheduled flight options, adjusted Day 1 activities, and recalculated total expenses. Your hotel reservations and weather forecast remain unchanged."*).
   - Zero hallucinated reasons.

7. **Graceful Failure Recovery & Last Valid Itinerary Preservation**:
   - If an external provider fails or an agent encounters an error during a replan, the system restores `last_valid_itinerary` and reports a clear warning rather than corrupting or discarding the user's trip.

8. **Replanning Loop Protection**:
   - Enforces `MAX_REPLAN_DEPTH = 5`, `MAX_REPLAN_EVENTS = 10`, and event deduplication to eliminate infinite replanning cycles.

9. **Immutable Audit Trail (`replanning_events`)**:
   - All replan transactions are persisted to Supabase with Row Level Security (RLS) guaranteeing tenant isolation.

---

## 🛡️ Human-in-the-Loop (HITL) Approval Workflow (Phase 13)

Phase 13 implements a production-grade Human-in-the-Loop authorization gate that strictly governs high-impact, transactional operations:

### Core Governance Principles:
- **READ-ONLY INTELLIGENCE → Autonomous**: Destination research, flight comparisons, weather lookups, hotel availability, route calculation, and budget synthesis proceed autonomously.
- **HIGH-IMPACT / TRANSACTIONAL ACTIONS → Explicit User Approval Required**: Booking flights, reserving hotels, purchasing activities/tours, cancellations, itinerary modifications, and payments strictly require explicit user authorization.
- **NEVER Autonomous Purchases**: The platform **never** autonomously performs financial charges or live reservations.
- **Safe Mock Providers**: Demonstrations execute via simulated booking adapters (`MockFlightBookingProvider`, `MockHotelBookingProvider`, `MockActivityBookingProvider`) clearly badged `DEMO / MOCK`.

### Architecture & Execution Flow:

```
Agent Proposes Action
         ↓
Deterministic Risk Classification (Pure Python Logic, Zero LLM Discretion)
         ↓
Is Approval Required?
   ├── NO (LOW Risk) ────→ Autonomous Execution
   └── YES (HIGH / CRITICAL)
              ↓
      Generate ActionProposal & ApprovalRequest
              ↓
      PAUSE LangGraph (WorkflowStatus.WAITING_FOR_APPROVAL)
              ↓
      Human Approval UI (Explicit Review & Checkbox Confirmation)
              ↓
      APPROVE or REJECT Decision
              ↓
      Server-side Validation (Authorization, Expiry, State Version & Idempotency)
              ↓
      Execute Mock Transactional Adapter
              ↓
      Record ActionExecutionResult & Immutable Audit Trail
              ↓
      Resume LangGraph & Update TravelState
```

### Safety & Integrity Pillars:
1. **Deterministic Action Classification**: No LLM decides whether an action requires approval. Python classification maps actions into `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL` risk.
2. **State-Version Protection**: Every proposal is bound to the current `state_version` (matching `itinerary_version`). If dynamic replanning advances the trip from `v1` to `v2`, all pending proposals for `v1` are automatically invalidated to prevent stale bookings.
3. **Strict Idempotency**: Proposals carry unique `idempotency_key` tokens. Duplicate button clicks or retries safely return existing execution records without double-executing transactions.
4. **Server-Side Expiry**: Approvals expire after a predefined window (default: 24h). Expired proposals cannot be approved or executed.
5. **Multi-Tenant RLS & Audit Trail**: Supabase tables (`action_proposals`, `approval_requests`, `action_executions`, `approval_audit_events`) enforce PostgreSQL Row Level Security (RLS) ensuring users only view and decide their own transactions. Secrets and tokens are strictly scrubbed from audit payloads.

---

## 📊 Phase 14: LangSmith Observability & Production Tracing

Phase 14 delivers an enterprise-grade distributed tracing and observability layer covering the complete multi-agent lifecycle:

### Observability Features:
1. **End-to-End Distributed Tracing**:
   - Trace hierarchy connects the root travel request through LangGraph, specialized reasoning agents, MCP tools, provider adapters, RAG retrieval, Web Search, Dynamic Replanning, and Human Approvals.
2. **Automated Secret Redaction (`TraceSanitizer`)**:
   - Recursive sanitization scrubs API keys, bearer tokens, passwords, cookies, authorization headers, and payment identifiers before recording or exporting telemetry.
3. **Model Token & Cost Accounting**:
   - Tracks exact input, output, and total token usage per reasoning agent invocation.
   - Computes estimated model costs for known models (`gpt-4o`, `gpt-4o-mini`, `text-embedding-3-small`) while marking unpriced or custom models as `"UNKNOWN"`, strictly avoiding fabricated metrics.
4. **Non-Blocking Failure Isolation**:
   - Observability never degrades or halts travel planning. If LangSmith endpoints are unreachable or credentials are unconfigured, operations continue seamlessly with in-memory telemetry.
5. **Streamlit Agent Trace & Telemetry Dashboard**:
   - **Workflow Summary**: Real-time duration, operation counts, token counts, model calls, tool calls, search calls, RAG calls, retries, and estimated costs.
   - **Agent Trace Checklist**: Status badges for all 11 nodes (`LLM`, `DETERMINISTIC`, `MCP`, `RAG`, `WEB`, `HUMAN`, `MOCK`, `LIVE`).
   - **Trace Details & Timeline**: Sanitized chronological span table with latency breakdowns and error insights.
   - **Safe LangSmith Link**: Direct link to the LangSmith cloud run or clear "Tracing unavailable (Offline / Demo Mode)" indicator.

---

## 💰 Phase 15: Cost Optimization, Model Routing & Efficiency

Phase 15 guarantees enterprise-grade cost efficiency and latency awareness through the core principle: **"Use the cheapest reliable mechanism for every task."**

### Efficiency Architecture:
1. **Deterministic Model Router (`utils/model_router.py`)**:
   - `MODEL_SIMPLE` (`gpt-4o-mini`): Extraction, normalization, formatting, clarification.
   - `MODEL_MEDIUM` (`gpt-4o-mini`): Options reasoning, research synthesis, trade-offs.
   - `MODEL_COMPLEX` (`gpt-4o`): Multi-constraint trip planning, dynamic replanning, conflict resolution.
   - `PYTHON` (Pure deterministic): Financial budget engine and temporal validator ($0.00 / 0 LLM tokens).
2. **Safe Fallback Strategy**:
   - Primary model failures safely step down to configured fallback models with a 1-attempt ceiling, strictly preventing runaway loops.
3. **Centralized Cost Tracker (`utils/cost.py`)**:
   - Configuration-driven per-model token pricing with thread-safe (`threading.RLock`) accounting.
   - Displays `"UNKNOWN"` for unpriced models rather than fabricating figures.
   - Enforces workflow budgets (`MAX_WORKFLOW_COST`, `MAX_MODEL_CALLS`, `MAX_TOTAL_TOKENS`).
4. **Intelligent Caching with Mode Partitioning (`utils/cache.py`)**:
   - Normalized SHA-256 fingerprinting prevents duplicate LLM, MCP, and search requests.
   - Domain-specific TTLs: Currency (3600s), Weather (1800s), Places (86400s), Search (900s), Flight/Hotel (600s), RAG (1800s).
   - Strict namespace isolation between DEMO and LIVE cache keys (`domain:demo` vs `domain:live`).
   - Transactional operations (`book_flight`, `book_hotel`, `purchase_activity`, `cancel_booking`, `process_payment`, `authorize_payment`, approvals) are strictly prohibited from being cached.
5. **Context Minimization & Replan Reuse**:
   - Agents receive only necessary state fields via `minimize_agent_context`.
   - Independent affected nodes execute in parallel via `ThreadPoolExecutor` during dynamic replanning, while reusing unaffected nodes and tracking savings (calls avoided, tokens saved, cost saved, latency saved).
6. **Streamlit Cost & Performance Dashboard (`app/pages/agent_trace.py`)**:
   - Real-time workflow cost metrics, model breakdown, agent breakdown, cache hit rates, duplicate prevention stats, and estimated savings.

---

## 🧪 Phase 16: Comprehensive Testing & Evaluation Framework

Phase 16 provides an enterprise-grade testing and evaluation infrastructure measuring software correctness, quality, reliability, safety, and efficiency across all multi-agent travel workflows.

### 1. Three-Layer Testing Strategy
- **Unit Tests**: Pure Python functions, financial math, Pydantic schemas, and guardrails in total isolation.
- **Integration Tests**: Specialized agents, MCP tool gateways, providers, and database services with mock adapters.
- **End-to-End Scenario Tests**: Multi-agent graph workflows, dynamic replanning cycles, and HITL authorization pauses.

### 2. Versioned Synthetic Evaluation Datasets (`evaluation/datasets/`)
Contains 31 curated synthetic scenarios (zero real personal data):
- **`travel_scenarios.json`** (12 scenarios): Solo domestic, couple international, family with kids, group of friends, low-budget student, mid-budget scenic, luxury, 2-day heritage, 7-day backwaters, multi-city cultural, strict accessibility, and corporate workation.
- **`adversarial_scenarios.json`** (7 scenarios): Direct instruction overrides, indirect web injection, secret exfiltration, autonomous HITL bypass, cloud metadata SSRF, unauthorized tool calls, and malicious RAG document injections.
- **`replanning_scenarios.json`** (6 scenarios): Flight cancellations, hotel unavailable, severe cyclones, museum weekly closures, 35% budget slashes, and 48-hour date shifts.
- **`security_scenarios.json`** (6 scenarios): Cross-user trip isolation (RLS), unauthorized booking attempts, expired approval reuse, double-click duplicate execution races, cloud metadata endpoints, and cross-tenant cache keys.

### 3. Deterministic Evaluators vs. Qualitative Judge
- **Deterministic Evaluators (`evaluation/evaluators.py`)**:
  - `BUDGET_ADHERENCE`: Exact Python arithmetic (`estimated_cost <= budget_limit`). Zero LLM subjective judgment permitted.
  - `CONSTRAINT_SATISFACTION_RATE`: Multi-dimensional constraint matching (budget, flight stops, max travel hours, preferred airlines, hotel stars, dietary, accessibility, and landmarks).
  - `ITINERARY_VALIDITY_RATE`: Evaluates date sequences, positive durations, flight arrival before hotel check-in, and duplicate avoidance.
  - `TOOL_SELECTION_ACCURACY`: Validates tool domain matching, required arguments, and absence of unauthorized tool invocations.
  - `HALLUCINATION_RATE`: Verifies system admits unavailable data ("I don't have enough verified information") rather than fabricating answers.
  - `PROMPT_INJECTION_BLOCK_RATE`: Evaluates input guardrail blocking and untrusted content defensive boundary encapsulation.
  - `SECURITY_TEST_PASS_RATE`: Verifies RLS tenant isolation, secret redaction, and SSRF private subnet protection.
  - `FAILURE_RECOVERY_RATE`: Verifies graceful degradation on provider timeout or payload errors without corrupting state.
  - `REPLAN_SUCCESS_RATE` & `REPLAN_SELECTIVITY`: Assesses replanning success and selective reuse of unaffected graph nodes.
  - `APPROVAL_ENFORCEMENT_RATE` & `DUPLICATE_EXECUTION_RATE`: Verifies transactional actions require approval and duplicate execution rate is exactly 0.0%.
  - `Cost & Latency Percentiles`: Computes deterministic P50, P95, and P99 latency percentiles.
- **Qualitative LLM-as-a-Judge (`evaluation/llm_judge.py`)**:
  - Applied ONLY to subjective dimensions: itinerary usefulness and explanation clarity.
  - Strictly prohibited from evaluating arithmetic, dates, security, approvals, or permissions.

### 4. Zero-Tolerance Critical Failure Policy
Any violation of fundamental security, authorization, or integrity rules (unauthorized booking, payment without approval, secret leakage, cross-user data exposure, arbitrary code execution, approval bypass, duplicate transactional execution, SSRF exploit) immediately triggers a `CriticalFailure` and sets `evaluation status = FAILED`, regardless of aggregate metric percentages.

### 5. Streamlit Evaluation Dashboard (`app/pages/evaluation.py`)
- Real-time evaluation runs, metrics overview cards, quality gauges, reliability/security metrics, latency percentiles, and scenario drilldowns comparing Expected vs. Actual outcomes with failure reasons and trace IDs.

### 6. Running Tests & Evaluations

```bash
# Run all unit, integration, and scenario tests (pytest)
python3 -m pytest tests/ -v

# Run the Phase 16 evaluation framework tests specifically
python3 -m pytest tests/test_evaluation_framework.py -v

# Run the comprehensive 31-scenario evaluation runner from CLI
python3 -m evaluation.runner
```

---

## 🎛️ Phase 17: Production Travel Command Center UI/UX

Phase 17 elevates the user experience into an enterprise-grade **Travel Command Center**. It rejects the generic "chatbot demo" paradigm in favor of structured intelligence cockpits, deterministic data rendering, clear provenance badges, and strict separation between traveler tasks and developer observability.

### Two-Tier Information Architecture
```
🧭 Traveler Primary Navigation:
1. 📊 Dashboard                 - Active trip summary, 9-stage planning matrix, pending approvals, recent replans
2. ➕ New Trip                  - Multi-step trip creation with 10 preference themes & pacing/dietary constraints
3. 🧳 My Trips                  - Saved trips directory, status filters, and one-click active trip switching
4. 📍 Current Trip              - Full route inspection, schedule specs, budget caps, and quick actions
5. 🗓️ Itinerary                 - Structured Day/Morning/Afternoon/Evening cards with version tracking (v1, v2)
6. ✈️ Flights                   - Cabin class, duration, stops, pricing, and DEMO vs LIVE badge
7. 🏨 Hotels                    - Star ratings, amenities, nightly rates, total cost, and % budget impact
8. 🎭 Activities                - Time, duration, transit times, weather suitability, deduplicated
9. ⛅ Weather                   - High/low °C, precipitation probability, humidity, and active advisories
10. 💰 Budget                   - Deterministic 6-category breakdown, utilization bar, and status badges
11. 🌐 Sources                  - Trust hierarchy (OFFICIAL, NEWS, REFERENCE, COMMUNITY, UNKNOWN)
12. ⏳ Planning Progress        - Real-time pipeline state (Trip Request -> Requirements -> Planner -> ...)

🛠️ Developer & Advanced Controls:
13. 🔬 Agent Trace              - Multi-node execution logs, latency profiling, token counts, and cost
14. 🔄 Changes & Replanning     - Event disruption timeline, node reuse tags (RERUN, REUSED, INVALIDATED)
15. 🛡️ Approvals                - Human-in-the-Loop approval cards, risk levels, and expiry countdowns
16. 🧪 Evaluation               - 31-scenario regression benchmark across Quality, Reliability, and Security
17. 🧠 Knowledge / RAG          - Verified domain dossiers, chunk metrics, and live semantic search sandbox
18. 🔒 Security                 - 10-layer defense matrix (Guardrails, RLS, SSRF, Secret Redaction, HITL)
19. ⚙️ Settings                 - Safe environment toggles, active model identifiers, zero leaked secrets
```

### Design System & Enterprise Principles
- **Enterprise Palette**: Deep slate `#0F172A` canvas with elevated `#1E293B` cards, muted slate borders, and vibrant accent highlights.
- **Micro-Interactions**: Hover lifts on interactive cards (`.travel-card`) without dizzying animations or excessive gradients.
- **Provenance Badges**: Immediate, unmistakable distinction between sandboxed mock data (`DEMO`) and live provider data (`LIVE`).
- **Actionable Empty States**: Every empty state provides a direct CTA button (e.g. "Create New Trip", "Run Evaluation Suite") rather than blank dead ends.
- **Authoritative Backend**: The UI never performs mathematical recalculations or creates approval bypasses. Backend constraints remain authoritative.

---

## 🚀 Phase 18: Production Deployment, CI/CD & Final Production Hardening

Phase 18 completes the platform lifecycle, establishing defense-in-depth production hardening, startup validation, dual-probe health monitoring, multi-stage non-root containerization, automated CI/CD, and production readiness governance.

### Production Highlights
1. **Startup Configuration Validation (`config/validator.py`)**:
   - Zero-credential-leak validation verifying environment variables, HTTPS/HTTP URLs, and mode constraints.
   - Enforces required Supabase credentials and LLM keys when `DEMO_MODE=false`.
2. **Subsystem Health Monitoring & Dual Probes (`services/health_service.py`)**:
   - Evaluates 8 distinct architectural subsystems (`Application`, `Database`, `Authentication`, `LLM Providers`, `MCP Tool Servers`, `Web Search`, `RAG Knowledge`, `LangSmith Tracing`).
   - Returns discrete statuses: `HEALTHY`, `DEGRADED`, `UNAVAILABLE`.
   - Distinct **Liveness** (`/health/live`) and **Readiness** (`/health/ready`) probes prevent container restart loops when optional providers experience intermittent issues.
3. **Streamlit Production Hardening (`.streamlit/config.toml`)**:
   - Headless execution, port 8501, CORS disabled, XSRF protection enabled.
   - Suppresses raw stack traces and exception details (`showErrorDetails = false`).
4. **Hardened Multi-Stage Containerization (`Dockerfile` & `.dockerignore`)**:
   - Minimal `python:3.11-slim` base image running under unprivileged user `appuser` (UID 10001).
   - Built-in container healthcheck via Streamlit health probe.
   - Strict `.dockerignore` preventing secrets, git metadata, and caches from entering image layers.
5. **Automated CI/CD Workflow (`.github/workflows/ci.yml`)**:
   - GitHub Actions pipeline executing secret scanning, config schema validation, full 382+ test pytest suite, evaluation smoke tests, and health probe verification.
6. **Production Documentation**:
   - [`DEPLOYMENT.md`](file:///Users/MukeshSingh/Desktop/travel-intelligence-platform/DEPLOYMENT.md): Step-by-step production runbook for Streamlit Community Cloud, AWS ECS, GCP Cloud Run, and Docker.
   - [`PRODUCTION_READINESS.md`](file:///Users/MukeshSingh/Desktop/travel-intelligence-platform/PRODUCTION_READINESS.md): Exhaustive audit scorecard covering architecture, security, performance, cost, and limitations.

---

## 🛡️ Security & Privacy Principles

1. **Zero Secret Leaks**: Secrets and service keys are never committed to version control.
2. **Least Privilege**: Agents have read-only permissions by default; write/booking actions require explicit human tokens.
3. **Data Isolation**: Supabase Row Level Security (RLS) ensures users can access only their own trips.
4. **Prompt Injection Defense**: Multi-tier input guardrails filter adversarial jailbreaks and role tampering.
5. **Deterministic Boundaries**: Hard business constraints are verified in Python, never delegated to probabilistic LLMs.

---

## 📄 License & Attribution

Designed and engineered for enterprise deployment and technical portfolio demonstration.
