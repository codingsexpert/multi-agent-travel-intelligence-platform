# System Architecture: Multi-Agent AI Travel Intelligence & Dynamic Replanning Platform

## 1. Overall System Architecture

The platform follows a layered, decoupled architecture designed for high availability, verifiable correctness, and modular scalability.

```mermaid
graph TD
    User([Traveler / Operator]) <--> UI[Streamlit UI Layer]
    UI <--> Auth[Supabase Auth - JWT]
    UI <--> AppController[Application Controller / Session Manager]
    
    subgraph Orchestration [LangGraph State Machine]
        AppController <--> GraphEngine[LangGraph Engine & State Graph]
        GraphEngine <--> Checkpointer[Postgres/Memory Checkpointer]
        
        Planner[Planner Agent] --> SubAgents
        
        subgraph SubAgents [Domain Reasoning Agents]
            FlightAgent[Flight Agent]
            HotelAgent[Hotel Agent]
            ActivityAgent[Activity Agent]
            WeatherAgent[Weather Agent]
            ResearchAgent[Research Agent]
        end
        
        SubAgents --> DeterministicRules
        
        subgraph DeterministicRules [Deterministic Python Engines]
            BudgetEngine[Budget Optimizer & Aggregator]
            ValidatorEngine[Temporal & Feasibility Validator]
        end
        
        DeterministicRules --> SynthesisNode[Itinerary Agent]
        DeterministicRules -.->|Constraint Violation| ReplanNode[Replanning Router]
        ReplanNode --> SubAgents
        
        SynthesisNode --> ApprovalGate{Human Approval Required?}
        ApprovalGate -- Yes --> HITLInterrupt[LangGraph Interrupt / Paused State]
        ApprovalGate -- No --> FinalState[Final Itinerary Committed]
        HITLInterrupt --> UI
    end
    
    subgraph ToolingAndData [Integration & Knowledge Fabric]
        SubAgents <--> MCPGateway[MCP Client Gateway]
        MCPGateway <--> MCPServers[Local / Remote MCP Servers]
        MCPGateway <--> ExternalAPIs[Live Travel APIs / Mocks]
        
        ResearchAgent <--> RAGSystem[pgvector Semantic Search]
        ResearchAgent <--> WebSearchSystem[Web Search Provider]
    end
    
    subgraph Persistence [Data Tier]
        AppController <--> SupabaseDB[(Supabase PostgreSQL)]
        RAGSystem <--> SupabaseDB
        Checkpointer <--> SupabaseDB
    end
    
    subgraph Observability [Telemetry & Evaluation]
        GraphEngine -.-> LangSmith[LangSmith Tracing & Evaluation]
        DeterministicRules -.-> LangSmith
    end
```

---

## 2. Streamlit Architecture

The user interface is structured around a reactive, multi-view paradigm that separates presentation logic from agent orchestration:

1. **State Isolation (`st.session_state`)**:
   - `session_id` & `user_id`: Authenticated user session tokens.
   - `current_trip`: Current active trip entity loaded from Supabase.
   - `graph_state`: Snapshot of the active LangGraph execution state.
   - `interrupt_payload`: Holds pending human-approval tokens and approval request payloads.
   - `chat_history`: Conversation timeline of user intents and agent responses.
2. **View Decomposition**:
   - **Trip Conception View**: Conversational natural language input, date pickers, budget sliders, and travel preference chips.
   - **Agent Execution Monitor**: Live visualization of active agents, step-by-step reasoning logs, tool calls, and latency indicators.
   - **Interactive Itinerary View**: Day-by-day interactive timeline with flight cards, hotel details, weather forecasts, and route maps.
   - **Dynamic Disruption & Replanning Sandbox**: Interactive controls allowing users to inject disruptions (e.g. simulated 5-hour flight delay, thunderstorm alert, or hotel cancellation) and observe live delta-replanning.
   - **Human Approval Modal / Card**: Explicit approval checkpoint with action summary, total financial charge, and cancellation terms.
