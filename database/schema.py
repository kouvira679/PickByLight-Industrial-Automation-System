from database.db import get_connection


def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        part_name TEXT PRIMARY KEY,
        quantity INTEGER NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_log (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        model_id INTEGER NOT NULL,
        step_index INTEGER NOT NULL,
        task_code INTEGER NOT NULL,
        part_name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


def reset_inventory():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM inventory")

    starting_inventory = [
        ("pcb", 8),
        ("fuse", 16),
        ("red top", 8),
        ("red bottom", 8),
        ("blue top", 8),
        ("blue bottom", 8),
        ("grey top", 8),
        ("grey bottom", 8),
    ]

    cursor.executemany("""
    INSERT INTO inventory (part_name, quantity)
    VALUES (?, ?)
    """, starting_inventory)

    conn.commit()
    conn.close()


def reset_order_log():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM order_log")

    conn.commit()
    conn.close()


def initialize_database():
    create_tables()
    reset_inventory()
    reset_order_log()
    print("Database initialized successfully with fresh inventory and empty logs.")


if __name__ == "__main__":
    initialize_database()