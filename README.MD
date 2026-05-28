# 📦 Inventory Management System  
## Python Flask Example for Software Spec & Modelling Class

> "A simple Flask inventory app used as a teaching example for understanding
> the **Model-View-Controller (MVC)** software architecture. Yes, it's simple.
> That's the point. Don't overthink it."

---

## 🚀 Quick Start (Run It In 10 Seconds)

Open your terminal/command prompt and type these two lines:

```bash
pip install flask
python app.py
```

Then open your browser and go to: **http://localhost:2026**

That's it. You're done. You're now a software engineer. 🎉

---

## 📂 Project Structure

```
app.py              → The brain of the app (Model + Controller + DB)
view/
  ├── base.html     → The shared layout (header, nav, footer)
  ├── index.html    → Dashboard page (see stock levels at a glance)
  ├── products.html → Product catalogue (list all products)
  ├── product_form.html → New / Edit product form
  ├── inventory_move.html  → Move stock IN or OUT
  └── inventory_log.html   → History of every stock movement
inventory.db        → Your SQLite database (auto-created, don't delete)
```

---

## 🧱 Architecture: Model-View-Controller (MVC) Explained Like You're Brilliant (Because You Are)

Think of MVC like a **restaurant**. It's not that complicated.

| Role       | Restaurant Analogy         | In Our Code                  | What It Does                                   |
|------------|---------------------------|------------------------------|-------------------------------------------------|
| **Model**  | The kitchen              | `ProductModel`, `InventoryModel`, `InventoryLogModel` | Knows about data. Reads/writes the database. Doesn't care about users or HTML. |
| **View**   | The menu & dining room   | `view/*.html` files          | What the user sees. Pure HTML. No logic. Just displays data passed to it. |
| **Controller** | The waiter          | Route functions in `app.py`  | Takes user requests, talks to the Model, picks the right View, and delivers. |

### The Flow (Step by Step)

```
User clicks "Move Stock"
        │
        ▼
  CONTROLLER gets the request (a URL endpoint like /inventory/move)
        │
        ▼
  CONTROLLER asks the MODEL for data (e.g., get all products for dropdown)
        │
        ▼
  MODEL queries the DATABASE and returns rows
        │
        ▼
  CONTROLLER passes that data to the VIEW (a Jinja2 HTML template)
        │
        ▼
  VIEW renders the HTML and sends it back to the user's browser
```

---

## 🗂️ Model Layer — The Data Guys

There are **three model classes**. Each one handles one table in the database.

### 1. `ProductModel` → `master_product` table

Stores the product catalogue. This is the "master list" of what you sell.

| Method      | What It Does                          | SQL Equivalent       |
|-------------|---------------------------------------|-----------------------|
| `get_all()`     | Returns every product                  | `SELECT * FROM master_product` |
| `get_by_sku()`  | Finds one product by its SKU           | `SELECT * WHERE sku = ?` |
| `create()`      | Adds a new product (+ sets stock to 0) | `INSERT INTO ...`    |
| `update()`      | Changes name/category (SKU stays fixed) | `UPDATE ... WHERE sku = ?` |

**Key concept:** SKU is the **Primary Key** — it's the unique ID for each product. Once set, it never changes. Think of it like a student ID.

---

### 2. `InventoryModel` → `tbl_inventory` table

Tracks how many units of each product are currently in stock.

| Method            | What It Does                                  |
|-------------------|-----------------------------------------------|
| `get_all_with_product()` | Returns inventory **joined** with product info (SKU, name, category) |
| `get_by_sku()`    | Gets stock level for one specific SKU         |
| `adjust_stock()`  | Adds or subtracts from `qty_on_hand`          |

**Key concept:** **JOIN** = connecting two tables using a shared column (the `sku`). It's like matching your name to your ID card — two tables, one link.

---

### 3. `InventoryLogModel` → `tbl_inventory_log` table

