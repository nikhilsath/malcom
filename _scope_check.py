import sys
sys.path.insert(0, "/Users/nikhilsathyanarayana/Documents/malcom")
from backend.services.connector_activities_runtime import get_missing_connector_activity_scopes

r1 = get_missing_connector_activity_scopes(
    {"scopes": ["https://www.googleapis.com/auth/spreadsheets"]},
    {"required_scopes": ["https://www.googleapis.com/auth/spreadsheets"]}
)
print("create_spreadsheet check (should be []):", r1)

r2 = get_missing_connector_activity_scopes(
    {"scopes": ["https://www.googleapis.com/auth/spreadsheets"]},
    {"required_scopes": ["https://www.googleapis.com/auth/spreadsheets.readonly"]}
)
print("readonly satisfied by full scope (should be []):", r2)

r3 = get_missing_connector_activity_scopes(
    {"scopes": ["https://www.googleapis.com/auth/spreadsheets.readonly"]},
    {"required_scopes": ["https://www.googleapis.com/auth/spreadsheets"]}
)
print("readonly cannot satisfy write (should have spreadsheets):", r3)

assert r1 == [], f"FAIL: {r1}"
assert r2 == [], f"FAIL: {r2}"
assert "https://www.googleapis.com/auth/spreadsheets" in r3, f"FAIL: {r3}"
print("All assertions passed.")
