import sqlite3
from datetime import datetime
from config import DB, CATEGORIES


def connect():
    return sqlite3.connect(DB)


def init_db():
    con = connect()
    cur = con.cursor()
    
    
    # =========================
    # PAYMENT HISTORY
    # =========================

    cur.execute("""
        CREATE TABLE IF NOT EXISTS payments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reservation_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_type TEXT NOT NULL,
            payment_method TEXT DEFAULT '',
            status TEXT DEFAULT 'Paid',
            created_at TEXT NOT NULL,
            FOREIGN KEY(reservation_id)
                REFERENCES reservations(id)
        )
    """)

    # =========================
    # USERS
    # =========================

    cur.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT,
        full_name TEXT DEFAULT '',
        email TEXT DEFAULT '',
        contact TEXT DEFAULT ''
    )""")

    # Upgrade older EventHub databases without deleting existing accounts.
    cols = {
        r[1]
        for r in cur.execute(
            "PRAGMA table_info(users)"
        ).fetchall()
    }

    for col in ("full_name", "email", "contact"):
        if col not in cols:
            cur.execute(
                f"ALTER TABLE users "
                f"ADD COLUMN {col} TEXT DEFAULT ''"
            )

    # =========================
    # PACKAGES
    # =========================

    cur.execute("""CREATE TABLE IF NOT EXISTS packages(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        name TEXT,
        event_type TEXT,
        provider TEXT,
        description TEXT,
        inclusions TEXT DEFAULT '',
        menu TEXT DEFAULT '',
        price REAL
    )""")

    # Upgrade existing packages table
    package_cols = {
        r[1]
        for r in cur.execute(
            "PRAGMA table_info(packages)"
        ).fetchall()
    }

    if "inclusions" not in package_cols:
        cur.execute(
            "ALTER TABLE packages "
            "ADD COLUMN inclusions TEXT DEFAULT ''"
        )

    if "menu" not in package_cols:
        cur.execute(
            "ALTER TABLE packages "
            "ADD COLUMN menu TEXT DEFAULT ''"
        )
    
    if "image_path" not in package_cols:
        cur.execute(
            "ALTER TABLE packages "
            "ADD COLUMN image_path TEXT DEFAULT ''"
        )


    # =========================
    # RESERVATIONS
    # =========================

    cur.execute("""CREATE TABLE IF NOT EXISTS reservations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer TEXT,
        contact TEXT,
        event_type TEXT,
        event_date TEXT,
        guests INTEGER,
        catering_id INTEGER,
        photography_id INTEGER,
        venue_id INTEGER,
        styling_id INTEGER,
        total REAL,
        status TEXT,
        payment_method TEXT DEFAULT '',
        created_at TEXT
    )""")

    # Upgrade existing reservations table
    reservation_cols = {
        r[1]
        for r in cur.execute(
            "PRAGMA table_info(reservations)"
        ).fetchall()
    }

    if "payment_method" not in reservation_cols:
        cur.execute(
            "ALTER TABLE reservations "
            "ADD COLUMN payment_method TEXT DEFAULT ''"
        )

    # =========================
    # DEFAULT USERS
    # =========================

    if cur.execute(
        "SELECT COUNT(*) FROM users"
    ).fetchone()[0] == 0:

        cur.executemany(
            """
            INSERT INTO users(
                username,
                password,
                role,
                full_name,
                email,
                contact
            )
            VALUES(?,?,?,?,?,?)
            """,
            [
                (
                    "admin",
                    "admin123",
                    "admin",
                    "EventHub Admin",
                    "admin@eventhub.local",
                    ""
                ),
                (
                    "customer",
                    "1234",
                    "customer",
                    "Demo Customer",
                    "customer@eventhub.local",
                    ""
                )
            ]
        )

    # =========================
    # DEFAULT PACKAGES
    # =========================

    if cur.execute(
        "SELECT COUNT(*) FROM packages"
    ).fetchone()[0] == 0:

        seed_packages(cur)

    # Add details to existing packages
    populate_package_details(cur)

    con.commit()
    con.close()


# =========================================================
# SEED PACKAGES
# =========================================================

def seed_packages(cur):

    provider_names = {
        "Catering": [
            "Delicious Bites Catering",
            "Fiesta Feast",
            "Golden Plate",
            "Celebration Catering"
        ],

        "Photography": [
            "Memory Lane Studio",
            "Forever Frames",
            "Moments Studio",
            "Everlasting Shots"
        ],

        "Venue": [
            "Grand Pavilion",
            "Rose Events Place",
            "Crystal Ballroom",
            "Garden Hall"
        ],

        "Event Styling & Decoration": [
            "Dream Decor",
            "Elegant Events",
            "Bloom Styling",
            "Perfect Theme"
        ]
    }

    event_types = [
        "Birthday",
        "Debut",
        "Wedding"
    ]

    for event_type in event_types:

        for category, _ in CATEGORIES:

            for i in range(1, 51):

                provider = provider_names[
                    category
                ][(i - 1) % 4]

                if category == "Catering":

                    name = (
                        f"Catering Package {i:02d}"
                    )

                    guests = (
                        50 + (i % 6) * 10
                    )

                    desc = (
                        f"Complete catering package "
                        f"for {guests} guests."
                    )

                    price = (
                        18000 + (i % 10) * 2500
                    )

                elif category == "Photography":

                    name = (
                        f"Photography Package {i:02d}"
                    )

                    hours = 4 + i % 5

                    desc = (
                        f"{hours} hours of "
                        "professional photo coverage."
                    )

                    price = (
                        10000 + (i % 10) * 3000
                    )

                elif category == "Venue":

                    name = (
                        f"Venue Package {i:02d}"
                    )

                    capacity = (
                        80 + (i % 7) * 20
                    )

                    desc = (
                        f"Elegant event place suitable "
                        f"for {capacity} guests."
                    )

                    price = (
                        20000 + (i % 10) * 5000
                    )

                else:

                    name = (
                        f"Styling Package {i:02d}"
                    )

                    desc = (
                        "Customized backdrop, balloons, "
                        "tables, entrance and theme styling."
                    )

                    price = (
                        8000 + (i % 10) * 2000
                    )

                cur.execute("""
                    INSERT INTO packages
                    (
                        category,
                        name,
                        event_type,
                        provider,
                        description,
                        price
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    category,
                    name,
                    event_type,
                    provider,
                    desc,
                    price
                ))


