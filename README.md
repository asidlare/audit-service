# Audit Service with Cassandra

## Goal

The primary goal of this project was to build a **FastAPI application with an async connection to Apache Cassandra** and verify how well the available Python libraries handle this in practice.

Specific objectives:

- Implement a production-style async Cassandra connection using FastAPI's `lifespan` context manager — connecting on startup, closing on shutdown — and evaluate how `cassandra-driver` with `AsyncioConnection` and `aiocassandra` behave in a real async environment.
- Verify how to **stabilize a containerized FastAPI application with a 3-node Cassandra cluster** in Docker Compose, including proper health checks, sequential startup, and dependency management — to observe real-world cluster behavior rather than simulating it.
- Use a **QUORUM consistency level** (`ConsistencyLevel.QUORUM`), which requires 2 out of 3 nodes to confirm each read/write. This provides strong consistency while tolerating a single node failure — the minimum viable setup for testing distributed Cassandra behavior.
- Apply a **DCAwareRoundRobinPolicy** load balancing policy to distribute queries evenly across all nodes in the local datacenter, with automatic fallback if a node goes down.


## Simplifications & Design Decisions

This project is intentionally a **learning and testing environment**, not a production system. The following simplifications were made deliberately:

- **Schema loaded from code, no migrations** — The Cassandra keyspace and tables are created directly in `database.py` on startup from a hardcoded `SCHEMA` list. For this project, a simple script-based approach was sufficient and kept the setup minimal.

- **No pytest — testing via scripts and HTTP** — Instead of a traditional test suite, the application is tested through dedicated utility scripts (`log_and_verify.py`, `audit_tester.py`) that call the running API and verify results directly in the database. This approach was chosen to test the full stack end-to-end, including Docker networking and Cassandra replication, which would be difficult to replicate in unit tests.

- **tmpfs for Cassandra volumes** — Each Cassandra node uses an in-memory `tmpfs` filesystem instead of a persistent volume. This ensures a **clean state on every restart**, eliminates leftover data between test runs, and significantly speeds up I/O. The trade-off is that all data is lost on container stop — acceptable for a testing environment, not for production.

- **Single datacenter setup** — The cluster uses `datacenter1` as the only datacenter. A production deployment would typically span multiple datacenters with `LOCAL_QUORUM` consistency to avoid cross-datacenter latency.

## Infrastructure Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   DOCKER INFRASTRUCTURE ARCHITECTURE                    │
└─────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                        DOCKER COMPOSE SERVICES                          │
└─────────────────────────────────────────────────────────────────────────┘

                       ┌─────────────────────────┐
                       │  audit_net (bridge)     │
                       └────────────┬────────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │                         │                         │
          V                         V                         V
    ┌────────────┐          ┌────────────────┐       ┌────────────────┐
    │cassandra-1 │          │  cassandra-2   │       │  cassandra-3   │
    │   (seed)   │          │                │       │                │
    │            │<─────────│  SEEDS=cass-1  │<──────│  SEEDS=cass-1  │
    │ Token:     │  CLUSTER │                │CLUSTER│                │
    │    0       │          │  Token:        │       │  Token:        │
    │            │          │  5534023...484 │       │ -5534023...485 │
    │ tmpfs: 2GB │          │  tmpfs: 2GB    │       │  tmpfs: 2GB    │
    │            │          │                │       │                │
    │ Health: OK │          │  Health: OK    │       │  Health: OK    │
    │ Start:120s │          │  Start: 180s   │       │  Start: 240s   │
    └────────────┘          └────────────────┘       └────────────────┘
          │                         │                         │
          └─────────────────────────┼─────────────────────────┘
                                    │ depends_on: service_healthy
                                    │
                                    V
                             ┌────────────────┐
                             │   audit_api    │
                             │                │
                             │  FastAPI App   │
                             │  Port: 8000    │
                             │                │
                             │  Env:          │
                             │  CASSANDRA_    │
                             │  HOSTS=        │
                             │  cass-1,2,3    │
                             │                │
                             │  restart:      │
                             │  on-failure:10 │
                             └────────────────┘
                                    │
                                    V
                          Host: localhost:8000


