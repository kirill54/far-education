/** Остаток по позиции: приход − списание. */
export function stockForItem(db, itemId) {
  const row = db
    .prepare(
      `SELECT
         COALESCE(SUM(CASE WHEN kind = 'receipt' THEN quantity ELSE 0 END), 0) AS received,
         COALESCE(SUM(CASE WHEN kind = 'issue' THEN quantity ELSE 0 END), 0) AS issued
       FROM warehouse_movements WHERE item_id = ?`,
    )
    .get(itemId);
  const balance = row.received - row.issued;
  return {
    received: row.received,
    issued: row.issued,
    balance,
  };
}

export function listItemsWithStock(db, activeOnly = true) {
  const clause = activeOnly ? 'WHERE w.active = 1' : '';
  const items = db
    .prepare(
      `SELECT w.id, w.name, w.unit_label, w.min_stock, w.active, w.sort_order
       FROM warehouse_items w ${clause} ORDER BY w.sort_order, w.name`,
    )
    .all();
  return items.map((item) => {
    const st = stockForItem(db, item.id);
    return {
      ...item,
      stock_received: st.received,
      stock_issued: st.issued,
      stock_balance: st.balance,
      below_min: item.min_stock > 0 && st.balance < item.min_stock,
    };
  });
}
