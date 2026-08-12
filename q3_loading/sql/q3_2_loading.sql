SELECT
    (SELECT COUNT(*) FROM customers) +
    (SELECT COUNT(*) FROM orders) +
    (SELECT COUNT(*) FROM order_items) +
    (SELECT COUNT(*) FROM payments) AS total_linhas;