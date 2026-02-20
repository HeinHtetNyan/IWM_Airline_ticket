# Full Example Requests & Responses

Notes:
- Replace `http://localhost:8000` with your server base URL.
- Replace tokens and IDs (`<TOKEN>`, `<BOOKING_ID>`, `<OVERRIDE_ID>`) with real values.

1) Customer signup (create user)

Request:

```bash
curl -X POST "http://localhost:8000/api/auth/customer/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@example.com",
    "password": "secret123",
    "full_name": "Alice Example",
    "phone": "+959123456789"
  }'
```

Response (201):

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {"id":"1","email":"alice@example.com","full_name":"Alice Example","phone":"+959123456789"}
}
```

2) Customer login (get token)

Request:

```bash
curl -X POST "http://localhost:8000/api/auth/customer/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"secret123"}'
```

Response:

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {"id":"1","email":"alice@example.com","full_name":"Alice Example","phone":"+959123456789"}
}
```

3) Flight search (one-way)

Request:

```bash
curl -G "http://localhost:8000/api/flights/search" \
  --data-urlencode "origin=RGN" \
  --data-urlencode "destination=KUL" \
  --data-urlencode "departure_date=2026-03-10" \
  --data-urlencode "adults=1"
```

Response (example):

```json
[
  {
    "id": "bundle_abc123",
    "origin": "RGN",
    "destination": "KUL",
    "departure_date": "2026-03-10",
    "final_price_usd": 120.0,
    "final_price_mmk": 60000.0,
    "segments": [/* ... */]
  }
]
```

4) Create booking (customer)

Request (authenticated):

```bash
curl -X POST "http://localhost:8000/api/bookings" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{
    "type": "ONE_WAY",
    "adults": 1,
    "bundle_key": "bundle_abc123",
    "flight_snapshot": {"final_price_usd": 120.0, "final_price_mmk": 60000.0, "segments": []},
    "final_price_usd": 120.0,
    "final_price_mmk": 60000.0
  }'
```

Response:

```json
{
  "booking_id": "550e8400-e29b-41d4-a716-446655440000",
  "booking_code": null,
  "type": "ONE_WAY",
  "adults": 1,
  "bundle_key": "bundle_abc123",
  "flight_snapshot": {"final_price_usd":120.0,"final_price_mmk":60000.0},
  "final_price_usd": 120.0,
  "final_price_mmk": 60000.0,
  "status": "PROCESSING",
  "payment_status": "PENDING",
  "created_at": "2026-02-20T12:34:56.789Z",
  "passengers": null
}
```

5) Add passengers to booking (customer)

Request:

```bash
curl -X POST "http://localhost:8000/api/bookings/<BOOKING_ID>/passengers" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{
    "passengers": [
      {
        "given_name":"Alice",
        "last_name":"Example",
        "passport_number":"N1234567",
        "gender":"FEMALE",
        "date_of_birth":"1990-01-01",
        "nationality":"MM",
        "phone_number":"+959123456789"
      }
    ]
  }'
```

Response:

```json
[
  {
    "id": "c0a8012e-0000-0000-0000-000000000001",
    "booking_id": "550e8400-e29b-41d4-a716-446655440000",
    "given_name":"Alice",
    "last_name":"Example",
    "passport_number":"N1234567",
    "gender":"FEMALE",
    "date_of_birth":"1990-01-01",
    "nationality":"MM",
    "phone_number":"+959123456789",
    "created_at":"2026-02-20T12:35:10.123Z"
  }
]
```

6) Get my bookings (customer)

Request:

```bash
curl -X GET "http://localhost:8000/api/bookings/me" \
  -H "Authorization: Bearer <TOKEN>"
```

Response (example):

```json
[
  {
    "booking_id":"550e8400-e29b-41d4-a716-446655440000",
    "booking_code":"IWM-2026-000001",
    "type":"ONE_WAY",
    "adults":1,
    "bundle_key":"bundle_abc123",
    "flight_snapshot":{/*...*/},
    "final_price_usd":120.0,
    "final_price_mmk":60000.0,
    "status":"PROCESSING",
    "payment_status":"PENDING",
    "created_at":"2026-02-20T12:34:56.789Z",
    "passengers":null
  }
]
```

7) Create or update contact (customer)

Request:

```bash
curl -X POST "http://localhost:8000/api/contact" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{
    "given_name":"Alice",
    "last_name":"Example",
    "email":"alice@example.com",
    "country_of_residence":"MM",
    "phone_number":"+959123456789"
  }'
```

Response:

```json
{
  "id":"c0a8012e-0000-0000-0000-000000000002",
  "given_name":"Alice",
  "last_name":"Example",
  "email":"alice@example.com",
  "country_of_residence":"MM",
  "phone_number":"+959123456789",
  "created_at":"2026-02-20T12:40:00.000Z"
}
```

8) Admin: get dashboard (admin auth)

Request:

```bash
curl -X GET "http://localhost:8000/api/admin/dashboard" \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

Response (example):

```json
{
  "financial": {"total_paid_bookings": 42, "total_revenue_usd": 5040.0, "total_revenue_mmk": 2520000.0},
  "operational": {"processing": 3, "paid_processing":1, "confirmed":10, "completed":25, "cancelled":3},
  "today": {"bookings_today": 5, "revenue_today_usd": 600.0, "revenue_today_mmk": 300000.0}
}
```

9) Admin: update booking payment status

Request:

```bash
curl -X PUT "http://localhost:8000/api/admin/bookings/<BOOKING_ID>/payment-status" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -d '{"payment_status":"PAID"}'
```

Response:

```json
{"booking_id":"550e8400-e29b-41d4-a716-446655440000","payment_status":"PAID","updated_by":"admin@example.com"}
```

10) Admin: upload ticket

Request:

```bash
curl -X PUT "http://localhost:8000/api/admin/bookings/<BOOKING_ID>/upload-ticket" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -d '{"ticket_file_url":"https://storage.example.com/tickets/550e84.pdf"}'
```

Response:

```json
{
  "booking_id":"550e8400-e29b-41d4-a716-446655440000",
  "ticket_file_url":"https://storage.example.com/tickets/550e84.pdf",
  "ticket_uploaded_at":"2026-02-20T13:00:00.000Z",
  "status":"CONFIRMED",
  "uploaded_by":"admin@example.com"
}
```

11) Admin: booking audit (super admin)

Request:

```bash
curl -X GET "http://localhost:8000/api/admin/bookings/<BOOKING_ID>/audit" \
  -H "Authorization: Bearer <SUPER_ADMIN_TOKEN>"
```

Response (example):

```json
{
  "payment": {"status":"PAID","marked_at":"2026-02-20T12:50:00Z","marked_by":{"id":"...","email":"admin@example.com","name":"Admin"}},
  "status": {"current_status":"CONFIRMED","updated_at":"2026-02-20T13:00:00Z","updated_by":{"id":"...","email":"admin@example.com","name":"Admin"}},
  "ticket": {"uploaded_at":"2026-02-20T13:00:00Z","uploaded_by":{"id":"...","email":"admin@example.com","name":"Admin"}}
}
```

---

Notes & troubleshooting
- Validation errors return 400 with a `detail` message.
- Authentication failures return 401; role/permission failures return 403.

---

Documentation file: [docs/API.md](docs/API.md)
