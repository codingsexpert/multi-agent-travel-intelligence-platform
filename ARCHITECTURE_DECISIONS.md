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
