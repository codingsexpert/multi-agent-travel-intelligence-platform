# Architectural Decision Records (ADRs)

This document records the foundational architectural decisions made for the **Multi-Agent AI Travel Intelligence & Dynamic Replanning Platform**, detailing the context, decision, rationale, and alternatives considered.

---

## Table of Contents
1. [ADR-01: Multi-Agent Architecture vs. Monolithic LLM](#adr-01-multi-agent-architecture-vs-monolithic-llm)
2. [ADR-02: LangGraph for Stateful Orchestration](#adr-02-langgraph-for-stateful-orchestration)
3. [ADR-03: Model Context Protocol (MCP) for Tool Integration](#adr-03-model-context-protocol-mcp-for-tool-integration)
4. [ADR-04: Supabase as Unified Backend Platform](#adr-04-supabase-as-unified-backend-platform)
5. [ADR-05: Supabase pgvector for Vector Search](#adr-05-supabase-pgvector-for-vector-search)
6. [ADR-06: Hybrid Knowledge Strategy: RAG vs. Web Search](#adr-06-hybrid-knowledge-strategy-rag-vs-web-search)
7. [ADR-07: Streamlit for Interactive Application Interface](#adr-07-streamlit-for-interactive-application-interface)
8. [ADR-08: Pydantic v2 for Schema Enforcement & Validation](#adr-08-pydantic-v2-for-schema-enforcement--validation)
9. [ADR-09: LangSmith for Observability & Evaluation](#adr-09-langsmith-for-observability--evaluation)
10. [ADR-10: Strict Boundaries — When NOT to Use an Agent](#adr-10-strict-boundaries--when-not-to-use-an-agent)
11. [ADR-19: Dynamic Replanning Engine & Selective Execution](#adr-19-dynamic-replanning-engine-deterministic-dependency-mapping-and-selective-execution)
12. [ADR-20: Human-in-the-Loop (HITL) Approval Workflow & Transactional Governance](#adr-20-human-in-the-loop-hitl-approval-workflow--transactional-governance)
13. [ADR-21: Production LangSmith Observability, Secret Redaction, & Failure Isolation](#adr-21-production-langsmith-observability-secret-redaction--failure-isolation)

---

## ADR-01: Multi-Agent Architecture vs. Monolithic LLM

### Context
Travel planning requires balancing disparate domain spaces: aviation schedules, hospitality inventory, geographic routing, weather forecasts, visa regulations, budgeting math, and temporal synchronization. A single monolithic prompt given to a single LLM must handle hundreds of parameters at once.

### Decision
We adopt a **Multi-Agent Architecture** with specialized domain agents (Planner, Flight, Hotel, Activity, Weather, Research, Itinerary) coordinated through a central graph.

### Rationale
- **Cognitive Load & Context Windows**: Specialized agents receive concise system prompts and only the relevant tools. This dramatically minimizes context window bloat, reduces attention degradation, and mitigates hallucination.
- **Independent Evolutions & Tool Scoping**: The Flight Agent only needs flight search schemas; it should never have access to hotel or payment APIs. Least-privilege tool distribution reduces catastrophic tool calling errors.
- **Model Tiering & Cost Optimization**: Lightweight tasks (e.g., extracting date ranges, parsing weather forecasts) can run on ultra-fast, cheap models (`gpt-4o-mini`), while strategic reasoning (Planner, Replanner) uses high-capacity models (`gpt-4o`).
- **Parallel Execution**: Flights, hotels, activities, and weather can be queried simultaneously, slashing end-to-end plan generation latency by over 60%.

### Alternatives Considered
- *Monolithic Mega-Prompt*: Failed on complex multi-city constraints, frequently hallucinated missing connections, and exceeded token budgets.
- *Linear Pipeline (Chain of Thought)*: Sequential execution is too slow (exceeding 90 seconds per query) and lacks backtracking/replanning capabilities.

---

## ADR-02: LangGraph for Stateful Orchestration

### Context
Travel planning is intrinsically iterative. If a selected hotel blows the remaining budget, or if bad weather invalidates an outdoor activity, the system must loop back, replan specific components, and adjust state without restarting from scratch. Furthermore, human approval requires pausing execution mid-flight and resuming safely.

### Decision
We use **LangGraph** as the core stateful graph orchestrator.

### Rationale
- **Cyclic Graphs**: Unlike standard DAG engines (e.g., Airflow, LangChain sequential chains), LangGraph natively supports cycles, conditional loops, and state-preserving replanning loops.
- **First-Class Human-in-the-Loop (HITL)**: LangGraph provides native `interrupt()` mechanisms that pause graph execution, snapshot state to durable persistence, and await external input (e.g., user booking confirmation) before resuming.
- **Strict State Typing**: LangGraph uses typed schemas (`TypedDict` / Pydantic), ensuring every node has deterministic read/write contracts against the shared state.
- **Time-Travel & Debuggability**: Every node execution creates an immutable checkpoint, enabling interviewers and developers to inspect state evolution step-by-step.

### Alternatives Considered
- *AutoGen / CrewAI*: Provide conversational multi-agent loops but lack deterministic state control, robust checkpointing, and fine-grained graph routing needed for production enterprise software.
- *Vanilla Python Loops*: Hard to scale, lack built-in persistence/interrupt primitives, and cannot easily integrate with distributed tracing tools.

---

## ADR-03: Model Context Protocol (MCP) for Tool Integration

### Context
Agents need access to external tools: flight databases, hotel listings, weather services, and currency converters. Hardcoding vendor-specific REST SDKs into agent code creates tight coupling, complicates testing, and creates security vulnerabilities.

### Decision
We adopt the **Model Context Protocol (MCP)** as the standard abstraction layer for tool integration.

### Rationale
- **Standardized Client-Server Protocol**: MCP decouples agent reasoning from tool implementation via standard JSON-RPC contracts over stdio or SSE.
- **Seamless Mocking (`DEMO_MODE`)**: We can run local mock MCP servers that simulate flight and hotel APIs without altering a single line of agent code. This guarantees 100% offline interview readiness and reliable unit testing.
- **Sandboxed Security**: MCP tool servers run in isolated processes with scoped permissions, preventing arbitrary network egress from the core agent runtime.

### Alternatives Considered
- *LangChain `@tool` Python wrappers*: Simple to write but tightly coupled to the Python process and lack protocol-level isolation across different tool ecosystems.

---

## ADR-04: Supabase as Unified Backend Platform

### Context
The platform requires user authentication, relational database storage for trips and itineraries, vector similarity search for destination knowledge, and real-time subscription capabilities.

### Decision
We use **Supabase** (PostgreSQL, Supabase Auth, Row Level Security, and pgvector) as our primary backend infrastructure.

### Rationale
- **All-in-One Developer Velocity**: Combines enterprise-grade PostgreSQL, JWT-based user authentication, and vector capabilities in a single unified platform.
- **Row Level Security (RLS)**: Enforces multi-tenant data isolation directly at the database engine level (`auth.uid() = user_id`), eliminating risk of data leaks across users.
- **Docker Optional**: Can be hosted via Supabase Cloud free tier or run locally, adhering to the principle that local Docker installation must not be mandatory for reviewers.

### Alternatives Considered
- *Custom FastAPI + SQLite + Redis + Pinecone*: Sprawls architecture across 4 distinct operational dependencies with complex sync overhead.

---

## ADR-05: Supabase pgvector for Vector Search

### Context
The Research and Activity agents need semantic retrieval over curated destination guides, visa requirements, seasonal tips, and cultural etiquette.

### Decision
We use **`pgvector`** within our existing Supabase PostgreSQL instance.

### Rationale
- **Zero Data Fragmentation**: Vector embeddings reside alongside relational trip and user data. A single SQL transaction can query both relational metadata (e.g. `destination = 'Japan' AND category = 'visa'`) and vector cosine distance.
- **HNSW Indexing**: Delivers fast, low-latency approximate nearest neighbor (ANN) retrieval without requiring an expensive external vector database cluster.
- **Cost & Operational Simplicity**: Eliminates the cost, operational overhead, and synchronization latency of dedicated vector databases (e.g. Pinecone, Qdrant).

### Alternatives Considered
- *Pinecone / Milvus*: Excellent at billion-scale vector workloads, but unnecessary overhead for curated travel intelligence domain knowledge (<100,000 documents) and separates transactional data from vector data.

---

## ADR-06: Hybrid Knowledge Strategy: RAG vs. Web Search

### Context
Travel information has two distinct temporal characteristics:
1. **Static / Slow-moving facts**: Visa laws, cultural etiquette, transit pass rules, museum permanent collections, regional climate trends.
2. **Volatile / Live conditions**: Flight cancellations, weather alerts, festival dates, temporary renovations, currency spikes.

### Decision
We implement a **Hybrid Knowledge Retrieval Architecture**:
- **RAG via pgvector** is strictly dedicated to curated, verified static destination guides.
- **Web Search (Tavily/Brave)** is dynamically triggered only for time-sensitive, fresh, or ambiguous real-world queries.

### Rationale
- **Prevents Hallucinations on Rules**: Consular and visa requirements should never be guessed or pulled from unvetted blog search results; RAG ensures grounded, authoritative knowledge.
- **Prevents Stale Itineraries**: RAG alone would fail to detect a typhoon warning or a subway line closure; Web Search provides freshness.
- **Cost & Latency Efficiency**: Querying local vector databases is sub-10ms and costs fractions of a cent; web search takes 1-3 seconds and consumes external API quotas. We only invoke Web Search when freshness is necessary.

---

## ADR-07: Streamlit for Interactive Application Interface

### Context
The platform requires an interactive UI capable of displaying complex multi-agent execution graphs, step-by-step reasoning logs, interactive daily itinerary timelines, disruption simulations, and human approval modals.

### Decision
We use **Streamlit** with a tailored CSS design system.

### Rationale
- **Python-Native Full Stack**: Allows rapid, direct integration with LangGraph state objects, Pydantic schemas, and Supabase client libraries without maintaining a disconnected TypeScript/Node frontend build system.
- **Interview & Demo Friendly**: Enables live walkthroughs where recruiters and engineers can inspect agent state, toggle between `DEMO_MODE` and live APIs, and trigger replanning events on a single running screen.
- **Stateful Session Management**: Streamlit's `st.session_state` maps cleanly to LangGraph thread IDs and user session context.

### Alternatives Considered
- *Next.js + FastAPI*: Modern and production-grade, but splits the codebase into two languages/stacks, significantly increasing setup friction and local dependency requirements for evaluators.

---

## ADR-08: Pydantic v2 for Schema Enforcement & Validation

### Context
Agents communicate across graph boundaries. Passing untyped dictionaries or raw strings leads to silent parsing errors, broken UI components, and hallucinated data structures.

### Decision
We standardize on **Pydantic v2** for all data transfer objects, agent inputs, agent outputs, and persistence models.

### Rationale
- **Deterministic Contract Enforcement**: If an LLM returns a flight price as a string (`"$550"`), Pydantic validators sanitize and cast it to `float(550.0)`. If a required field is missing, validation fails immediately at the node boundary, triggering a clean retry rather than crashing downstream.
- **High Performance**: Pydantic v2 core is implemented in Rust, offering 5x to 20x faster serialization/deserialization than v1.
- **JSON Schema Export**: Pydantic models automatically export OpenAPI-compliant JSON schemas for structured LLM tool calling.

---

## ADR-09: LangSmith for Observability & Evaluation

### Context
Multi-agent systems exhibit emergent non-deterministic behaviors. Debugging why an itinerary failed, identifying which agent caused a latency spike, or tracking token expenditure requires deep tracing.

### Decision
We integrate **LangSmith** as the central telemetry and evaluation platform.

### Rationale
- **Native LangGraph Instrumentation**: Automatically traces the full hierarchical run tree of the graph, capturing every state transition, node execution, and tool input/output without invasive custom logging.
- **Cost & Token Attribution**: Accurately attributes prompt and completion tokens to specific agents, enabling pinpoint optimization.
- **Regression Evaluation**: Allows creating standardized evaluation datasets (e.g. 50 challenging travel prompts) and benchmarking model versions against budget adherence, constraint satisfaction, and hallucination metrics.

---

## ADR-10: Strict Boundaries — When NOT to Use an Agent

### Context
A frequent anti-pattern in AI engineering is using LLM agents for tasks that are deterministic, mathematical, or rule-based. This results in slow execution, high costs, and catastrophic arithmetic errors.

### Decision
We establish explicit architectural boundaries where **LLM Agents are strictly forbidden**, delegating these tasks exclusively to pure Python:

| Capability | Prohibited Implementation | Mandatory Implementation | Rationale |
|------------|---------------------------|--------------------------|-----------|
| **Budget Summation** | Prompting an LLM: *"Calculate the sum of these 4 hotel nights and flights..."* | `sum(item.cost for item in items)` in Python | LLMs make frequent floating-point arithmetic errors. Python guarantees 100% precision. |
| **Date & Duration Math** | LLM calculating: *"How many days between April 3 and April 11?"* | `(end_date - start_date).days` via `datetime` | Zero risk of off-by-one errors or leap year mistakes. |
| **Temporal Overlap Checks** | LLM evaluating if an activity at 2:00 PM overlaps with a 1:30 PM lunch | Interval tree / datetime range comparison in Python | Deterministic collision detection. |
| **Hard Budget Threshold Checks** | LLM deciding if `$3,250 > $3,000` budget limit | `if total_cost > budget_limit:` | Prevents LLMs from "hallucinating away" budget limits. |
| **Data Schema Validation** | LLM self-checking: *"Did you include all fields?"* | `pydantic.BaseModel.model_validate()` | Compiler-level typing and validation guarantees. |
| **Direct Database Queries** | Natural language Text-to-SQL for core application queries | Supabase PostgREST client with parameterized queries | Eliminates SQL injection and performance degradation. |

### Summary Rule
> **Agents are for Reasoning, Qualitative Evaluation, and Natural Language Synthesis.**  
> **Python is for Arithmetic, Hard Constraint Enforcement, and Deterministic Logic.**

---

## ADR-11: LangGraph Core Engine, Typed TravelState & Planner Agent Boundaries

### Context
In Phase 4, we introduce the first agentic reasoning node: the Planner Agent. We need a clear division between intake reasoning, deterministic validation, clarification dialogue, and future specialized agent execution.

### Decision
1. **LangGraph as State Machine**: We use `langgraph.graph.StateGraph` backed by a strongly typed `TravelState` TypedDict. Transitions between nodes are governed by deterministic Python conditional routing (`route_after_planner`), not LLM intent parsing.
2. **Planner Agent Responsibility**: The Planner Agent only extracts parameters, detects missing critical requirements, and identifies conflicts. It is strictly forbidden from searching flights, scraping hotels, or writing full itineraries.
3. **Structured Pydantic Validation**: All extracted specifications must pass through `NormalizedTravelRequest` and `PlannerResult`. Raw LLM outputs are never directly injected into state.
4. **Deterministic Validation Post-Processing**: Date order, positive duration, traveler count, and budget non-negativity are verified deterministically in Python.
5. **Loop and Retry Limits**: Execution is protected by `MAX_GRAPH_STEPS = 10` and `MAX_PLANNER_RETRIES = 2`.
6. **Graceful DEMO_MODE Fallback**: When live LLM credentials are absent or in `DEMO_MODE=true`, `DemoPlannerExtractor` handles extraction deterministically, flagging outputs with `is_demo=True`.

---

## ADR-12: Multi-Agent Parallel Execution, Failure Isolation & Decoupled State

### Context
In Phase 5, the workflow expands from a single reasoning node into 5 specialized domain agents (Flight, Hotel, Activity, Weather, Research). We must prevent tight agent-to-agent coupling, eliminate concurrent state update collisions, and handle partial agent failures gracefully.

### Decision
1. **Decoupled State Communication**: Agents never call one another directly. All inputs and outputs flow through the centralized `TravelState`.
2. **Parallel Fan-Out via Dedicated Keys**: Domain-specific keys (`flight_options`, `hotel_options`, `activities`, `weather`, `research_results`) isolate parallel writes, while shared diagnostic lists (`agent_runs`, `warnings`, `errors`) utilize `Annotated[List, operator.add]` reducers.
3. **Failure Isolation**: Each agent executes wrapped in `execute_agent_safely`. If an individual agent encounters a network/sensor failure, the exception is caught, logged, recorded as `FAILED` in `agent_runs`, and appended to `warnings`. The workflow transitions to `PARTIAL_RESULTS` rather than aborting.
4. **Deterministic Mock Catalog (`DEMO_DATA`)**: All candidate options are generated deterministically and explicitly marked with `demo_data: True` and mock catalog sources. No fake live availability is reported.

---

## ADR-13: Pure Python Budget Engine & Deterministic Itinerary Validator

### Context
Travel budgeting and constraint verification involve strict mathematical addition, currency checks, temporal feasibility, and safety boundaries. Probabilistic Large Language Models (LLMs) hallucinate arithmetic totals, fail floating-point precision, and display sycophantic tendencies that overlook scheduling conflicts and budget overages.

### Decision
1. **Zero LLM Arithmetic in Budgeting**:
   - `BudgetEngine` is implemented in pure Python with exact floating-point precision.
   - Calculates flights, hotels, activities, food allowances, local transit, and incidental buffers deterministically.
   - Enforces a **STRICT budget strategy**: if `total_estimated_cost > budget`, marks `within_budget = False`, calculates exact overage and utilization %, and issues an `OVER_BUDGET` warning.
   - Currency mismatch is flagged as an explicit advisory notice rather than executing ungrounded conversions until the Currency MCP/API is introduced.
2. **Zero LLM Logic in Feasibility Validation**:
   - `ValidatorEngine` applies deterministic Python rules to verify itinerary viability:
     - *Dates*: Enforces positive durations, valid ISO parsing, and date order (`end_date >= start_date`). Supports flexible unpinned dates with non-fatal warnings.
     - *Travelers*: Enforces positive integer headcounts (`travelers >= 1`).
     - *Flights*: Verifies departure strictly precedes arrival (`departure < arrival`).
     - *Hotels*: Validates non-negative nightly rates and stay durations.
     - *Activities*: Detects duplicate activity recommendations and flags travel-time conflicts (`POSSIBLE_TIME_CONFLICT`) when flight arrivals buffer insufficiently with activity starts.
     - *Weather*: Audits presence of meteorological feeds; flags `WEATHER_UNAVAILABLE` on agent failure without fabricating forecasts.
3. **Tiered Severity Hierarchy**:
   - `INFO`: Informational telemetry notice (e.g. `DEMO_DATA_ACTIVE`).
   - `WARNING`: Non-fatal advisory (e.g. `OVER_BUDGET`, `WEATHER_UNAVAILABLE`, `POSSIBLE_TIME_CONFLICT`, `CURRENCY_MISMATCH`). Workflow transitions to `READY_WITH_WARNINGS`.
   - `ERROR`: Critical blocking invalidity (e.g. `INVALID_DATE_ORDER`, `INVALID_TRAVELER_COUNT`, `NEGATIVE_BUDGET`). Workflow transitions to `VALIDATION_FAILED`.
   - When 0 errors and 0 warnings exist: workflow transitions to `READY_FOR_ITINERARY`.
4. **LangGraph Pipeline Integration**:
   - The workflow connects `[flight, hotel, activity, weather] -> research -> budget_engine -> validator -> END`.
   - Budget Engine and Validator are explicitly tracked in `agent_runs` as `engine_type: "DETERMINISTIC"`.

---

## ADR-14: Model Context Protocol (MCP) Tool Integration, Least Privilege & Security Sandboxing

### Context
In Phase 7, agents require access to external capabilities (flight discovery, lodging specifications, spatial routing, weather forecasts, web search, and currency exchange). Direct coupling of agents to provider SDKs leads to vendor lock-in, credential leakage, uncontrolled tool permissions, and vulnerability to prompt injection via retrieved web content.

### Decision
1. **Decoupled MCP Architecture**:
   - Capabilities are partitioned into 6 distinct MCP tool modules: Flight, Hotel, Maps, Weather, Search, and Currency.
   - Agents interact strictly with tool interfaces through `MCPClient.call_tool()`. No provider SDKs or MCP implementation logic reside within agents.
2. **Strict Least-Privilege Permissions**:
   - Each agent role is governed by `AGENT_TOOL_PERMISSIONS`. Unauthorized tool invocations fail immediately with `PERMISSION_DENIED`.
   - Booking, payments, booking cancellations, code execution, and shell access are explicitly prohibited across all tool definitions.
3. **Defense-in-Depth Security Sandboxing**:
   - *SSRF Prevention*: URLs targeting loopback (`127.0.0.1`, `localhost`) or private RFC-1918 subnets (`10.x.x.x`, `192.168.x.x`) are rejected.
   - *Untrusted Content Sanitization*: All retrieved web snippets are tagged `untrusted: True` and sanitized to strip script tags and neutralize prompt injection attempts.
   - *Secret Scrubbing*: Telemetry payloads automatically mask sensitive credentials (`api_key`, `secret`, `token`, `password`, `authorization`).
4. **Structured Error Handling & Resiliency**:
   - MCP failures return structured `ToolExecutionError` objects (`tool_name`, `error_code`, `message`, `retryable`, `execution_id`) without crashing LangGraph orchestration.
5. **Observability & UI Telemetry**:
   - Tool calls emit `MCPToolCall` audit records capturing latency, retry counts, execution mode (`DEMO` vs `LIVE`), and status chips rendered live in the Streamlit Travel Command Center.

---

## ADR-15: Real Provider Adapters, In-Memory Caching, and Resiliency

### Context
In Phase 8, external capabilities accessed via MCP tools must transition from synthetic mock responses to legitimate external APIs (Frankfurter ECB, Open-Meteo, Photon/OSRM, Wikipedia/Tavily, and Amadeus GDS) while keeping the strict architectural rule: **Agents must never directly call external APIs**. The integration must maintain deterministic DEMO mode, protect secrets, handle rate limits (HTTP 429), prevent cascading failures, and cache idempotent responses.

### Decision
1. **MCP as the Capability Boundary**:
   - The integration follows a clean layered design:
     ```
     Agent  ──>  MCP Tool  ──>  Provider Adapter  ──>  External API
                                                           │
     Agent  <──  MCP Tool  <──  Normalized Model  <────────┘
     ```
   - Agents remain completely decoupled from HTTP clients, provider request formats, and authentication flows.
2. **Real Provider Selection**:
   - *Currency*: Frankfurter API (live European Central Bank reference exchange rates, open and keyless).
   - *Weather*: Open-Meteo API (WMO standard meteorological data, live daily forecasts, open and keyless).
   - *Maps & Places*: Photon (OpenStreetMap geocoding & POI discovery) and OSRM (driving/transit route distance & duration calculation, open and keyless).
   - *Search*: Wikipedia OpenSearch API (live open knowledge) and Tavily AI search (when configured), with strict untrusted data isolation.
   - *Flights & Hotels*: Amadeus Travel Innovation API (GDS flight offers search v2, hotel search by city, OAuth2 client credentials token caching). When credentials are missing in LIVE mode, raises clear `ProviderConfigurationError` without fabricating fake live data.
3. **Resilient HTTP Client & Backoff**:
   - Base adapter `BaseProvider` enforces bounded exponential backoff (`max_retries=2`), explicit 5-8s timeout ceilings, and structured error mapping (`ProviderError`, `ProviderConfigurationError`, `ProviderAuthenticationError`, `ProviderRateLimitError`, `ProviderTimeoutError`, `ProviderNetworkError`, `ProviderResponseValidationError`).
   - Rate limiting: HTTP 429 parses `Retry-After` header and sleeps before bounded retry, failing cleanly if exhausted.
4. **Thread-Safe In-Memory TTL Caching**:
   - `ProviderCache` provides thread-safe TTL caching for idempotent data (FX rates 1h, weather 10m, routes/places 1h, flight/hotel searches 30m) to reduce redundant API calls and latency. Volatile real-time seat locks are never cached.
5. **Security & Zero Secret Exposure**:
   - API keys and tokens are loaded strictly from environment variables.
   - HTTP headers and telemetry scrub all sensitive credentials (`Authorization`, `api_key`, `token`, `secret`).
   - All retrieved web content is tagged `untrusted: True` and sanitized before reaching reasoning agents.
6. **DEMO vs. LIVE Diagnostics**:
   - `DEMO_MODE=true` returns deterministic mock data with `demo_data=True` and `[DEMO_DATA]` markers.
   - `DEMO_MODE=false` executes live providers; if credentials are missing, returns structured `PROVIDER_CONFIGURATION_ERROR`.
   - Streamlit Agent Trace page clearly displays provider attribution, live vs demo badges (`✓ LIVE` vs `✓ DEMO DATA`), duration, and failure diagnostics.

---

## ADR-16: RAG + Supabase pgvector Architecture, Metadata Filtering, and Prompt Injection Defense

### Context
In Phase 9, reasoning agents (Activity Agent, Research Agent, and Planner) require reliable, curated travel knowledge (local customs, shrine etiquette, transit rules, attraction heritage, neighborhood overviews). Treating volatile operational APIs or unstructured web search as the sole knowledge source leads to hallucinated customs, broken recommendations, or excessive API cost. Conversely, dumping entire travel guidebooks into prompt contexts triggers token bloat, high latency, and vulnerability to indirect prompt injection.

### Decision
1. **Tri-Partite Information Source Taxonomy**:
   - **RAG Knowledge Base**: Stable, vetted, curated travel domain knowledge (customs, etiquette, attractions, transit rules).
   - **MCP / API Gateway**: Volatile, structured operational data (live flights, hotel inventory, current forecasts, FX rates).
   - **Web Search (Phase 10)**: Dynamic, breaking, ephemeral information (airport strikes, festival dates, emergency alerts).
2. **Supabase pgvector Database Architecture**:
   - Migration `20260928000003_pgvector_rag.sql` enables the `vector` extension and creates a dedicated `public.travel_documents` table.
   - Vector column: `embedding vector(1536)` matching OpenAI `text-embedding-3-small`.
   - Indexing: HNSW index (`idx_travel_documents_embedding_hnsw`) with cosine similarity (`vector_cosine_ops`) for sub-10ms nearest neighbor search.
   - Stored procedure: `match_travel_documents` executes combined vector cosine similarity and relational predicate filtering under `SECURITY INVOKER`.
3. **Configurable Embedding Strategy & Offline DEMO_MODE**:
   - Configurable via `config/settings.py` (`embedding_model="text-embedding-3-small"`, `embedding_dimension=1536`).
   - If `OPENAI_API_KEY` is missing in live mode, raises explicit `EmbeddingConfigurationError`.
   - In `DEMO_MODE=true`: `MockEmbeddingService` generates deterministic, unit-normalized 1536-dimensional float vectors from text SHA-256 hashes and token buckets, enabling realistic offline cosine similarity evaluation without external APIs or cost.
4. **Deterministic Ingestion & Deduplication**:
   - Supports Markdown (.md), Plain Text (.txt), and JSON (.json).
   - Text cleaning normalizes spacing, strips unprintable control characters, and collapses redundant blank lines.
   - Deterministic chunking preserves paragraph and sentence boundaries (`rag_chunk_size=500`, `rag_chunk_overlap=80`), pruning micro-fragments (< 25 chars).
   - SHA-256 content hashing deduplicates ingestion, reusing cached chunks and preventing redundant embedding generation costs.
5. **Hybrid Vector Similarity + Metadata Filtering**:
   - Retrieval queries accept `query`, `destination`, `country`, `category` (e.g. customs, attractions, food, transport), and `source_trust`.
   - Relational metadata filters run alongside vector distance to maximize precision and eliminate cross-destination pollution (e.g. Tokyo query never retrieves Paris customs).
6. **Row Level Security (RLS) & Private Knowledge Isolation**:
   - Public curated baseline documents (`is_public = true`) are readable by all authenticated and anonymous sessions.
   - User-uploaded private documents (`is_public = false`) are guarded by `auth.uid() = user_id`. Cross-user data leakage is strictly blocked by database RLS.
7. **Prompt Injection Defense & Untrusted Data Sandboxing**:
   - Retrieved chunks are treated as **UNTRUSTED DATA** (`untrusted: True`).
   - Regex-based sanitization defangs adversarial directives (`Ignore previous instructions`, `SYSTEM:`, `<script>`).
   - Injected into agent prompts inside isolated `<curated_travel_knowledge>` blocks with explicit directives instructing the LLM that content represents factual reference data, not instructions.
8. **No Fabricated Citations**:
   - Every chunk retains source attribution, trust classification (`OFFICIAL`, `CURATED`, `REFERENCE`, `UNKNOWN`), and real canonical URLs. Documents without URLs are explicitly labeled `[Curated Knowledge]`.

---

## ADR-17: Web Search, Fresh Information Research, and Search MCP Architecture

### Context
In Phase 10, the multi-agent travel platform requires access to fresh, volatile, and time-sensitive intelligence (temporary attraction closures, transport strikes, seasonal festivals, breaking travel advisories, and official border requirements). Static RAG cannot serve these volatile facts, while structured operational APIs (Amadeus, Open-Meteo) only provide pricing and schedules. Furthermore, allowing agents to call external search APIs directly would couple agent reasoning to provider endpoints and bypass least-privilege security controls. Direct web retrieval also introduces Server-Side Request Forgery (SSRF) and indirect prompt injection vulnerabilities from unvetted third-party web content.

### Decision
1. **Strict Tri-Modal Information Separation**:
   - **RAG Knowledge Base**: Stable, vetted, curated travel knowledge (etiquette, customs, attraction heritage, transit rules).
   - **MCP Operational APIs**: Volatile, structured operational data (flight inventory, hotel rooms, weather forecasts, FX rates).
   - **Search MCP / Web Search**: Fresh, unpredictable real-world intelligence (festivals, temporary closures, strikes, advisories, news).
2. **Search MCP Gateway Boundary**:
   - Agents never invoke search APIs directly. The Research Agent accesses search tools strictly through the Search MCP client gateway.
   - MCP tools exposed:
     - `web_search`: Structured query with recency (`today`, `24h`, `7d`, `30d`, `all`), max results, language, and domain filters.
     - `search_news`: Specialized discovery for regional news, disruptions, and festival schedules.
     - `fetch_page`: Sandboxed HTTP document retrieval for targeted inspection of official advisory pages.
3. **Source Trust Classification & Official Verification**:
   - Web domains are programmatically classified into 5 trust tiers: `OFFICIAL` (government, embassy, official tourism), `NEWS` (established journalism), `REFERENCE` (curated encyclopedias), `COMMUNITY` (forums), and `UNKNOWN`.
   - Sensitive legal claims (visa rules, passport validity, border restrictions) **require `OFFICIAL` authority sources**. If official verification cannot be confirmed, the system explicitly reports verification as incomplete rather than fabricating requirements.
4. **Source Discrepancies & Conflict Handling**:
   - When independent sources report conflicting data (e.g. market operating hours, renovation dates), the system does not silently choose one.
   - A structured `ConflictingClaim` record is generated containing both claims, sources, publication dates, and actionable uncertainty guidance for travelers.
5. **SSRF & Private Network Defense**:
   - `MCPSecurityManager.validate_url()` enforces strict URL validation before any outbound HTTP connection:
     - Blocks loopbacks (`localhost`, `127.0.0.1`, `0.0.0.0`, `[::1]`).
     - Blocks private RFC 1918 subnets (`10.x`, `192.168.x`, `172.16-31.x`) and IPv6 unique local / link-local addresses (`fc00::`, `fe80::`).
     - Blocks cloud metadata endpoints (`169.254.169.254`, `metadata.google.internal`).
     - Disallows dangerous schemes (`file://`, `ftp://`), permitting only HTTP/HTTPS.
     - Enforces domain allowlists for page fetching.
6. **Prompt Injection Defense & Untrusted Data Isolation**:
   - All retrieved web content is tagged `untrusted: True`.
   - Content sanitization strips `<script>`, `<style>`, `<nav>`, `<header>`, `<footer>`, `<aside>`, and tracking elements.
   - Adversarial instructions (`Ignore previous instructions`, `SYSTEM INSTRUCTIONS:`, `developer mode`) are filtered and neutralized.
   - Retrieved web content is treated strictly as data and can never alter LangGraph state flow, grant permissions, or invoke tools.
7. **Rate Limiting, Bounded Retries & Resilient Caching**:
   - Bounded retries (maximum 2 attempts) on 5xx errors; no indefinite retry loops.
   - HTTP 429 response handling inspects `Retry-After` headers and applies bounded backoff.
   - In-memory `ProviderCache` (15-minute TTL) prevents redundant searches and excessive upstream consumption.
8. **DEMO vs LIVE Mode Determinism**:
   - In `DEMO_MODE=true`: Deterministic mock results marked `DEMO` with realistic publication dates, trust classifications, and structured findings.
   - In `DEMO_MODE=false`: Queries live Tavily AI or Brave Search API. If credentials are missing, raises explicit `ProviderConfigurationError` without fabricating live data.

---

## ADR-18: Centralized Production Guardrails, Zero Trust Security Layer, and Execution Circuit Breakers

### Context
In Phase 11, the multi-agent travel intelligence platform requires an enterprise-grade, centralized security and guardrails architecture protecting the system across all attack vectors: user inputs, agent reasoning boundaries, tool executions, MCP invocations, RAG knowledge retrievals, external web content, API payloads, outputs, and multi-tenant persistence. A decentralized, ad-hoc approach where each agent implements custom validation leads to inconsistent policies, security blindspots, and code duplication. Furthermore, relying purely on LLMs for safety checks introduces non-deterministic vulnerabilities and latency.

### Decision
1. **Zero Trust Architecture**:
   - Every external artifact (`USER INPUT`, `RETRIEVED RAG CONTENT`, `WEB CONTENT`, `TOOL RESULTS`, `EXTERNAL API RESPONSES`) is categorized as untrusted data (`untrusted: True`).
   - The security boundary follows a deterministic four-tier pipeline:
     ```
     USER -> INPUT GUARDRAILS -> LANGGRAPH -> AGENTS -> TOOL GUARDRAILS -> MCP/RAG/WEB -> OUTPUT GUARDRAILS -> VALIDATOR -> RESPONSE
     ```
2. **Deterministic-First Security Controls**:
   - Safety does not rely exclusively on an LLM judge.
   - Core controls use deterministic validation: strict Pydantic v2 schemas, role-based allowlists, regex pattern filters, URL network checks, circuit breakers, and sliding-window rate limiters.
3. **Input Guardrails & Prompt Injection Defense (`guardrails/input.py`)**:
   - Length bounds (`MAX_INPUT_CHARS=2000`).
   - Instruction/Data Separation: blocks explicit prompt injection (`ignore previous instructions`, `reveal system prompt`, `show api keys`, `bypass security`) and code execution syntax (`eval`, `__import__`, `<script>`).
   - Domain parameter validation: positive budgets, realistic traveler counts (1–50), ISO currency checks, valid date sequences (return >= departure), minimum 1-day trip duration.
   - Automatic PII detection and masking (credit cards, passport numbers, email, phone numbers).
4. **Tool Guardrails & High-Risk Action Blocking (`guardrails/tools.py`)**:
   - Centralized authorization layer inside `MCPClient.call_tool()`.
   - Explicit agent allowlists: Flight (`search_flights`, `compare_flights`, `get_flight_details`), Hotel (`search_hotels`, `get_hotel_details`), Activity (`search_places`, `calculate_route`, `estimate_travel_time`), Weather (`get_current_weather`, `get_forecast`, `get_weather_alerts`), Research (`web_search`, `fetch_page`, `search_news`), Budget/Validator (`get_exchange_rate`, `estimate_travel_time`).
   - **Autonomous High-Risk Action Blocker**: Unconditionally blocks autonomous execution of `booking`, `purchasing`, `payment`, `cancellation`, and `financial_transaction`. These require explicit human approval in future phases.
   - Argument validation: coordinates, dates, currencies, and bounded search queries.
5. **Output Guardrails & Fact/Source Safety (`guardrails/output.py`)**:
   - Pydantic schema validation for every agent deliverable.
   - Prohibits negative pricing, negative budgets, or invalid temporal spans.
   - Fact/Source Safety: verifies all external claims carry legitimate attribution (`source`, `provider`, `retrieved_at`, `status`); prohibits fabricated citations.
6. **Secret Management & PII Sanitization (`guardrails/security.py`)**:
   - `SecretRedactor`: Continuously redacts OpenAI/Tavily keys, JWTs, Bearer tokens, passwords, postgres connection strings, and Authorization headers across logs, exceptions, and traces.
   - Secrets are strictly forbidden from being stored in LangGraph state.
   - `PIISanitizer`: Masks credit cards, passport numbers, phone numbers, and emails.
7. **Execution Circuit Breakers & Rate Limiting (`guardrails/security.py`)**:
   - `WorkflowCircuitBreaker`: Enforces hard runtime limits (`MAX_AGENT_STEPS=15`, `MAX_TOOL_CALLS=25`, `MAX_RETRIES=2`, `MAX_SEARCH_CALLS=5`, `WORKFLOW_TIMEOUT_SECONDS=30.0`). Prevents infinite LangGraph loops.
   - `RateLimiter`: Thread-safe sliding-window rate limiter (`RATE_LIMIT_REQUESTS=60 / 60s`).
8. **Structured Security Auditing & Safe Telemetry**:
   - `SecurityAuditor`: Records structured security events (`PROMPT_INJECTION_DETECTED`, `HIGH_RISK_ACTION_BLOCKED`, `TOOL_PERMISSION_DENIED`, etc.) with safe metadata.
   - Streamlit UI (`agent_trace.py` and `settings.py`) provides real-time visibility into guardrail statuses and security events.
9. **Supabase Row-Level Security (RLS) & Tenant Isolation**:
   - All relational tables enforce `auth.uid() = user_id`.
   - Cross-user data leakage is strictly blocked at the database engine tier.
10. **Consistent DEMO vs LIVE Guardrails**:
    - Security guardrails remain 100% active in both `DEMO_MODE=true` and `DEMO_MODE=false`. Mocking data never bypasses safety boundaries.

---

## ADR-19: Dynamic Replanning Engine, Deterministic Dependency Mapping, and Selective Execution

### Context
In real-world travel, disruptions are inevitable: flights are delayed or cancelled, sudden weather events close outdoor attractions, hotel rates surge or rooms sell out, and users frequently modify budgets or dates mid-stream. 
A naive approach would prompt an LLM to "re-plan the entire trip from scratch." This is brittle, non-deterministic, cost-inefficient, and destructive: confirmed flights and hotels might be needlessly altered, budgets recomputed with arithmetic errors, and previously verified elements corrupted. 
In Phase 12, the platform requires an intelligent, deterministic Dynamic Replanning Engine that:
1. Detects exactly what changed (`ChangeEvent`).
2. Deterministically identifies affected components and trip days via a dependency graph (`ImpactAnalysis`).
3. Re-executes ONLY affected nodes (`RERUN`), safely reusing unaffected deliverables (`REUSED`).
4. Re-computes financial budgets deterministically and verifies constraints with `ValidatorEngine`.
5. Preserves immutable history through state versioning (`v1 -> v2`).
6. Preserves `last_valid_itinerary` if replanning fails.
7. Prevents infinite replanning recursion cycles.

### Decision
1. **Core Philosophy: REPLAN ONLY WHAT IS AFFECTED**:
   - Rejection of monolithic LLM trip regeneration.
   - Deterministic dependency resolution ensures predictable, surgical updates.
2. **Typed Change Event Model (`models/replanning.py`)**:
   - Categorical enums (`ChangeEventType`) covering 15 disruption variants (`FLIGHT_CANCELLED`, `WEATHER_ALERT`, `HOTEL_UNAVAILABLE`, `BUDGET_CHANGED`, etc.).
   - Standardized payload with severity tiers, target entities, old/new values, and timestamps.
3. **Explicit Deterministic Dependency Graph (`ReplanningEngine.DEPENDENCY_GRAPH`)**:
   - Upstream nodes map directly to downstream consequences:
     - `flight` -> `day_1_schedule`, `day_1_activities`, `hotel_checkin`, `budget_engine`
     - `hotel` -> `lodging_location`, `transit_routes`, `evening_activities`, `budget_engine`
     - `weather` -> `outdoor_activities`, `daily_schedule`
     - `activity` -> `daily_schedule`, `transit_routes`, `budget_engine`
     - `budget_engine` -> `validator`
4. **Selective Re-Execution Pipeline**:
   - Workflow nodes are partitioned into `rerun_nodes`, `reusable_nodes`, and `invalidated_nodes`.
   - In LangGraph (`replanning_graph`), only rerun nodes execute; reusable deliverables are preserved intact.
   - Every node records its execution mode (`RERUN`, `REUSE`, `INVALIDATE`, `SKIP`) for transparent telemetry in the Streamlit Agent Trace.
5. **State & Itinerary Versioning (`ItineraryVersion`)**:
   - Trip states transition `v1 -> v2 -> v3` with an append-only `itinerary_history`.
   - Each version records its trigger event, execution actions, validation status, and human-readable explanation.
6. **Graceful Failure Handling & Previous Itinerary Preservation**:
   - If an external carrier API fails or an agent encounters an error during a replan, `last_valid_itinerary` is restored and the trip remains valid with clear user advisories.
7. **Replanning Loop Protection**:
   - Configurable safeguards (`MAX_REPLAN_DEPTH = 5`, `MAX_REPLAN_EVENTS = 10`, `MAX_REPLAN_NODE_EXECUTIONS = 20`) halt runaway cascading disruptions.
8. **Auditing & Row Level Security**:
   - Persistent `replanning_events` table in PostgreSQL with strict RLS policies ensuring users can only read and write replan logs for trips they own.

---

## ADR-20: Human-in-the-Loop (HITL) Approval Workflow & Transactional Governance

### Context
In autonomous AI agent systems, one of the greatest operational risks is runaway actions: an LLM deciding on its own to charge a credit card, purchase an expensive airline ticket, cancel a prepaid hotel reservation, or alter an itinerary without the traveler's explicit consent.
In Phase 13, the platform requires an enterprise-grade safety boundary enforcing that:
1. **Read-only intelligence is autonomous**: research, comparisons, weather forecasts, and route computations proceed without interruption.
2. **High-impact / transactional actions require human approval**: booking flights, reserving hotels, purchasing activities, cancellations, modifications, and payments strictly require explicit user approval.
3. **No LLM decides approval**: The approval requirement must be deterministically classified by application logic.
4. **Idempotency is guaranteed**: Network retries, page refreshes, or duplicate button clicks must never trigger duplicate bookings or payments.
5. **Dynamic replanning invalidates stale approvals**: An approval created for Trip Version 1 must never execute if dynamic replanning advances the trip to Version 2.
6. **No real money is spent**: Safe mock transactional providers simulate bookings clearly badged `DEMO / MOCK`.

### Decision
1. **Deterministic Action Classification (`models/approval.py`)**:
   - Pure Python function `classify_action_risk(action_type)` deterministically maps actions to `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL` risk.
   - Any action with risk > `LOW` automatically sets `requires_approval = True`.
2. **Strongly-Typed Pydantic Domain Models**:
   - `ActionProposal`, `ApprovalRequest`, `ApprovalDecision`, `ActionExecutionResult`, and `ApprovalAuditEvent`.
   - All parameters, costs, and state versions are strictly validated before persistence.
3. **LangGraph State Machine Pause & Resume (`graph/workflow.py`)**:
   - An `approval_gate_node` intercepts any high-impact `ActionProposal`.
   - If not yet approved by the authenticated human, it sets `hitl_paused = True` and transitions workflow status to `WAITING_FOR_APPROVAL`, halting the graph safely without polling loops.
   - Upon explicit user decision in the Streamlit Approvals UI, `resume_graph_after_approval` resumes execution, verifies permissions and version matching, and executes the approved adapter.
4. **Strict Idempotency via `idempotency_key`**:
   - Every proposal carries a unique `idempotency_key`.
   - Before executing an adapter, `ActionExecutionService` queries `action_executions`. If an execution already succeeded, it returns the existing confirmation code and payload without re-executing.
5. **State-Version Protection**:
   - Proposals store `state_version`. If dynamic replanning increments the version (`v1 -> v2`), `approval_service.invalidate_proposals_for_trip` marks pending proposals and approval requests as `CANCELLED`.
6. **Server-Side Expiry Enforcement**:
   - Proposals and requests define `expires_at`. Expired approvals cannot be approved or executed.
7. **Safe Mock Transactional Providers (`mcp/transactional_providers.py`)**:
   - `MockFlightBookingProvider`, `MockHotelBookingProvider`, `MockActivityBookingProvider` generate synthetic confirmation codes (`DEMO-FLT-XXXX`, `DEMO-HTL-XXXX`, `DEMO-ACT-XXXX`) and explicitly declare `is_mock: True`.
8. **Row Level Security (RLS) & Audit Logging**:
   - Supabase migration `20260928000005_hitl_approvals.sql` provisions tables with `auth.uid() = user_id` tenant isolation.
   - All events (`PROPOSAL_CREATED`, `APPROVAL_REQUESTED`, `APPROVED`, `REJECTED`, `EXPIRED`, `EXECUTION_STARTED`, `EXECUTION_COMPLETED`, `EXECUTION_FAILED`, `EXECUTION_CANCELLED`) are logged without secrets or credentials.

---

## ADR-21: Production LangSmith Observability, Secret Redaction, & Failure Isolation

### Context
Operating a production multi-agent system comprising LangGraph state transitions, specialized reasoning agents, MCP tool invocations, real-world API providers, vector RAG lookups, and dynamic replanning requires granular, distributed observability. Without structured tracing:
- Debugging cascading agent decisions or validator rejections is nearly impossible.
- Latency bottlenecks and slow external provider APIs cannot be systematically identified.
- Token consumption and model costs remain untracked.
- Sensitive credentials, API keys, passwords, and private user details risk leaking into external tracing platforms.
- Crucially, if an external tracing endpoint experiences a network timeout or authentication outage, the core travel planning application must NEVER crash or freeze.

### Decision
1. **Centralized Observability Service (`services/observability_service.py`)**:
   - Implemented `ObservabilityService` providing non-blocking distributed tracing across all agents, tools, RAG, Web Search, Dynamic Replanning, and HITL approvals.
   - Built `WorkflowTelemetryTracker` capturing workflow run IDs, parent/child spans, token usage, durations, retries, and errors.
2. **Strict Non-Blocking Failure Isolation**:
   - Observability is strictly non-blocking. If LangSmith API keys are missing, network connectivity is lost, or API requests return errors (e.g. 401/403/500/timeout), all exceptions are safely caught and logged.
   - The primary travel planning application continues uninterrupted in full functionality with in-memory telemetry fallback.
3. **Automated Recursive Secret & PII Scrubbing (`TraceSanitizer`)**:
   - Centralized sanitizer scans every dictionary, list, string, and URL parameter before recording or transmitting telemetry.
   - Redacts any sensitive field matching `api_key`, `token`, `password`, `secret`, `authorization`, `cookie`, `payment`, `card_number`, `cvv`, `credential`, etc.
   - Redacts `Bearer <token>` headers and URL query parameters containing keys.
4. **Authentic Model Cost & Token Accounting**:
   - Tracks exact input and output token consumption for reasoning LLMs.
   - Calculates estimated costs using official published pricing for known models (`gpt-4o`, `gpt-4o-mini`, `text-embedding-3-small`).
   - If an unknown or custom model is used, the cost is explicitly reported as `"UNKNOWN"`, strictly adhering to the architectural rule to **never fabricate token or cost metrics**.
5. **Hierarchical Span Architecture**:
   - Trace hierarchy mirrors the real execution graph:
     - Root: `Travel Request` (workflow_run_id, trip_id, user_id)
     - Level 1: `Input Guardrail`, `Planner Agent`, `Specialized Agents`, `Budget Engine`, `Validator`, `Dynamic Replanning`, `Approval Gate`
     - Level 2: `MCP Tools` (`search_flights`, `search_hotels`, `search_activities`, `get_weather`, `search_web`, `search_news`), `RAG Knowledge Retrieval`
     - Level 3: External provider adapters (`Amadeus`, `Open-Meteo`, `Wikipedia`, `Tavily`, `Frankfurter`)
6. **Unified Developer Visibility in Streamlit**:
   - Refactored `app/pages/agent_trace.py` to display:
     - WORKFLOW SUMMARY: real-time duration, operation counts, token counts, model calls, tool calls, search calls, RAG calls, and estimated costs.
     - AGENT TRACE: visual checklist for all 11 nodes with categorical labels (`LLM`, `DETERMINISTIC`, `MCP`, `RAG`, `WEB`, `HUMAN`, `MOCK`, `LIVE`).
     - TRACE DETAILS & TIMELINE: sanitized, chronological breakdown of spans.
     - LangSmith run link or safe "Tracing unavailable (Offline / Demo Mode)" indicator.

---

## ADR-22: Deterministic Model Routing, Intelligent Caching, Token Optimization, & Workflow Cost Controls

### Context
In multi-agent architectures, operational cost and latency are dominated by repetitive LLM invocations and redundant external network calls. Without disciplined controls:
- Agents may invoke expensive frontier models (e.g., `gpt-4o`) for lightweight classification, entity extraction, or text formatting that cheaper models (e.g., `gpt-4o-mini`) can perform identically.
- Re-executing workflows or polling external services triggers duplicate MCP requests, redundant web searches, and vector database queries.
- Whole-graph restarts on minor disruptions waste computational budget and tokens on already-valid travel segments.
- Runaway retries or recursive model fallbacks can lead to exponential token inflation and unexpected cloud bills.
- Crucially, cost optimization must NEVER compromise security guardrails, row-level security, SSRF defenses, or human approval requirements.

### Decision
1. **The Cheapest Reliable Mechanism Principle**:
   - Deterministic calculations & validations → Pure Python (zero LLM tokens).
   - Simple extraction, classification, and normalization → `MODEL_SIMPLE` (`gpt-4o-mini`).
   - Options reasoning and research synthesis → `MODEL_MEDIUM` (`gpt-4o-mini`).
   - Multi-constraint planning, dynamic replanning, and conflict resolution → `MODEL_COMPLEX` (`gpt-4o`).
   - Stable domain knowledge → Curated RAG vector store (`pgvector`).
   - Fresh news & advisories → Web Search MCP (`Tavily`).
   - External systems → MCP client gateway with permission verification.
   - Repeated requests → Normalized SHA-256 Intelligent Cache.

2. **Centralized Model Router (`utils/model_router.py`)**:
   - Application logic deterministically decides model tiers via `ROUTING_POLICY`.
   - The LLM is NEVER permitted to choose its own model tier.
   - Resolves provider model names from environment configuration (`MODEL_SIMPLE`, `MODEL_MEDIUM`, `MODEL_COMPLEX`).

3. **Safe Controlled Fallback Strategy**:
   - If a preferred model fails (timeout, rate limit, provider outage), the router safely switches to the configured fallback model (`model_medium_fallback`, `model_complex_fallback`).
   - Bounded to a maximum of 1 fallback attempt with fallback count attribution, preventing infinite retry loops.

4. **Centralized Cost Tracker (`utils/cost.py`)**:
   - Thread-safe (`threading.RLock`) token and dollar attribution across models, agents, and workflows.
   - Calculates exact costs based on configured input and output prices per 1,000,000 tokens.
   - Reports `"UNKNOWN"` when pricing is unconfigured; strictly forbids fabricating costs.
   - Exposes `get_workflow_summary()`, `get_model_breakdown()`, `get_agent_breakdown()`, and `get_efficiency_metrics()`.

5. **Configurable Workflow Cost Budgets**:
   - Enforces configurable ceilings: `MAX_WORKFLOW_COST` (default $1.00), `MAX_MODEL_CALLS` (default 10), and `MAX_TOTAL_TOKENS` (default 50,000).
   - Before executing an expensive model call, `check_budget()` verifies constraints and halts runaway execution with `WorkflowBudgetExceededError`, preserving valid partial state.

6. **Agent Context Minimization (`agents/base_agent.py`)**:
   - Implemented `minimize_agent_context(agent_name, state)` ensuring agents only receive their required slice of state (e.g. Weather only gets destination/dates/duration, not flight or hotel details), reducing token footprint and latency.

7. **Intelligent Caching with Mode Partitioning (`utils/cache.py`)**:
   - Stores idempotent responses keyed by domain, operation, and secret-scrubbed JSON parameter fingerprints (`hashlib.sha256`).
   - Enforces domain-specific configurable TTLs (Currency: 3600s, Weather: 1800s, Places: 86400s, Search: 900s, Flight/Hotel: 600s, RAG: 1800s).
   - Strict mode partition: DEMO cache keys and LIVE cache keys are isolated (`domain:demo` vs `domain:live`) ensuring DEMO mock data never satisfies LIVE queries.

8. **Strict Non-Caching of Transactional Operations**:
   - Operations classified as transactional (`book_flight`, `book_hotel`, `purchase_activity`, `cancel_booking`, `process_payment`, `authorize_payment`, `approve_action`, etc.) are hard-blocked from cache writes or reads (`TRANSACTIONAL_OPERATIONS`).

9. **Selective Replan Parallelization & Reused Node Tracking (`graph/workflow.py`)**:
   - Independent affected nodes in dynamic replanning execute in parallel via `ThreadPoolExecutor`.
   - Reused unaffected nodes are tracked in `cost_tracker.record_savings`, recording calls avoided, tokens saved, cost saved, and latency saved.

10. **Human-in-the-Loop Cost Guard**:
    - During human approval waiting (`WAITING_FOR_APPROVAL`), graph execution halts completely, generating zero repeated LLM calls.
    - Idempotency keys prevent duplicate execution attempts on repeated clicks.

11. **Streamlit Cost & Performance Dashboard (`app/pages/agent_trace.py`)**:
    - Section 9 provides real-time visibility into workflow cost, model breakdown, agent breakdown, cache hit rates, duplicate prevention, and estimated savings.





