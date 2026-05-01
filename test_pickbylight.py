"""
PickByLight MES — Automated Test Suite
Run with:  pytest tests/test_pickbylight.py -v
"""

import sqlite3
import pytest


# ── point the DB module at a temp file for every test ──────────────────────
@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """
    Each test gets its own fresh SQLite file so tests never interfere.
    We monkeypatch database.db.DB_NAME then re-initialise the schema.
    """
    db_path = str(tmp_path / "test_pick_by_light.db")
    monkeypatch.setattr("database.db.DB_NAME", db_path)
    from database.schema import initialize_database
    initialize_database()
    yield db_path


# ══════════════════════════════════════════════════════════════════════════
# TC-01  Database initialisation
# ══════════════════════════════════════════════════════════════════════════
class TestDatabaseInit:

    def test_TC01_inventory_table_created(self, isolated_db):
        """TC-01: initialize_database creates the inventory table."""
        conn = sqlite3.connect(isolated_db)
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        conn.close()
        assert "inventory" in tables

    def test_TC01_order_log_table_created(self, isolated_db):
        """TC-01: initialize_database creates the order_log table."""
        conn = sqlite3.connect(isolated_db)
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        conn.close()
        assert "order_log" in tables

    def test_TC01_starting_inventory_correct(self, isolated_db):
        """TC-01: Starting inventory is seeded with correct quantities."""
        conn = sqlite3.connect(isolated_db)
        rows = dict(conn.execute(
            "SELECT part_name, quantity FROM inventory"
        ).fetchall())
        conn.close()
        assert rows["red top"]     == 8
        assert rows["red bottom"]  == 8
        assert rows["blue top"]    == 8
        assert rows["blue bottom"] == 8
        assert rows["grey top"]    == 8
        assert rows["grey bottom"] == 8
        assert rows["pcb"]         == 8
        assert rows["fuse"]        == 16

    def test_TC01_order_log_empty_on_init(self, isolated_db):
        """TC-01: order_log is empty after initialisation."""
        conn = sqlite3.connect(isolated_db)
        count = conn.execute("SELECT COUNT(*) FROM order_log").fetchone()[0]
        conn.close()
        assert count == 0


# ══════════════════════════════════════════════════════════════════════════
# TC-02  Models catalogue
# ══════════════════════════════════════════════════════════════════════════
class TestModelsCatalog:

    def test_TC02_red_product_workplan_length(self):
        """TC-02: Red Product workplan has exactly 4 steps."""
        from models.models_catalog import get_model
        assert len(get_model(1)["workplan"]) == 4

    def test_TC02_red_product_step_sequence(self):
        """TC-02: Red Product steps are red top → red bottom → pcb → fuse."""
        from models.models_catalog import get_model
        workplan = get_model(1)["workplan"]
        assert workplan[0]["part_name"] == "red top"
        assert workplan[1]["part_name"] == "red bottom"
        assert workplan[2]["part_name"] == "pcb"
        assert workplan[3]["part_name"] == "fuse"

    def test_TC02_red_product_fuse_quantity(self):
        """TC-02: Red Product fuse step requires quantity 2."""
        from models.models_catalog import get_model
        assert get_model(1)["workplan"][3]["quantity"] == 2

    def test_TC02_red_product_task_codes(self):
        """TC-02: Red Product task codes match specification."""
        from models.models_catalog import get_model
        workplan = get_model(1)["workplan"]
        assert workplan[0]["task_code"] == 401
        assert workplan[1]["task_code"] == 404
        assert workplan[2]["task_code"] == 411
        assert workplan[3]["task_code"] == 701

    def test_TC02_unknown_model_returns_none(self):
        """TC-02: Requesting a non-existent model_id returns None."""
        from models.models_catalog import get_model
        assert get_model(99) is None

    def test_TC02_step_out_of_range_raises(self):
        """TC-02: Requesting a step index beyond the workplan raises IndexError."""
        from models.models_catalog import get_step_for_model
        with pytest.raises(IndexError):
            get_step_for_model(1, 99)

    def test_TC02_all_three_models_present(self):
        """TC-02: Models 1, 2, and 3 all exist in the catalogue."""
        from models.models_catalog import get_model
        assert get_model(1)["model_name"] == "Red Product"
        assert get_model(2)["model_name"] == "Blue Product"
        assert get_model(3)["model_name"] == "Grey Product"