┌─────────────────────────────────────────────────────────────────────────┐
│                    CASSANDRA CLUSTER CONFIGURATION                      │
└─────────────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────────────┐
  │ WHY 3 NODES? - QUORUM & FAULT TOLERANCE                              │
  └──────────────────────────────────────────────────────────────────────┘

    Production-Grade Setup:
    • QUORUM consistency: (RF/2) + 1 = (3/2) + 1 = 2 nodes
    • Fault tolerance: Survives 1 node failure
    • Data replication: RF=3 (each write copied to 3 nodes)

    Token Ring Distribution:

                    cassandra-1
                   (token: 0)
                    /        \
                   /    o     \
                  /   Ring     \
                 /    Space     \
                /                \
         cassandra-3        cassandra-2
      (token: -5534...)    (token: 5534...)

    Benefits:
    • Even data distribution (120 degrees per node)
    • Load balancing across cluster
    • High availability (1 node can fail)
    • Realistic testing environment


  ┌──────────────────────────────────────────────────────────────────────┐
  │ WHY INITIAL TOKENS? - PREVENTING TOKEN COLLISION                     │
  └──────────────────────────────────────────────────────────────────────┘

    WITHOUT explicit tokens:               WITH explicit tokens:
    ┌──────────────────────────┐          ┌──────────────────────────┐
    │ Random token selection   │          │ Predictable layout       │
    │ Possible collisions      │          │ Even distribution        │
    │ Cluster instability      │          │ Fast startup             │
    │ Bootstrap failures       │          │ Repeatable tests         │
    │ Uneven data spread       │          │ No conflicts             │
    └──────────────────────────┘          └──────────────────────────┘

    Token Calculation (3 nodes, 64-bit range):
    ┌────────────┬───────────────────────────────────────────┐
    │ Node       │ Token Value                               │
    ├────────────┼───────────────────────────────────────────┤
    │ cassandra-1│ 0                                         │
    │ cassandra-2│ 2^64 / 3  =  5534023222112865484          │
    │ cassandra-3│ -2^64 / 3 = -5534023222112865485          │
    └────────────┴───────────────────────────────────────────┘

    Configuration:
      JVM_OPTS=-Dcassandra.initial_token=<value>


  ┌──────────────────────────────────────────────────────────────────────┐
  │ WHY HEALTH CHECKS? - CLUSTER STABILIZATION                           │
  └──────────────────────────────────────────────────────────────────────┘

    PROBLEM: Cassandra Takes Time to Stabilize
    ┌──────────────────────────────────────────────────────────────────┐
    │ • Node startup: 2-3 minutes                                      │
    │ • Schema agreement: additional time                              │
    │ • Cluster gossip: nodes must discover each other                 │
    │ • Without health checks: API crashes on connection               │
    └──────────────────────────────────────────────────────────────────┘

    SOLUTION: Sequential Startup with Health Checks
    ┌──────────────────────────────────────────────────────────────────┐
    │                                                                  │
    │  T+0s    ┌─────────────┐                                         │
    │   │      │ cassandra-1 │ start_period: 120s                      │
    │   │      │   starts    │ retries: 30 x 30s interval              │
    │   V      └─────────────┘                                         │
    │  T+120s         │                                                │
    │   │             V HEALTHY                                        │
    │   │      ┌─────────────┐                                         │
    │   │      │ cassandra-2 │ depends_on: cassandra-1                 │
    │   │      │   starts    │ start_period: 180s                      │
    │   V      └─────────────┘                                         │
    │  T+240s         │                                                │
    │   │             V HEALTHY                                        │
    │   │      ┌─────────────┐                                         │
    │   │      │ cassandra-3 │ depends_on: cassandra-1,2               │
    │   │      │   starts    │ start_period: 240s                      │
    │   V      └─────────────┘                                         │
    │  T+360s         │                                                │
    │   │             V HEALTHY                                        │
    │   │      ┌─────────────┐                                         │
    │   │      │  audit_api  │ depends_on: all healthy                 │
    │   │      │   starts    │ restart: on-failure:10                  │
    │   V      └─────────────┘                                         │
    │  T+380s         │                                                │
    │                 V READY                                          │
    │                                                                  │
    └──────────────────────────────────────────────────────────────────┘

    Health Check Command:
      test: cqlsh -e 'SELECT now() FROM system.local'

    Verifies:
      • CQL interface responsive
      • Cassandra internal state OK
      • Node ready to accept connections


  ┌──────────────────────────────────────────────────────────────────────┐
  │ WHY TMPFS VOLUMES? - TEST ENVIRONMENT OPTIMIZATION                   │
  └──────────────────────────────────────────────────────────────────────┘

    Test Environment Requirements:
    ┌──────────────────────────────────────────────────────────────────┐
    │ • Fresh state for each test run                                  │
    │ • No persistent data between tests                               │
    │ • Fast cleanup (no manual deletion)                              │
    │ • Repeatable conditions                                          │
    └──────────────────────────────────────────────────────────────────┘

    Configuration:
      volumes:
        - type: tmpfs
          target: /var/lib/cassandra    # Cassandra data directory
          tmpfs:
            size: 2G                    # Sufficient for test data

    Benefits vs. Persistent Volumes:
    ┌─────────────────────────┬──────────────┬─────────────────────┐
    │ Metric                  │ tmpfs        │ Persistent Volume   │
    ├─────────────────────────┼──────────────┼─────────────────────┤
    │ I/O Speed               │ faster       │ Disk limited        │
    │ Cleanup                 │ Automatic    │ Manual required     │
    │ Disk Usage              │ 0 bytes      │ Persistent          │
    │ Fresh Start             │ Always       │ Requires cleanup    │
    │ RAM Usage               │ ~2GB         │ 0 bytes             │
    └─────────────────────────┴──────────────┴─────────────────────┘

    WARNING: NOT FOR PRODUCTION


