from database.db import get_connection


def use_part(part_name, quantity):
    """Deduct `quantity` of `part_name` from inventory. Raises if stock is insufficient."""
    if quantity <= 0:
        raise ValueError("Quantity must be greater than 0")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT quantity FROM inventory WHERE part_name = ?",
        (part_name,)
    )
    row = cursor.fetchone()

    if row is None:
        conn.close()
        raise ValueError(f"Unknown part: {part_name}")

    current_quantity = row[0]

    if current_quantity < quantity:
        conn.close()
        raise ValueError(
            f"Not enough stock for {part_name}. "
            f"Available: {current_quantity}, Requested: {quantity}"
        )

    new_quantity = current_quantity - quantity

    cursor.execute(
        "UPDATE inventory SET quantity = ? WHERE part_name = ?",
        (new_quantity, part_name)
    )

    conn.commit()
    conn.close()

    return new_quantity