# ══════════════════════════════════════════════════════════════════════════
# TC-03  Inventory deduction (use_part)
# ══════════════════════════════════════════════════════════════════════════
class TestInventory:

    def test_TC03_use_part_deducts_correct_amount(self, isolated_db):
        """TC-03: use_part reduces inventory by the requested quantity."""
        from logic.inventory import use_part
        assert use_part("red top", 1) == 7

    def test_TC03_use_part_deducts_fuse_by_two(self, isolated_db):
        """TC-03: use_part deducts 2 fuses correctly (qty=2 step)."""
        from logic.inventory import use_part
        assert use_part("fuse", 2) == 14

    def test_TC03_use_part_persists_to_db(self, isolated_db):
        """TC-03: use_part change is visible when re-reading the database."""
        from logic.inventory import use_part
        use_part("pcb", 1)
        conn = sqlite3.connect(isolated_db)
        qty = conn.execute(
            "SELECT quantity FROM inventory WHERE part_name='pcb'"
        ).fetchone()[0]
        conn.close()
        assert qty == 7

    def test_TC03_use_part_raises_on_insufficient_stock(self, isolated_db):
        """TC-03: use_part raises ValueError when stock is below requested quantity."""
        from logic.inventory import use_part
        for _ in range(8):
            use_part("red top", 1)
        with pytest.raises(ValueError, match="Not enough stock"):
            use_part("red top", 1)

    def test_TC03_use_part_raises_on_unknown_part(self, isolated_db):
        """TC-03: use_part raises ValueError for a part not in inventory."""
        from logic.inventory import use_part
        with pytest.raises(ValueError, match="Unknown part"):
            use_part("purple widget", 1)

    def test_TC03_use_part_raises_on_zero_quantity(self, isolated_db):
        """TC-03: use_part raises ValueError if quantity is 0."""
        from logic.inventory import use_part
        with pytest.raises(ValueError):
            use_part("red top", 0)


# ══════════════════════════════════════════════════════════════════════════
# TC-04  Order step processing (process_order_step)
# ══════════════════════════════════════════════════════════════════════════
class TestOrderLogic:

    def test_TC04_step0_returns_red_top(self, isolated_db):
        """TC-04: process_order_step(1, 0) returns red top with task_code 401."""
        from logic.order_logic import process_order_step
        result = process_order_step(1, 0)
        assert result["part_name"] == "red top"
        assert result["task_code"] == 401
        assert result["quantity"]  == 1

    def test_TC04_step3_returns_fuse_qty2(self, isolated_db):
        """TC-04: process_order_step(1, 3) returns fuse with quantity 2."""
        from logic.order_logic import process_order_step
        result = process_order_step(1, 3)
        assert result["part_name"] == "fuse"
        assert result["quantity"]  == 2

    def test_TC04_step0_is_not_final(self, isolated_db):
        """TC-04: Step 0 is not marked as the final step."""
        from logic.order_logic import process_order_step
        assert process_order_step(1, 0)["is_final_step"] is False

    def test_TC04_step3_is_final(self, isolated_db):
        """TC-04: Step 3 (fuse) is marked as the final step."""
        from logic.order_logic import process_order_step
        assert process_order_step(1, 3)["is_final_step"] is True

    def test_TC04_next_step_increments(self, isolated_db):
        """TC-04: next_step_index is step_index + 1 for non-final steps."""
        from logic.order_logic import process_order_step
        assert process_order_step(1, 0)["next_step_index"] == 1

    def test_TC04_inventory_reduced_after_step(self, isolated_db):
        """TC-04: Inventory is reduced after processing a step."""
        from logic.order_logic import process_order_step
        assert process_order_step(1, 0)["remaining_inventory"] == 7

    def test_TC04_unknown_model_raises(self, isolated_db):
        """TC-04: process_order_step raises ValueError for unknown model_id."""
        from logic.order_logic import process_order_step
        with pytest.raises(ValueError, match="Unknown model_id"):
            process_order_step(99, 0)

    def test_TC04_invalid_step_raises(self, isolated_db):
        """TC-04: process_order_step raises IndexError for out-of-range step."""
        from logic.order_logic import process_order_step
        with pytest.raises(IndexError):
            process_order_step(1, 99)

    def test_TC04_full_red_product_sequence(self, isolated_db):
        """TC-04: All 4 steps of Red Product process in order correctly."""
        from logic.order_logic import process_order_step
        expected = [
            ("red top",    401, 1, False),
            ("red bottom", 404, 1, False),
            ("pcb",        411, 1, False),
            ("fuse",       701, 2, True),
        ]
        for step_index, (part, code, qty, is_final) in enumerate(expected):
            result = process_order_step(1, step_index)
            assert result["part_name"]     == part,     f"Step {step_index} part wrong"
            assert result["task_code"]     == code,     f"Step {step_index} task_code wrong"
            assert result["quantity"]      == qty,      f"Step {step_index} quantity wrong"
            assert result["is_final_step"] == is_final, f"Step {step_index} is_final wrong"


