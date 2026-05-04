# How to Use Kassensturz

This guide is for the person using Kassensturz during an event or venue cash
workflow. It focuses on the app itself: what to enter, where to look, and what
each action means.

## The Basic Idea

Kassensturz tracks two kinds of cash facts:

- Cash counts: what is physically in a cash account right now.
- Cash movements: money moved from one account to another.

A cash count sets the balance of one account. A cash movement changes two
balances: it subtracts from the source account and adds to the target account.

Example:

```text
Count:    Bar Cash Box = 200.00 EUR
Movement: Bar Cash Box -> Runner Float = 50.00 EUR

Result:   Bar Cash Box = 150.00 EUR
          Runner Float = 50.00 EUR
```

## Main Pages

Kassensturz has four everyday areas:

- Cash count page: record counted cash in one account.
- Cash movement page: record cash moved between accounts.
- Balances page: check what each account should currently contain.
- Admin page: rebuild exports, sync, view status, and restore backups.

## Cash Accounts

The app starts with a fixed set of accounts:

- Bar Cash Box
- Entrance Cash Box
- Runner Float
- Supplier / Drinks Purchase
- Cash Handout
- Bank

These account names describe where the cash is or why it left the cash system.

Use cash boxes for physical sales boxes. Use `Runner Float` for temporary cash
given to a runner. Use supplier, handout, or bank accounts when cash leaves the
main boxes for a specific purpose.

## Record a Cash Count

Use a cash count when someone physically counts the money in one account.

Typical moments:

- start of an event
- end of an event
- shift handover
- spot check during operation
- correction after checking real cash

Steps:

1. Open the cash count page.
2. Choose the cash account.
3. Enter who counted the cash.
4. Choose the count type.
5. Enter the event or context label.
6. Enter either the total amount or the denominations.
7. Submit the count.

Count types:

- `opening`: the starting amount.
- `closing`: the final amount.
- `spot_check`: a check during operation.
- `reconciliation`: a correction or audit count.

After saving, the selected account balance becomes the counted amount.

## Record a Cash Movement

Use a cash movement when cash physically moves.

Examples:

- Bar Cash Box -> Runner Float
- Entrance Cash Box -> Bank
- Runner Float -> Supplier / Drinks Purchase
- Bar Cash Box -> Cash Handout

Steps:

1. Open the cash movement page.
2. Choose the source account.
3. Choose the target account.
4. Enter the amount.
5. Enter the event or context label.
6. Add actor, reference, or note if helpful.
7. Submit the movement.

The source account goes down by the movement amount. The target account goes up
by the movement amount.

At least one side must be selected. Use only a target account when cash enters
the tracked system. Use only a source account when cash leaves the tracked
system.

## Runner Float Rule

There is one special rule:

When money moves from `Runner Float` to `Supplier / Drinks Purchase`, the app
automatically returns the remaining runner float balance to `Bar Cash Box`.

This keeps the runner float from accidentally staying open after a supplier
purchase.

## Use Context Labels

The context label is usually the event, shift, or day.

Good examples:

- Friday Bar
- Main Hall Saturday
- Summer Event 2026
- Shift 2

Use the same label for related counts and movements. This makes the recent
history easier to read later.

## Check Balances

Open the balances page to answer:

```text
How much cash should be in each account right now?
```

Use this page during the event to compare expected cash with physical cash.

If an account looks wrong:

1. Check the latest count for that account.
2. Check recent movements into or out of that account.
3. If the physical cash is correct and the app should be corrected, record a
   reconciliation count.

## Admin Page

The admin page is for maintenance and recovery.

It shows:

- app version
- database schema version
- number of accounts, contexts, movements, and counts
- sync status
- production bootstrap status
- available backups

Admin actions:

- Rebuild exports now: recreate Excel and text exports from the local database.
- Sync now: rebuild exports and run the sync workflow.
- Restore selected backup: replace the current database with a previous backup.

Restoring a backup overwrites the current local database. Use it only when you
are sure the selected backup is the state you want to return to.

## Exports

Kassensturz creates two export files:

- Excel workbook
- plain text summary

The database is the source of truth. The export files are copies generated from
the database. If they are missing or stale, use the admin page to rebuild them.

## Sync

When sync is configured, Kassensturz can exchange data through the remote
workbook.

In plain terms, sync does this:

1. Save a local backup.
2. Rebuild local exports.
3. Check whether a remote workbook exists.
4. Import remote rows.
5. Add rows that are not already in the local database.
6. Rebuild the merged export.
7. Upload the new export files.

Sync imports are append-only. Running sync again with the same remote rows
should not create duplicates.

## Production Bootstrap

If the app starts in production with an empty database, it can import existing
remote cash count data before new entries are made.

This is meant for the first production run when older cash-count data already
exists remotely.

The admin page shows whether bootstrap is:

- inactive
- ready
- blocked
- skipped
- imported

## Backups

Kassensturz creates local database backups before sync/export work.

To restore a backup:

1. Open the admin page.
2. Choose a backup from the dropdown.
3. Confirm the restore.
4. Check balances and recent entries afterward.

After a restore, exports are rebuilt from the restored database.

## Daily Event Workflow

A simple event routine:

1. Record opening counts for active cash boxes.
2. Record every relevant cash movement during the event.
3. Check the balances page during operation.
4. Record closing counts at the end.
5. Use the admin page to sync if needed.
6. Keep the generated backup and exports for recovery or review.

## Troubleshooting

If balances look wrong:

- review the latest count for the affected account
- review recent movements for that account
- record a reconciliation count if the physical cash should become the new truth

If a movement was entered incorrectly:

- record a correcting movement in the opposite direction
- add a note that explains the correction

If sync did not appear to work:

- open the admin page
- check the sync state
- run sync again if needed
- ask the technical maintainer to check the remote settings if it keeps failing

If a backup was restored by mistake:

- restore a newer backup if one exists
- check balances before entering new records

For technical setup and deployment, see [configuration.md](configuration.md).
