-- ============================================================
-- DESAFIO LIGHTHOUSE - DADOS E IA
-- QUESTÃO 3.2 - VALIDAÇÃO DO CARREGAMENTO
-- ============================================================

SELECT
    (SELECT COUNT(*) FROM customers)
    + (SELECT COUNT(*) FROM orders)
    + (SELECT COUNT(*) FROM order_items)
    + (SELECT COUNT(*) FROM payments)
        AS total_linhas;