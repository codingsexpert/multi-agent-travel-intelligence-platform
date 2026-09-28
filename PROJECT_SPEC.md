# Project Specification: Multi-Agent AI Travel Intelligence & Dynamic Replanning Platform

## 1. Executive Summary & Vision

The **Multi-Agent AI Travel Intelligence & Dynamic Replanning Platform** is a production-oriented, interview-ready enterprise travel operating system. Unlike simple one-shot travel itinerary generators that produce hallucinated or rigid itineraries, this platform treats trip planning and execution as a **stateful, multi-agent distributed decision workflow** governed by strict business logic, live contextual retrieval, deterministic budget guarantees, and dynamic replanning when conditions change.

The platform coordinates specialized autonomous agents orchestrated through **LangGraph**, integrates standard external tools via **Model Context Protocol (MCP)**, grounds domain knowledge with **Supabase pgvector RAG**, enriches live status with **Web Search & real-time APIs**, and enforces safety through **Input/Tool/Output Guardrails** and **Human-in-the-Loop (HITL) approval gates**.

---

## 2. Problem Statement & Value Proposition

### 2.1 The Problem with Existing AI Travel Planners
1. **Hallucination & Stale Data**: Monolithic LLMs hallucinate non-existent flights, hotels, operating hours, and seasonal closures.
2. **Mathematical Incompetence**: LLMs are notoriously poor at deterministic currency conversions, budget aggregation, tax calculations, and constraint satisfaction.
3. **Rigid Fragility**: If a flight gets delayed by 4 hours, rain washes out a day, or a museum is closed for refurbishment, existing tools cannot surgically repair the itinerary without starting from scratch.
4. **Unsafe Autonomous Execution**: Autonomous agents attempting to book, charge cards, or commit reservations without explicit human authorization present unacceptable financial and legal risks.
5. **Black-Box Architecture**: Monolithic prompts offer zero observability into why a specific decision was made, making debugging and production monitoring impossible.

### 2.2 The Solution
This platform establishes a clear separation of concerns:
- **Agents Reason**: LLMs make contextual decisions, weigh qualitative trade-offs, and synthesize recommendations.
- **Python Calculates**: Pure Python code handles deterministic math, currency conversions, temporal conflict checks, budget boundaries, and hard constraint validation.
- **LangGraph Coordinates**: Manages persistent state, agent routing, cyclic execution, replanning loops, and human approval interrupts.
- **Hybrid Retrieval**: Combines long-term curated knowledge (pgvector RAG) with real-time volatility (live APIs and web search).
- **Human in the Loop**: Sensitive actions (booking, payments, destructive cancellations) pause the execution graph for explicit user consent.

---

## 3. Core Functional Capabilities

### 3.1 Natural Language Requirement Ingestion
- Accepts open-ended, complex user prompts (e.g., *"Family trip of 4 to Tokyo and Kyoto for 8 days in early April with a $5,500 total budget. We love ramen, hate rushing, need kid-friendly activities, and need direct flights from SFO."*).
- Structures unorganized prompts into a strict, validated **Pydantic schema (`TripRequirementSpec`)**.
- Clarifies ambiguous parameters proactively before triggering costly downstream agent cascades.

### 3.2 Multi-Agent Collaborative Trip Planning
- Parallelized and sequential execution of specialized agents (Flights, Hotels, Activities, Weather, Research).
- Each agent operates with least-privilege tools, specific domain prompts, and typed output schemas.

### 3.3 Deterministic Budget Optimization
- Pure Python calculation engine evaluates itemized expenses against traveler limits.
- Detects budget overruns, categorizes expenditures (transport, lodging, activities, food, contingency), and instructs agents to back off or recommend budget alternatives when thresholds are breached.

### 3.4 Temporal & Feasibility Validation
- Validates travel logic: flight arrival vs. hotel check-in times, geographic transit buffers between activities, operating hours, and pace fatigue scores.
- Rejects logically invalid plans before they reach the user.

### 3.5 Dynamic Replanning Triggered by Disruptions
- Responds to real-world disruption events (e.g., flight cancellation, severe storm advisory, sudden attraction closure, traveler request to change budget).
- The replanner performs surgical delta-replanning: preserves unaffected itinerary blocks and re-invokes only the relevant agents to find alternatives, presenting an *impact diff* to the user.

### 3.6 Human-in-the-Loop (HITL) Gateways
- High-stakes operations (initiating checkout, booking reservations, applying non-refundable changes) pause LangGraph execution using checkpointer interrupts.
- Streamlit presents an interactive approval card with full cost breakdown and cancellation policies. Execution resumes only upon cryptographic user confirmation.

### 3.7 Full Observability & Evaluation
- Every node execution, tool invocation, token consumption metric, and latency profile is tracked in **LangSmith**.
- Continuous evaluation pipelines assess plan quality, groundedness, constraint satisfaction, and cost efficiency.