┌─────────────────────────────────────────────────────────────────────────┐
│                       DOCKERFILE ARCHITECTURE                           │
└─────────────────────────────────────────────────────────────────────────┘

  Multi-Stage Build Process:

  ┌──────────────────────────────────────────────────────────────────────┐
  │ STAGE 1: Builder (python:3.13)                                       │
  └──────────────────────────────────────────────────────────────────────┘

    FROM python:3.13 AS builder

    ┌──────────────────────────────────────────────────────────────────┐
    │ UV Package Manager                                               │
    │ COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/           │
    │                                                                  │
    │ Benefits:                                                        │
    │  • 10-100x faster than pip                                       │
    │  • Reliable dependency resolution                                │
    │  • Modern Python package installer                               │
    └──────────────────────────────────────────────────────────────────┘

    ┌──────────────────────────────────────────────────────────────────┐
    │ Build Dependencies for cassandra-driver                          │
    │                                                                  │
    │ apt-get install:                                                 │
    │   • gcc         ----> C compiler for Cython extensions           │
    │   • g++         ----> C++ compiler                               │
    │   • libev-dev   ----> Event loop library (dev headers)           │
    │                                                                  │
    │ WHY NEEDED?                                                      │
    │ ┌────────────────────────────────────────────────────────────┐   │
    │ │ cassandra-driver uses Cython-compiled C extensions:        │   │
    │ │  • Fast binary protocol parsing                            │   │
    │ │  • Efficient event loop integration (libev)                │   │
    │ │  • Performance-critical operations                         │   │
    │ │                                                            │   │
    │ │ Without build tools:                                       │   │
    │ │  • "error: command 'gcc' failed"                           │   │
    │ │  • "libev.h: No such file or directory"                    │   │
    │ │  • Installation fails completely                           │   │
    │ └────────────────────────────────────────────────────────────┘   │
    └──────────────────────────────────────────────────────────────────┘

    WORKDIR /code
    COPY pyproject.toml .
    RUN uv sync --no-dev --no-install-project
        # Creates .venv with all dependencies


  ┌──────────────────────────────────────────────────────────────────────┐
  │ STAGE 2: Runtime (python:3.13-slim)                                  │
  └──────────────────────────────────────────────────────────────────────┘

    FROM python:3.13-slim

    ┌──────────────────────────────────────────────────────────────────┐
    │ Runtime Dependencies for cassandra-driver                        │
    │                                                                  │
    │ apt-get install:                                                 │
    │   • libev4      ----> Event loop library (runtime only)          │
    │                                                                  │
    │ WHY NEEDED?                                                      │
    │ ┌────────────────────────────────────────────────────────────┐   │
    │ │ Compiled C extensions link to libev at runtime:            │   │
    │ │                                                            │   │
    │ │ Without libev4:                                            │   │
    │ │  • ImportError: libev.so.4: cannot open shared object      │   │
    │ │  • Application crashes on startup                          │   │
    │ │                                                            │   │
    │ │ NOTE: Only runtime library needed (not -dev headers)       │   │
    │ └────────────────────────────────────────────────────────────┘   │
    └──────────────────────────────────────────────────────────────────┘

    COPY --from=builder /code/.venv /usr/local/.venv
    COPY . .
    ENV PATH="/usr/local/.venv/bin:$PATH"
    ENV PYTHONUNBUFFERED=1
    EXPOSE 8000
    CMD ["python", "-m", "uvicorn", "app.main:app",
         "--host", "0.0.0.0", "--port", "8000"]

  Benefits of Multi-Stage Build:
  ┌─────────────────────────┬──────────────┬─────────────────────┐
  │ Metric                  │ Multi-Stage  │ Single Stage        │
  ├─────────────────────────┼──────────────┼─────────────────────┤
  │ Final Image Size        │ smaller      │ big.                │
  │ Build Tools in Image    │ No           │ Yes (security risk) │
  │ Build Time (cached)     │ Fast         │ Moderate            │
  └─────────────────────────┴──────────────┴─────────────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                         PYTHON DEPENDENCIES                             │
