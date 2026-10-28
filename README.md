# Hotel Booking Service

Hotel Booking Service is an online hotel booking management system built with Django REST Framework.
Guests can register, browse rooms, check availability, make and cancel bookings, and pay through **Stripe**.
Hotel staff receive **Telegram notifications** about new bookings, cancellations, no-shows, and successful payments.

The system is fully usable through a browsable API (no frontend is included). Interactive documentation is available via Swagger.

## Features

- **Users:** registration, JWT authentication, profile management (email is the login).
- **Rooms:** CRUD for rooms, filtering by type and capacity, availability calendar for a date range.
- **Bookings:** create, cancel, check-in, check-out; non-admins see only their own bookings.
- **Payments (Stripe):** Checkout sessions for bookings, cancellation fees, no-show fees, and overstay fees.
- **Notifications (Telegram):** messages to the staff chat about important events.
- **Background tasks (Celery + Redis):** daily no-show detection and payment creation.
- **API docs:** Swagger UI and ReDoc generated with `drf-spectacular`.
- **Docker Compose:** one command to run the whole stack.

## Tech Stack

- Python, Django, Django REST Framework
- PostgreSQL
- Redis, Celery, django-celery-beat
- Stripe API (test mode)
- Telegram Bot API
- JWT (`djangorestframework-simplejwt`)
- drf-spectacular (OpenAPI / Swagger)
- Docker, Docker Compose

## Project Structure

| App | Responsibility |
|---|---|
| `users` | Custom user model, registration, JWT, profile |
| `rooms` | Room inventory, filters, availability calendar |
| `bookings` | Bookings, cancel / check-in / check-out flows, no-show task |
| `payments` | Stripe sessions, success / cancel pages, payment records |
| `notifications` | Telegram helper and notification tasks |

## Getting Started

### Prerequisites

- Git
- Docker and Docker Compose (recommended way to run), **or** Python 3.11+ for a local setup
- A Stripe account (test mode only, no real money)
- A Telegram bot token and chat ID

### Environment variables

Copy the sample file and fill in your values:

```shell
cp .env.sample .env        # Windows PowerShell: copy .env.sample .env
```

### Run with Docker (recommended)

```shell
git clone <repository-url>
cd hotel-booking-service
cp .env.sample .env
docker compose up --build
```

This starts the Django server, PostgreSQL, Redis, a Celery worker, and Celery beat.
Migrations are applied automatically on startup.

Create a superuser:

```shell
docker compose exec hotel-booking python manage.py createsuperuser
```

## Authentication

The API uses JWT. Obtain a token pair, then send the access token in the `Authorize` header:

```
Authorize: Bearer <access_token>
```

## Telegram Notifications

1. Create a bot with @BotFather and copy its token.
2. Create a chat for staff, add the bot, and send any message.
3. Get the chat ID from `https://api.telegram.org/bot<TOKEN>/getUpdates`.
4. Put both values into `.env`.

Notifications are sent by Celery tasks for new bookings, cancellations, no-shows, and successful payments.

## Testing

```shell
python manage.py test
```

Test coverage:

```shell
coverage run manage.py test
coverage report -m
coverage html                  # report in htmlcov/index.html
```

Inside Docker:

```shell
docker compose exec hotel-booking python manage.py test
```

Custom code coverage target: **60%+**.