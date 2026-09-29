# Production Deployment Guide: Multi-Agent Travel Intelligence Platform

This document outlines the deployment strategy, environment configuration, container runtime instructions, and operational verification procedures for deploying the **Multi-Agent AI Travel Intelligence & Dynamic Replanning Platform** to production environments.

---

## 1. Target Architecture Overview

```
                                [ Traveler / Operator ]
                                          │
                                          ▼
                      ┌───────────────────────────────────────┐
                      │    Streamlit Production App (8501)    │
                      │  - Headless runtime                   │
                      │  - Zero raw exceptions exposed        │
                      │  - Custom Travel Command Center CSS   │
                      └──────────────────┬────────────────────┘
                                         │
             ┌───────────────────────────┼───────────────────────────┐
             ▼                           ▼                           ▼
┌─────────────────────────┐ ┌─────────────────────────┐ ┌─────────────────────────┐
│ Supabase Database & Auth│ │   LangGraph Core Engine │ │ LangSmith Observability │
│ - PostgreSQL            │ │   - 9 Specialized Agents│ │ - Distributed Traces    │
│ - pgvector Embeddings   │ │   - Deterministic Math  │ │ - Latency Profiling     │
│ - Strict RLS Isolation  │ │   - Dynamic Replanner   │ │ - Token & Cost Tracking │
└─────────────────────────┘ └────────────┬────────────┘ └─────────────────────────┘
                                         │
             ┌───────────────────────────┼───────────────────────────┐
             ▼                           ▼                           ▼
┌─────────────────────────┐ ┌─────────────────────────┐ ┌─────────────────────────┐
│   Primary LLM Router    │ │   Model Context Protocol│ │ External Travel APIs    │
│ - Simple (gpt-4o-mini)  │ │   - Flight MCP Server   │ │ - Amadeus GDS (Live)    │
│ - Complex (gpt-4o)      │ │   - Hotel MCP Server    │ │ - Open-Meteo / Weather  │
│ - Python (Deterministic)│ │   - Weather MCP Server  │ │ - Tavily / Brave Search │
└─────────────────────────┘ └─────────────────────────┘ └─────────────────────────┘
```

---

## 2. Deployment Options

### Option A: Streamlit Community Cloud (Recommended for Managed Hosting)

Streamlit Community Cloud provides native hosting directly integrated with your GitHub repository.

1. **Repository Link**: Navigate to [share.streamlit.io](https://share.streamlit.io/) and connect `codingsexpert/multi-agent-travel-intelligence-platform`.
2. **Main File Path**: Set to `app/main.py`.
3. **Branch**: `main`.
4. **Python Version**: Select `3.11`.
5. **Secrets Configuration**: Under App Settings -> Secrets, populate the TOML configuration:
   ```toml
   APP_ENV = "production"
   DEMO_MODE = "false"
   LOG_LEVEL = "INFO"

   # Supabase
   SUPABASE_URL = "https://your-project-id.supabase.co"
   SUPABASE_KEY = "your-anon-public-key"

   # LLM Reasoning
   PRIMARY_LLM_PROVIDER = "openai"
   OPENAI_API_KEY = "sk-proj-your-openai-api-key"
   PRIMARY_LLM_MODEL = "gpt-4o"
   FAST_LLM_MODEL = "gpt-4o-mini"

   # Observability
   LANGSMITH_TRACING = "true"
   LANGSMITH_API_KEY = "lsv2_pt_your-key"
   LANGSMITH_PROJECT = "travel-intelligence-platform"

   # Optional External Providers
   AMADEUS_CLIENT_ID = "your-amadeus-key"
   AMADEUS_CLIENT_SECRET = "your-amadeus-secret"
   TAVILY_API_KEY = "tvly-your-tavily-key"
   ```
6. **Deploy**: Streamlit Cloud will execute `pip install -r requirements.txt` and launch `app/main.py`.

---

### Option B: Docker Container (Self-Hosted, Cloud Run, AWS ECS, or Kubernetes)

The platform includes a hardened, multi-stage, non-root `Dockerfile`.

#### 1. Build the Production Image
```bash
docker build -t travel-intelligence-platform:latest .
```

#### 2. Run the Container
```bash
docker run -d \
  --name travel-platform \
  -p 8501:8501 \
  -e APP_ENV=production \
  -e DEMO_MODE=false \
  -e SUPABASE_URL="https://your-project.supabase.co" \
  -e SUPABASE_KEY="your-anon-key" \
  -e OPENAI_API_KEY="sk-proj-..." \
  --restart unless-stopped \
  travel-intelligence-platform:latest
```

#### 3. Container Verification
Check container status and health:
```bash
docker ps
docker inspect --format='{{json .State.Health}}' travel-platform
```

---

## 3. Database Migration Procedures

Before pointing production traffic to Supabase, execute migrations in sequence using the Supabase CLI or SQL Editor:

```bash
# Sequential migration files located in supabase/migrations/:
1. 20260928000001_initial_schema.sql     # Profiles, trips, conversations, agent_runs
2. 20260928000002_rls_policies.sql       # User-level RLS policies and isolation
3. 20260928000003_pgvector_rag.sql       # Document chunks, pgvector extension, match function
4. 20260928000004_replanning_events.sql   # Replan audit logs, version histories
5. 20260928000005_hitl_approvals.sql     # Action proposals, requests, executions, audit trail
```

> **Data Safety Guarantee**: Migrations are strictly non-destructive. Never execute `DROP SCHEMA public CASCADE` or destructive table alterations on live production databases.

---

## 4. Health Checks, Liveness & Readiness Probes

The application provides automated programmatic probes via [`services/health_service.py`](file:///Users/MukeshSingh/Desktop/travel-intelligence-platform/services/health_service.py):

| Probe Type | Endpoint / Function | Success Criteria | Failure Recovery |
|---|---|---|---|
| **Liveness** | `get_liveness_status()` or `/_stcore/health` | HTTP 200 / `liveness=True` | Container restart |
| **Readiness** | `get_readiness_status()` | `overall_status` in (`HEALTHY`, `DEGRADED`) | Inspect missing database/LLM secrets |
| **Subsystems** | `get_health_status().components` | Tracks all 8 architectural tiers | Non-critical tiers degrade safely to fallbacks |

---

## 5. Security & Secret Hygiene

1. **Zero Secret Leaks**: No `.env` or production credentials are ever committed. `.gitignore` and CI secret scanners enforce compliance.
2. **Supabase Anon Key vs Service Role**:
   - The application strictly uses `SUPABASE_ANON_KEY` combined with user authentication tokens.
   - `SUPABASE_SERVICE_ROLE_KEY` is NEVER exposed to Streamlit sessions, browser cookies, or client logs.
3. **Client Error Masking**: `showErrorDetails = false` in `.streamlit/config.toml` prevents internal stack traces from leaking to end users.