└─────────────────────────────────────────────────────────────────────────┘

  pyproject.toml - Dependency Stack:

  ┌──────────────────────┬──────────┬───────────────────────────────────┐
  │ Package              │ Version  │ Purpose                           │
  ├──────────────────────┼──────────┼───────────────────────────────────┤
  │ fastapi              │ >=0.115  │ Web Framework                     │
  │                      │          │  • Async request handling         │
  │                      │          │  • Auto OpenAPI/Swagger docs      │
  │                      │          │  • Pydantic integration           │
  │                      │          │  • Type validation                │
  ├──────────────────────┼──────────┼───────────────────────────────────┤
  │ uvicorn[standard]    │ >=0.32   │ ASGI Server                       │
  │                      │          │  • Production-grade performance   │
  ├──────────────────────┼──────────┼───────────────────────────────────┤
  │ cassandra-driver     │ >=3.29   │ Apache Cassandra Client           │
  │                      │          │  • CQL query execution            │
  │                      │          │  • Connection pooling             │
  │                      │          │  • Cluster management             │
  │                      │          │  • Requires: gcc, g++, libev      │
  ├──────────────────────┼──────────┼───────────────────────────────────┤
  │ aiocassandra         │ >=2.0    │ Async Cassandra Wrapper           │
  │                      │          │  • AsyncIO integration            │
  │                      │          │  • Non-blocking queries           │
  │                      │          │  • Concurrent operations          │
  ├──────────────────────┼──────────┼───────────────────────────────────┤
  │ pydantic             │ >=2.9    │ Data Validation                   │
  │                      │          │  • Request/response models        │
  │                      │          │  • Runtime type checking          │
  │                      │          │  • JSON serialization             │
  ├──────────────────────┼──────────┼───────────────────────────────────┤
  │ httpx                │ >=0.27   │ HTTP Client (Testing)             │
  │                      │          │  • Async API testing              │
  │                      │          │  • Integration tests              │
  └──────────────────────┴──────────┴───────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                         STARTUP SEQUENCE                                │
└─────────────────────────────────────────────────────────────────────────┘

  $ docker-compose up

  Time      Event                          Status
  ───────── ────────────────────────────── ──────────────────────────────
  T+0s      cassandra-1 starts             Container created
            └─ Token: 0                    Initializing...
            └─ Role: Seed node
  T+120s    cassandra-1 HEALTHY            CQL interface responsive
            └─ Health check passed         Ready for connections
  T+120s    cassandra-2 starts             Container created
            └─ Token: 5534023...           Connecting to seed...
            └─ Seed: cassandra-1           Joining cluster...
  T+240s    cassandra-2 HEALTHY            Joined cluster
            └─ Replication active          Syncing data...
  T+240s    cassandra-3 starts             Container created
            └─ Token: -5534023...          Connecting to seed...
            └─ Seed: cassandra-1           Joining cluster...
  T+360s    cassandra-3 HEALTHY            Joined cluster
            └─ Cluster complete (3/3)      Replication factor: 3
  T+360s    audit_api starts               Container created
            └─ Connecting to cluster...    Waiting for Cassandra...
            └─ Initialize keyspace         CREATE KEYSPACE audit_log
            └─ Create tables (3x)          Schema deployed
  T+380s    audit_api READY                Server running
            └─ http://localhost:8000       API accessible
            └─ /docs available             Swagger UI ready

  ─────────────────────────────────────────────────────────────────────
  Total startup time:
    • First run:   ~6-8 minutes  (image pull + compilation)
    • Cached run:  ~4-5 minutes  (Docker cache used)


┌─────────────────────────────────────────────────────────────────────────┐
│                      NETWORK ARCHITECTURE                               │
└─────────────────────────────────────────────────────────────────────────┘

  Docker Network: audit_net (bridge driver)

  ┌───────────────────────────────────────────────────────────────────┐
  │                        INTERNAL CLUSTER                           │
  │                                                                   │
  │   cassandra-1:9042  <─────┐                                       │
  │   cassandra-2:9042  <─────┼──── audit_api (load balanced)         │
  │   cassandra-3:9042  <─────┘                                       │
  │                                                                   │
  └───────────────────────────────────────────────────────────────────┘
                                  │
                                  │ Port mapping
                                  V
  ┌───────────────────────────────────────────────────────────────────┐
  │                         HOST MACHINE                              │
  │                                                                   │
  │   localhost:8000 ─────> audit_api:8000                            │
  │                                                                   │
  │   Access Points:                                                  │
  │   • http://localhost:8000/docs          Swagger UI                │
  │   • http://localhost:8000/redoc         ReDoc                     │
  │   • http://localhost:8000/openapi.json  OpenAPI spec              │
  │                                                                   │
  └───────────────────────────────────────────────────────────────────┘
