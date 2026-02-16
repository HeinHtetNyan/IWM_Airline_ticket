# API Quick Reference Guide

## Base URL
```
http://localhost:8000/api
```

## Authentication
Include token in header: `Authorization: Bearer <access_token>`

---

## Health Check
```
GET /health
```
✅ No auth required

---

## Customer Auth

### Sign Up
```
POST /auth/customer/signup
{
  "email": "user@example.com",
  "password": "pass123",
  "full_name": "John Doe",
  "phone": "+959123456789"
}
→ Returns: access_token + user details
```

### Login
```
POST /auth/customer/login
{
  "email": "user@example.com",
  "password": "pass123"
}
→ Returns: access_token + user details
```

### OAuth2 Token
```
POST /auth/customer/token
Content-Type: application/x-www-form-urlencoded
username=user@example.com&password=pass123
→ Returns: access_token + user details
```

---

## Admin Auth

### Admin Sign Up
```
POST /auth/admin/signup
{
  "name": "Admin Name",
  "email": "admin@example.com",
  "password": "pass123",
  "role": "STAFF"
}
→ Returns: Admin details
```

### Admin Login
```
POST /auth/admin/login
{
  "email": "admin@example.com",
  "password": "pass123"
}
→ Returns: access_token + admin details
```

### Get Admin Profile
```
GET /admin/me
🔒 Requires: Admin token
→ Returns: Admin details
```

---

## Flight Search

### Search Flights
```
GET /flights/search?origin=YGN&destination=BKK&departure_date=2026-03-01
✅ No auth required
→ Returns: [flights with pricing]
```

---

## Bookings

### Create Booking
```
POST /bookings
🔒 Requires: Customer token
{
  "airline_code": "TG",
  "flight_number": "TG101",
  "origin": "YGN",
  "destination": "BKK",
  "departure_time": "2026-03-01T15:00:00",
  "arrival_time": "2026-03-01T17:00:00",
  "final_price_usd": 150.00,
  "final_price_mmk": 315000.00
}
→ Returns: booking_id + status
```

### List My Bookings
```
GET /bookings/me
🔒 Requires: Customer token
→ Returns: [customer's bookings]
```

### Get Booking Details
```
GET /bookings/{booking_id}
🔒 Requires: Customer token
→ Returns: Booking details
```

---

## Admin Management

### Create Price Override
```
POST /admin/overrides
🔒 Requires: Admin token
{
  "flight_number": "TG101",
  "origin": "YGN",
  "destination": "BKK",
  "override_price_usd": 180.00
}
→ Returns: Override details
```

### List All Overrides
```
GET /admin/overrides
🔒 Requires: Admin token
→ Returns: [price overrides]
```

### Update Override
```
PUT /admin/overrides/{override_id}
🔒 Requires: Admin token
{
  "override_price_usd": 175.00
}
→ Returns: Updated override
```

### Delete Override
```
DELETE /admin/overrides/{override_id}
🔒 Requires: Admin token
→ Returns: Success message
```

### List All Bookings (Admin)
```
GET /admin/bookings
🔒 Requires: Admin token
→ Returns: [all bookings with timestamps]
```

---

## Status Codes
- **200** - OK / Success
- **201** - Created
- **400** - Bad Request (e.g., duplicate email)
- **401** - Unauthorized (invalid/missing token)
- **403** - Forbidden (inactive user or insufficient permissions)
- **404** - Not Found
- **422** - Validation Error
- **500** - Internal Server Error

---

## Key Field Names
| Context | Status Values |
|---------|---------------|
| Bookings | PROCESSING, CONFIRMED, CANCELLED |
| Admins | STAFF, SUPER_ADMIN |
| Customers | N/A (boolean flags: is_active, is_verified) |

---

## Notes
- All dates/times: ISO 8601 UTC format
- Email validation: must contain @ and .
- Password limit: 72 bytes
- Currency: USD and MMK supported
- Token type: Bearer JWT
