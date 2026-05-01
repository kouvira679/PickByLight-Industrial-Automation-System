from __future__ import annotations

import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

_HERE = Path(__file__).resolve().parent
INV_DB    = _HERE / "pick_by_light.db"
ORDERS_DB = _HERE / "production_orders.db"

REFRESH_SECONDS = 3

MODEL_NAMES = {1: "Red Product", 2: "Blue Product", 3: "Grey Product"}
STATUS_COLORS = {
    "pending":     "#f0ad4e",
    "in_progress": "#5bc0de",
    "complete":    "#5cb85c",
}


def read_table(db_file: Path, query: str) -> pd.DataFrame:
    if not db_file.exists():
        return pd.DataFrame()
    try:
        conn = sqlite3.connect(db_file)
        return pd.read_sql_query(query, conn)
    except Exception as e:
        print(f"DB read error ({db_file.name}): {e}")
        return pd.DataFrame()
    finally:
        conn.close()


def draw(fig, ax_inv, ax_log, ax_orders) -> None:
    """Redraw all three panels from the latest DB data."""

    # ── Left panel: inventory bar chart ──────────────────────────────
    ax_inv.clear()

    df_inv = read_table(
        INV_DB,
        "SELECT part_name, quantity FROM inventory ORDER BY part_name"
    )

    if not df_inv.empty:
        colors = [
            "tomato" if q == 0 else "steelblue"
            for q in df_inv["quantity"]
        ]
        bars = ax_inv.bar(df_inv["part_name"], df_inv["quantity"], color=colors)
        ax_inv.set_title("Current Inventory", fontsize=12)
        ax_inv.set_xlabel("Part")
        ax_inv.set_ylabel("Quantity Remaining")
        ax_inv.tick_params(axis="x", rotation=30)

        for bar, qty in zip(bars, df_inv["quantity"]):
            ax_inv.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.1,
                str(qty),
                ha="center", va="bottom", fontsize=9, fontweight="bold"
            )
    else:
        ax_inv.set_title("No inventory data found")
        ax_inv.text(0.5, 0.5, f"Database not found:\n{INV_DB.name}",
                    ha="center", va="center", transform=ax_inv.transAxes)

    # ── Middle panel: recent picks log table ─────────────────────────
    ax_log.clear()
    ax_log.axis("off")

    df_log = read_table(
        INV_DB,
        """
        SELECT
            order_id    AS 'Order',
            model_id    AS 'Model',
            part_name   AS 'Part',
            quantity    AS 'Qty',
            created_at  AS 'Time'
        FROM order_log
        ORDER BY log_id DESC
        LIMIT 12
        """
    )

    if not df_log.empty:
        df_log["Model"] = df_log["Model"].map(MODEL_NAMES).fillna(df_log["Model"])
        df_log["Time"] = df_log["Time"].astype(str).str[-8:]

        ax_log.set_title("Recent Picks", fontsize=12)
        tbl = ax_log.table(
            cellText=df_log.values,
            colLabels=df_log.columns,
            loc="center",
            cellLoc="center",
        )
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(9)
        tbl.scale(1, 1.5)
    else:
        ax_log.set_title("Recent Picks")
        ax_log.text(0.5, 0.5, "No picks logged yet.",
                    ha="center", va="center", transform=ax_log.transAxes)

    # ── Right panel: production orders status table ───────────────────
    ax_orders.clear()
    ax_orders.axis("off")

    df_orders = read_table(
        ORDERS_DB,
        """
        SELECT
            order_id     AS 'Order ID',
            model_id     AS 'Model',
            order_status AS 'Status'
        FROM orders
        ORDER BY order_id ASC
        """
    )

    if not df_orders.empty:
        df_orders["Model"] = df_orders["Model"].map(MODEL_NAMES).fillna(df_orders["Model"])

        ax_orders.set_title("Production Orders", fontsize=12)
        tbl = ax_orders.table(
            cellText=df_orders.values,
            colLabels=df_orders.columns,
            loc="center",
            cellLoc="center",
        )
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(9)
        tbl.scale(1, 1.8)

        for (row, col), cell in tbl.get_celld().items():
            if row == 0:
                cell.set_facecolor("#343a40")
                cell.set_text_props(color="white", fontweight="bold")
            elif col == 2:
                status_val = df_orders.iloc[row - 1]["Status"]
                cell.set_facecolor(STATUS_COLORS.get(status_val, "#ffffff"))
                cell.set_text_props(fontweight="bold")
    else:
        ax_orders.set_title("Production Orders")
        ax_orders.text(0.5, 0.5, f"Database not found:\n{ORDERS_DB.name}",
                       ha="center", va="center", transform=ax_orders.transAxes)

    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.canvas.draw_idle()


def show_live_dashboard() -> None:
    fig = plt.figure(figsize=(18, 7))
    fig.suptitle("Pick By Light — Live Dashboard", fontsize=14, fontweight="bold")

    gs = fig.add_gridspec(1, 3, wspace=0.35)
    ax_inv    = fig.add_subplot(gs[0, 0])
    ax_log    = fig.add_subplot(gs[0, 1])
    ax_orders = fig.add_subplot(gs[0, 2])

    draw(fig, ax_inv, ax_log, ax_orders)
    plt.show(block=False)

    while plt.fignum_exists(fig.number):
        plt.pause(REFRESH_SECONDS)
        if plt.fignum_exists(fig.number):
            draw(fig, ax_inv, ax_log, ax_orders)


if __name__ == "__main__":
    print(f"Dashboard starting — refreshes every {REFRESH_SECONDS}s. Close the window to quit.")
    show_live_dashboard()