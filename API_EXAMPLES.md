# API Examples with cURL

## Setup
```bash
# Base URL
BASE_URL="http://localhost:8000/api"

# Optional: Save tokens to variables
CUSTOMER_TOKEN=""
ADMIN_TOKEN=""
```

---

## Health Check

```bash
curl -X GET "$BASE_URL/health"
```

**Output:**
```json
{"status": "ok"}
```

---

## Customer Authentication

### 1. Customer Sign Up

```bash
curl -X POST "$BASE_URL/auth/customer/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePass123!",
    "full_name": "John Doe",
    "phone": "+959123456789"
  }'
```

**Output:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "john@example.com",
    "full_name": "John Doe",
    "phone": "+959123456789"
  }
}
```

**Store the token:**
```bash
CUSTOMER_TOKEN="<access_token_from_response>"
```

---

### 2. Customer Login

```bash
curl -X POST "$BASE_URL/auth/customer/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePass123!"
  }'
```

**Output:** Same as signup response

---

### 3. Customer OAuth2 Token (Form Data)

```bash
curl -X POST "$BASE_URL/auth/customer/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=john@example.com&password=SecurePass123!"
```

---

## Admin Authentication

### 1. Admin Sign Up

```bash
curl -X POST "$BASE_URL/auth/admin/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jane Admin",
    "email": "admin@example.com",
    "password": "AdminPass123!",
    "role": "STAFF"
  }'
```

**Output:**
```json
{
  "id": "660e8400-e39b-41d4-a716-446655440000",
  "name": "Jane Admin",
  "email": "admin@example.com",
  "role": "STAFF",
  "is_active": true
}
```

---

### 2. Admin Login

```bash
curl -X POST "$BASE_URL/auth/admin/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "AdminPass123!"
  }'
```

**Output:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "660e8400-e39b-41d4-a716-446655440000",
    "email": "admin@example.com",
    "name": "Jane Admin",
    "role": "STAFF",
    "is_active": true
  }
}
```

**Store the token:**
```bash
ADMIN_TOKEN="<access_token_from_response>"
```

---

### 3. Get Admin Profile

```bash
curl -X GET "$BASE_URL/admin/me" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Output:**
```json
{
  "id": "660e8400-e39b-41d4-a716-446655440000",
  "email": "admin@example.com",
  "name": "Jane Admin",
  "role": "STAFF",
  "is_active": true
}
```

---

## Flight Search

### Search Available Flights

```bash
curl -X GET "$BASE_URL/flights/search?origin=YGN&destination=BKK&departure_date=2026-03-01"
```

**Output:**
```json
[
  {
    "id": "flight_001",
    "airline_code": "TG",
    "flight_number": "TG101",
    "origin": "YGN",
    "destination": "BKK",
    "departure_time": "2026-03-01T15:00:00",
    "arrival_time": "2026-03-01T17:00:00",
    "base_price_usd": 150.00,
    "override_price_usd": null,
    "final_price_usd": 150.00,
    "exchange_rate": 2100.00,
    "final_price_mmk": 315000.00,
    "duration_minutes": 120,
    "stops": 0
  },
  {
    "id": "flight_002",
    "airline_code": "FD",
    "flight_number": "FD234",
    "origin": "YGN",
    "destination": "BKK",
    "departure_time": "2026-03-01T18:30:00",
    "arrival_time": "2026-03-01T20:00:00",
    "base_price_usd": 120.00,
    "override_price_usd": 140.00,
    "final_price_usd": 140.00,
    "exchange_rate": 2100.00,
    "final_price_mmk": 294000.00,
    "duration_minutes": 90,
    "stops": 0
  }
]
```

---

## Booking Operations

### 1. Create a Booking

```bash
curl -X POST "$BASE_URL/bookings" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CUSTOMER_TOKEN" \
  -d '{
    "airline_code": "TG",
    "flight_number": "TG101",
    "origin": "YGN",
    "destination": "BKK",
    "departure_time": "2026-03-01T15:00:00",
    "arrival_time": "2026-03-01T17:00:00",
    "final_price_usd": 150.00,
    "final_price_mmk": 315000.00
  }'
```

**Output:**
```json
{
  "booking_id": "770e8400-e49b-41d4-a716-446655440000",
  "airline_code": "TG",
  "flight_number": "TG101",
  "origin": "YGN",
  "destination": "BKK",
  "departure_time": "2026-03-01T15:00:00",
  "arrival_time": "2026-03-01T17:00:00",
  "final_price_usd": 150.00,
  "status": "PROCESSING"
}
```

**Store the booking ID:**
```bash
BOOKING_ID="770e8400-e49b-41d4-a716-446655440000"
```

---

### 2. List Customer's Bookings

```bash
curl -X GET "$BASE_URL/bookings/me" \
  -H "Authorization: Bearer $CUSTOMER_TOKEN"
```

**Output:**
```json
[
  {
    "booking_id": "770e8400-e49b-41d4-a716-446655440000",
    "airline_code": "TG",
    "flight_number": "TG101",
    "origin": "YGN",
    "destination": "BKK",
    "departure_date": "2026-03-01",
    "departure_time": "2026-03-01T15:00:00",
    "arrival_time": "2026-03-01T17:00:00",
    "final_price_usd": 150.00,
    "final_price_mmk": 315000.00,
    "status": "PROCESSING"
  }
]
```

---

### 3. Get Booking Details

```bash
curl -X GET "$BASE_URL/bookings/$BOOKING_ID" \
  -H "Authorization: Bearer $CUSTOMER_TOKEN"
