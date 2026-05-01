from database.db import get_connection

def deduct_inventory(part_name, quantity):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE inventory 
        SET quantity = MAX(0, quantity - ?)
        WHERE part_name = ?
    """, (quantity, part_name))
    conn.commit()
    conn.close()

def log_order_step(order_id, model_id, step_index, task_code, part_name, quantity):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO order_log (
        order_id,
        model_id,
        step_index,
        task_code,
        part_name,
        quantity
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """, (order_id, model_id, step_index, task_code, part_name, quantity))

    conn.commit()
    conn.close()


def get_order_logs(limit=20):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        log_id,
        order_id,
        model_id,
        step_index,
        task_code,
        part_name,
        quantity,
        created_at
    FROM order_log
    ORDER BY log_id DESC
    LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return rows