Keeps a permanent record of every stock movement. Never updated. Never deleted. Just grows.

| Method        | What It Does                                    |
|---------------|--------------------------------------------------|
| `get_all()`   | Returns all log entries (newest first) with product name joined |
| `add_entry()` | Writes a new log record with timestamp           |

**Key concept:** This is an **immutable log**. Think of it like a bank statement — every transaction is recorded once and never erased.

---

## 🌐 Controller Layer — The Waiters

The controller is the middleman. In `app.py`, every route handler (a function decorated with `@app.route`) is a **controller action**.

| URL Endpoint       | HTTP Method | Controller Function     | What Happens                                                                 |
|-------------------|-------------|--------------------------|-------------------------------------------------------------------------------|
| `/`               | GET         | `index()`                | Dashboard — shows stock levels for all products                              |
| `/products`        | GET         | `product_list()`         | Lists all products from the master table                                     |
| `/products/new`    | GET + POST  | `product_new()`          | GET → shows blank form. POST → creates a new product with validation          |
| `/products/edit/<sku>` | GET + POST | `product_edit(sku)`    | GET → shows pre-filled form. POST → saves changes                            |
| `/inventory/move`  | GET + POST  | `inventory_move()`       | GET → shows stock movement form. POST → processes IN/OUT with validation      |
| `/inventory/log`   | GET         | `inventory_log()`        | Shows full movement history (read-only)                                      |

### What's a "Route"?

A **route** is just a URL that your app listens to. When a user visits that URL, Flask "calls" the function attached to it. Simple.

### What's `<sku>` in `/products/edit/<sku>`?

That's a **URL parameter**. If someone visits `/products/edit/PROD-001`, the `<sku>` part becomes the variable `sku = "PROD-001"` inside the function.

### Dual-Method Routes (GET + POST)

Some routes handle **two things**:
- **GET** → Load a page (show a form, display data)
- **POST** → Submit a page (save data, process a form)

Flask figures this out using `request.method`.

---

## 🎨 View Layer — The Pretty Face

All views live in the `view/` folder. They're written in **HTML + Jinja2 templating**.

### What is Jinja2?

Jinja2 is a way to put **Python-like logic** inside HTML. It's not scary:

```html
<!-- This loops through a list of products -->
{% for p in products %}
  <tr>
    <td>{{ p.sku }}</td>
    <td>{{ p.product_name }}</td>
  </tr>
{% endfor %}

<!-- This is an if/else -->
{% if row.qty_on_hand == 0 %}
  <ins>0 — OUT OF STOCK</ins>
{% else %}
  {{ row.qty_on_hand }}
{% endif %}
```

### Template Inheritance (`base.html`)

`base.html` is the **master template**. It contains:
- The `<head>` with CSS (Pico CSS framework — no classes needed!)
- The navigation bar (links to all pages)
- Flash message display
- A `{% block content %}` slot

Every other template `extends` it and only fills in the `{% block content %}` part. This way, you don't repeat the nav bar on every page.

### The Pages

| Template             | What You See                                                |
|---------------------|-------------------------------------------------------------|
| `base.html`          | Shared layout (header, nav, flash messages)                 |
| `index.html`         | Dashboard table — SKU, category, name, qty (highlights 0)   |
| `products.html`      | Product master list with Edit links                         |
| `product_form.html`  | Form for creating/editing a product                         |
| `inventory_move.html`| Form for moving stock IN or OUT with dropdowns              |
| `inventory_log.html` | Scrollable table of every movement (timestamped, never deleted) |

---

## 📊 Database Schema (SQLite)

Your data lives in `inventory.db` — a single file database. No setup needed.

### Table: `master_product` (Product Catalogue)

| Column       | Type   | Notes                              |
|-------------|--------|-------------------------------------|
| `sku`       | TEXT   | **Primary Key** — unique product code |
| `category`  | TEXT   | e.g. "Electronics", "Stationery"   |
| `product_name` | TEXT | Human-readable name                |

