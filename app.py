# =============================================================================
# app.py
# PURPOSE: Entry point of the application. Ties everything together.
# ARCHITECTURE: MVC (Model-View-Controller)
#   - MODEL      → Handles data and database logic
#   - VIEW        → HTML templates (rendered via Jinja2 in /templates folder)
#   - CONTROLLER  → Route handlers (functions that respond to HTTP requests)
# =============================================================================

from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os
from datetime import datetime

# ------------------------------------------------------------------------------
# APP SETUP
# Flask(__name__) tells Flask to use the current file as the root of the app.
# 'secret_key' is needed to use flash messages (just a random string, keep it secret IRL).
# ------------------------------------------------------------------------------
app = Flask(__name__, template_folder='view')
app.secret_key = "supersecretkey_changethisinproduction"

# Path to our SQLite database file (created automatically if it doesn't exist)
DATABASE = "inventory.db"


# ==============================================================================
# ██████████████████████████████████████████████████████████████████████████████
# SECTION 1: DATABASE LAYER
# This section handles ALL raw database operations.
# Think of this as the plumbing — no business logic here, just SQL.
# ██████████████████████████████████████████████████████████████████████████████
# ==============================================================================

def get_db():
    """
    Opens a connection to the SQLite database.
    sqlite3.Row lets us access columns by name (e.g. row['sku']) instead of index.
    """
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Makes rows behave like dictionaries
    return conn


