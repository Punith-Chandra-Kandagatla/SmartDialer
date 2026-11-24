# SmartDialer — System Architecture

## 1. Architecture Overview

```mermaid
flowchart TD
    A[Campaign Manager] --> B[Borrower Queue]
    B --> C[Dialing Strategy]

    C --> D[Progressive Dialer]
    C --> E[Predictive Pacing Engine]

    D --> F[Independent Safety Controller]
    E --> F

    F --> G[Call Allocator]
    G --> H[Provider Manager]

    H --> I[Reliable Mock Provider]
    H --> J[Unreliable Mock Provider]

    I --> K[Provider Event Processor]
    J --> K

    K --> L[State Manager]
    L --> M[(PostgreSQL)]

    M --> N[Operations Dashboard]

    O[Execution Recovery] --> M
    P[Provider Reconciliation] --> M