3. **Async-to-Sync Bridge**:
   - LangGraph runs asynchronously; Streamlit operates synchronously per script run.
   - Background execution is bridged via an async runner with streaming queue consumption, updating UI components dynamically as graph nodes complete.

---

## 3. LangGraph Architecture

LangGraph orchestrates the multi-agent system as a **Stateful Directed Acyclic/Cyclic Graph** with explicit checkpoints.

```mermaid
stateDiagram-v2
    [*] --> InputGuardrail
    InputGuardrail --> PlannerNode: Validated Input
    InputGuardrail --> RejectInput: Injection / Malicious Prompt
    
    state ParallelDiscovery {
        PlannerNode --> WeatherNode
        PlannerNode --> ResearchNode
        PlannerNode --> FlightNode
        PlannerNode --> HotelNode
        PlannerNode --> ActivityNode
    }
    
    WeatherNode --> BudgetNode
    ResearchNode --> BudgetNode
    FlightNode --> BudgetNode
    HotelNode --> BudgetNode
    ActivityNode --> BudgetNode
    
    BudgetNode --> ValidationNode
    
    ValidationNode --> ReplanningNode: Constraints Violated
    ReplanningNode --> ParallelDiscovery: Delta Instructions
    
    ValidationNode --> ItineraryNode: Validated & Within Budget
    
    ItineraryNode --> HumanApprovalGate: Sensitive Action Detected
    HumanApprovalGate --> AwaitingHumanAction: Graph Paused (Interrupt)
    AwaitingHumanAction --> ExecutionNode: User Approved
    AwaitingHumanAction --> ReplanningNode: User Rejected
    
    ItineraryNode --> OutputGuardrail: Non-sensitive Read Plan
    ExecutionNode --> OutputGuardrail
    OutputGuardrail --> [*]
```

### 3.1 Phase 4 Workflow Engine & Planner Architecture

Phase 4 establishes the core LangGraph state machine and the first reasoning node (Planner Agent):

```mermaid
graph TD
    START([START]) --> Planner[Planner Agent]
    Planner --> Check{Requirements Complete?}
    Check -- No --> Clarification[Clarification Node]
    Check -- Yes --> Ready[Ready for Specialized Agents]
    Clarification --> END([END])
    Ready --> END([END])
```

#### Core Components & Responsibilities
1. **TravelState Schema (`graph/state.py`)**:
   - Central `TypedDict` capturing identity context (`user_id`, `trip_id`, `conversation_id`, `original_request`), normalized requirements (`origin`, `destination`, `start_date`, `end_date`, `duration`, `travelers`, `budget`, `currency`), preferences (`interests`, `travel_style`, `accommodation_preference`, `food_preferences`, `constraints`), execution state (`planning_status`, `clarification_required`, `clarification_questions`, `warnings`, `errors`), and future agent slots (`flight_options`, `hotel_options`, `activities`, `weather`, `budget_breakdown`, `itinerary`).
2. **Planner Agent Node (`agents/planner.py`)**:
   - Reads arbitrary natural language travel requests (multilingual, English, Hinglish).
   - Extracts structured parameters, detects missing critical requirements, and identifies conflicting constraints.
   - Enforces loop protection (`MAX_GRAPH_STEPS = 10`) and retry limits (`MAX_PLANNER_RETRIES = 2`).
   - Does **NOT** search the web, book flights, or synthesize final itineraries (reserved for specialized agents in subsequent phases).
3. **Clarification Node (`agents/clarification.py`)**:
   - Routes incomplete requests to `NEEDS_CLARIFICATION`, formatting structured, user-friendly clarification questions.
4. **Structured Output (`models/planner.py`)**:
   - Validated through Pydantic schemas: `NormalizedTravelRequest`, `ClarificationRequest`, and `PlannerResult`.
5. **DEMO_MODE / Offline Execution (`services/llm_service.py`)**:
   - When running without live LLM credentials or with `DEMO_MODE=true`, routes to `DemoPlannerExtractor`.
   - Tags outputs with `is_demo=True` and clearly identifies assumptions without simulating artificial responses.
