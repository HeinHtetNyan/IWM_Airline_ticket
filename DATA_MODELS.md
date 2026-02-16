# Data Models Reference

## Overview

This document describes the database models and their relationships in the IWM Airline Ticket Booking System.

---

## User Models

### AdminUser (admin_user model)

Represents an admin/staff member of the system.

**Database Table:** `admin_user`

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique identifier |
| email | String(255) | UNIQUE, NOT NULL | Email address |
| password_hash | String | NOT NULL | Bcrypt hashed password |
| name | String(255) | NOT NULL | Admin's full name |
| role | String(50) | NOT NULL | Role: STAFF, SUPER_ADMIN |
| is_active | Boolean | DEFAULT: True | Account active status |
| created_at | DateTime | DEFAULT: Now | Creation timestamp |
| updated_at | DateTime | DEFAULT: Now | Last update timestamp |

**Relationships:**
- One-to-Many with FlightOverride

**Indexes:**
- `email` (unique)

**Example:**
```python
{
  "id": "660e8400-e39b-41d4-a716-446655440000",
  "email": "admin@example.com",
  "name": "Jane Admin",
  "role": "STAFF",
  "is_active": True,
  "created_at": "2026-02-16T08:00:00",
  "updated_at": "2026-02-16T08:00:00"
}
```

---

### CustomerUser (customer_user model)

Represents a customer who can book flights.

**Database Table:** `customer_user`

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique identifier |
| email | String(255) | UNIQUE, NOT NULL | Email address (lowercase) |
| password_hash | String | NOT NULL | Bcrypt hashed password |
| full_name | String(255) | NOT NULL | Customer's full name |
| phone | String(20) | NOT NULL | Contact phone number |
| is_verified | Boolean | DEFAULT: False | Email verification status |
| is_active | Boolean | DEFAULT: True | Account active status |
| created_at | DateTime | DEFAULT: Now | Creation timestamp |
| updated_at | DateTime | DEFAULT: Now | Last update timestamp |

**Relationships:**
- One-to-Many with Booking

**Indexes:**
- `email` (unique)

**Example:**
```python
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "john@example.com",
  "full_name": "John Doe",
  "phone": "+959123456789",
  "is_verified": False,
  "is_active": True,
  "created_at": "2026-02-16T08:00:00",
  "updated_at": "2026-02-16T08:00:00"
}
```

---

## Booking Model

### Booking

Represents a flight booking made by a customer.

**Database Table:** `booking`

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique booking ID |
| customer_id | UUID | FOREIGN KEY | Reference to CustomerUser.id |
| airline_code | String(5) | NOT NULL | Airline IATA code (e.g., TG, FD) |
| flight_number | String(10) | NOT NULL | Flight number |
| origin | String(3) | NOT NULL | Departure airport code (IATA) |
| destination | String(3) | NOT NULL | Arrival airport code (IATA) |
| departure_date | Date | NOT NULL | Date of departure |
| departure_time | DateTime | NOT NULL | Departure time (ISO 8601) |
| arrival_time | DateTime | NOT NULL | Arrival time (ISO 8601) |
| final_price_usd | Numeric(10,2) | NOT NULL | Final price in USD |
| final_price_mmk | Numeric(15,2) | NOT NULL | Final price in Myanmar Kyat |
| status | String(20) | DEFAULT: PROCESSING | Booking status |
| created_at | DateTime | DEFAULT: Now | Creation timestamp |
| updated_at | DateTime | DEFAULT: Now | Last update timestamp |

**Relationships:**
- Many-to-One with CustomerUser

**Indexes:**
- `customer_id`
- `created_at`
- `status`
- `(airline_code, flight_number, departure_date)`

**Status Values:**
- `PROCESSING` - Initial status, awaiting confirmation
- `CONFIRMED` - Booking confirmed
- `CANCELLED` - Booking has been cancelled

**Example:**
```python
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
  "created_at": "2026-02-16T09:00:00",
  "updated_at": "2026-02-16T09:00:00"
}
```

---

## Flight Related Models

### FlightOverride

Represents an admin price override for a specific flight route.

**Database Table:** `flight_override`

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | String(50) | PRIMARY KEY | Unique override ID |
| flight_number | String(10) | NOT NULL | Flight number |
| origin | String(3) | NOT NULL | Departure airport code |
| destination | String(3) | NOT NULL | Arrival airport code |
| override_price_usd | Numeric(10,2) | NOT NULL | Override price in USD |
| admin_id | UUID | FOREIGN KEY | Reference to AdminUser.id |
| is_active | Boolean | DEFAULT: True | Override active status |
| created_at | DateTime | DEFAULT: Now | Creation timestamp |
| updated_at | DateTime | DEFAULT: Now | Last update timestamp |

**Relationships:**
- Many-to-One with AdminUser

**Indexes:**
- `(flight_number, origin, destination)`
- `created_at`

**Example:**
```python
{
  "id": "880e8400-e59b-41d4-a716-446655440000",
  "flight_number": "TG101",
  "origin": "YGN",
  "destination": "BKK",
  "override_price_usd": 180.00,
  "admin_id": "660e8400-e39b-41d4-a716-446655440000",
  "is_active": True,
  "created_at": "2026-02-16T10:30:00",
  "updated_at": "2026-02-16T10:30:00"
}
```

---

### ExchangeRate

Stores exchange rate information for currency conversion.