# ══════════════════════════════════════════════════════════════════════════
# TC-05  Order logging (log_order_step / get_order_logs)
# ══════════════════════════════════════════════════════════════════════════
class TestOrderLogging:

    def test_TC05_log_creates_record(self, isolated_db):
        """TC-05: log_order_step inserts a row into order_log."""
        from database.queries import log_order_step, get_order_logs
        log_order_step(1001, 1, 0, 401, "red top", 1)
        assert len(get_order_logs()) == 1

    def test_TC05_log_fields_correct(self, isolated_db):
        """TC-05: Logged record contains the correct field values."""
        from database.queries import log_order_step, get_order_logs
        log_order_step(1001, 1, 2, 411, "pcb", 1)
        row = get_order_logs()[0]
        assert row[1] == 1001    # order_id
        assert row[2] == 1       # model_id
        assert row[3] == 2       # step_index
        assert row[4] == 411     # task_code
        assert row[5] == "pcb"   # part_name
        assert row[6] == 1       # quantity

    def test_TC05_multiple_logs_ordered_newest_first(self, isolated_db):
        """TC-05: get_order_logs returns records newest-first."""
        from database.queries import log_order_step, get_order_logs
        log_order_step(1001, 1, 0, 401, "red top",    1)
        log_order_step(1001, 1, 1, 404, "red bottom", 1)
        log_order_step(1001, 1, 2, 411, "pcb",        1)
        logs = get_order_logs()
        assert logs[0][5] == "pcb"      # most recent first
        assert logs[2][5] == "red top"  # oldest last

    def test_TC05_log_limit_respected(self, isolated_db):
        """TC-05: get_order_logs limit parameter is respected."""
        from database.queries import log_order_step, get_order_logs
        for i in range(5):
            log_order_step(1001, 1, i, 400 + i, f"part{i}", 1)
        assert len(get_order_logs(limit=3)) == 3


# ══════════════════════════════════════════════════════════════════════════
# TC-06  Order queue (dbh.DB)
# ══════════════════════════════════════════════════════════════════════════
class TestOrderQueue:

    @pytest.fixture
    def orders_db(self, tmp_path):
        from dbh import DB
        return DB(str(tmp_path / "orders.db"))

    def test_TC06_insert_and_pull_pending(self, orders_db):
        """TC-06: Inserted pending order appears in pull(pending)."""
        from dbh import STATUS_PENDING
        orders_db.insert_order(1001, 1)
        rows = orders_db.pull(order_status=STATUS_PENDING)
        assert len(rows) == 1
        assert dict(rows[0])["order_id"] == 1001

    def test_TC06_status_update_to_in_progress(self, orders_db):
        """TC-06: update_status changes order from pending to in_progress."""
        from dbh import STATUS_PENDING, STATUS_IN_PROGRESS
        orders_db.insert_order(1001, 1)
        orders_db.update_status(1001, STATUS_IN_PROGRESS)
        assert len(orders_db.pull(order_status=STATUS_PENDING))     == 0
        assert len(orders_db.pull(order_status=STATUS_IN_PROGRESS)) == 1

    def test_TC06_status_update_to_complete(self, orders_db):
        """TC-06: update_status changes order to complete correctly."""
        from dbh import STATUS_COMPLETE
        orders_db.insert_order(1001, 1)
        orders_db.update_status(1001, STATUS_COMPLETE)
        assert len(orders_db.pull(order_status=STATUS_COMPLETE)) == 1

    def test_TC06_no_pending_returns_empty(self, orders_db):
        """TC-06: pull(pending) returns empty list when no pending orders exist."""
        from dbh import STATUS_PENDING
        assert len(orders_db.pull(order_status=STATUS_PENDING)) == 0

    def test_TC06_multiple_orders_ordered_by_id(self, orders_db):
        """TC-06: pull returns orders sorted ascending by order_id."""
        orders_db.insert_order(1003, 3)
        orders_db.insert_order(1001, 1)
        orders_db.insert_order(1002, 2)
        ids = [dict(r)["order_id"] for r in orders_db.pull()]
        assert ids == [1001, 1002, 1003]