# =========================================================
# PACKAGE DETAILS
# =========================================================

def populate_package_details(cur):

    rows = cur.execute("""
        SELECT id, category, name
        FROM packages
    """).fetchall()

    for pid, category, name in rows:

        import re

        match = re.search(
            r"(\d+)\s*$",
            str(name)
        )

        number = (
            int(match.group(1))
            if match
            else 1
        )

        # =================================================
        # CATERING
        # =================================================

        if category == "Catering":

            guests = 50 + (number % 6) * 10

            service_hours = 4 + (number % 3)

            catering_inclusions = [
                f"{guests} guests",
                "Buffet setup",
                f"{service_hours}-hour catering service",
                "Dining tables and chairs",
                "Table linens",
                "Complete plates and utensils",
                "Serving staff",
                "Food preparation area",
                "Buffet table setup"
            ]

            if number >= 10:
                catering_inclusions.extend([
                    "Dessert station",
                    "Beverage station"
                ])

            if number >= 20:
                catering_inclusions.extend([
                    "Appetizer station",
                    "Premium table setup"
                ])

            if number >= 30:
                catering_inclusions.extend([
                    "Customized buffet arrangement",
                    "Additional serving staff"
                ])

            if number >= 40:
                catering_inclusions.extend([
                    "Premium buffet presentation",
                    "Special dessert display"
                ])

            if number >= 50:
                catering_inclusions.extend([
                    "Customized menu consultation",
                    "Dedicated catering coordinator"
                ])

            menu_sets = [

                (
                    "Steamed Rice",
                    "Chicken Adobo",
                    "Beef Caldereta",
                    "Chopsuey",
                    "Leche Flan",
                    "Iced Tea"
                ),

                (
                    "Garlic Rice",
                    "Fried Chicken",
                    "Beef Kare-Kare",
                    "Fresh Vegetable Salad",
                    "Buko Pandan",
                    "Iced Tea"
                ),

                (
                    "Plain Rice",
                    "Chicken BBQ",
                    "Beef Mechado",
                    "Filipino Salad",
                    "Fruit Salad",
                    "Soft Drinks"
                ),

                (
                    "Steamed Rice",
                    "Chicken Afritada",
                    "Beef Caldereta",
                    "Vegetable Spring Rolls",
                    "Leche Flan",
                    "Fruit Juice"
                ),

                (
                    "Garlic Rice",
                    "Chicken Teriyaki",
                    "Beef Broccoli",
                    "Garden Salad",
                    "Macaroni Salad",
                    "Iced Tea"
                )
            ]

            menu = list(
                menu_sets[(number - 1) % len(menu_sets)]
            )

            if number >= 20:
                menu.append("Assorted Appetizers")

            if number >= 30:
                menu.append("Premium Dessert Selection")

            if number >= 40:
                menu.append("Additional Beverage Choice")

            if number >= 50:
                menu.append("Chef's Special Dish")

            inclusions = ",".join(
                catering_inclusions
            )

            menu_text = ",".join(menu)

        # =================================================
        # PHOTOGRAPHY
        # =================================================

        elif category == "Photography":

            hours = 4 + (number % 5)

            photography_inclusions = [
                f"{hours}-hour event coverage",
                "Professional photographer",
                "Unlimited event shots",
                "Basic photo editing",
                "Color correction",
                "High-resolution digital copies",
                "Online photo gallery"
            ]

            if number >= 10:
                photography_inclusions.extend([
                    "Pre-event photo session",
                    "Event detail shots"
                ])

            if number >= 20:
                photography_inclusions.extend([
                    "Same-day preview photos",
                    "Enhanced photo retouching"
                ])

            if number >= 30:
                photography_inclusions.extend([
                    "Event highlights selection",
                    "Premium photo editing"
                ])

            if number >= 40:
                photography_inclusions.extend([
                    "Extended photo coverage",
                    "Priority photo delivery"
                ])

            if number >= 50:
                photography_inclusions.extend([
                    "Premium edited photo collection",
                    "Dedicated photography coordinator"
                ])

            inclusions = ",".join(
                photography_inclusions
            )

            menu_text = ""

        # =================================================
        # VENUE
        # =================================================

        elif category == "Venue":

            capacity = 80 + (number % 7) * 20

            venue_inclusions = [
                f"Venue for up to {capacity} guests",
                "Tables and chairs",
                "Table linens",
                "Basic lighting",
                "Air-conditioning",
                "Restroom access",
                "Basic venue setup",
                "8-hour venue use"
            ]

            if number >= 10:
                venue_inclusions.extend([
                    "Parking area",
                    "Preparation room"
                ])

            if number >= 20:
                venue_inclusions.extend([
                    "Basic sound system",
                    "Entrance reception area"
                ])

            if number >= 30:
                venue_inclusions.extend([
                    "Extended setup time",
                    "Additional venue staff"
                ])

            if number >= 40:
                venue_inclusions.extend([
                    "Premium lighting setup",
                    "Dedicated event coordinator"
                ])

            if number >= 50:
                venue_inclusions.extend([
                    "Extended venue access",
                    "Premium sound system"
                ])

            inclusions = ",".join(
                venue_inclusions
            )

            menu_text = ""

        # =================================================
        # EVENT STYLING & DECORATION
        # =================================================

        else:

            styling_inclusions = [
                "Main event backdrop",
                "Balloon decoration",
                "Entrance styling",
                "Guest table styling",
                "Table centerpieces",
                "Cake table styling",
                "Basic event theme setup",
                "Setup and teardown service"
            ]

            if number >= 10:
                styling_inclusions.extend([
                    "Welcome signage",
                    "Stage decoration"
                ])

            if number >= 20:
                styling_inclusions.extend([
                    "Customized color palette",
                    "Additional table centerpieces"
                ])

            if number >= 30:
                styling_inclusions.extend([
                    "Floral arrangements",
                    "Premium backdrop design"
                ])

            if number >= 40:
                styling_inclusions.extend([
                    "Entrance arch decoration",
                    "Premium table styling"
                ])

            if number >= 50:
                styling_inclusions.extend([
                    "Fully customized event theme",
                    "Dedicated styling coordinator"
                ])

            inclusions = ",".join(
                styling_inclusions
            )

            menu_text = ""

        cur.execute("""
            UPDATE packages
            SET inclusions=?,
                menu=?
            WHERE id=?
        """, (
            inclusions,
            menu_text,
            pid
        ))


