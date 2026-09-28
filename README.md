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
│   ├── state/                    # Session state management
│   │   ├── __init__.py
│   │   └── session.py            # Active trip & navigation state
│   ├── components/               # Modular UI components
│   │   ├── __init__.py
│   │   ├── sidebar.py            # Navigation & environment indicators
│   │   └── trip_summary_card.py  # Structured TravelRequest summary cards
│   └── pages/                    # 13 dedicated command center views
│       ├── __init__.py
│       ├── dashboard.py          # Platform readiness & quick action
│       ├── new_trip.py           # Pydantic-validated trip intake form
│       ├── my_trips.py           # In-memory saved trips & history
│       ├── conversation.py       # Conversational planning interface
│       ├── itinerary.py          # Day-by-day activity slot layouts
│       ├── flights.py            # Flight search & corridor analysis
│       ├── hotels.py             # Accommodation & lodging alternatives
│       ├── activities.py         # Experience curation & pacing
│       ├── weather.py            # 14-day forecasts & hazard radar
│       ├── budget.py             # Deterministic budget breakdown grid
│       ├── sources.py            # Citations (RAG, Web, APIs)
│       ├── agent_trace.py        # 9 agents execution telemetry
│       └── settings.py           # Environment diagnostics & secrets mask
├── config/                       # Centralized settings & environment loading
│   ├── __init__.py
│   └── settings.py               # Pydantic Settings with DEMO_MODE defaults
├── models/                       # Pydantic v2 domain schemas & data validation
│   ├── __init__.py
│   └── travel_request.py         # TravelRequest, TravelerPreferences, Constraints
├── services/                     # Backend services & integration abstractions
│   ├── __init__.py
│   ├── health_service.py         # Non-blocking health & configuration verification
│   └── supabase_service.py       # Supabase client wrapper with DEMO_MODE fallback
├── utils/                        # Logging & error handling foundations
│   ├── __init__.py
│   ├── exceptions.py             # Structured application exception hierarchy
│   └── logger.py                 # Structured logger with secret scrubbing filter
├── agents/                       # Specialized travel domain agents (Phases 4 & 5)
├── graph/                        # LangGraph orchestration state machine (Phase 4)
├── repositories/                 # Data access layer (Phase 3)
├── guardrails/                   # Input, tool & output safety guardrails (Phase 11)
├── mcp/                          # Model Context Protocol servers & clients (Phase 7)
├── rag/                          # pgvector RAG domain knowledge base (Phase 9)
├── evaluation/                   # Automated evaluation & benchmark datasets (Phase 16)
├── tests/                        # Comprehensive test suite (pytest)
│   ├── test_config.py            # Environment & settings loading tests
│   ├── test_health.py            # Health status & component checks
│   ├── test_logger_exceptions.py # Secret scrubbing & exception hierarchy tests
│   ├── test_models.py            # Pydantic travel schema validation tests
│   ├── test_supabase.py          # Supabase service & DEMO_MODE fallback tests
│   ├── test_ui_form.py           # Travel intake form validation tests
│   └── test_ui_state.py          # Session state & navigation tests
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
- [ ] **Phase 3: Supabase Integration (PostgreSQL, Auth & RLS)**
- [ ] **Phase 4: LangGraph Core Engine & Planner Agent**
- [ ] **Phase 5: Specialized Mock Domain Agents**
- [ ] **Phase 6: Budget Engine & Validator/Safety Agent (Pure Python)**
- [ ] **Phase 7: Model Context Protocol (MCP) Integration**
- [ ] **Phase 8: Real External APIs Integration**
- [ ] **Phase 9: RAG Knowledge Base & Supabase pgvector**
- [ ] **Phase 10: Live Web Search Integration**
- [ ] **Phase 11: Guardrails & Security Implementation**
- [ ] **Phase 12: Dynamic Replanning Engine**
- [ ] **Phase 13: Human-in-the-Loop (HITL) Gateways**
- [ ] **Phase 14: LangSmith Observability & Tracing**
- [ ] **Phase 15: Latency & Cost Optimization**
- [ ] **Phase 16: Comprehensive Testing & Evaluation**
- [ ] **Phase 17: Production UI Polish & Experience**
- [ ] **Phase 18: Deployment & Interview Runbook**

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