def init_db():
    """
    Creates all tables if they don't already exist.
    Called once when the app starts.

    TABLES:
    -------
    master_product   → The product catalogue (SKU, category, name)
    tbl_inventory    → Current stock level per SKU
    tbl_inventory_log → Every stock movement (in/out) with timestamp & notes
    """
    conn = get_db()
    cursor = conn.cursor()

    # ------------------------------------------------------------------
    # TABLE: master_product
    # Stores the product catalogue.
    # 'sku' is the PRIMARY KEY — unique identifier for each product.
    # ------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS master_product (
            sku          TEXT PRIMARY KEY,   -- Stock Keeping Unit (unique product code)
            category     TEXT NOT NULL,      -- Product category (e.g. "Electronics")
            product_name TEXT NOT NULL       -- Human-readable product name
        )
    """)

    # ------------------------------------------------------------------
    # TABLE: tbl_inventory
    # Tracks how many units of each SKU are currently in stock.
    # One row per SKU. Updated every time stock moves in or out.
    # ------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tbl_inventory (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,  -- Auto-generated row ID
            sku          TEXT NOT NULL UNIQUE,               -- Links to master_product.sku
            qty_on_hand  INTEGER NOT NULL DEFAULT 0,         -- Current stock count
            FOREIGN KEY (sku) REFERENCES master_product(sku) -- Enforces referential integrity
        )
    """)

    # ------------------------------------------------------------------
    # TABLE: tbl_inventory_log
    # Immutable log of every stock movement. Never update/delete this.
    # 'movement_type' is either 'IN' (stock added) or 'OUT' (stock removed).
    # ------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tbl_inventory_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            sku             TEXT NOT NULL,               -- Which product moved
            movement_type   TEXT NOT NULL CHECK(movement_type IN ('IN', 'OUT')), -- Direction
            qty             INTEGER NOT NULL,            -- How many units
            notes           TEXT,                        -- Optional user note
            created_at      TEXT NOT NULL,               -- Timestamp of movement
            FOREIGN KEY (sku) REFERENCES master_product(sku)
        )
    """)

    conn.commit()
    conn.close()


# ==============================================================================
# ██████████████████████████████████████████████████████████████████████████████
# SECTION 2: MODEL LAYER
# Models are classes that represent a "thing" in our system.
# They know how to read/write themselves from/to the database.
# No HTTP, no HTML — just pure data logic.
# ██████████████████████████████████████████████████████████████████████████████
# ==============================================================================

class ProductModel:
    """
    MODEL: Product
    Represents a product in master_product.
    Responsible for all CRUD operations on the product table.
    """

    @staticmethod
    def get_all():
        """Fetch every product from master_product."""
        conn = get_db()
        rows = conn.execute("SELECT * FROM master_product ORDER BY product_name").fetchall()
        conn.close()
        return rows

    @staticmethod
    def get_by_sku(sku):
        """Fetch a single product by its SKU. Returns None if not found."""
        conn = get_db()
        row = conn.execute("SELECT * FROM master_product WHERE sku = ?", (sku,)).fetchone()
        conn.close()
        return row

    @staticmethod
    def create(sku, category, product_name):
        """
        Insert a new product into master_product.
        Also creates a corresponding row in tbl_inventory with qty = 0.
        """
        conn = get_db()
        conn.execute(
            "INSERT INTO master_product (sku, category, product_name) VALUES (?, ?, ?)",
            (sku, category, product_name)
        )
        # Every product starts with 0 stock
        conn.execute(
            "INSERT INTO tbl_inventory (sku, qty_on_hand) VALUES (?, 0)",
            (sku,)
        )
        conn.commit()
        conn.close()

    @staticmethod
    def update(sku, category, product_name):
        """Update name and category of an existing product. SKU cannot change."""
        conn = get_db()
        conn.execute(
            "UPDATE master_product SET category = ?, product_name = ? WHERE sku = ?",
            (category, product_name, sku)
        )
        conn.commit()
        conn.close()


class InventoryModel:
    """
    MODEL: Inventory
    Manages current stock levels in tbl_inventory.
    """

    @staticmethod
    def get_all_with_product():
        """
        Fetch all inventory rows, JOINed with product info.
        JOIN = combining rows from two tables based on a shared column (sku).
        """
        conn = get_db()
        rows = conn.execute("""
            SELECT i.sku, i.qty_on_hand, p.product_name, p.category
            FROM tbl_inventory i
            JOIN master_product p ON i.sku = p.sku
            ORDER BY p.product_name
        """).fetchall()
        conn.close()
        return rows

    @staticmethod
    def get_by_sku(sku):
        """Fetch the current stock row for a specific SKU."""
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM tbl_inventory WHERE sku = ?", (sku,)
        ).fetchone()
        conn.close()
        return row

    @staticmethod
    def adjust_stock(sku, qty_change):
        """
        Add or subtract from qty_on_hand.
        qty_change is positive for IN, negative for OUT.
        """
        conn = get_db()
        conn.execute(
            "UPDATE tbl_inventory SET qty_on_hand = qty_on_hand + ? WHERE sku = ?",
            (qty_change, sku)
        )
        conn.commit()
        conn.close()


class InventoryLogModel:
    """
    MODEL: Inventory Log
    Handles writing and reading the movement history in tbl_inventory_log.
    """

    @staticmethod
    def get_all():
        """
        Fetch all log entries, newest first, with product name via JOIN.
        """
        conn = get_db()
        rows = conn.execute("""
            SELECT l.id, l.sku, p.product_name, l.movement_type, l.qty, l.notes, l.created_at
            FROM tbl_inventory_log l
            JOIN master_product p ON l.sku = p.sku
            ORDER BY l.created_at DESC
        """).fetchall()
        conn.close()
        return rows

    @staticmethod
    def add_entry(sku, movement_type, qty, notes):
        """
        Write a new log entry.
        created_at is set here using Python's datetime — not in the DB — for clarity.
        """
        conn = get_db()
        conn.execute(
            """INSERT INTO tbl_inventory_log (sku, movement_type, qty, notes, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (sku, movement_type, qty, notes, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        conn.close()


# ==============================================================================
# ██████████████████████████████████████████████████████████████████████████████
# SECTION 3: CONTROLLER LAYER (Flask Routes)
# Controllers receive HTTP requests, call the right Model, then return a View.
# Each function below is a CONTROLLER ACTION mapped to a URL ENDPOINT.
#
# HTTP Methods reminder:
#   GET  → Read/fetch data (loading a page)
#   POST → Send/submit data (submitting a form)
# ██████████████████████████████████████████████████████████████████████████████
# ==============================================================================

# ------------------------------------------------------------------------------
# CONTROLLER: Home
# ------------------------------------------------------------------------------

@app.route("/")
def index():
    """
    ENDPOINT: GET /
    Controller action for the home/dashboard page.
    Fetches inventory summary and passes it to the view.
    """
    inventory = InventoryModel.get_all_with_product()  # Call Model
    return render_template("index.html", inventory=inventory)  # Return View


# ------------------------------------------------------------------------------
# CONTROLLER: Product (CRUD)
# ------------------------------------------------------------------------------

@app.route("/products")
def product_list():
    """
    ENDPOINT: GET /products
    Lists all products from master_product.
    """
    products = ProductModel.get_all()
    return render_template("products.html", products=products)


@app.route("/products/new", methods=["GET", "POST"])
def product_new():
    """
    ENDPOINT: GET /products/new  → Show the empty form
              POST /products/new → Handle form submission and create product

    This is a classic 'dual-method' route pattern in MVC.
    """
    if request.method == "POST":
        # Pull data from the submitted HTML form
        sku          = request.form["sku"].strip().upper()
        category     = request.form["category"].strip()
        product_name = request.form["product_name"].strip()

        # Basic validation — never trust user input
        if not sku or not category or not product_name:
            flash("All fields are required.", "error")
            return redirect(url_for("product_new"))

        # Check for duplicate SKU
        if ProductModel.get_by_sku(sku):
            flash(f"SKU '{sku}' already exists.", "error")
            return redirect(url_for("product_new"))

        ProductModel.create(sku, category, product_name)
        flash(f"Product '{product_name}' created successfully!", "success")
        return redirect(url_for("product_list"))

    # GET request — just show the blank form
    return render_template("product_form.html", product=None, action="Create")


@app.route("/products/edit/<sku>", methods=["GET", "POST"])
def product_edit(sku):
    """
    ENDPOINT: GET /products/edit/<sku>  → Show pre-filled form
              POST /products/edit/<sku> → Save changes

    '<sku>' is a URL parameter — Flask extracts it and passes it as an argument.
    """
    product = ProductModel.get_by_sku(sku)
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for("product_list"))

    if request.method == "POST":
        category     = request.form["category"].strip()
        product_name = request.form["product_name"].strip()

        if not category or not product_name:
            flash("All fields are required.", "error")
            return redirect(url_for("product_edit", sku=sku))

        ProductModel.update(sku, category, product_name)
        flash(f"Product '{sku}' updated.", "success")
        return redirect(url_for("product_list"))

    return render_template("product_form.html", product=product, action="Edit")


# ------------------------------------------------------------------------------
# CONTROLLER: Stock Movement (IN / OUT)
# ------------------------------------------------------------------------------

@app.route("/inventory/move", methods=["GET", "POST"])
def inventory_move():
    """
    ENDPOINT: GET /inventory/move  → Show stock movement form
              POST /inventory/move → Process the movement

    This single action handles both stock IN and stock OUT.
    The 'movement_type' hidden/select field in the form tells us which direction.
    """
    products = ProductModel.get_all()  # Needed to populate the SKU dropdown

    if request.method == "POST":
        sku           = request.form["sku"]
        movement_type = request.form["movement_type"]  # "IN" or "OUT"
        qty           = request.form["qty"]
        notes         = request.form.get("notes", "").strip()  # Optional field

        # --- Validation ---
        if not qty.isdigit() or int(qty) <= 0:
            flash("Quantity must be a positive number.", "error")
            return redirect(url_for("inventory_move"))

        qty = int(qty)
        stock = InventoryModel.get_by_sku(sku)

        # Can't take out more than you have
        if movement_type == "OUT" and stock["qty_on_hand"] < qty:
            flash(f"Not enough stock. Current qty: {stock['qty_on_hand']}", "error")
            return redirect(url_for("inventory_move"))

        # Positive number for IN, negative for OUT
        qty_change = qty if movement_type == "IN" else -qty

        # Update the stock level in tbl_inventory
        InventoryModel.adjust_stock(sku, qty_change)

        # Write to the log — always log every movement, forever
        InventoryLogModel.add_entry(sku, movement_type, qty, notes)

        flash(f"Stock {'added' if movement_type == 'IN' else 'removed'} successfully!", "success")
        return redirect(url_for("index"))

    return render_template("inventory_move.html", products=products)


# ------------------------------------------------------------------------------
# CONTROLLER: Inventory Log (read-only view)
# ------------------------------------------------------------------------------

@app.route("/inventory/log")
def inventory_log():
    """
    ENDPOINT: GET /inventory/log
    Displays the full movement history. Read-only.
    """
    logs = InventoryLogModel.get_all()
    return render_template("inventory_log.html", logs=logs)


# ==============================================================================
# ██████████████████████████████████████████████████████████████████████████████
# SECTION 4: APP BOOTSTRAP
# This block only runs when you execute `python app.py` directly.
# It initialises the DB and starts Flask's built-in dev server.
# ██████████████████████████████████████████████████████████████████████████████
# ==============================================================================

if __name__ == "__main__":
    init_db()           # Make sure all tables exist before starting
    app.run(debug=True, port=2026) # debug=True auto-reloads on code changes — NEVER use in production