```

## Application Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          AUDIT SERVICE APPLICATION                      │
└─────────────────────────────────────────────────────────────────────────┘

                                ┌──────────────┐
                                │   main.py    │
                                │  (FastAPI)   │
                                └──────┬───────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
                    V                  V                  V
            ┌──────────────┐   ┌─────────────┐   ┌─────────────┐
            │   config.py  │   │  logger.py  │   │   routers/  │
            │              │   │             │   │             │
            │ - CASSANDRA_ │   │ - setup_    │   │ - /api_v1   │
            │   HOSTS      │   │   logger()  │   │             │
            └──────────────┘   └─────────────┘   └──────┬──────┘
                                                        │
                                              ┌─────────┴──────────┐
                                              │                    │
                                              |                    |
                                              V                    V     
                                ┌──────────────────┐   ┌─────────────────────────────┐
                                │ audit_log.py     │   │   audit.py                  │
                                │   (Router)       │   │   (Router)                  │
                                │                  │   │                             │
                                │ POST /log/read   │   │ GET /audit/person/{id}      │
                                │ POST /log/change │   │ GET /audit/institution/{id} │
                                │                  │   │ GET /audit/code/{code       │
                                └─────────┬────────┘   └────────┬────────────────────┘
                                          │                     │
                                          └──────────────┬──────┘
                                                         │
                                                         V
                                                 ┌────────────────┐
                                                 │   schemas/     │
                                                 │  (Pydantic)    │
                                                 │                │
                                                 │ - audit_log.py │
                                                 │ - audit.py     │
                                                 │ - enums.py     │
                                                 └───────┬────────┘
                                                         │
                                                         V
                                                 ┌────────────────┐
                                                 │      api/      │
                                                 │   (Business    │
                                                 │     Logic)     │
                                                 │                │
                                                 │ - audit_log.py │
                                                 │ - audit.py     │
                                                 └───────┬────────┘
                                                         │
                                                         V
                                                 ┌────────────────┐
                                                 │   services/    │
                                                 │                │
                                                 │ - database.py  │
                                                 │ - utils.py     │
                                                 └───────┬────────┘
                                                         │
                                                         │
                                                         V
                                        ┌─────────────────────────────────┐
                                        │                                 │
                                        │     Apache Cassandra Cluster    │
                                        │                                 │
                                        │  ┌──────────────────────────┐   │
                                        │  │  audit_by_person         │   │
                                        │  │  - person_id (PK)        │   │
                                        │  │  - event_time (CK)       │   │
                                        │  │  - event_type            │   │
                                        │  │  - institution_id        │   │
                                        │  │  - change_code           │   │
                                        │  │  - change_json           │   │
                                        │  └──────────────────────────┘   │
                                        │                                 │
                                        │  ┌──────────────────────────┐   │
                                        │  │  changes_by_inst         │   │
                                        │  │  - institution_id (PK)   │   │
                                        │  │  - changed_at (CK)       │   │
                                        │  │  - person_id             │   │
                                        │  │  - change_code           │   │
                                        │  │  - change_json           │   │
                                        │  └──────────────────────────┘   │
                                        │                                 │
                                        │  ┌──────────────────────────┐   │
                                        │  │  changes_by_code         │   │
                                        │  │  - change_code (PK)      │   │
                                        │  │  - changed_at (CK)       │   │
                                        │  │  - person_id             │   │
                                        │  │  - institution_id        │   │
                                        │  │  - change_json           │   │
                                        │  └──────────────────────────┘   │
                                        │                                 │
                                        └─────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                              DATA FLOW                                  │
└─────────────────────────────────────────────────────────────────────────┘

  CLIENT REQUEST
       │
       V
  ┌─────────┐     ┌─────────┐     ┌──────────┐     ┌──────────┐
  │ Router  │ --> │ Schema  │ --> │   API    │ --> │ Service  │
  │         │     │ (Valid) │     │ (Logic)  │     │ (DB)     │
  └─────────┘     └─────────┘     └──────────┘     └──────────┘
                                                          │
                                                          V
                                                   ┌─────────────┐
                                                   │  Cassandra  │
                                                   └─────────────┘
                                                          │
                                                          V
  ┌─────────┐     ┌─────────┐     ┌──────────┐     ┌──────────┐
  │  JSON   │ <-- │ Schema  │ <-- │   API    │ <-- │ Service  │
  │Response │     │ (Serial)│     │ (Map)    │     │ (Query)  │
  └─────────┘     └─────────┘     └──────────┘     └──────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                          ENDPOINTS OVERVIEW                             │
└─────────────────────────────────────────────────────────────────────────┘

  POST /api_v1/log/read
    ├─> routers/audit_log.py → api/audit_log.py
    ├─> Log read event for multiple persons
    └─> Insert into: audit_by_person

  POST /api_v1/log/change
    ├─> routers/audit_log.py → api/audit_log.py
    ├─> Log change event for a person
    └─> Insert into: audit_by_person, changes_by_inst, changes_by_code

  GET /api_v1/audit/person/{p_id}
    ├─> routers/audit.py → api/audit.py
    ├─> Get audit trail for person (default limit: 20)
    └─> Query: audit_by_person WHERE person_id = ?

  GET /api_v1/audit/institution/{i_id}
    ├─> routers/audit.py → api/audit.py
    ├─> Get changes for institution (default limit: 20)
    └─> Query: changes_by_inst WHERE institution_id = ?

  GET /api_v1/audit/code/{code}
    ├─> routers/audit.py → api/audit.py
    ├─> Get changes by code (default limit: 20)
    └─> Query: changes_by_code WHERE change_code = ?


┌─────────────────────────────────────────────────────────────────────────┐
│                          FILE STRUCTURE                                 │
└─────────────────────────────────────────────────────────────────────────┘

  app/
   ├── main.py              # FastAPI application entry point
   ├── config.py            # Configuration (Cassandra hosts)
   ├── logger.py            # Logging setup
   │
   ├── routers/             # HTTP endpoint definitions
   │   ├── audit_log.py     # POST /log/read, /log/change
   │   └── audit.py         # GET /audit/{person|institution|code}
   │
   ├── schemas/             # Pydantic models
   │   ├── audit_log.py     # ReadEventRequest, ChangeEventRequest
   │   ├── audit.py         # AuditResponse, LogEventResponse, etc.
   │   └── enums.py         # ChangeCode enum
   │
   ├── api/                 # Business logic layer
   │   ├── audit_log.py     # log_read_event(), log_change_event()
   │   └── audit.py         # get_person_history(), get_institution_changes()
   │
   └── services/            # Data access layer
       ├── database.py      # CassandraDatabase class, connection management
       └── utils.py         # cassandra_future_to_asyncio()
```