# ══════════════════════════════════════════════════════════════════════════
# TC-07  RFID parsing (reader.parse_rfid_data / is_blank_rfid)
# ══════════════════════════════════════════════════════════════════════════
class TestRFIDParsing:

    def test_TC07_parse_valid_rfid_bytes(self):
        """TC-07: parse_rfid_data correctly decodes order_id, model_id, step_index."""
        from opcua_connection.reader import parse_rfid_data
        # order_id=1001 little-endian, model_id=1, step_index=2
        raw = [0xE9, 0x03, 0x00, 0x00, 0x01, 0x02] + [0] * 26
        order_id, model_id, step_index = parse_rfid_data(raw)
        assert order_id   == 1001
        assert model_id   == 1
        assert step_index == 2

    def test_TC07_parse_rfid_list_input(self):
        """TC-07: parse_rfid_data accepts a plain list of ints."""
        from opcua_connection.reader import parse_rfid_data
        raw = [0xE9, 0x03, 0x00, 0x00, 0x02, 0x00]
        order_id, model_id, _ = parse_rfid_data(raw)
        assert order_id  == 1001
        assert model_id  == 2

    def test_TC07_parse_rfid_too_short_raises(self):
        """TC-07: parse_rfid_data raises ValueError if data is less than 6 bytes."""
        from opcua_connection.reader import parse_rfid_data
        with pytest.raises(ValueError, match="too short"):
            parse_rfid_data([0x01, 0x02])

    def test_TC07_parse_rfid_none_raises(self):
        """TC-07: parse_rfid_data raises ValueError if data is None."""
        from opcua_connection.reader import parse_rfid_data
        with pytest.raises(ValueError, match="empty"):
            parse_rfid_data(None)

    def test_TC07_blank_rfid_detected(self):
        """TC-07: is_blank_rfid returns True for an all-zero tag."""
        from opcua_connection.reader import is_blank_rfid
        assert is_blank_rfid([0] * 32) is True

    def test_TC07_non_blank_rfid_detected(self):
        """TC-07: is_blank_rfid returns False for a tag with data."""
        from opcua_connection.reader import is_blank_rfid
        assert is_blank_rfid([0xE9, 0x03, 0x00, 0x00, 0x01, 0x00]) is False

    def test_TC07_blank_rfid_none_input(self):
        """TC-07: is_blank_rfid returns True when passed None."""
        from opcua_connection.reader import is_blank_rfid
        assert is_blank_rfid(None) is True


# ══════════════════════════════════════════════════════════════════════════
# TC-08  RFID / DB fallback logic (resolve_order_from_rfid_or_db)
# ══════════════════════════════════════════════════════════════════════════
class TestResolveOrder:

    @pytest.fixture
    def orders_db(self, tmp_path):
        from dbh import DB
        db = DB(str(tmp_path / "orders.db"))
        db.insert_order(1001, 1)
        return db

    def test_TC08_valid_rfid_uses_rfid(self, orders_db):
        """TC-08: Valid RFID data is used directly without touching the DB."""
        from order_processing import resolve_order_from_rfid_or_db
        rfid = {"order_id": 2002, "model_id": 2, "step_index": 1}
        result = resolve_order_from_rfid_or_db(rfid, orders_db)
        assert result["source"]     == "rfid"
        assert result["order_id"]   == 2002
        assert result["model_id"]   == 2
        assert result["step_index"] == 1

    def test_TC08_blank_rfid_falls_back_to_db(self, orders_db):
        """TC-08: Blank RFID (order_id=0) falls back to first pending DB order."""
        from order_processing import resolve_order_from_rfid_or_db
        rfid = {"order_id": 0, "model_id": 0, "step_index": 0}
        result = resolve_order_from_rfid_or_db(rfid, orders_db)
        assert result["source"]     == "database_fallback"
        assert result["order_id"]   == 1001
        assert result["step_index"] == 0

    def test_TC08_blank_rfid_no_pending_raises(self, tmp_path):
        """TC-08: Blank RFID with no pending orders raises RuntimeError."""
        from order_processing import resolve_order_from_rfid_or_db
        from dbh import DB
        empty_db = DB(str(tmp_path / "empty.db"))
        rfid = {"order_id": 0, "model_id": 0, "step_index": 0}
        with pytest.raises(RuntimeError, match="no pending orders"):
            resolve_order_from_rfid_or_db(rfid, empty_db)

    def test_TC08_invalid_model_id_falls_back(self, orders_db):
        """TC-08: RFID with model_id not in (1,2,3) triggers DB fallback."""
        from order_processing import resolve_order_from_rfid_or_db
        rfid = {"order_id": 9999, "model_id": 99, "step_index": 0}
        result = resolve_order_from_rfid_or_db(rfid, orders_db)
        assert result["source"] == "database_fallback"


