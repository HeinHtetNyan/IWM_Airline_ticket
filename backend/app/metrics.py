"""
Prometheus metrics for the Airline Booking System
"""

from prometheus_client import Counter, Histogram, Gauge

# BUSINESS METRICS - Track what matters


bookings_created_total = Counter(
    "bookings_created_total", "Total number of bookings created"
)

searches_performed_total = Counter(
    "searches_performed_total", "Total number of flight searches"
)

users_registered_total = Counter(
    "users_registered_total", "Total number of user registrations"
)


# PERFORMANCE METRICS - Track speed


search_duration_seconds = Histogram(
    "search_duration_seconds",
    "Time spent searching for flights",
    buckets=[0.1, 0.5, 1, 2, 5, 10],  # 100ms, 500ms, 1s, 2s, 5s, 10s
)

booking_duration_seconds = Histogram(
    "booking_duration_seconds",
    "Time spent creating bookings",
    buckets=[0.1, 0.5, 1, 2, 5, 10],
)


# STATE METRICS - Track current status


active_users_gauge = Gauge("active_users_current", "Number of currently active users")