6. **Future Agent Extensibility**:
   - Future domain agents (Flight, Hotel, Activity, Weather, Research, Budget) will fan out from `READY_FOR_SPECIALIZED_AGENTS` without altering the initial intake graph.

### 3.2 Graph Structural Design
- **Deterministic Routing**: Conditional edges check typed flags in the graph state rather than relying on LLM routing decisions for state transitions.
- **Cycle Prevention**: Loop protection limits (`MAX_GRAPH_STEPS = 10`) guarantee termination; retries on LLM parsing failures are strictly bounded to `MAX_PLANNER_RETRIES = 2`.
- **State Checkpointing**: Every node transition creates a persistent snapshot in the Supabase/Memory checkpointer, enabling seamless crash recovery and human approval suspension.

---

## 4. Agent Responsibilities & Division of Labor

The system enforces a strict boundary between **Agent Reasoning** and **Deterministic Calculation**:

| Component | Nature | Technologies | Role & Boundaries |
|-----------|--------|--------------|-------------------|
| **Planner Agent** | Probabilistic (LLM) | GPT-4o / Claude 3.5 Sonnet | Deconstructs user prompt into a structured `TripRequirementSpec`; identifies constraints, preferences, and tradeoffs. |
| **Flight Agent** | Probabilistic + Tool | LLM + Flight Tools | Identifies viable flight corridors, compares transit durations, filters baggage options, selects best candidate flights. |
| **Hotel Agent** | Probabilistic + Tool | LLM + Hotel Tools | Evaluates lodging alternatives considering proximity to attractions, ratings, and price bands. |
| **Activity Agent** | Probabilistic + Tool | LLM + Places/RAG Tools | Curates cultural, leisure, and dining experiences respecting user pacing and travel style. |
| **Weather Agent** | Hybrid | LLM + Weather Tool | Fetches forecast and seasonal patterns; flags outdoor risk factors for the Planner. |
| **Research Agent** | Hybrid | LLM + RAG + Web Search | Queries destination guidelines (visas, local customs, transit passes, seasonal alerts). |
| **Budget Engine** | **Deterministic (Python)** | **Pure Python** | **Calculates exact totals, taxes, currency conversions, contingency buffers. Zero LLM math.** |
| **Validator Engine** | **Deterministic (Python)** | **Pure Python** | **Verifies timing feasibility, minimum connection times, open hours, pace fatigue indices.** |
| **Replanner Agent** | Probabilistic (LLM) | GPT-4o / Fast LLM | Formulates delta correction instructions when budget or validation engines flag an issue. |
| **Itinerary Agent** | Probabilistic (LLM) | GPT-4o | Synthesizes all approved components into a cohesive, narrative day-by-day itinerary. |

---

## 5. LangGraph State Schema

The graph operates on an immutable, strongly-typed state model governed by Pydantic v2:

```python
from typing import TypedDict, List, Dict, Optional, Any
from pydantic import BaseModel, Field

class TripState(TypedDict):
    # Workflow Metadata
    session_id: str
    user_id: str
    trip_id: str
    replan_count: int
    current_status: str
    
    # User Inputs & Extracted Spec
    user_prompt: str
    trip_spec: Dict[str, Any]             # Serialized TripRequirementSpec
    
    # Agent Candidate Outputs
    weather_data: Optional[Dict[str, Any]]
    research_insights: List[Dict[str, Any]]
    flight_options: List[Dict[str, Any]]
    selected_flights: Optional[Dict[str, Any]]
    hotel_options: List[Dict[str, Any]]
    selected_hotel: Optional[Dict[str, Any]]
    activity_options: List[Dict[str, Any]]
    selected_activities: List[Dict[str, Any]]
    
    # Deterministic Evaluation Results
    budget_breakdown: Optional[Dict[str, Any]]   # Total, transport, lodging, activities, contingency
    budget_approved: bool
    budget_overrun_amount: float
    
    validation_passed: bool
    validation_issues: List[Dict[str, Any]]      # Detailed feasibility or safety warnings
    
    # Replanning & Disruption Context
    disruption_event: Optional[Dict[str, Any]]
    replanning_instructions: Optional[str]
    
    # Human-in-the-Loop Approval State
    requires_human_approval: bool
    approval_type: Optional[str]                 # "booking", "cancellation", "budget_override"
    approval_payload: Optional[Dict[str, Any]]
    is_approved: Optional[bool]
    
    # Final Output
    final_itinerary: Optional[Dict[str, Any]]
    error_message: Optional[str]
```