# =========================================================
# MONEY
# =========================================================

def money(v):
    return f"₱{v:,.2f}"


# =========================================================
# GET PACKAGE
# =========================================================

def package(pid):

    con = connect()

    r = con.execute(
        """
        SELECT
            id,
            category,
            name,
            event_type,
            provider,
            description,
            inclusions,
            menu,
            price,
            image_path
        FROM packages
        WHERE id=?
        """,
        (pid,)
    ).fetchone()

    con.close()

    return r


# =========================================================
# PACKAGE AVAILABILITY
# =========================================================

def is_available(pid, event_date, ignore_id=None):

    con = connect()

    sql = """
        SELECT id
        FROM reservations
        WHERE event_date=?
        AND status IN ('Pending','Approved')
        AND (? IN (
            catering_id,
            photography_id,
            venue_id,
            styling_id
        ))
    """

    params = [
        event_date,
        pid
    ]

    if ignore_id:

        sql += " AND id != ?"

        params.append(
            ignore_id
        )

    result = con.execute(
        sql,
        params
    ).fetchone()

    con.close()

    return result is None


def get_unavailable_package_ids(event_date):
    con = connect()

    try:
        rows = con.execute(
            """
            SELECT DISTINCT package_id
            FROM (
                SELECT catering_id AS package_id
                FROM reservations
                WHERE event_date = ?
                  AND status IN ('Pending', 'Approved')
                  AND catering_id IS NOT NULL

                UNION ALL

                SELECT photography_id
                FROM reservations
                WHERE event_date = ?
                  AND status IN ('Pending', 'Approved')
                  AND photography_id IS NOT NULL

                UNION ALL

                SELECT venue_id
                FROM reservations
                WHERE event_date = ?
                  AND status IN ('Pending', 'Approved')
                  AND venue_id IS NOT NULL

                UNION ALL

                SELECT styling_id
                FROM reservations
                WHERE event_date = ?
                  AND status IN ('Pending', 'Approved')
                  AND styling_id IS NOT NULL
            )
            """,
            (event_date, event_date, event_date, event_date)
        ).fetchall()

        return {row[0] for row in rows}

    finally:
        con.close()


