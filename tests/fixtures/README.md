# Test Fixtures

`legacy_cash_counts_anonymized.xlsx` is a sanitized legacy cash-count workbook.
It keeps representative spreadsheet quirks from production-style files while
using neutral event, person, and comment values:

- metadata rows before the header row
- Excel serial date and time cells
- two-digit German date text
- German time text with dots
- formatted numeric currency cells
- currency text with non-breaking spaces
- German legacy status labels