---

## 6. Model Context Protocol (MCP) Architecture

The platform adopts the **Model Context Protocol (MCP)** to standardize agent-to-tool integration.

```mermaid
graph LR
    subgraph AgentHost [LangGraph Host Environment]
        Agent[Domain Agent] <--> MCPClient[LangChain MCP Client Gateway]
    end
    
    subgraph MCPServers [Decoupled MCP Tool Servers]
        MCPClient <-->|JSON-RPC 2.0 / SSE / Stdio| WeatherServer[MCP Weather Server]
        MCPClient <-->|JSON-RPC 2.0 / SSE / Stdio| FlightServer[MCP Flight Server]
        MCPClient <-->|JSON-RPC 2.0 / SSE / Stdio| HotelServer[MCP Hotel Server]
    end
    
    subgraph ExternalWorld [Real APIs or Mock Providers]
        WeatherServer <--> OpenWeather[OpenWeather API / Mock]
        FlightServer <--> AmadeusFlights[Amadeus Flight API / Mock]
        HotelServer <--> BookingService[Hotel Content API / Mock]
    end
```

### Why MCP?
- **Tool Decoupling**: Agents do not contain proprietary API client libraries; they communicate via standardized JSON-RPC specifications.
- **Security Sandboxing**: MCP servers can run in isolated processes with restricted network and credential access.
- **Mock Interchangeability**: Switching between `DEMO_MODE=true` and live production only requires swapping MCP endpoints or server configurations, without modifying agent prompt logic.

---

## 7. RAG (Retrieval-Augmented Generation) Architecture

RAG is dedicated to **relatively stable domain knowledge**:
- Destination guides and seasonal climates
- Visa requirements and entry regulations
- Neighborhood safety ratings and public transit tips
- Curated dining and historical activity recommendations

### Pipeline Design:
1. **Document Ingestion**: Markdown/PDF guides chunked with semantic boundaries (chunk size 600 tokens, 100 token overlap).
2. **Embeddings**: Generated using OpenAI `text-embedding-3-small` (1536 dimensions).
3. **Storage & Vector Index**: Supabase PostgreSQL with the `pgvector` extension using an `HNSW` (Hierarchical Navigable Small World) index for fast approximate nearest neighbor search.
4. **Metadata Filtering**: Queries are filtered by `country_code`, `destination_city`, and `category` (e.g., `visa`, `cuisine`, `transit`) prior to vector distance calculation.
5. **Contextual Grounding**: Retrieved context is injected into the Research Agent's system prompt with strict citation constraints.

---

## 8. Web Search Architecture

While RAG handles static travel knowledge, **Web Search** handles **fresh, volatile real-time conditions**:
- Sudden airport terminal closures or airline strikes
- Live festival and event dates
- Seasonal weather anomalies or unexpected attraction renovations
- Current currency exchange fluctuations

### Integration Pattern:
- **Search Query Synthesizer**: The Research Agent formulates targeted, temporal search queries (e.g. `"Louvre museum renovation closures October 2026"`).
- **Provider Gateway**: Uses search providers (Tavily / Brave Search API) optimized for LLM context retrieval.
- **Content Deduplication & Truncation**: Retrieved markdown/snippets are scrubbed of HTML tags, deduplicated, and truncated to avoid token waste before entering the context window.

---

