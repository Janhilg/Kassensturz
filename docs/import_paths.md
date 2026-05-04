# Import Paths

New code should import the direct module that owns the implementation.
Compatibility facades remain in place so older call sites can migrate gradually.

## Preferred Imports

Prefer direct class modules:

```python
from web.app_paths import AppPaths
from web.kassensturz_web_app import KassensturzWebApp

from core.cash.cash_count_request import CashCountRequest
from core.cash.cash_movement_request import CashMovementRequest
from core.cash.cash_service import CashService
from core.cash.cash_sync_context import CashSyncContext
from core.cash.cash_sync_service import CashSyncService

from core.storage_objects.cash_storage import CashStorage
from core.storage_objects.cash_account_repository import CashAccountRepository
from core.storage_objects.cash_context_repository import CashContextRepository
from core.storage_objects.cash_count_repository import CashCountRepository
from core.storage_objects.cash_movement_repository import CashMovementRepository

from core.storage_accounts import fetch_all_cash_accounts
from core.storage_contexts import get_or_create_cash_context
from core.storage_counts import create_cash_count
from core.storage_movements import create_cash_movement
from core.storage_migrations import ensure_db_file
```

Avoid importing new code through package-level facades such as `core.cash`,
`core.storage_objects`, or legacy compatibility modules such as
`core.cash_service`.

## Storage Function Modules

- `core.storage_connection`: SQLite connection, row/value helpers, denomination
  helpers, row counts
- `core.storage_migrations`: schema SQL, `PRAGMA user_version` migrations, DB
  initialization
- `core.storage_accounts`: account records, balance helpers, account statements,
  account imports
- `core.storage_contexts`: context records and context imports
- `core.storage_counts`: cash count records and count imports
- `core.storage_movements`: cash movement records and movement imports
- `core.storage_backups`: backup create/list/restore helpers

## Compatibility Facades

These imports still work, but new code should avoid adding more dependencies on
them:

```python
from core import storage
from core.cash_service import CashService
from core.storage_objects import CashStorage
from core.cash import CashCountRequest
```

Use facades when preserving old code is the goal. Use direct modules when adding
or changing implementation code.

Implementation files are guarded by `tests/test_import_paths.py` and should not
import `core.storage` or other compatibility facades. Keep facade coverage in
small compatibility tests only.

## Migration Rule

When touching an internal file or test that already uses a facade, prefer moving
only the imports you are actively working near. Do not turn a small behavior
change into a broad import rewrite.

Good cleanup targets:

- tests that exercise a specific storage domain can import that domain directly,
  such as `from core.storage_counts import create_cash_count`
- service or web code should import request/result/service classes from their
  one-class modules
- storage adapters should import focused storage functions directly

Keep compatibility-path tests intentionally small. They should prove old imports
still resolve, not encourage new code to use them.
