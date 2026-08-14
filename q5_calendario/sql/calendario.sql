-- ============================================================
-- DESAFIO LIGHTHOUSE - DADOS E IA
-- QUESTÃO 5 - DIMENSÃO DE CALENDÁRIO
-- ============================================================
--
-- Objetivo:
-- Calcular a média de vendas por dia da semana considerando
-- todos os dias do período analisado, inclusive aqueles em que
-- não houve nenhuma venda registrada.
--
-- Premissas:
-- - Considerar somente vendas de lojas físicas (channel = 'pos');
-- - Criar calendário entre a menor e a maior data das vendas;
-- - Considerar dias sem vendas como R$ 0,00;
-- - Calcular vendas diárias pela soma de orders.total;
-- - Apresentar o dia da semana em português.
-- ============================================================


-- ============================================================
-- 1. DIMENSÃO DE CALENDÁRIO
-- ============================================================

WITH calendario AS (

    SELECT
        data::date AS data,

        -- ISO: Segunda-feira = 1 ... Domingo = 7
        EXTRACT(
            ISODOW FROM data
        ) AS numero_dia_semana,

        -- Nome do dia da semana em português
        CASE EXTRACT(ISODOW FROM data)
            WHEN 1 THEN 'Segunda-feira'
            WHEN 2 THEN 'Terça-feira'
            WHEN 3 THEN 'Quarta-feira'
            WHEN 4 THEN 'Quinta-feira'
            WHEN 5 THEN 'Sexta-feira'
            WHEN 6 THEN 'Sábado'
            WHEN 7 THEN 'Domingo'
        END AS dia_semana

    FROM generate_series(

        -- Primeira data de venda das lojas físicas
        (
            SELECT
                MIN(created_at)::date
            FROM orders
            WHERE channel = 'pos'
        ),

        -- Última data de venda das lojas físicas
        (
            SELECT
                MAX(created_at)::date
            FROM orders
            WHERE channel = 'pos'
        ),

        INTERVAL '1 day'
    ) AS data
),


-- ============================================================
-- 2. AGREGAÇÃO DAS VENDAS POR DIA
-- ============================================================

vendas_diarias AS (

    SELECT
        created_at::date AS data,

        -- Total vendido no dia
        SUM(total) AS vendas

    FROM orders

    WHERE channel = 'pos'

    GROUP BY
        created_at::date
),


-- ============================================================
-- 3. RELACIONAMENTO DO CALENDÁRIO COM AS VENDAS
-- ============================================================
--
-- LEFT JOIN garante que todas as datas do calendário
-- permaneçam no resultado, mesmo quando não houver vendas.
--
-- COALESCE transforma ausência de venda em R$ 0,00.
-- ============================================================

calendario_vendas AS (

    SELECT
        c.data,
        c.numero_dia_semana,
        c.dia_semana,

        COALESCE(
            v.vendas,
            0
        ) AS vendas

    FROM calendario c

    LEFT JOIN vendas_diarias v
        ON v.data = c.data
)


-- ============================================================
-- 4. MÉDIA DE VENDAS POR DIA DA SEMANA
-- ============================================================

SELECT
    numero_dia_semana,
    dia_semana,

    AVG(vendas) AS media_vendas

FROM calendario_vendas

GROUP BY
    numero_dia_semana,
    dia_semana

ORDER BY
    numero_dia_semana;