## Testing diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    AUDIT SERVICE - TESTING FRAMEWORK                    │
└─────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                         PHASE 1: DATA GENERATION                        │
└─────────────────────────────────────────────────────────────────────────┘

                          ┌──────────────────┐
                          │ generate_seed.py │
                          │                  │
                          │ generate(        │
                          │  institutions,   │
                          │  persons,        │
                          │  changes,        │
                          │  reads           │
                          │ )                │
                          └────────┬─────────┘
                                   │
                                   ├─> uses generators.py:
                                   │   ├─ generate_institutions()
                                   │   ├─ generate_persons()
                                   │   ├─ generate_change_events()
                                   │   └─ generate_read_events()
                                   │
                                   V
                          ┌──────────────────┐
                          │  seed_data.json  │<─── GENERATED FILE
                          │                  │
                          │ {                │
                          │   institutions,  │
                          │   persons,       │
                          │   events: {      │
                          │     changes,     │
                          │     reads        │
                          │   }              │
                          │ }                │
                          └──────────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                    PHASE 2: DATABASE SEEDING                            │
└─────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────┐              ┌─────────────────────────┐
    │  seed_data.json  │─────────────>│      seeder.py          │
    └──────────────────┘              │                         │
                                      │ 1. Connect to Cassandra │
                                      │ 2. Read seed_data.json  │
                                      │ 3. Prepare INSERT       │
                                      │    queries (x3 tables)  │
                                      │ 4. Batch insert         │
                                      │    (BATCH_SIZE=50)      │
                                      │ 5. Save test IDs        │
                                      │ 6. Close connection     │
                                      └────────┬────────────────┘
                                               │
                                 ┌─────────────┴─────────────┐
                                 │                           │
                                 V                           V
                    ┌────────────────────┐      ┌───────────────────┐
                    │  test_ids.json     │      │   Cassandra DB    │
                    │                    │      │                   │
                    │ {                  │      │ ✓ audit_by_person │
                    │   person_id,       │      │ ✓ changes_by_inst │
                    │   institution_id,  │      │ ✓ changes_by_code │
                    │   code             │      │                   │
                    │ }                  │      │ [500+ records]    │
                    └────────────────────┘      └───────────────────┘
                         ^
                         └─── GENERATED FILE (for testing)