```

**Output:**
```json
{
  "booking_id": "770e8400-e49b-41d4-a716-446655440000",
  "airline_code": "TG",
  "flight_number": "TG101",
  "origin": "YGN",
  "destination": "BKK",
  "departure_date": "2026-03-01",
  "departure_time": "2026-03-01T15:00:00",
  "arrival_time": "2026-03-01T17:00:00",
  "final_price_usd": 150.00,
  "final_price_mmk": 315000.00,
  "status": "PROCESSING"
}
```

---

## Admin Flight Price Overrides

### 1. Create Price Override

```bash
curl -X POST "$BASE_URL/admin/overrides" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "flight_number": "TG101",
    "origin": "YGN",
    "destination": "BKK",
    "override_price_usd": 180.00
  }'
```

**Output:**
```json
{
  "id": "880e8400-e59b-41d4-a716-446655440000",
  "flight_number": "TG101",
  "origin": "YGN",
  "destination": "BKK",
  "override_price_usd": 180.00,
  "created_at": "2026-02-16T10:30:00"
}
```

**Store the override ID:**
```bash
OVERRIDE_ID="880e8400-e59b-41d4-a716-446655440000"
```

---

### 2. List All Overrides

```bash
curl -X GET "$BASE_URL/admin/overrides" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Output:**
```json
[
  {
    "id": "880e8400-e59b-41d4-a716-446655440000",
    "flight_number": "TG101",
    "origin": "YGN",
    "destination": "BKK",
    "override_price_usd": 180.00,
    "created_at": "2026-02-16T10:30:00"
  }
]
```

---

### 3. Update Override Price

```bash
curl -X PUT "$BASE_URL/admin/overrides/$OVERRIDE_ID" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "override_price_usd": 175.00
  }'
```

**Output:**
```json
{
  "id": "880e8400-e59b-41d4-a716-446655440000",
  "flight_number": "TG101",
  "origin": "YGN",
  "destination": "BKK",
  "override_price_usd": 175.00,
  "created_at": "2026-02-16T10:30:00"
}
```

---

### 4. Delete Override

```bash
curl -X DELETE "$BASE_URL/admin/overrides/$OVERRIDE_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Output:**
```json
{
  "message": "Override deleted successfully"
}
```

---

### 5. List All Bookings (Admin View)

```bash
curl -X GET "$BASE_URL/admin/bookings" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Output:**
```json
[
  {
    "booking_id": "770e8400-e49b-41d4-a716-446655440000",
    "customer_id": "550e8400-e29b-41d4-a716-446655440000",
    "airline_code": "TG",
    "flight_number": "TG101",
    "origin": "YGN",
    "destination": "BKK",
    "departure_date": "2026-03-01",
    "departure_time": "2026-03-01T15:00:00",
    "arrival_time": "2026-03-01T17:00:00",
    "final_price_usd": 150.00,
    "status": "PROCESSING",
    "created_at": "2026-02-16T09:00:00"
  }
]
```

---

## Error Examples

### Invalid Credentials

```bash
curl -X POST "$BASE_URL/auth/customer/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "WrongPassword"
  }'
```

**Response (401):**
```json
{
  "detail": "Invalid credentials"
}
```

---

### Missing Authentication Header

```bash
curl -X GET "$BASE_URL/bookings/me"
```

**Response (403):**
```json
{
  "detail": "Not authenticated"
}
```

---

### Duplicate Email

```bash
curl -X POST "$BASE_URL/auth/customer/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePass123!",
    "full_name": "John Doe",
    "phone": "+959123456789"
  }'
```

**Response (400):**
```json
{
  "detail": "Email already registered"
}
```

---

### Validation Error

```bash
curl -X POST "$BASE_URL/auth/customer/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "invalid-email",
    "password": "pass",
    "full_name": "John Doe",
    "phone": "+959123456789"
  }'
```

**Response (422):**
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "email"],
      "msg": "Invalid email"
    }
  ]
}
```

---

## Tips for Testing

### Using jq for Pretty Output
```bash
curl -s -X GET "$BASE_URL/flights/search?origin=YGN&destination=BKK&departure_date=2026-03-01" | jq '.'
```

### Saving Response to File
```bash
curl -X GET "$BASE_URL/flights/search?origin=YGN&destination=BKK&departure_date=2026-03-01" \
  > response.json
```

### Adding Verbose Output
```bash
curl -v -X GET "$BASE_URL/health"
```

### Testing with Headers
```bash
curl -i -X POST "$BASE_URL/auth/customer/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "john@example.com", "password": "SecurePass123!"}'
```

---

## Postman Collection Import

Create a `postman_collection.json` file with the examples above for easier testing in Postman or Insomnia.

---

## Notes
- Replace `$CUSTOMER_TOKEN`, `$ADMIN_TOKEN`, `$BOOKING_ID`, `$OVERRIDE_ID` with actual values
- All POST/PUT requests require `Content-Type: application/json`
- Authentication endpoints don't require Bearer token
- Dates must be in YYYY-MM-DD format
- Timestamps must be in ISO 8601 format
