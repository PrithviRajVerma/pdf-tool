# System Architecture & Flowchart Sample

This sample document showcases **Markdown to PDF** compilation with embedded **Mermaid.js vector diagrams**, code syntax highlighting, and responsive typography.

---

## 1. High-Level Flowchart

```mermaid
flowchart TD
    Client["Client (Web / Mobile)"] -->|HTTPS / REST| Gateway["API Gateway"]
    Gateway --> Auth["Authentication Service (JWT)"]
    Gateway --> Service["Application Core"]
    Service -.->|"Cache-Aside (Redis)"| Cache[("Redis Cache")]
    Service --> DB[("PostgreSQL Cluster")]
```

---

## 2. Request Lifecycle Sequence

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Browser as React SPA
    participant API as Spring Boot API
    participant DB as PostgreSQL

    User->>Browser: Click Submit Form
    Browser->>API: POST /api/v1/items (Bearer Token)
    API->>API: Validate Request DTO
    API->>DB: INSERT INTO items (name, status)
    DB-->>API: 201 Created (Item Row)
    API-->>Browser: 200 OK (Response JSON)
    Browser-->>User: Display Success Toast
```

---

## 3. Entity Data Model

```mermaid
erDiagram
    WORKSPACE ||--o{ PROJECT : contains
    PROJECT ||--o{ ISSUE : tracks
    USER ||--o{ ISSUE : assigned_to

    WORKSPACE {
        uuid id PK
        string name
        timestamp created_at
    }
    PROJECT {
        uuid id PK
        uuid workspace_id FK
        string key
        string name
    }
    ISSUE {
        uuid id PK
        uuid project_id FK
        uuid assignee_id FK
        string title
        string status
    }
    USER {
        uuid id PK
        string email
        string full_name
    }
```

---

## 4. Configuration & Settings Table

| Setting Key | Default Value | Description |
| :--- | :--- | :--- |
| `app.security.token-ttl` | `3600s` | Expiration time for generated JWT bearer tokens |
| `app.cache.max-entries` | `10000` | Maximum cache capacity in Redis |
| `app.concurrency.workers` | `8` | Thread pool size for parallel batch operations |

---

## 5. Sample Application Code

```python
def process_event(event_id: str, payload: dict) -> bool:
    """Validate and dispatch domain event to transactional outbox."""
    if not event_id or not payload:
        return False
    logger.info("Processing event %s with %d entries", event_id, len(payload))
    return True
```