┌─────────────────────────────────────────────────────────────────────────┐
│              PHASE 3: INSERT & VERIFICATION TESTING                     │
└─────────────────────────────────────────────────────────────────────────┘

                         ┌────────────────────┐
                         │ log_and_verify.py  │
                         │                    │
                         │ run_insert_and_    │
                         │ query_tests()      │
                         └──────────┬─────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │                         │                         │
          │                         │                         │
          V                         V                         V       
    ┌────────────────────┐    ┌────────────────────┐      ┌───────────────────────────────────┐
    │  Generate Test IDs │    │  Test Scenarios    │      │  Direct DB Verification           │
    │                    │    │                    │      │                                   │
    │ - institution_id   │    │ 1. READ event      │      │ Query all 3 tables:               │
    │ - 3x person_ids    │    │ 2-7. CHANGE events │      │                                   │
    └────────────────────┘    │ * PASSWORD_RESET   │      │ * audit_by_person                 │
                              │ * EMAIL_CHANGE     │      │ * changes_by_institution          │
                              │ * ADDRESS_UPDATE   │      │ * changes_by_code                 │
                              │ * PERMISSION_GRANT │      │                                   │
                              │ * STATUS_INACTIVE  │      │ Verify event exists in all tables │
                              │ * LIMIT_INCREASE   │      └───────────────────────────────────┘
                              └────────────────────┘      
                                    │                     
                                    │
                                    │ For each test:
                                    │ 1. POST to API (insert)
                                    │ 2. Wait for propagation (0.5s)
                                    │ 3. Query DB directly
                                    │ 4. Verify event found
                                    │
                                    V
                    ┌─────────────────────────────────┐
                    │  insert_query_report.json       │<─── GENERATED REPORT
                    │                                 │
                    │ {                               │
                    │   timestamp,                    │
                    │   test_configuration: {         │
                    │     institution_id,             │
                    │     person_ids[]                │
                    │   },                            │
                    │   tests: [                      │
                    │     {                           │
                    │       event_type,               │
                    │       api_insert: {             │
                    │         endpoint,               │
                    │         payload,                │
                    │         response                │
                    │       },                        │
                    │       database_queries: {       │
                    │         by_person: {...},       │
                    │         by_institution: {...},  │
                    │         by_code_filtered: {...} │
                    │       },                        │
                    │       found_in_all_tables       │
                    │     },                          │
                    │     ...                         │
                    │   ]                             │
                    │ }                               │
                    └─────────────────────────────────┘
                                    │
                                    V
                    ┌───────────────────────────────┐
                    │  insert_test_ids.json         │<─── GENERATED FILE
                    │                               │
                    │ {                             │
                    │   institution_id,             │
                    │   person_id,                  │
                    │   person_ids[],               │
                    │   code                        │
                    │ }                             │
                    └───────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                PHASE 4: END-TO-END API TESTING                          │
└─────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────┐              ┌───────────────────────────────────────┐
    │  test_ids.json   │─────────────>│   audit_tester.py                     │
    └──────────────────┘              │                                       │
                                      │ generate_report()                     │
                                      │                                       │
                                      │ Test Scenarios:                       │
                                      │                                       │
                                      │ 1. Audit by Person                    │
                                      │    GET /api_v1/audit/person/{id}      │
                                      │                                       │
                                      │ 2. Audit by Institution.              │
                                      │    GET /api_v1/audit/institution/{id} │
                                      │                                       │
                                      │ 3. Audit by Code                      │
                                      │    GET /api_v1/audit/code/{code}      │
                                      │                                       │
                                      │ For each:                             │
                                      │ - Measure latency                     │
                                      │ - Count results                       │
                                      │ - Validate response                   │
                                      └────────┬──────────────────────────────┘
                                               │
                                               V
                                ┌──────────────────────────────┐
                                │   audit_report.json          │<─── FINAL REPORT
                                │                              │
                                │ {                            │
                                │   timestamp,                 │
                                │   environment,               │
                                │   summary: {                 │
                                │     passed: 3,               │
                                │     failed: 0,               │
                                │     errors: 0                │
                                │   },                         │
                                │   details: [                 │
                                │     {                        │
                                │       scenario,              │
                                │       endpoint,              │
                                │       status: "PASSED",      │
                                │       http_status: 200,      │
                                │       results_count: 10,     │
                                │       latency_ms: 29.69,     │
                                │       response_data: [...],  │
                                │       error: null            │
                                │     },                       │
                                │     ...                      │
                                │   ]                          │
                                │ }                            │
                                └──────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                      TESTING WORKFLOW SUMMARY                           │
