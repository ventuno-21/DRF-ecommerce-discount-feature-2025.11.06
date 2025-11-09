# Afagh Nik Andishan 20 – Django + Docker + PostgreSQL + Redis + Celery

## [Part 1](#install) - **Dockerized Django with Auth & API** 
## [Part 2](#discount) - **Flexible Pricing Rules & Service**
---
# PART 1 - **Dockerized Django with Auth & API**   <a id="install"></a>
A production-ready **Django 5.2** backend project with **Docker Compose** orchestration, featuring:

- **Django REST Framework (DRF)**
- **PostgreSQL** as the database
- **Redis** as message broker for celery
- **Celery** for asynchronous task processing for cending email after registration anf when a client forget a password
- **JWT Authentication** via `djangorestframework-simplejwt` for authentication a logged in client  
- **JWT in URL**  via PYJWT to send a crypted link to client's email for reseting his password
- **OpenAPI Schema** via `drf-spectacular`
- **Environment-based configuration** (`.env`)
- **Health checks** for all services
- **Development server** (`runserver`) with hot-reload

---

## Project Structure  
```
├── a_config/              # Django settings & core  
├── app_accounts/          # Custom User/Profile/Vendor models    
├── app_api/               # All API endpoints  
├── app_orders/            # Not completed 
├── app_products/          # Products management  
├── app_cart/              # Shopping cart & PricingRule & related service  
├── static/                # Static files (dev)  
├── media/                 # Uploaded media  
├── Dockerfile
├── docker-compose.yml  
├── .env                   # Environment variables (gitignored)  
├── requirements.txt  
└── README.md  
```
## Quick Start

### 1. Clone & Enter Directory

```bash
git clone <your-repo-url>
cd <project-directory>
```
### 2. Create .env File
```bash
cp .env.example .env
```
Edit .env with your values (see Environment Variables). 
``` 
SECRET_KEY=your-super-secret-key-here  
DEBUG=True  

POSTGRES_NAME=afagh_db  
POSTGRES_USER=afagh_user  
POSTGRES_PASSWORD=afagh_password  
POSTGRES_HOST=db  
POSTGRES_PORT=5432  


CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1


EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=no-reply@afagh.com
```
Warning: Never commit .env to version control. Add it to .gitignore.

### 3. Build & Run with Docker Compose
```bash
docker-compose up --build -d
```
### 4. Apply Migrations & Create Superuser
```bash 
# Run migrations
docker-compose exec web python manage.py migrate
```

### 5. Create superuser
```bash 
docker-compose exec web python manage.py createsuperuser
``` 
### 6. Access the Application  

| Service       | URL                                | Notes                 |
|---------------|------------------------------------|-----------------------|
| Django App    | http://localhost:8000              | DRF browsable API     |
| Admin Panel   | http://localhost:8000/admin        | Login with superuser  |
| API Schema    | http://localhost:8000/schema/  | Swagger/Redoc         |
| Swagger UI    | http://localhost:8000/docs/    | Auto-generated        |


###  some docker useful notes:
#### Look for (healthy) status

Development Workflow
View Logs
```bash
docker-compose logs -f web           # Django
docker-compose logs -f celery            # Celery worker
docker-compose logs -f db                # PostgreSQL
Run Commands Inside Container
bashdocker-compose exec web python manage.py shell
docker-compose exec web python manage.py test
Rebuild After Code Changes
bashdocker-compose up --build -d
```


Useful Commands
```bash
# Stop all services
docker-compose down

# Remove volumes (reset DB)
docker-compose down -v

# Rebuild only web
docker-compose build web && docker-compose up -d web

# Check service status
docker-compose ps
```
---

# Part 2 - **Flexible Pricing Rules & Service** <a id="discount"></a>


A **flexible, reusable discount system** for e-commerce platforms, supporting:

- Cart-wide, category, and product-specific discounts  
- Percentage or fixed-amount discounts  
- Coupon codes + auto-apply rules  
- Min/max cart value & category thresholds  
- Global & per-user usage limits  
- Stackable (combinable) vs exclusive rules  
- Priority-based rule ordering  
- Multi-currency & time-limited promotions  

The `PricingService` is **read-only by design** — computes discounts **without side effects** (except `record_applied_rules`).

---

## Key Features

| Method | Description |
|-------|-------------|
| `get_applicable_rules()` | Finds all valid rules: explicit (M2M) + auto/coupon |
| `calculate_discounts()` | Computes total discount + applied rule breakdown |
| `record_applied_rules()` | **Only write method** — updates usage counters |
| **Stackable Logic** | Non-combinable → pick **best one**; Combinable → apply **all** |

---

## Example 1: 10% Off Entire Cart (Auto-Apply, Min $50)

### Rule Setup
```python
PricingRule.objects.create(
    name="SUMMER SALE",
    rule_type="cart_percentage",
    discount_percentage=10,
    min_cart_value=50,
    auto_apply=True,
    combinable=False,
    priority=10
)
```
| Item     | Price | Qty | Subtotal |
|----------|-------|-----|----------|
| T-Shirt  | $30   | 2   | $60      |

Final Price: $60 - $6 = $54

