# Import Paths

New code should import the module that owns the implementation. Compatibility
facades remain in place so older call sites can migrate gradually.

## Preferred Imports

```python
from web.app_paths import AppPaths
from web.kassensturz_web_app import KassensturzWebApp

from core.cash.cash_count_request import CashCountRequest
from core.cash.cash_movement_request import CashMovementRequest
from core.cash.cash_service import CashService
from core.cash.cash_sync_context import CashSyncContext

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