---

## 4. Planned Agents & Roles Specification

The platform utilizes **9 specialized agents**, each with a strictly scoped mandate:

| # | Agent Name | Core Responsibility | Tooling / Data Sources | Execution Model |
|---|------------|---------------------|------------------------|-----------------|
| 1 | **Planner Agent** | Parses natural language input into structured trip requirements; formulates execution plans; coordinates delegation. | LLM Reasoning, Prompt Parsing | Graph Entry Node |
| 2 | **Flight Agent** | Searches, ranks, and selects flight options based on origin, destination, dates, cabin class, and transit tolerance. | Flight MCP / Flight APIs / Mock Engine | Specialized Subgraph / Parallel Node |
| 3 | **Hotel Agent** | Identifies lodging matching location preferences, guest counts, amenities, and price ceilings. | Hotel MCP / Booking APIs / Mock Engine | Specialized Subgraph / Parallel Node |
| 4 | **Activity / Experience Agent** | Curates daily cultural, culinary, and recreational experiences fitting travel pace and interests. | Places API / RAG Knowledge Base / Mock Engine | Specialized Subgraph / Parallel Node |
| 5 | **Weather Agent** | Analyzes historical climate patterns and 14-day forecasts for target destinations to flag outdoor hazards. | Weather MCP / OpenWeather API / Mock Engine | Pre-planning Context Enricher |
| 6 | **Research Agent** | Retrieves visa guidelines, health advisories, seasonal tips, cultural customs, and local transit advice. | Supabase pgvector RAG + Fresh Web Search | Parallel Context Provider |
| 7 | **Budget Agent** | Enforces hard financial constraints, calculates total costs, taxes, reserves contingency funds, and suggests trade-offs. | Pure Python Deterministic Financial Engine | Constraint Validator & Optimizer |
| 8 | **Validator / Safety Agent** | Validates temporal feasibility, travel pacing, geographic proximity, and safety advisories; flags contradictions. | Pure Python Validation Rules + Safety Guardrails | Final Gatekeeper Node |
| 9 | **Itinerary Agent** | Synthesizes approved flights, hotels, activities, and research into a coherent, hour-by-hour interactive itinerary. | LLM Synthesis Engine + Structured Markdown/JSON | Output Generation Node |

---

## 5. Architectural Guardrails & Security Policies

1. **Input Guardrails**:
   - Sanitizes user input against prompt injection, jailbreak attempts, and system prompt extraction attacks.
   - Enforces character limits, token quotas, and language detection.
2. **Tool Execution Guardrails**:
   - Least-privilege permissions: read-only access for search and data retrieval tools.
   - Action tools (e.g., booking) require explicit HITL tokens and mock sandbox execution in demo environments.
   - Maximum timeout of 25 seconds on all external HTTP/MCP calls.
3. **Output Guardrails**:
   - Every agent output is validated against strict Pydantic models with `model_validate()`.
   - Hallucination checks verify that cited flight numbers, prices, and locations match tool observation data.
4. **Data Isolation & Multi-Tenancy**:
   - Supabase PostgreSQL with Row Level Security (RLS) ensures users can access only their own trips, profiles, and preferences.
   - Sensitive credentials (API keys, Supabase Service Role keys) are strictly isolated to server runtime and never sent to the client.

---

## 6. Technical Stack Specifications

- **Runtime & Orchestration**: Python 3.11+, LangGraph, LangChain Core, Pydantic v2
- **Frontend / UI**: Streamlit with custom CSS design tokens, dynamic cards, stateful re-rendering, and interactive approval modals
- **Tool Protocol**: Model Context Protocol (MCP) clients and servers
- **Database & Storage**: Supabase (PostgreSQL 15+, Supabase Auth, pgvector extension for high-performance embeddings)
- **Knowledge & Retrieval**: RAG (text-embedding-3-small, cosine distance similarity) + Web Search (Tavily / Brave Search)
- **Observability & QA**: LangSmith (tracing, token usage, latency analysis, automated regression evaluation datasets)
- **Execution Modes**:
  - `DEMO_MODE=true`: Deterministic, offline-capable mocks for reliable unit testing, local demoing, and interviews without requiring active API keys.
  - `DEMO_MODE=false`: Live API integration with real travel service providers.

---

## 7. Deliverables & Acceptance Criteria

- Fully functional, interview-ready multi-agent architecture executed across 18 distinct phases.
- Zero secrets committed to version control; verified automated `.gitignore` and clean `.env.example`.
- Clear, reproducible setup with deterministic mock mode (`DEMO_MODE=true`).
- Comprehensive test coverage across deterministic logic, Pydantic schemas, and LangGraph state transitions.
- Interactive Streamlit application displaying live agent execution traces, interactive itineraries, dynamic disruption replanning demonstrations, and human approval checkpoints.
