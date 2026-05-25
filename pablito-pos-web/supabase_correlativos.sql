-- ==========================================
-- SCRIPT: CORRELATIVOS ATÓMICOS PARA VENTAS
-- ==========================================

-- 1. Crear tabla para llevar el control de las secuencias
CREATE TABLE IF NOT EXISTS document_sequences (
    series TEXT PRIMARY KEY,
    current_number BIGINT NOT NULL DEFAULT 0
);

-- 2. Crear función para asignar el correlativo
CREATE OR REPLACE FUNCTION assign_sale_correlative()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- Solo asignar si no viene un número manual o viene en 0
    IF NEW.number IS NULL OR NEW.number = 0 THEN
        INSERT INTO document_sequences (series, current_number)
        VALUES (NEW.series, 1)
        ON CONFLICT (series) DO UPDATE
        SET current_number = document_sequences.current_number + 1
        RETURNING current_number INTO NEW.number;
    END IF;
    RETURN NEW;
END;
$$;

-- 3. Eliminar el trigger si ya existe (para evitar errores en re-ejecución)
DROP TRIGGER IF EXISTS tr_assign_sale_correlative ON sales;

-- 4. Crear el trigger en la tabla sales
CREATE TRIGGER tr_assign_sale_correlative
BEFORE INSERT ON sales
FOR EACH ROW
EXECUTE FUNCTION assign_sale_correlative();
