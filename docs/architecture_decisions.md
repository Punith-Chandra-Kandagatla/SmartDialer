# SmartDialer — Architecture Decisions

## 1. Overview

SmartDialer is designed as a modular backend application with an independent safety layer between dialing strategies and telecom providers.

The primary design goal is to gain the efficiency of predictive dialing without sacrificing the deterministic agent-capacity guarantees of progressive dialing.

Rather than introducing unnecessary distributed infrastructure, the prototype uses a straightforward architecture with clear service boundaries and database-backed concurrency control.

## 2. Technology Choices

| Technology | Why We Chose It | Problem It Solves | Trade-off |
|---|---|---|---|
| Python | Simple syntax and strong ecosystem for backend development and simulation. | Enables rapid development of dialing logic and predictive calculations. | CPU-intensive workloads may require optimization or separate workers. |
| FastAPI | Lightweight framework with automatic API documentation. | Provides structured REST APIs for campaigns, agents, calls and operations. | Requires additional components for background processing and long-running tasks. |
| PostgreSQL | Reliable relational database with transactions and row-level locking. | Maintains consistent agent reservations, call records and event history. | High contention and large transaction volumes require careful query and index optimization. |
| SQLAlchemy | Database abstraction and transaction management. | Keeps database operations organized and maintainable. | Adds an abstraction layer that requires ORM knowledge and query tuning. |
| React | Component-based frontend framework. | Provides an interactive operations dashboard. | Requires maintaining a separate frontend application. |
| Pytest and HTTPX | Testing framework and API test client. | Validates business logic, concurrency-related behavior and API functionality. | Test simulations cannot completely reproduce real telecom or production failures. |

## 3. Architectural Decisions

### 3.1 Modular Monolith Instead of Microservices

We chose a modular monolithic architecture with separate services for reservations, dialing, safety, provider communication, event processing and recovery.

**Why:**
- Easier to develop, test and deploy within the assignment scope.
- Avoids unnecessary network communication between services.
- Maintains clear separation of responsibilities.

**Trade-off:**
Individual components cannot be independently deployed or scaled. If traffic grows significantly, selected components can be extracted into separate services.

### 3.2 PostgreSQL for Reservation and Concurrency Control

Agent and borrower reservations use database transactions and `SELECT FOR UPDATE SKIP LOCKED`.

**Why:**
Multiple workers may attempt to reserve the same agent simultaneously. Database-level locking ensures that competing workers do not allocate the same agent.

Reservation tokens and lease expiry provide additional protection against abandoned reservations.

**Trade-off:**
Database locking introduces contention under heavy workloads. At larger scales, reservation partitioning and carefully designed worker pools may be necessary.

### 3.3 Independent Safety Controller

The predictive engine recommends dialing aggressiveness, but it cannot directly initiate calls.

Every recommendation passes through an independent Safety Controller, which can approve, reduce, reject or fall back to progressive dialing.

**Why:**
Predictive calculations are estimates and may become inaccurate when answer rates or provider conditions change. The safety layer enforces operational limits independently of those estimates.

**Trade-off:**
The additional validation step introduces some processing overhead and may reduce dialing aggressiveness. This is an intentional trade-off for correctness.

### 3.4 Provider Adapter Pattern

Telecom integrations are isolated behind a common provider interface. The prototype includes two mock providers with different latency and failure characteristics.

**Why:**
Dialing logic does not need to understand provider-specific implementation details. New providers can be introduced without changing the core orchestration logic.

**Trade-off:**
The adapter must support provider-specific capabilities and differences, which may require additional implementation.

### 3.5 Event Ledger and Idempotent Processing

Provider events are stored with unique provider event identifiers.

**Why:**
Telecom providers may send duplicate or out-of-order events. Persisting events and checking their processing status helps prevent duplicate state transitions.

**Trade-off:**
Maintaining event history increases database storage and requires event retention and cleanup policies.

### 3.6 Recovery and Reconciliation

Call execution is recorded before making an external provider request. Uncertain requests are marked for reconciliation rather than blindly retried.

Expired reservations can also be recovered using their lease information.

**Why:**
A worker may crash after sending a provider request but before recording its response. Retrying immediately could initiate a duplicate call.

**Trade-off:**
Reconciliation introduces additional processing and may delay retries, but it avoids unsafe assumptions about whether an external operation succeeded.

## 4. Scalability Considerations

The prototype uses PostgreSQL as the source of truth and keeps dialing logic modular.

As the system grows:

- **100 agents:** A single application instance and PostgreSQL database are sufficient for the prototype.
- **1,000 agents:** Introduce multiple workers, database connection pooling, query optimization and workload monitoring.
- **10,000 agents:** Partition campaigns and reservation workloads, distribute workers, optimize event processing and consider dedicated queues for asynchronous tasks.

The main bottleneck is likely to move from application-level calculations to database contention, provider throughput and event-processing volume.

Scaling should therefore target the measured bottleneck rather than simply adding more application servers.

## 5. Final Design Principle

The predictive engine is responsible for efficiency, while the Safety Controller is responsible for correctness.

This separation allows the system to benefit from predictive dialing while retaining progressive dialing as a deterministic fallback.

The objective is not to maximize the number of calls initiated. It is to maximize useful agent utilization while ensuring that every outbound call has a valid allocation and remains within defined operational safety limits.