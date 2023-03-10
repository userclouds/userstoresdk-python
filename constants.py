import uuid

COLUMN_TYPE_INVALID = "invalid"
COLUMN_TYPE_STRING = "string"
COLUMN_TYPE_TIMESTAMP = "timestamp"

AUTHN_TYPE_PASSWORD = "password"

ACCESS_POLICY_OPEN_ID = uuid.UUID("1bf2b775-e521-41d3-8b7e-78e89427e6fe")
TRANSFORMATION_POLICY_PASS_THROUGH_ID = uuid.UUID(
    "c0b5b2a1-0b1f-4b9f-8b1a-1b1f4b9f8b1a"
)
VALIDATION_POLICY_PASS_THROUGH_ID = uuid.UUID("c0b5b2a1-0b1f-4b9f-8b1a-1b1f4b9f8b1a")
