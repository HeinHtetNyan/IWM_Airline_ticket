# API Documentation Index

Welcome to the IWM Airline Ticket Booking System API Documentation. This directory contains complete documentation for developers working with this API.

## 📚 Documentation Files

### 1. **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - Complete API Reference
The main comprehensive guide covering:
- Overview and base information
- Authentication mechanisms
- All endpoints with detailed descriptions
- Request/response examples
- Data models
- Error handling and status codes
- Example workflows

**Best for:** Full understanding of the API, development, and integration

---

### 2. **[API_QUICK_REFERENCE.md](API_QUICK_REFERENCE.md)** - Quick Lookup Guide
A condensed reference guide with:
- Quick endpoint listings
- Brief request/response formats
- Key status codes
- Authentication quick start
- One-page overview

**Best for:** Quick lookups, reminders, and copy-paste templates

---

### 3. **[API_EXAMPLES.md](API_EXAMPLES.md)** - Practical cURL Examples
Ready-to-use command examples including:
- All endpoints with sample cURL commands
- Expected output for each request
- Error response examples
- Token management
- Tips for testing with tools like jq and Postman

**Best for:** Testing the API from CLI, learning by example, Postman setup

---

### 4. **[DATA_MODELS.md](DATA_MODELS.md)** - Database Schema Reference
Complete data model documentation with:
- All database tables and fields
- Field types and constraints
- Relationships between models
- Entity relationship diagram
- Index information
- Query examples

**Best for:** Understanding data structure, writing queries, database design

---

## 🚀 Quick Start

### For First-Time Users