## 9. Supabase Architecture (PostgreSQL, Auth & pgvector)

Supabase serves as the unified persistence, authentication, and security foundation:

```mermaid
erDiagram
    PROFILES ||--o{ TRIPS : owns
    PROFILES ||--o{ CONVERSATIONS : starts
    TRIPS ||--|| TRIP_PREFERENCES : configures
    TRIPS ||--o{ CONVERSATIONS : context
    TRIPS ||--o{ AGENT_RUNS : logs
    CONVERSATIONS ||--o{ MESSAGES : contains

    PROFILES {
        uuid id PK
        string email
        string full_name
        timestamp created_at
        timestamp updated_at
    }

    TRIPS {
        uuid id PK
        uuid user_id FK
        string origin
        string destination
        date start_date
        date end_date
        integer travelers
        numeric budget
        string currency
        string status
        timestamp created_at
        timestamp updated_at
    }

    TRIP_PREFERENCES {
        uuid id PK
        uuid trip_id FK
        jsonb preferences
        string travel_style
        string accommodation_preference
        text additional_requirements
        timestamp created_at
        timestamp updated_at
    }

    CONVERSATIONS {
        uuid id PK
        uuid user_id FK
        uuid trip_id FK
        string title
        timestamp created_at
        timestamp updated_at
    }

    MESSAGES {
        uuid id PK
        uuid conversation_id FK
        string role
        text content
        timestamp created_at
    }

    AGENT_RUNS {
        uuid id PK
        uuid trip_id FK
        string agent_name
        string status
        timestamp started_at
        timestamp completed_at
        text error_message
        jsonb metadata
        timestamp created_at
    }
```

### 9.1 Database Schema Design
1. **`profiles`**: Linked 1-to-1 with `auth.users(id)` via an automated PostgreSQL trigger (`on_auth_user_created`). Ensures user records exist within public schema.
2. **`trips`**: Normalized table containing core route, scheduling, budget limits, and status (`DRAFT`, `PLANNING`, `APPROVED`, `COMPLETED`, `CANCELLED`).
3. **`trip_preferences`**: Decoupled preference table for qualitative traveler parameters, travel style, lodging preferences, and additional notes.
4. **`conversations`**: Thread parent entities linked to `user_id` and optionally to `trip_id`.
5. **`messages`**: Chronological conversation history with roles strictly validated to `user`, `assistant`, or `system`.
6. **`agent_runs`**: Immutable audit log tracking start, completion, error messages, and telemetry for every agent node in the workflow.

### 9.2 Row Level Security (RLS) Strategy
- **Engine-Level Isolation**: RLS is activated on all 6 tables (`ALTER TABLE ... ENABLE ROW LEVEL SECURITY;`).
- **Direct Ownership**: Tables with direct user ownership (`profiles`, `trips`, `conversations`) use `USING (auth.uid() = user_id)`.
- **Hierarchical Ownership**: Child tables (`trip_preferences`, `messages`, `agent_runs`) use correlated subqueries (`EXISTS (SELECT 1 FROM trips WHERE trips.id = trip_id AND trips.user_id = auth.uid())`), eliminating the risk of data leakage.

### 9.3 Repository Layer & DEMO_MODE Fallback
- Services and UI components never execute raw SQL or PostgREST queries directly.
- The repository layer (`TripRepository`, `ConversationRepository`, `MessageRepository`, `AgentRunRepository`) inspects `is_demo_mode`:
  - In `DEMO_MODE=true` or when credentials are missing, repositories route to an in-memory `MockDataStore` tagging records as `is_demo: True`.
  - In live mode, operations execute against Supabase with JWT authorization.
- Zero code changes required to toggle between local offline demos and production.

---

## 10. Guardrails & Security Architecture

1. **Input Guardrails**:
   - Inspects raw prompts for known jailbreaks, role-reversal attacks, and prompt injection signatures.
   - Rejects or sanitizes prompts attempting to alter core instructions or extract system prompts.