# ══════════════════════════════════════════════════════════════════════════
# TC-09  Order status lifecycle (mark_order_complete_if_final)
# ══════════════════════════════════════════════════════════════════════════
class TestOrderStatusLifecycle:

    @pytest.fixture
    def orders_db(self, tmp_path):
        from dbh import DB
        db = DB(str(tmp_path / "orders.db"))
        db.insert_order(1001, 1)
        return db

    def test_TC09_non_final_step_sets_in_progress(self, orders_db):
        """TC-09: Non-final step marks order as in_progress."""
        from order_processing import mark_order_complete_if_final
        from dbh import STATUS_IN_PROGRESS
        mark_order_complete_if_final(orders_db, 1001, is_final_step=False)
        assert len(orders_db.pull(order_status=STATUS_IN_PROGRESS)) == 1

    def test_TC09_final_step_sets_complete(self, orders_db):
        """TC-09: Final step marks order as complete."""
        from order_processing import mark_order_complete_if_final
        from dbh import STATUS_COMPLETE
        mark_order_complete_if_final(orders_db, 1001, is_final_step=True)
        assert len(orders_db.pull(order_status=STATUS_COMPLETE)) == 1

    def test_TC09_complete_order_not_pending(self, orders_db):
        """TC-09: Completed order no longer appears in pending queue."""
        from order_processing import mark_order_complete_if_final
        from dbh import STATUS_PENDING
        mark_order_complete_if_final(orders_db, 1001, is_final_step=True)
        assert len(orders_db.pull(order_status=STATUS_PENDING)) == 0


# ══════════════════════════════════════════════════════════════════════════
# TC-10  End-to-end: complete Red Product order (no PLC)
# ══════════════════════════════════════════════════════════════════════════
class TestEndToEnd:

    def test_TC10_full_red_product_order(self, isolated_db, tmp_path):
        """
        TC-10: Simulate a complete Red Product order through all 4 steps.
        Verifies inventory deductions, order_log entries, and final order status.
        """
        from dbh import DB, STATUS_COMPLETE
        from logic.order_logic import process_order_step
        from database.queries import log_order_step, get_order_logs
        from order_processing import mark_order_complete_if_final

        orders_db = DB(str(tmp_path / "orders.db"))
        orders_db.insert_order(1001, 1)

        for step_index in range(4):
            result = process_order_step(1, step_index)
            log_order_step(
                order_id=1001,
                model_id=1,
                step_index=step_index,
                task_code=result["task_code"],
                part_name=result["part_name"],
                quantity=result["quantity"],
            )
            mark_order_complete_if_final(orders_db, 1001, result["is_final_step"])

        conn = sqlite3.connect(isolated_db)
        inv = dict(conn.execute(
            "SELECT part_name, quantity FROM inventory"
        ).fetchall())
        conn.close()

        assert inv["red top"]    == 7   # 8 - 1
        assert inv["red bottom"] == 7   # 8 - 1
        assert inv["pcb"]        == 7   # 8 - 1
        assert inv["fuse"]       == 14  # 16 - 2

        assert len(get_order_logs()) == 4

        complete = orders_db.pull(order_status=STATUS_COMPLETE)
        assert len(complete) == 1
        assert dict(complete[0])["order_id"] == 1001

    def test_TC10_stock_exhaustion_raises_on_9th_order(self, isolated_db):
        """
        TC-10: After 8 Red Product orders, a 9th raises ValueError (stock exhausted).
        """
        from logic.order_logic import process_order_step

        for _ in range(8):
            for step_index in range(4):
                process_order_step(1, step_index)

        with pytest.raises(ValueError, match="Not enough stock"):
            process_order_step(1, 0)
