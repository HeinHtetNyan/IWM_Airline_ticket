# IWM Airline Ticket Booking API Documentation

## Table of Contents
1. [Overview](#overview)
2. [Base Information](#base-information)
3. [Authentication](#authentication)
4. [API Endpoints](#api-endpoints)
   - [Health Check](#health-check)
   - [Customer Authentication](#customer-authentication)
   - [Admin Authentication](#admin-authentication)
   - [Flight Search](#flight-search)
   - [Bookings](#bookings)
   - [Admin Management](#admin-management)
5. [Data Models](#data-models)
6. [Error Handling](#error-handling)

---

## Overview

The IWM Airline Ticket Booking API is a FastAPI-based REST API that enables customers to search for flights, create bookings, and manage their reservations. It also provides admin functionality for managing flight pricing overrides and booking status updates.

**Key Features:**
- Customer registration and login
- Admin authentication and management
- Flight search with dynamic pricing
- Booking creation and management
- Flight price override management
- Multi-currency support (USD and MMK)

---

## Base Information

- **API Version:** 1.0
- **Base URL:** `http://localhost:8000/api` (or your deployment URL)
- **Content-Type:** `application/json`
- **Response Format:** JSON

---

## Authentication

The API uses Bearer token authentication for protected endpoints. After login or signup, you receive an access token that must be included in the `Authorization` header.

### Token Header Format
```
Authorization: Bearer <access_token>
```

### Token Structure
- **Token Type:** JWT (JSON Web Token)
- **Token Type Field:** "bearer"
- **Token Expiration:** Depends on server configuration
- **Roles:** CUSTOMER, ADMIN, STAFF, SUPER_ADMIN

---

## API Endpoints

### Health Check

#### GET `/health`
Check if the API is running.

**Authentication:** Not required

**Response:**
```json
{
  "status": "ok"
}
```

**Status Code:** 200

---

### Customer Authentication

#### POST `/auth/customer/signup`
Register a new customer account.

**Authentication:** Not required

**Request Body:**
```json
{
  "email": "customer@example.com",
  "password": "securePassword123",
  "full_name": "John Doe",
  "phone": "+959123456789"
}
```

**Request Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| email | string | Yes | Valid email address |
| password | string | Yes | Password (max 72 bytes) |
| full_name | string | Yes | Customer's full name |
| phone | string | Yes | Contact phone number |

**Response (Status 201):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "customer@example.com",
    "full_name": "John Doe",
    "phone": "+959123456789"
  }
}
```

**Error Responses:**
- **400:** Email already registered
- **422:** Invalid request format or validation error

---

#### POST `/auth/customer/login`
Login to an existing customer account.

**Authentication:** Not required

**Request Body:**
```json
{
  "email": "customer@example.com",
  "password": "securePassword123"
}
```

**Response (Status 200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "customer@example.com",
    "full_name": "John Doe",
    "phone": "+959123456789"
  }
}
```

**Error Responses:**
- **401:** Invalid credentials
- **403:** User is inactive
- **422:** Invalid request format

---

#### POST `/auth/customer/token`
Alternative token endpoint for OAuth2 form-data authentication.

**Authentication:** Not required

**Content-Type:** `application/x-www-form-urlencoded`

**Form Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| username | string | Yes | Email address |
| password | string | Yes | Password |

**Example Request:**
```
POST /auth/customer/token
Content-Type: application/x-www-form-urlencoded

username=customer@example.com&password=securePassword123
```

**Response (Status 200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "customer@example.com",
    "full_name": "John Doe",
    "phone": "+959123456789"
  }
}
```

**Error Responses:**
- **401:** Invalid credentials
- **403:** User is inactive

---

### Admin Authentication

#### POST `/auth/admin/signup`
Create a new admin account (requires admin credentials for certain roles).

**Authentication:** Not required (for initial setup)

**Request Body:**
```json
{
  "name": "Admin Name",
  "email": "admin@example.com",
  "password": "adminPassword123",
  "role": "STAFF"
}
```

**Request Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | Admin's full name |
| email | string | Yes | Valid email address |
| password | string | Yes | Password (max 72 bytes) |
| role | string | No | Role (STAFF, SUPER_ADMIN). Default: STAFF |

**Response (Status 201):**
```json
{
  "id": "660e8400-e39b-41d4-a716-446655440000",
  "name": "Admin Name",
  "email": "admin@example.com",
  "role": "STAFF",
  "is_active": true
}
```

**Error Responses:**
- **400:** Email already registered
- **422:** Invalid request format

---

#### POST `/auth/admin/login`
Login to an admin account.

**Authentication:** Not required

**Request Body:**
```json
{
  "email": "admin@example.com",
  "password": "adminPassword123"
}
```

**Response (Status 200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "660e8400-e39b-41d4-a716-446655440000",
    "email": "admin@example.com",
    "name": "Admin Name",
    "role": "STAFF",
    "is_active": true
  }
}
```

**Error Responses:**
- **401:** Invalid credentials
- **403:** User is inactive

---

### Flight Search

#### GET `/flights/search`
Search for available flights based on route and date.

**Authentication:** Not required

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| origin | string | Yes | Departure airport code (e.g., YGN) |
| destination | string | Yes | Arrival airport code (e.g., BKK) |
| departure_date | string | Yes | Departure date (YYYY-MM-DD format) |

**Example Request:**
```
GET /flights/search?origin=YGN&destination=BKK&departure_date=2026-03-01
```

**Response (Status 200):**
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
  }
]
```

**Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique flight identifier |
| airline_code | string | Airline IATA code |
| flight_number | string | Flight number |
| origin | string | Departure airport code |
| destination | string | Arrival airport code |
| departure_time | datetime | Departure time (ISO 8601) |
| arrival_time | datetime | Arrival time (ISO 8601) |
| base_price_usd | number | Base price in USD |
| override_price_usd | number | Admin-set override price (if any) |
| final_price_usd | number | Final price in USD (override or base) |
| exchange_rate | number | USD to MMK exchange rate |
| final_price_mmk | number | Final price in Myanmar Kyat |
| duration_minutes | number | Flight duration in minutes |
| stops | integer | Number of stops |

**Error Responses:**
- **422:** Missing or invalid query parameters

---

### Bookings

#### POST `/bookings`
Create a new booking for a customer.

**Authentication:** Required (Customer Bearer Token)

**Request Body:**
```json
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
```

**Request Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| airline_code | string | Yes | Airline code |
| flight_number | string | Yes | Flight number |
| origin | string | Yes | Departure airport code |
| destination | string | Yes | Arrival airport code |
| departure_time | string | Yes | Departure time (ISO 8601) |
| arrival_time | string | Yes | Arrival time (ISO 8601) |
| final_price_usd | number | Yes | Final price in USD |
| final_price_mmk | number | Yes | Final price in MMK |

**Response (Status 200):**
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

**Error Responses:**
- **401:** Invalid or missing token
- **422:** Invalid request format
- **403:** User is inactive

---

#### GET `/bookings/me`
Get list of all bookings for the current customer.

**Authentication:** Required (Customer Bearer Token)

**Response (Status 200):**
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

**Query Parameters:** None

**Error Responses:**
- **401:** Invalid or missing token
- **403:** User is inactive

---

#### GET `/bookings/{booking_id}`
Get details of a specific booking.

**Authentication:** Required (Customer Bearer Token)

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| booking_id | UUID | Booking ID |

**Example Request:**
```
GET /bookings/770e8400-e49b-41d4-a716-446655440000
```

**Response (Status 200):**
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

**Error Responses:**
- **401:** Invalid or missing token
- **403:** User is inactive or not authorized for this booking
- **404:** Booking not found

---

### Admin Management

#### GET `/admin/me`
Get current admin user information.

**Authentication:** Required (Admin Bearer Token)

**Response (Status 200):**
```json
{
  "id": "660e8400-e39b-41d4-a716-446655440000",
  "email": "admin@example.com",
  "name": "Admin Name",
  "role": "STAFF",
  "is_active": true
}
```

**Error Responses:**
- **401:** Invalid or missing admin token
- **403:** User is not an admin

---

#### POST `/admin/overrides`
Create a flight price override.

**Authentication:** Required (Admin Bearer Token)

**Request Body:**
```json
{
  "flight_number": "TG101",
  "origin": "YGN",
  "destination": "BKK",
  "override_price_usd": 180.00
}
```

**Request Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| flight_number | string | Yes | Flight number |
| origin | string | Yes | Departure airport code |
| destination | string | Yes | Arrival airport code |
| override_price_usd | number | Yes | Override price in USD |

**Response (Status 200):**
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

**Error Responses:**
- **401:** Invalid or missing admin token
- **403:** User is not an admin
- **422:** Invalid request format

---

#### GET `/admin/overrides`
List all flight price overrides.

**Authentication:** Required (Admin Bearer Token)

**Response (Status 200):**
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

**Error Responses:**
- **401:** Invalid or missing admin token
- **403:** User is not an admin

---

#### PUT `/admin/overrides/{override_id}`
Update a flight price override.

**Authentication:** Required (Admin Bearer Token)

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| override_id | string | Override ID |

**Request Body:**
```json
{
  "override_price_usd": 175.00
}
```

**Response (Status 200):**
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

**Error Responses:**
- **401:** Invalid or missing admin token
- **403:** User is not an admin
- **404:** Override not found
- **422:** Invalid request format

---

#### DELETE `/admin/overrides/{override_id}`
Delete a flight price override.

**Authentication:** Required (Admin Bearer Token)

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| override_id | string | Override ID |

**Example Request:**
```
DELETE /admin/overrides/880e8400-e59b-41d4-a716-446655440000
```

**Response (Status 200):**
```json
{
  "message": "Override deleted successfully"
}
```

**Error Responses:**
- **401:** Invalid or missing admin token
- **403:** User is not an admin
- **404:** Override not found

---

#### GET `/admin/bookings`
List all bookings (admin view).

**Authentication:** Required (Admin Bearer Token)

**Response (Status 200):**
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

**Error Responses:**
- **401:** Invalid or missing admin token
- **403:** User is not an admin

---

## Data Models

### User Objects

#### CustomerUser
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "customer@example.com",
  "full_name": "John Doe",
  "phone": "+959123456789",
  "is_verified": false,
  "is_active": true,
  "created_at": "2026-02-16T08:00:00"
}
```

#### AdminUser
```json
{
  "id": "660e8400-e39b-41d4-a716-446655440000",
  "email": "admin@example.com",
  "name": "Admin Name",
  "role": "STAFF",
  "is_active": true,
  "created_at": "2026-02-16T08:00:00"
}
```

### Booking Object
```json
{
  "id": "770e8400-e49b-41d4-a716-446655440000",
  "customer_id": "550e8400-e29b-41d4-a716-446655440000",
  "airline_code": "TG",
  "flight_number": "TG101",
  "origin": "YGN",
  "destination": "BKK",
  "departure_date": "2026-03-01",
  "departure_time": "2026-03-01T15:00:00",
  "arrival_time": "2026-03-01T17:00:00",
  "final_price_usd": 150.00,
  "final_price_mmk": 315000.00,
  "status": "PROCESSING",
  "created_at": "2026-02-16T09:00:00"
}
```

**Booking Status Values:**
- `PROCESSING` - Booking is being processed
- `CONFIRMED` - Booking is confirmed
- `CANCELLED` - Booking has been cancelled

### FlightOverride Object
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

---

## Error Handling

### Standard Error Response Format

All error responses follow this format:

```json
{
  "detail": "Error message or list of validation errors"
}
```

### HTTP Status Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Client error (e.g., duplicate email) |
| 401 | Unauthorized | Invalid/missing token or invalid credentials |
| 403 | Forbidden | User is inactive or insufficient permissions |
| 404 | Not Found | Resource not found |
| 422 | Unprocessable Entity | Validation error in request body or query params |
| 500 | Internal Server Error | Server error |

### Common Error Scenarios

**Invalid Email Format:**
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

**Password Too Long:**
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "password"],
      "msg": "Password too long (max 72 bytes)"
    }
  ]
}
```

**Missing Authentication:**
```json
{
  "detail": "Not authenticated"
}
```

**Expired or Invalid Token:**
```json
{
  "detail": "Could not validate credentials"
}
```

---

## Example Workflows

### Customer Booking Flow

1. **Sign Up**
   ```bash
   POST /auth/customer/signup
   ```

2. **Search Flights**
   ```bash
   GET /flights/search?origin=YGN&destination=BKK&departure_date=2026-03-01
   ```

3. **Create Booking**
   ```bash
   POST /bookings
   Authorization: Bearer <customer_token>
   ```

4. **View Bookings**
   ```bash
   GET /bookings/me
   Authorization: Bearer <customer_token>
   ```

### Admin Override Flow

1. **Login as Admin**
   ```bash
   POST /auth/admin/login
   ```

2. **Create Price Override**
   ```bash
   POST /admin/overrides
   Authorization: Bearer <admin_token>
   ```

3. **View All Overrides**
   ```bash
   GET /admin/overrides
   Authorization: Bearer <admin_token>
   ```

4. **Update Override**
   ```bash
   PUT /admin/overrides/{override_id}
   Authorization: Bearer <admin_token>
   ```

---

## Requirements & Notes

- All timestamps are in UTC (ISO 8601 format)
- All currency values are decimal numbers
- Email addresses are case-insensitive (stored in lowercase)
- UUIDs are used for user and booking IDs
- Passwords are hashed using bcrypt (max 72 bytes)
- Exchange rates are applied dynamically during flight searches
- Authentication tokens expire after server-configured duration

---

## Support & Contact

For issues or questions about the API, please contact the development team.

**Last Updated:** February 16, 2026
