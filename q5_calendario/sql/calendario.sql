WITH calendario AS (
    SELECT
        data::date AS data,
        EXTRACT(ISODOW FROM data) AS numero_dia_semana,
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
        (
            SELECT MIN(created_at)::date
            FROM orders
            WHERE channel = 'pos'
        ),
        (
            SELECT MAX(created_at)::date
            FROM orders
            WHERE channel = 'pos'
        ),
        INTERVAL '1 day'
    ) AS data
),

vendas_diarias AS (
    SELECT
        created_at::date AS data,
        SUM(total) AS vendas
    FROM orders
    WHERE channel = 'pos'
    GROUP BY created_at::date
),

calendario_vendas AS (
    SELECT
        c.data,
        c.numero_dia_semana,
        c.dia_semana,
        COALESCE(v.vendas, 0) AS vendas
    FROM calendario c
    LEFT JOIN vendas_diarias v
        ON v.data = c.data
)

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