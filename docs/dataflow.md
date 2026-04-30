## Data Flow Diagram

```mermaid
flowchart TD
    A[User opens app] --> B[Flask route in app.py]

    B --> C1[Cash Count form]
    B --> C2[Cash Movement form]
    B --> C3[Admin actions]
    B --> C4[Balances page]

    C1 --> D1[cash_service.record_cash_count_and_sync]
    C2 --> D2[cash_service.record_cash_movement_and_sync]
    C3 --> D3[cash_service.rebuild_exports_and_sync]
    C4 --> D4[storage.fetch_cash_account_balances]

    D1 --> E1[storage.create_cash_count]
    D1 --> E2[storage.set_cash_account_balance_cents]

    D2 --> E3[storage.create_cash_movement]
    D2 --> E4[storage.adjust_cash_account_balance_cents from_account]
    D2 --> E5[storage.adjust_cash_account_balance_cents to_account]

    E1 --> F[(SQLite DB)]
    E2 --> F
    E3 --> F
    E4 --> F
    E5 --> F
    D4 --> F

    D1 --> G[create_backup]
    D2 --> G
    D3 --> G

    G --> H[Local backup .db files]

    D1 --> I[export_utils.export_all]
    D2 --> I
    D3 --> I

    F --> I
    I --> J[Local Excel export]
    I --> K[Local TXT export]

    D1 --> L[nextcloud_sync.download_remote_excel_if_exists]
    D2 --> L
    D3 --> L

    L --> M{Remote Excel exists?}
    M -->|Yes| N[export_utils.import_all_from_excel]
    M -->|No| O[Skip remote import]

    N --> P[merge cash_accounts]
    N --> Q[merge cash_contexts]
    N --> R[merge cash_counts]
    N --> S[merge cash_movements]

    P --> F
    Q --> F
    R --> F
    S --> F

    F --> T[Re-export full dataset]
    T --> J
    T --> K

    J --> U[nextcloud_sync.upload_files]
    K --> U

    U --> V[Nextcloud remote files]

    U --> W[sync_state.update_sync_state]
    W --> X[sync_state.json]

    F --> Y[Balances page]
    X --> Z[Admin sync state view]
    H --> AA[Admin backup restore]