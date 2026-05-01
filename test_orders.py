from dbh import DB, STATUS_PENDING

DB_FILE = "production_orders.db"

# Model 1 = "Red Product":  red top (x1), red bottom (x1), pcb (x1), fuse (x2)
# Model 2 = "Blue Product": blue top (x1), blue bottom (x1), pcb (x1), fuse (x2)
# Model 3 = "Grey Product": grey top (x1), grey bottom (x1), pcb (x1), fuse (x2)
TEST_ORDERS = [
    {"order_id": 1001, "model_id": 1, "order_status": STATUS_PENDING},
    {"order_id": 1002, "model_id": 2, "order_status": STATUS_PENDING},
    {"order_id": 1003, "model_id": 3, "order_status": STATUS_PENDING},
]


def seed_test_orders(db_file: str = DB_FILE) -> None:
    db = DB(db_file)
    for order in TEST_ORDERS:
        db.insert_order(
            order_id=order["order_id"],
            model_id=order["model_id"],
            status=order["order_status"],
        )


if __name__ == "__main__":
    seed_test_orders()
    print("Seeded 3 test orders into production_orders.db")
    print("  Order 1001 — Red Product  (model 1)")
    print("    Step 0: red top    x1  (task 401)")
    print("    Step 1: red bottom x1  (task 404)")
    print("    Step 2: pcb        x1  (task 411)")
    print("    Step 3: fuse       x2  (task 701)")
    print("  Order 1002 — Blue Product (model 2)")
    print("    Step 0: blue top   x1  (task 403)")
    print("    Step 1: blue bottom x1 (task 405)")
    print("    Step 2: pcb        x1  (task 411)")
    print("    Step 3: fuse       x2  (task 701)")
    print("  Order 1003 — Grey Product (model 3)")
    print("    Step 0: grey top   x1  (task 402)")
    print("    Step 1: grey bottom x1 (task 406)")
    print("    Step 2: pcb        x1  (task 411)")
    print("    Step 3: fuse       x2  (task 701)")