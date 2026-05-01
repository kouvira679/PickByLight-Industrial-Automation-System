from dbh import DB, STATUS_IN_PROGRESS, STATUS_COMPLETE


def get_next_pending_order(db: DB):
    from dbh import STATUS_PENDING
    pending = [dict(row) for row in db.pull(order_status=STATUS_PENDING)]
    return pending[0] if pending else None


def mark_order_complete_if_final(db: DB, order_id: int, is_final_step: bool):
    if is_final_step:
        db.update_status(order_id, STATUS_COMPLETE)
    else:
        db.update_status(order_id, STATUS_IN_PROGRESS)


def resolve_order_from_rfid_or_db(rfid_result: dict, orders_db: DB) -> dict:
    order_id   = rfid_result["order_id"]
    model_id   = rfid_result["model_id"]
    step_index = rfid_result["step_index"]

    if model_id in (1, 2, 3) and order_id != 0:
        return {
            "order_id":   order_id,
            "model_id":   model_id,
            "step_index": step_index,
            "source":     "rfid",
        }

    pending = get_next_pending_order(orders_db)
    if pending is None:
        raise RuntimeError(
            "RFID was blank/invalid and there are no pending orders in production_orders.db"
        )

    return {
        "order_id":   pending["order_id"],
        "model_id":   pending["model_id"],
        "step_index": 0,
        "source":     "database_fallback",
    }