## Example 2: $5 Off Electronics (Coupon: TECH5)
Rule Setup
```python
pythonelectronics = Category.objects.get(name="Electronics")
PricingRule.objects.create(
    name="TECH DISCOUNT",
    rule_type="category_fixed",
    discount_amount=5,
    category=electronics,
    min_category_value=20,
    coupon_code="TECH5",
    combinable=True
)
```
| Item        | Category     | Price | Qty | Subtotal |
|--------------|--------------|-------|-----|-----------|
| Headphones   | Electronics  | $40   | 1   | $40       |
| T-Shirt      | Clothing     | $25   | 1   | $25       |

Electronics subtotal: $40 → qualifies


Apply Coupon
```python 
total_discount, applied_rules = PricingService.calculate_discounts(
    cart, coupon_codes=["TECH5"]
)
```
```
# total_discount → Decimal('5.00')
# applied_rules → [{'rule': TECH DISCOUNT, 'discount': 5.00, 'applied_to': 'category'}]
```
Final Price: $65 - $5 = $60

## Example 3: Stackable + Exclusive Rules
Rules
| Name       | Type            | Discount | Scope | Combinable | Priority |
|-------------|-----------------|-----------|--------|-------------|-----------|
| WELCOME10   | cart_percentage | 10%       | Cart   | No          | 20        |
| FREESHIP    | cart_fixed      | $8        | Cart   | Yes         | 15        |
| LOYALTY5    | cart_fixed      | $5        | Cart   | Yes         | 10        |

Cart Total: $100
Logic Flow

Non-combinable: Only WELCOME10 → $10  
Combinable: FREESHIP + LOYALTY5 → $13  
Total Discount: $10 + $13 = $23  

Output
```python# 
total_discount → Decimal('23.00')
# applied_rules → [
#   {'rule': WELCOME10, 'discount': 10.00, 'applied_to': 'cart'},
#   {'rule': FREESHIP,  'discount': 8.00,  'applied_to': 'cart'},
#   {'rule': LOYALTY5,  'discount': 5.00,  'applied_to': 'cart'}
# ]
```
Final Price: $100 - $23 = $77

WELCOME10 wins due to higher priority

## Example 4: Max Cart Value (Tiered Discount)
Rule: "15% off if cart ≤ $200"  

```
PricingRule.objects.create(
    name="MID SALE",
    rule_type="cart_percentage",
    discount_percentage=15,
    max_cart_value=200,
    auto_apply=True,
    combinable=False
)
```
| Cart | Total | Eligible? | Discount |
|------|--------|-----------|-----------|
| A    | $150   | Yes       | $22.50    |
| B    | $250   | No        | $0.00     |
```
PricingService.calculate_discounts(cart_a) → Decimal('22.50')
PricingService.calculate_discounts(cart_b) → Decimal('0.00')
```
## Example 5: Per-User Limit + Tracking
Rule
```
PricingRule.objects.create(
    name="FIRST ORDER",
    rule_type="cart_percentage",
    discount_percentage=20,
    per_user_limit=1,
    coupon_code="FIRST20"
)
```
User Applies Twice
```
# First use
PricingService.calculate_discounts(cart, ["FIRST20"]) → 20% applied
record_applied_rules() → user_usage = {"123": 1}

# Second use
PricingService.get_applicable_rules(cart, ["FIRST20"]) → [] (blocked)
```

Database Queries (Behind the Scenes)  
1. get_applicable_rules() – Auto/Coupon Rules  

```
SELECT * FROM pricing_rule 
WHERE active = TRUE
  AND (starts_at <= NOW() OR starts_at IS NULL)
  AND (ends_at >= NOW() OR ends_at IS NULL)
  AND (currency IS NULL OR currency = 'USD')
  AND (user_id IS NULL OR user_id = 123)
  AND (
    coupon_code IN ('SAVE10')
    OR (coupon_code IS NULL AND auto_apply = TRUE)
  )
ORDER BY priority DESC, created_at ASC;
```

2. Category Subtotal (in _compute_discount)
```
SELECT SUM(ci.quantity * pv.price)
FROM cartitem ci
JOIN productvariant pv ON ci.variant_id = pv.id
JOIN product p ON pv.product_id = p.id
WHERE ci.cart_id = 'abc' AND p.category_id = 5;
```

When to Use record_applied_rules()  

Only after order is confirmed:
```
total_discount, applied_rules = PricingService.calculate_discounts(cart, codes)
# ... create order ...
PricingService.record_applied_rules(cart, applied_rules)
```
Effects:

- Increments usage_count
- Updates user_usage JSON
- Links rule to cart (M2M)
- Ensures audit trail

| Feature              | Supported? | Example                |
|-----------------------|------------|------------------------|
| Cart-wide %           | Yes        | 10% off > $50          |
| Fixed $ off category  | Yes        | $5 off Electronics     |
| Coupon + Auto-apply   | Yes        | SAVE20 or auto         |
| Min/Max cart value    | Yes        | Tiered discounts       |
| Per-user limit        | Yes        | One-time coupon        |
| Stackable rules       | Yes        | Free shipping + % off  |
| Priority system       | Yes        | Best rule wins         |
| Multi-currency        | Yes        | USD-only rule          |
| Time-limited          | Yes        | Black Friday           |