└─────────────────────────────────────────────────────────────────────────┘

  STEP 1: Generate Mock Data
    $ python -m app.utils.generate_seed --institutions=20 --persons=100 --changes=500 --reads=50
    
    OUTPUT: seed_data.json (institutions, persons, events)

  ─────────────────────────────────────────────────────────────────────────

  STEP 2: Seed Database
    $ python -m app.utils.seeder
    
    INPUT:  seed_data.json
    OUTPUT: test_ids.json
    ACTION: Insert 500 events into Cassandra (3 tables, batched)

  ─────────────────────────────────────────────────────────────────────────

  STEP 3: Verify Insert & Query (Integration Test)
    $ python -m app.utils.log_and_verify
    
    TESTS:  1x READ + 6x CHANGE events (via API)
    OUTPUT: insert_query_report.json
            insert_test_ids.json
    CHECK:  * API insertion successful
            * Events found in all 3 tables
            * Data consistency verified

  ─────────────────────────────────────────────────────────────────────────

  STEP 4: End-to-End API Testing
    $ python -m app.utils.audit_tester
    
    INPUT:  test_ids.json
    TESTS:  3 GET endpoints (person, institution, code)
    OUTPUT: audit_report.json
    METRICS: * HTTP status codes
             * Response times (latency)
             * Result counts
             * Data validation


┌─────────────────────────────────────────────────────────────────────────┐
│                      GENERATED FILES OVERVIEW                           │
└─────────────────────────────────────────────────────────────────────────┘

  DATA FILES:
  ┌──────────────────────┬────────────────────┬─────────────────────────┐
  │ File                 │ Generated By       │ Purpose                 │
  ├──────────────────────┼────────────────────┼─────────────────────────┤
  │ seed_data.json       │ generate_seed.py   │ Mock data for seeding   │
  │ test_ids.json        │ seeder.py          │ Sample IDs for testing  │
  │ insert_test_ids.json │ log_and_verify.py  │ IDs from insert tests   │
  └──────────────────────┴────────────────────┴─────────────────────────┘

  REPORT FILES:
  ┌──────────────────────────┬──────────────────┬──────────────────────┐
  │ File                     │ Generated By     │ Contains             │
  ├──────────────────────────┼──────────────────┼──────────────────────┤
  │ insert_query_report.json │ log_and_verify   │ * API insert results │
  │                          │                  │ * DB query results   │
  │                          │                  │ * Data verification  │
  │                          │                  │ * Consistency checks │
  ├──────────────────────────┼──────────────────┼──────────────────────┤
  │ audit_report.json        │ audit_tester     │ * E2E test results   │
  │                          │                  │ * Performance metrics│
  │                          │                  │ * Success/fail counts│
  │                          │                  │ * Response samples   │
  └──────────────────────────┴──────────────────┴──────────────────────┘


┌─────────────────────────────────────────────────────────────────────────┐
│                        TEST COVERAGE                                    │
└─────────────────────────────────────────────────────────────────────────┘

  ┌────────────────────┬─────────────────────┬──────────────────────────┐
  │ Test Script        │ Test Type           │ What It Tests            │
  ├────────────────────┼─────────────────────┼──────────────────────────┤
  │ seeder.py          │ Data Loading        │ * Batch inserts          │
  │                    │                     │ * 3-table consistency    │
  │                    │                     │ * DB connection          │
  ├────────────────────┼─────────────────────┼──────────────────────────┤
  │ log_and_verify.py  │ Integration         │ * POST endpoints         │
  │                    │                     │ * API → DB consistency   │
  │                    │                     │ * Multi-table writes     │
  │                    │                     │ * Event propagation      │
  ├────────────────────┼─────────────────────┼──────────────────────────┤
  │ audit_tester.py    │ End-to-End / API    │ * GET endpoints          │
  │                    │                     │ * Query performance      │
  │                    │                     │ * Response validation    │
  │                    │                     │ * Read operations        │
  └────────────────────┴─────────────────────┴──────────────────────────┘
```

## Swagger UI

The Audit Service exposes a RESTful API documented with OpenAPI/Swagger. You can access the interactive API documentation at:

**Swagger UI**: `http://localhost:8000/docs`

![Swagger UI](misc/Audit_Service_swagger.png)