### Table: `tbl_inventory` (Current Stock Levels)

| Column       | Type   | Notes                              |
|-------------|--------|-------------------------------------|
| `id`        | INTEGER | Auto-generated row ID               |
| `sku`       | TEXT   | **Foreign Key** → links to `master_product.sku` |
| `qty_on_hand` | INTEGER | Current stock count (starts at 0) |

### Table: `tbl_inventory_log` (Movement History)

| Column         | Type    | Notes                              |
|---------------|---------|-------------------------------------|
| `id`          | INTEGER | Auto-generated                      |
| `sku`         | TEXT    | **Foreign Key** → `master_product.sku` |
| `movement_type` | TEXT  | Either `'IN'` or `'OUT'`            |
| `qty`         | INTEGER | How many units moved                |
| `notes`       | TEXT    | Optional user note                  |
| `created_at`  | TEXT    | Timestamp (e.g. "2025-01-15 14:30:00") |

---

## 🔄 Design Patterns & Key Concepts

| Pattern / Concept        | Where It Shows Up                                | Why It Matters                                         |
|-------------------------|---------------------------------------------------|---------------------------------------------------------|
| **MVC**                 | Entire app structure                              | Separates data, logic, and display — makes code easier to understand and change |
| **CRUD**                | `ProductModel` + `/products` routes               | **C**reate, **R**ead, **U**pdate, **D**elete — the four basic operations every app does |
| **Foreign Key**         | `tbl_inventory.sku → master_product.sku`          | Enforces data integrity — you can't have inventory for a product that doesn't exist |
| **JOIN**                | `InventoryModel.get_all_with_product()`           | Combines data from two tables using the shared `sku` column |
| **Immutable Log**       | `tbl_inventory_log` (never updated/deleted)       | Complete audit trail — you can always trace any stock movement |
| **Flash Messages**      | `base.html` + `flash()` in controllers           | One-time notifications (success/error) — disappears after next page load |
| **Template Inheritance**| `base.html` + `{% extends %}`                    | Write once, reuse everywhere — no copying HTML around    |
| **Parameterized Queries**| `?` placeholders in SQL (`WHERE sku = ?`)         | Prevents SQL injection — never trust user input         |
| **url_for()**           | Used in templates (e.g., `{{ url_for('index') }}`)| Generates URLs dynamically — if you change a route, you don't need to update every template |

---

## 🧪 Validation Logic (Because Users Are Chaotic)

The app doesn't trust user input. Here's what gets checked:

- **Product creation/editing:** SKU, category, and product name must not be empty.
- **Duplicate SKU:** You can't add the same SKU twice.
- **Stock movement quantity:** Must be a positive number.
- **OUT movements:** You can't remove more stock than you have.
- **SKU is always uppercased** on creation (so `prod-001` becomes `PROD-001`).

---

## 🛠️ Tech Stack

| Technology      | Purpose                                        |
|----------------|-------------------------------------------------|
| **Flask**       | Python web framework (handles routing, HTTP)   |
| **SQLite**      | Lightweight database (zero setup, file-based)  |
| **Jinja2**      | Template engine (renders HTML with Python data)|
| **Pico CSS**    | Classless CSS framework (semantic HTML only)   |
| **sqlite3**     | Python's built-in SQLite driver                 |

---

## 📝 Running Notes

```bash
# Install dependencies
pip install flask

# Run the app
python app.py

# App starts on port 2026 → go to http://localhost:2026
```

**Pro tip:** `debug=True` means Flask auto-reloads when you save code changes. Nice for class. Don't use it in production (but we're students, we don't care about production).

The database file `inventory.db` is created automatically. Delete it and restart to start fresh (all data gone, forever lost, RIP).

---

# Notes  

"If you understood this README, you understand 80% of what any web app does. The rest is just more HTML and slightly fancier SQL. Now go build something." 
— Maggie, probably, while drinking coffee.