1. **Read:** [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - Sections: Overview, Base Information, Authentication
2. **Copy:** cURL example from [API_EXAMPLES.md](API_EXAMPLES.md) - Start with health check
3. **Test:** Run the example in your terminal
4. **Reference:** Use [API_QUICK_REFERENCE.md](API_QUICK_REFERENCE.md) as quick lookup

### For Integration

1. **Understand:** Data flow from [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - Workflows section
2. **Reference:** Exact endpoints from [API_QUICK_REFERENCE.md](API_QUICK_REFERENCE.md)
3. **Test:** Use [API_EXAMPLES.md](API_EXAMPLES.md) - cURL commands
4. **Model:** Check [DATA_MODELS.md](DATA_MODELS.md) - for request/response structures

### For Database Work

1. Check [DATA_MODELS.md](DATA_MODELS.md) - for schema and relationships
2. Reference API responses in [API_DOCUMENTATION.md](API_DOCUMENTATION.md) to understand data flow
3. Use query examples from [DATA_MODELS.md](DATA_MODELS.md)

---

## 📋 API Endpoint Summary

### Health & Status
| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/health` | ❌ | Check API status |

### Customer Authentication
| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/auth/customer/signup` | ❌ | Register new customer |
| POST | `/auth/customer/login` | ❌ | Customer login |
| POST | `/auth/customer/token` | ❌ | OAuth2 token endpoint |

### Admin Authentication
| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/auth/admin/signup` | ❌ | Register new admin |
| POST | `/auth/admin/login` | ❌ | Admin login |
| GET | `/admin/me` | ✅ Admin | Get admin profile |

### Flight Search
| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/flights/search` | ❌ | Search available flights |

### Customer Bookings
| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/bookings` | ✅ Customer | Create new booking |
| GET | `/bookings/me` | ✅ Customer | List customer's bookings |
| GET | `/bookings/{booking_id}` | ✅ Customer | Get booking details |

### Admin Management
| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/admin/overrides` | ✅ Admin | Create price override |
| GET | `/admin/overrides` | ✅ Admin | List all overrides |
| PUT | `/admin/overrides/{override_id}` | ✅ Admin | Update override price |
| DELETE | `/admin/overrides/{override_id}` | ✅ Admin | Delete override |
| GET | `/admin/bookings` | ✅ Admin | List all bookings |

**Legend:** ✅ = Required, ❌ = Not required

---

## 🔐 Authentication

The API uses **Bearer Token Authentication** (JWT).

### Getting a Token

**Customer:**
```bash
POST /auth/customer/login
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Admin:**
```bash
POST /auth/admin/login
{
  "email": "admin@example.com",
  "password": "password123"
}
```

### Using the Token

Include in all protected endpoints:
```bash
Authorization: Bearer <your_access_token>
```

See [API_EXAMPLES.md](API_EXAMPLES.md) for complete examples.

---

## 📱 Data Formats

### Date Format
- **Date:** `YYYY-MM-DD` (e.g., 2026-03-01)
- **DateTime:** ISO 8601 UTC (e.g., 2026-03-01T15:30:00)

### Currency
- **USD:** Decimal number (e.g., 150.00)
- **MMK:** Decimal number (e.g., 315000.00)
- **Exchange Rate:** Decimal number (e.g., 2100.00)

### Client Identification
- **User IDs:** UUID v4 (e.g., 550e8400-e29b-41d4-a716-446655440000)
- **Booking IDs:** UUID v4
- **Override IDs:** String

---

## ✅ Common Workflows

### Complete Customer Journey

1. **Sign Up**
   ```bash
   POST /auth/customer/signup
   ```
   Get: `access_token`

2. **Search Flights**
   ```bash
   GET /flights/search?origin=YGN&destination=BKK&departure_date=2026-03-01
   ```
   Get: List of available flights with prices

3. **Create Booking**
   ```bash
   POST /bookings
   Authorization: Bearer <token>
   ```
   Get: `booking_id` (status: PROCESSING)

4. **View Bookings**
   ```bash
   GET /bookings/me
   Authorization: Bearer <token>
   ```

### Admin Flight Management

1. **Admin Login**
   ```bash
   POST /auth/admin/login
   ```
   Get: `access_token`

2. **Create Price Override**
   ```bash
   POST /admin/overrides
   Authorization: Bearer <admin_token>
   ```

3. **View & Monitor**
   ```bash
   GET /admin/bookings
   Authorization: Bearer <admin_token>
   ```

Detailed workflows in [API_DOCUMENTATION.md](API_DOCUMENTATION.md#example-workflows).

---

## 🐛 Troubleshooting

### Common Issues

**401 Unauthorized**
- Token may be expired → Re-login for new token
- Wrong token type → Ensure using correct user type (customer vs admin)
- Missing Authorization header → Added `Authorization: Bearer <token>`

**403 Forbidden**
- User is inactive → Contact admin
- Insufficient permissions → Check user role matches endpoint

**422 Validation Error**
- Check request format matches documentation
- Validate field types (string vs number vs datetime)
- See [API_DOCUMENTATION.md](API_DOCUMENTATION.md#error-handling)

**400 Bad Request**
- Common: Duplicate email on signup
- Check field values are valid (email format, password length, etc.)

### Error Responses

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md#error-handling) for complete error reference.

---

## 🛠️ Development Tips

### Using cURL for Testing
See [API_EXAMPLES.md](API_EXAMPLES.md#tips-for-testing) for:
- jq JSON formatting
- Saving responses
- Verbose output
- Header inspection

### API Testing Tools
- **cURL:** Command-line, built-in
- **Postman:** GUI, collections, environment variables
- **Insomnia:** Modern API client with similar features
- **Thunder Client:** VS Code extension

### Setting Environment Variables
```bash
# Store these after login
export BASE_URL="http://localhost:8000/api"
export CUSTOMER_TOKEN="<your_token>"
export ADMIN_TOKEN="<your_admin_token>"
export BOOKING_ID="<obtained_from_booking>"
```

---

## 📖 Additional Resources

### API Framework
- **Framework:** FastAPI
- **Python Version:** 3.8+
- **Database:** SQLAlchemy ORM

### Architecture
- REST API principles
- Bearer token (JWT) authentication
- UUID based identifiers
- Decimal for financial data

### Related Files in Repository
- API Routes: `backend/app/api/`
- Database Models: `backend/app/models/`
- Schemas (Pydantic): `backend/app/schemas/`
- Authentication: `backend/app/auth/`
- Configuration: `backend/app/core/`

---

## 🔄 API Versioning

**Current Version:** 1.0  
**Base Path:** `/api`

Future versions may be available at `/api/v2`, etc.

---

## 📞 Support

For issues or questions:
1. Check relevant documentation file above
2. Review [API_EXAMPLES.md](API_EXAMPLES.md) for working examples
3. Verify [DATA_MODELS.md](DATA_MODELS.md) for data structure
4. Contact development team

---

## 📝 Documentation Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-16 | Initial documentation release |

---

## ✅ Checklist for New Developers

- [ ] Read this file (overview)
- [ ] Read [API_DOCUMENTATION.md](API_DOCUMENTATION.md) (full reference)
- [ ] Review [DATA_MODELS.md](DATA_MODELS.md) (data structure)
- [ ] Test health endpoint with cURL from [API_EXAMPLES.md](API_EXAMPLES.md)
- [ ] Test signup and login flow
- [ ] Test flight search
- [ ] Create a test booking
- [ ] Review error handling section
- [ ] Keep [API_QUICK_REFERENCE.md](API_QUICK_REFERENCE.md) handy

---

## 📄 File Structure

```
/
├── API_DOCUMENTATION.md      ← Complete reference (start here)
├── API_QUICK_REFERENCE.md    ← Quick lookup guide
├── API_EXAMPLES.md           ← cURL examples and testing
├── DATA_MODELS.md            ← Database schema reference
└── README.md                 ← This file (index)
```

---

**Last Updated:** February 16, 2026  
**Status:** Complete and Ready for Use
