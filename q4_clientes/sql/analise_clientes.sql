-- ============================================================
-- DESAFIO LIGHTHOUSE - DADOS E IA
-- QUESTÃO 4 - ANÁLISE DE CLIENTES
-- ============================================================
--
-- Objetivo:
-- Identificar os 10 clientes com maior ticket médio entre
-- aqueles que compraram produtos de pelo menos 13 categorias
-- distintas e, para esse grupo, identificar as categorias
-- com maior quantidade de itens comprados.
--
-- Regras:
-- - Faturamento total = SUM(orders.total)
-- - Frequência = quantidade de pedidos
-- - Ticket médio = faturamento total / frequência
-- - Diversidade = quantidade de category_id distintos
-- - Filtro de elite = diversidade >= 13
-- - Desempate = customer_id ASC
-- - Ranking = maior ticket médio
-- ============================================================


-- ============================================================
-- 1. MÉTRICAS DE VENDAS POR CLIENTE
-- ============================================================

WITH customer_sales AS (

    SELECT
        customer_id,

        -- Faturamento total do cliente
        SUM(total) AS faturamento_total,

        -- Frequência de transações/pedidos
        COUNT(id) AS frequencia,

        -- Ticket médio
        SUM(total) / COUNT(id) AS ticket_medio

    FROM orders

    GROUP BY customer_id
),


-- ============================================================
-- 2. DIVERSIDADE DE CATEGORIAS POR CLIENTE
-- ============================================================
--
-- Cadeia de relacionamento:
--
-- orders
--   ↓ order_id
-- order_items
--   ↓ product_variant_id
-- product_variants
--   ↓ product_id
-- products
--   ↓ category_id
-- categories
--
-- ============================================================

customer_categories AS (

    SELECT
        o.customer_id,

        COUNT(DISTINCT p.category_id)
            AS diversidade_categorias

    FROM orders o

    JOIN order_items oi
        ON oi.order_id = o.id

    JOIN product_variants pv
        ON pv.id = oi.product_variant_id

    JOIN products p
        ON p.id = pv.product_id

    GROUP BY o.customer_id
),


-- ============================================================
-- 3. IDENTIFICAÇÃO DOS TOP 10 CLIENTES
-- ============================================================

top_10_fieis AS (

    SELECT
        cs.customer_id,
        cs.faturamento_total,
        cs.frequencia,
        cs.ticket_medio,
        cc.diversidade_categorias

    FROM customer_sales cs

    JOIN customer_categories cc
        ON cc.customer_id = cs.customer_id

    -- Critério mínimo de diversidade
    WHERE cc.diversidade_categorias >= 13

    -- Ranking:
    -- 1º maior ticket médio
    -- 2º menor customer_id em caso de empate
    ORDER BY
        cs.ticket_medio DESC,
        cs.customer_id ASC

    LIMIT 10
)


-- ============================================================
-- 4. CATEGORIAS MAIS COMPRADAS PELOS TOP 10
-- ============================================================

SELECT
    p.category_id,
    c.name AS categoria,

    -- Soma da quantidade de itens comprados
    SUM(oi.quantity) AS quantidade_total

FROM top_10_fieis t

JOIN orders o
    ON o.customer_id = t.customer_id

JOIN order_items oi
    ON oi.order_id = o.id

JOIN product_variants pv
    ON pv.id = oi.product_variant_id

JOIN products p
    ON p.id = pv.product_id

JOIN categories c
    ON c.id = p.category_id

GROUP BY
    p.category_id,
    c.name

ORDER BY
    quantidade_total DESC;