2. **Tool Execution Guardrails**:
   - Whitelisted tool names per agent.
   - Deterministic argument validation using Pydantic schemas before tool dispatch.
   - Least-privilege: Read-only for discovery agents; write/booking tools strictly gatekeeped.
3. **Output Guardrails**:
   - Every agent output passes through `pydantic.BaseModel.model_validate_json()`.
   - Prevents malformed JSON or markdown codeblocks from corrupting the graph state.
   - PII filter scrubs phone numbers, credit card numbers, or passport numbers from persistent logs.

---

## 11. Dynamic Replanning Architecture

Dynamic replanning is an essential differentiator for this platform:

```mermaid
sequenceDiagram
    autonumber
    actor User as Traveler / Monitor
    participant Graph as LangGraph Orchestrator
    participant Replan as Replanner Node
    participant Agents as Specialized Agents
    participant Budget as Budget Engine
    participant UI as Streamlit UI

    User->>Graph: Trigger Disruption (e.g. Flight Cancelled / Heavy Rain)
    Graph->>Replan: Assess Disruption Impact on Current State
    Replan->>Replan: Isolate Broken Nodes (e.g. Day 2 Outdoor Activities)
    Replan->>Agents: Re-dispatch Activity Agent with Indoor Constraint
    Agents-->>Replan: New Indoor Activity Options Returned
    Replan->>Budget: Re-calculate Total Budget & Verify No Overrun
    Budget-->>Graph: Budget Validated
    Graph->>UI: Present Itinerary Impact Diff (Before vs After)
    UI->>User: Request Human Approval for New Schedule
```

### Key Principles:
- **Surgical Delta Replanning**: Avoids regenerating unaffected days or confirmed flight bookings. Only invalidated segments are replanned.
- **Budget Preservation**: Any alternative activity or hotel must not exceed the remaining allocated category budget.
- **Versioned History**: Past itinerary versions are archived in `replanning_history` with the exact disruption cause and agent rationale.

---

## 12. Human-in-the-Loop (HITL) Architecture

LangGraph provides native support for pausing graph execution via **Interrupts**:
1. When the graph reaches a state requiring authorization (e.g. executing flight reservation, hotel booking, or paying an extra fee during replanning), the `ApprovalGate` node raises an `interrupt()`.
2. The graph state is automatically checkpointed to the persistent database.
3. The Streamlit UI detects the suspended state, displays the exact financial liability and itemized details, and renders **Approve** and **Reject/Modify** actions.
4. When the user clicks **Approve**, the UI calls `graph.invoke(Command(resume={"action": "approve"}))`.
5. The execution resumes from the exact checkpoint, completing the transaction and updating the itinerary status.

---

## 13. LangSmith Observability & Evaluation

Every user interaction and agent step is monitored:
- **Distributed Run Trees**: Hierarchical spans illustrate the exact flow from User Prompt -> Planner -> Parallel Sub-agents -> Budget Validation -> Synthesis.
- **Token & Cost Attribution**: Real-time token consumption breakdown per agent node, distinguishing between fast models (GPT-4o-mini) and reasoning models (GPT-4o).
- **Latency Profiling**: Identifies bottlenecks across external APIs, vector queries, and LLM completions.
- **Automated Regression Evaluation**: LangSmith dataset evaluators measure itinerary quality, constraint adherence, and hallucination rates across test suites.

---

## 14. Failure Handling & Resilience

1. **API Timeouts & Retries**: All outbound HTTP and MCP requests have a hard 25-second timeout, with exponential backoff retries (maximum 2 retries).
2. **Graceful Fallback to DEMO_MODE**: If an external provider (e.g., Amadeus or OpenWeather) returns 5xx or rate limit errors, the system seamlessly falls back to cached/mock data and notifies the user with a warning banner.
3. **Graph Circuit Breakers**: `MAX_GRAPH_STEPS = 30` prevents infinite recursion in replanning loops.
4. **Data Redundancy**: Itineraries are persisted at each stage, ensuring a transient browser refresh never loses trip progress.
