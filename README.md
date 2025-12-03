# Library API (Koha OPAC)

A small Python CLI for interacting with BRACU Koha OPAC to:

## Requirements

Install dependencies:

```pwsh
pip install -r .\requirements.txt
```

## Commands

Run the CLI:

```pwsh
# Get current checkouts (JSON to stdout)
python .\main.py get_book_info <userid> <password>

# Renew a specific item (JSON to stdout)
python .\main.py renew_book <userid> <password> <item_id>
```

Examples:

```pwsh
python .\main.py get_book_info 12345678 myPassword
python .\main.py renew_book 12345678 myPassword 123455
```

## Output Schema

- Success: `{ "status": "success", "items": [ { "item_id": 58734, "due_date": "10/12/2025" }, ... ] }`
- Error: `{ "status": "error", "error": "message" }`

- Success (redirect or "Renewed!" detected): `{ "status": "success", "renewal": { "status": "success", "item_ids": [58734] } }`
- Requires login (failed): `{ "status": "error", "error": "Renewal failed: not logged in", "error_code": "renewal_requires_login", "renewal": { "status": "failed", "reason": "not_logged_in", "item_id": 58734, "borrower_id": 33189 } }`
- Unknown (no explicit success/failure markers): `{ "status": "success", "renewal": { "status": "unknown" } }`

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0).
See the `LICENSE` file for the full text.

If you distribute modified versions, you must also distribute source code under GPL-3.0 terms.
