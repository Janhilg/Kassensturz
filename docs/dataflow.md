## Data Flow Diagram

```mermaid
flowchart TD
    A[User opens app] --> B[KassensturzWebApp in web/kassensturz_web_app.py]

    B --> C1[Cash count route]
    B --> C2[Cash movement route]
    B --> C3[Admin route]
    B --> C4[Balances route]

    B --> P[AppPaths]
    P --> SC[CashSyncContext]

    C1 --> R1[CashCountRequest]
    C2 --> R2[CashMovementRequest]

    R1 --> S1[CashService.record_count]
    R2 --> S2[CashService.record_movement]
    C3 --> S3[CashService.rebuild_exports]
    C4 --> B1[CashStorage accounts and reports]

    B --> ST[CashStorage bound to db_path]
    ST --> ARepo[CashAccountRepository]
    ST --> CRepo[CashContextRepository]
    ST --> MRepo[CashMovementRepository]
    ST --> CountRepo[CashCountRepository]
    ST --> BackupRepo[CashBackupRepository]

    S1 --> CountRepo
    S1 --> ARepo
    S2 --> MRepo
    S2 --> ARepo
    B1 --> ARepo

    ARepo --> DB[(SQLite DB)]
    CRepo --> DB
    MRepo --> DB
    CountRepo --> DB

    S1 --> Pipeline[Full sync pipeline]
    S2 --> Pipeline
    S3 --> Pipeline
    SC --> Pipeline

    Pipeline --> BackupRepo
    BackupRepo --> Backups[Local backup .db files]

    Pipeline --> Export[CashExportService.export_all]
    DB --> Export
    Export --> Excel[Local Excel export]
    Export --> Text[Local TXT export]

    Pipeline --> Download[NextcloudClient.download_remote_excel_if_exists]
    Download --> RemoteCheck{Remote Excel exists?}

    RemoteCheck -->|Yes| Import[CashExportService.import_all_from_excel]
    RemoteCheck -->|No| Skip[Skip remote import]

    Import --> MergeA[Merge cash_accounts append-only]
    Import --> MergeC[Merge cash_contexts append-only]
    Import --> MergeCount[Merge cash_counts append-only]
    Import --> MergeM[Merge cash_movements append-only]

    MergeA --> DB
    MergeC --> DB
    MergeCount --> DB
    MergeM --> DB

    DB --> ReExport[Re-export full dataset]
    ReExport --> Excel
    ReExport --> Text

    Excel --> Upload[NextcloudClient.upload_files]
    Text --> Upload
    Upload --> Remote[Nextcloud remote files]

    Upload --> SyncState[SyncStateStore.update_sync_state]
    SyncState --> StateFile[sync_state.json]

    Backups --> Restore[Admin backup restore]
    Restore --> DB
    StateFile --> AdminView[Admin sync state view]
```

## Notes

- Routes create request objects instead of passing many keyword arguments through the app.
- `CashService` owns the business workflow and sync orchestration.
- `CashStorage(db_path)` binds repositories to one database path, while module-level storage functions remain available for compatibility and focused tests.
- `CashSyncContext` carries the runtime paths and config needed by the sync pipeline.