**Database Table:** `exchange_rate`

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique identifier |
| from_currency | String(3) | NOT NULL | Source currency code (e.g., USD) |
| to_currency | String(3) | NOT NULL | Target currency code (e.g., MMK) |
| rate | Numeric(12,4) | NOT NULL | Exchange rate |
| effective_date | Date | NOT NULL | Date the rate is effective |
| source | String(100) | Optional | Source of the exchange rate |
| created_at | DateTime | DEFAULT: Now | Creation timestamp |
| updated_at | DateTime | DEFAULT: Now | Last update timestamp |

**Indexes:**
- `(from_currency, to_currency, effective_date)`
- `effective_date`

**Example:**
```python
{
  "id": "990e8400-e69b-41d4-a716-446655440000",
  "from_currency": "USD",
  "to_currency": "MMK",
  "rate": 2100.00,
  "effective_date": "2026-02-16",
  "source": "Central Bank of Myanmar",
  "created_at": "2026-02-16T00:00:00",
  "updated_at": "2026-02-16T00:00:00"
}
```

---

## Entity Relationship Diagram

```
┌─────────────────────┐
│   CustomerUser      │
├─────────────────────┤
│ id (PK)             │
│ email (UNIQUE)      │
│ password_hash       │
│ full_name           │
│ phone               │
│ is_verified         │
│ is_active           │
│ created_at          │
│ updated_at          │
└────────┬────────────┘
         │
         │ (1:M)
         │
         ▼
┌─────────────────────┐
│     Booking         │
├─────────────────────┤
│ id (PK)             │
│ customer_id (FK)    │◄────┐
│ airline_code        │     │
│ flight_number       │     │
│ origin              │     │
│ destination         │     │
│ departure_date      │     │
│ departure_time      │     │
│ arrival_time        │     │
│ final_price_usd     │     │
│ final_price_mmk     │     │
│ status              │     │
│ created_at          │     │
│ updated_at          │     │
└─────────────────────┘     │
                            │
                            │ References
┌─────────────────────┐     │
│    AdminUser        │     │
├─────────────────────┤     │
│ id (PK)             │─────┘
│ email (UNIQUE)      │
│ password_hash       │
│ name                │
│ role                │
│ is_active           │
│ created_at          │
│ updated_at          │
└────────┬────────────┘
         │
         │ (1:M)
         │
         ▼
┌──────────────────────┐
│  FlightOverride      │
├──────────────────────┤
│ id (PK)              │
│ flight_number        │
│ origin               │
│ destination          │
│ override_price_usd   │
│ admin_id (FK)        │
│ is_active            │
│ created_at           │
│ updated_at           │
└──────────────────────┘

┌──────────────────────┐
│  ExchangeRate        │
├──────────────────────┤
│ id (PK)              │
│ from_currency        │
│ to_currency          │
│ rate                 │
│ effective_date       │
│ source               │
│ created_at           │
│ updated_at           │
└──────────────────────┘
```

---

## Schema Creation Order

When setting up the database, tables should be created in this order:

1. **AdminUser** - No dependencies
2. **CustomerUser** - No dependencies
3. **Booking** - Depends on CustomerUser
4. **FlightOverride** - Depends on AdminUser
5. **ExchangeRate** - No dependencies

---

## Key Constraints & Validations

### CustomerUser Constraints
- **Email**: Must be unique, contain @ and ., stored in lowercase
- **Password**: Max 72 bytes (bcrypt limit)
- **Phone**: International format recommended

### AdminUser Constraints
- **Email**: Must be unique, contain @ and .
- **Role**: Must be one of (STAFF, SUPER_ADMIN)
- **Password**: Max 72 bytes (bcrypt limit)

### Booking Constraints
- **Customer**: Must exist in CustomerUser table
- **Status**: Must be one of (PROCESSING, CONFIRMED, CANCELLED)
- **Dates**: departure_date must be ≤ departure_time date
- **Prices**: Must be positive numbers

### FlightOverride Constraints
- **Admin**: Must exist in AdminUser table
- **Flight Key**: Combination of (flight_number, origin, destination)
- **Price**: Must be positive number
- **is_active**: Used for soft deletes

### ExchangeRate Constraints
- **Currencies**: ISO 4217 3-letter codes (e.g., USD, MMK, THB)
- **Rate**: Positive decimal number
- **Effective Date**: Usually today or future date

---

## Query Examples

### Get Customer's Total Spending
```python
SELECT 
  customer_id,
  SUM(final_price_usd) as total_usd,
  SUM(final_price_mmk) as total_mmk
FROM booking
WHERE status != 'CANCELLED'
GROUP BY customer_id
```

### Find Popular Routes
```python
SELECT 
  origin,
  destination,
  COUNT(*) as booking_count
FROM booking
WHERE status != 'CANCELLED'
GROUP BY origin, destination
ORDER BY booking_count DESC
```

### Get Active Price Overrides
```python
SELECT *
FROM flight_override
WHERE is_active = True
ORDER BY created_at DESC
```

### Check Customer's Recent Bookings
```python
SELECT *
FROM booking
WHERE customer_id = ?
ORDER BY created_at DESC
LIMIT 10
```

---

## Notes

- All IDs (except override_id) use UUID version 4
- Timestamps use UTC timezone
- Email addresses are normalized to lowercase
- Passwords are hashed using bcrypt with cost factor of 12
- Foreign key constraints should be enforced at database level
- Regular backups are recommended, especially before price updates