# =========================================================
# AUTHENTICATE
# =========================================================

def authenticate(
    username,
    password,
    role
):

    con = connect()

    row = con.execute(
        """
        SELECT username, role
        FROM users
        WHERE username=?
        AND password=?
        """,
        (
            username,
            password
        )
    ).fetchone()

    con.close()

    return (
        row
        if row and row[1] == role
        else None
    )


# =========================================================
# REGISTER CUSTOMER
# =========================================================

def register_customer(
    username,
    password,
    full_name,
    email,
    contact
):

    username = username.strip()
    full_name = full_name.strip()
    email = email.strip()
    contact = contact.strip()

    if (
        not username
        or not password
        or not full_name
        or not email
    ):
        return (
            False,
            "Please complete all required fields."
        )

    if len(password) < 4:

        return (
            False,
            "Password must be at least 4 characters."
        )

    con = connect()

    try:

        con.execute(
            """
            INSERT INTO users(
                username,
                password,
                role,
                full_name,
                email,
                contact
            )
            VALUES(?,?,?,?,?,?)
            """,
            (
                username,
                password,
                "customer",
                full_name,
                email,
                contact
            )
        )

        con.commit()

        return (
            True,
            "Account created successfully."
        )

    except sqlite3.IntegrityError:

        return (
            False,
            "That username is already registered."
        )

    finally:

        con.close()


# =========================================================
# CREATE RESERVATION
# =========================================================

def create_reservation(
    user,
    booking,
    event_type,
    selected,
    total,
    payment_method=""
):

    con = connect()
    cur = con.cursor()

    def get_selected(*keys):

        for key in keys:

            if key in selected:
                return selected[key]

        return None

    catering_id = get_selected(
        "Catering",
        "catering"
    )

    photography_id = get_selected(
        "Photography",
        "photography"
    )

    venue_id = get_selected(
        "Venue",
        "venue"
    )

    styling_id = get_selected(
        "Event Styling & Decoration",
        "styling"
    )

    cur.execute("""
        INSERT INTO reservations
        (
            customer,
            contact,
            event_type,
            event_date,
            guests,
            catering_id,
            photography_id,
            venue_id,
            styling_id,
            total,
            status,
            payment_method,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user[0],
        booking.get("contact", ""),
        event_type,
        booking["date"],
        booking["guests"],
        catering_id,
        photography_id,
        venue_id,
        styling_id,
        total,
        "Pending",
        payment_method,
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    ))

    rid = cur.lastrowid

    con.commit()
    con.close()

    return rid


# =========================================================
# MESSAGE TABLES
# =========================================================

def ensure_message_tables():

    con = connect()

    con.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            recipient TEXT NOT NULL,
            sender_role TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            important INTEGER DEFAULT 0
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL,
            is_active INTEGER DEFAULT 1
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS reservation_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reservation_id INTEGER NOT NULL,
            sender TEXT NOT NULL,
            note TEXT NOT NULL,
            created_at TEXT NOT NULL,
            is_read INTEGER DEFAULT 0
        )
    """)

    con.commit()
    con.close()
    

def get_unread_message_count(recipient, sender_role):
    con = connect()

    try:
        row = con.execute(
            """
            SELECT COUNT(*)
            FROM messages
            WHERE LOWER(TRIM(recipient)) = LOWER(TRIM(?))
              AND is_read = 0
              AND LOWER(TRIM(sender_role)) = LOWER(TRIM(?))
            """,
            (recipient, sender_role)
        ).fetchone()

        return row[0] if row else 0

    finally:
        con.close()


con = connect()

print("TOTAL PACKAGES:",
      con.execute("SELECT COUNT(*) FROM packages").fetchone()[0])

print("\nBY EVENT:")
for row in con.execute("""
    SELECT event_type, COUNT(*)
    FROM packages
    GROUP BY event_type
""").fetchall():
    print(row)

print("\nBY CATEGORY:")
for row in con.execute("""
    SELECT category, COUNT(*)
    FROM packages
    GROUP BY category
""").fetchall():
    print(row)

con.close()