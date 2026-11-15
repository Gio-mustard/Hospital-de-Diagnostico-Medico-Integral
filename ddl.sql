-- =====================================================================
-- DDL convertido de PostgreSQL a SQLite (requiere SQLite >= 3.37 por STRICT)
--
-- IMPORTANTE: SQLite NO valida llaves foráneas por defecto.
-- Cada conexión de la app debe ejecutar:  PRAGMA foreign_keys = ON; ESTO SE HARA DESDE EL OBJETO DE CONEXION EN PYTHON
--
-- Convenciones de tipos:
--   BOOLEAN   -> INTEGER con CHECK (0, 1)
--   DATE      -> TEXT 'YYYY-MM-DD'
--   TIMESTAMP -> TEXT 'YYYY-MM-DD HH:MM:SS'
--   JSONB     -> TEXT con CHECK json_valid()
--   TEXT[]    -> TEXT con un arreglo JSON
--   UUID      -> TEXT
-- =====================================================================

PRAGMA foreign_keys = ON;

-- Sin CASCADE en SQLite: se borra de hijas a padres
DROP VIEW IF EXISTS vista_citas_recepcion;
DROP TABLE IF EXISTS AuditoriaClinica;
DROP TABLE IF EXISTS DetalleReceta;
DROP TABLE IF EXISTS Receta;
DROP TABLE IF EXISTS IngresoEmergencia;
DROP TABLE IF EXISTS Ingreso;
DROP TABLE IF EXISTS Cita;
DROP TABLE IF EXISTS HistorialMedico;
DROP TABLE IF EXISTS MedicoEspecialidad;
DROP TABLE IF EXISTS EnfermeroEspecialidad;
DROP TABLE IF EXISTS Enfermero;
DROP TABLE IF EXISTS Recepcionista;
DROP TABLE IF EXISTS Medico;
DROP TABLE IF EXISTS Trabajador;
DROP TABLE IF EXISTS Paciente;
DROP TABLE IF EXISTS DerechoHabiente;
DROP TABLE IF EXISTS Medicamento;
DROP TABLE IF EXISTS Consultorio;
DROP TABLE IF EXISTS Habitacion;
DROP TABLE IF EXISTS Especialidad;

CREATE TABLE DerechoHabiente (
    id_derechohabiente INTEGER PRIMARY KEY AUTOINCREMENT,
    auth_user_id TEXT UNIQUE,                -- Antes FK a auth.users (Supabase); aquí no existe
    nombres TEXT NOT NULL,
    apellido_paterno TEXT NOT NULL,
    apellido_materno TEXT,
    direccion_calle TEXT NOT NULL,
    codigo_postal TEXT NOT NULL,
    ciudad TEXT NOT NULL,
    estado TEXT NOT NULL,
    fecha_nacimiento TEXT NOT NULL,
    genero TEXT,
    telefono TEXT,
    curp TEXT NOT NULL UNIQUE,
    activo INTEGER NOT NULL DEFAULT 1,

    -- Longitudes de los VARCHAR(n) originales (SQLite no las aplica solo)
    CONSTRAINT chk_dh_longitudes CHECK (
        length(nombres) <= 100 AND length(apellido_paterno) <= 100
        AND (apellido_materno IS NULL OR length(apellido_materno) <= 100)
        AND length(direccion_calle) <= 100
        AND length(ciudad) <= 50 AND length(estado) <= 50
    ),
    CONSTRAINT chk_dh_auth_uuid CHECK (auth_user_id IS NULL OR length(auth_user_id) = 36),
    -- '^[0-9]{5}$'
    CONSTRAINT chk_dh_cp CHECK (length(codigo_postal) = 5 AND codigo_postal NOT GLOB '*[^0-9]*'),
    -- La parte "<= hoy" vive en un trigger (SQLite prohíbe la fecha actual en CHECK)
    CONSTRAINT chk_dh_fecha_nac CHECK (fecha_nacimiento IS date(fecha_nacimiento) AND fecha_nacimiento >= '1900-01-01'),
    CONSTRAINT chk_dh_genero CHECK (genero IN ('Masculino', 'Femenino', 'Otro')),
    -- '^[A-Z]{4}[0-9]{6}[HM][A-Z]{5}[0-9A-Z][0-9]$'  (GLOB distingue mayúsculas)
    CONSTRAINT chk_dh_curp CHECK (
        length(curp) = 18 AND
        curp GLOB '[A-Z][A-Z][A-Z][A-Z][0-9][0-9][0-9][0-9][0-9][0-9][HM][A-Z][A-Z][A-Z][A-Z][A-Z][0-9A-Z][0-9]'
    ),
    -- '^\+[1-9][0-9]{7,14}$'  (E.164, ej. '+526866024822')
    CONSTRAINT chk_dh_telefono CHECK (
        telefono IS NULL OR (
            length(telefono) BETWEEN 9 AND 16
            AND telefono GLOB '+[1-9]*'
            AND substr(telefono, 2) NOT GLOB '*[^0-9]*'
        )
    ),
    CONSTRAINT chk_dh_activo CHECK (activo IN (0, 1))
) STRICT;

CREATE TABLE Paciente (
    id_paciente INTEGER PRIMARY KEY AUTOINCREMENT,
    id_derechohabiente INTEGER NOT NULL UNIQUE,
    tipo_sangre TEXT,
    FOREIGN KEY (id_derechohabiente) REFERENCES DerechoHabiente (id_derechohabiente) ON DELETE RESTRICT,

    CONSTRAINT chk_paciente_sangre CHECK (tipo_sangre IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'))
) STRICT;

CREATE TABLE Trabajador (
    id_trabajador INTEGER PRIMARY KEY AUTOINCREMENT,
    id_derechohabiente INTEGER NOT NULL UNIQUE,
    numero_empleado TEXT NOT NULL UNIQUE,
    departamento TEXT NOT NULL,
    fecha_ingreso TEXT NOT NULL,
    activo INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (id_derechohabiente) REFERENCES DerechoHabiente (id_derechohabiente) ON DELETE RESTRICT,

    -- '^EMP-[0-9]{4,}$'
    CONSTRAINT chk_trab_num_emp CHECK (
        length(numero_empleado) BETWEEN 8 AND 20
        AND numero_empleado GLOB 'EMP-[0-9][0-9][0-9][0-9]*'
        AND substr(numero_empleado, 5) NOT GLOB '*[^0-9]*'
    ),
    CONSTRAINT chk_trab_departamento CHECK (length(departamento) <= 100),
    -- La parte "<= hoy" vive en un trigger
    CONSTRAINT chk_trab_fecha_ing CHECK (fecha_ingreso IS date(fecha_ingreso)),
    CONSTRAINT chk_trab_activo CHECK (activo IN (0, 1))
) STRICT;

CREATE TABLE Recepcionista (
    id_recepcionista INTEGER PRIMARY KEY AUTOINCREMENT,
    id_derechohabiente INTEGER NOT NULL UNIQUE,
    id_trabajador INTEGER UNIQUE,
    turno TEXT NOT NULL DEFAULT 'Matutino',
    modulo_atencion TEXT NOT NULL DEFAULT 'Admisión Principal',
    extension_tel TEXT,
    activo INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (id_derechohabiente) REFERENCES DerechoHabiente (id_derechohabiente) ON DELETE RESTRICT,
    FOREIGN KEY (id_trabajador) REFERENCES Trabajador (id_trabajador) ON DELETE RESTRICT,

    CONSTRAINT chk_recep_turno CHECK (turno IN ('Matutino', 'Vespertino', 'Nocturno', 'Guardia')),
    CONSTRAINT chk_recep_longitudes CHECK (
        length(modulo_atencion) <= 50 AND (extension_tel IS NULL OR length(extension_tel) <= 10)
    ),
    CONSTRAINT chk_recep_activo CHECK (activo IN (0, 1))
) STRICT;

CREATE TABLE Medico (
    id_medico INTEGER PRIMARY KEY AUTOINCREMENT,
    id_trabajador INTEGER NOT NULL UNIQUE,
    cedula_profesional TEXT NOT NULL UNIQUE,
    activo INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (id_trabajador) REFERENCES Trabajador (id_trabajador) ON DELETE RESTRICT,

    -- '^[0-9]{7,10}$'
    CONSTRAINT chk_medico_cedula CHECK (
        length(cedula_profesional) BETWEEN 7 AND 10
        AND cedula_profesional NOT GLOB '*[^0-9]*'
    ),
    CONSTRAINT chk_medico_activo CHECK (activo IN (0, 1))
) STRICT;

CREATE TABLE Especialidad (
    id_esp INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,
    descripcion TEXT,

    CONSTRAINT chk_esp_nombre CHECK (length(nombre) <= 100)
) STRICT;

CREATE TABLE MedicoEspecialidad (
    id_medico INTEGER NOT NULL,
    id_esp INTEGER NOT NULL,
    documentos TEXT,
    institucion TEXT,
    PRIMARY KEY (id_medico, id_esp),
    FOREIGN KEY (id_medico) REFERENCES Medico (id_medico) ON DELETE RESTRICT,
    FOREIGN KEY (id_esp) REFERENCES Especialidad (id_esp) ON DELETE RESTRICT,

    -- '^https://[^[:space:]]+$'
    CONSTRAINT chk_medesp_documentos_url CHECK (
        documentos IS NULL OR (
            documentos GLOB 'https://?*'
            AND instr(documentos, ' ') = 0 AND instr(documentos, char(9)) = 0
            AND instr(documentos, char(10)) = 0 AND instr(documentos, char(13)) = 0
        )
    ),
    CONSTRAINT chk_medesp_institucion CHECK (institucion IS NULL OR length(institucion) <= 150)
) STRICT;

CREATE TABLE Enfermero (
    id_enfermero INTEGER PRIMARY KEY AUTOINCREMENT,
    id_trabajador INTEGER NOT NULL UNIQUE,
    activo INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (id_trabajador) REFERENCES Trabajador (id_trabajador) ON DELETE RESTRICT,

    CONSTRAINT chk_enf_activo CHECK (activo IN (0, 1))
) STRICT;

CREATE TABLE EnfermeroEspecialidad (
    id_enfermero INTEGER NOT NULL,
    id_esp INTEGER NOT NULL,
    documentos TEXT,
    institucion TEXT,
    PRIMARY KEY (id_enfermero, id_esp),
    FOREIGN KEY (id_enfermero) REFERENCES Enfermero (id_enfermero) ON DELETE RESTRICT,
    FOREIGN KEY (id_esp) REFERENCES Especialidad (id_esp) ON DELETE RESTRICT,

    CONSTRAINT chk_enfesp_documentos_url CHECK (
        documentos IS NULL OR (
            documentos GLOB 'https://?*'
            AND instr(documentos, ' ') = 0 AND instr(documentos, char(9)) = 0
            AND instr(documentos, char(10)) = 0 AND instr(documentos, char(13)) = 0
        )
    ),
    CONSTRAINT chk_enfesp_institucion CHECK (institucion IS NULL OR length(institucion) <= 150)
) STRICT;

CREATE TABLE Habitacion (
    num_habitacion INTEGER PRIMARY KEY,      -- Número manual, sin AUTOINCREMENT
    piso INTEGER NOT NULL,
    tipo TEXT NOT NULL,
    estado TEXT NOT NULL,

    CONSTRAINT chk_hab_piso CHECK (piso BETWEEN 1 AND 20),
    CONSTRAINT chk_hab_tipo CHECK (tipo IN ('Individual', 'Doble', 'Pediatría', 'UCI', 'Aislamiento')),
    CONSTRAINT chk_hab_estado CHECK (estado IN ('Disponible', 'Ocupada', 'Mantenimiento', 'Limpieza'))
) STRICT;

CREATE TABLE Consultorio (
    num_consultorio INTEGER PRIMARY KEY,
    piso INTEGER NOT NULL,
    departamento TEXT NOT NULL,
    estado TEXT NOT NULL,

    CONSTRAINT chk_cons_piso CHECK (piso BETWEEN 1 AND 20),
    CONSTRAINT chk_cons_departamento CHECK (length(departamento) <= 100),
    CONSTRAINT chk_cons_estado CHECK (estado IN ('Disponible', 'Ocupado', 'Mantenimiento'))
) STRICT;

CREATE TABLE Medicamento (
    id_medicamento INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    presentacion TEXT NOT NULL,
    stock INTEGER NOT NULL,
    lote TEXT NOT NULL,
    caducidad TEXT NOT NULL,
    disponible INTEGER NOT NULL,
    proximo_pedido TEXT,

    CONSTRAINT chk_med_longitudes CHECK (
        length(nombre) <= 150 AND length(presentacion) <= 100 AND length(lote) <= 50
    ),
    CONSTRAINT chk_med_fechas CHECK (
        caducidad IS date(caducidad)
        AND (proximo_pedido IS NULL OR proximo_pedido IS date(proximo_pedido))
    ),
    CONSTRAINT chk_med_disponible CHECK (disponible IN (0, 1)),
    CONSTRAINT chk_med_stock CHECK (stock >= 0),
    CONSTRAINT chk_med_stock_disponible CHECK (NOT (stock = 0 AND disponible = 1))
) STRICT;

CREATE TABLE HistorialMedico (
    id_historial INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Equivalente a gen_random_uuid(): UUID v4 armado con randomblob()
    uuid_publico TEXT NOT NULL UNIQUE DEFAULT (
        lower(hex(randomblob(4))) || '-' ||
        lower(hex(randomblob(2))) || '-4' ||
        substr(lower(hex(randomblob(2))), 2) || '-' ||
        substr('89ab', 1 + (abs(random()) % 4), 1) ||
        substr(lower(hex(randomblob(2))), 2) || '-' ||
        lower(hex(randomblob(6)))
    ),
    id_paciente INTEGER NOT NULL,
    id_medico INTEGER NOT NULL,
    fecha_registro TEXT NOT NULL,
    documento_url TEXT,

    tipo_documento TEXT NOT NULL DEFAULT 'Expediente PDF',
    -- NULL = pendiente de procesar por el algoritmo de extracción
    datos_dinamicos TEXT,
    etiquetas TEXT NOT NULL DEFAULT '[]',   -- Arreglo JSON, ej. '["urgente","cardio"]'

    FOREIGN KEY (id_paciente) REFERENCES Paciente (id_paciente) ON DELETE RESTRICT,
    FOREIGN KEY (id_medico) REFERENCES Medico (id_medico) ON DELETE RESTRICT,

    CONSTRAINT chk_hist_fecha CHECK (fecha_registro IS datetime(fecha_registro)),
    CONSTRAINT chk_hist_tipo CHECK (
        tipo_documento IN ('Expediente PDF', 'Nota Evolución', 'Resumen Urgencias', 'Laboratorio', 'Imagenología', 'Signos Vitales')
    ),
    CONSTRAINT chk_hist_documento_url CHECK (
        documento_url IS NULL OR (
            length(documento_url) <= 500
            AND documento_url GLOB 'https://?*'
            AND instr(documento_url, ' ') = 0 AND instr(documento_url, char(9)) = 0
            AND instr(documento_url, char(10)) = 0 AND instr(documento_url, char(13)) = 0
        )
    ),
    CONSTRAINT chk_hist_json_valido CHECK (
        datos_dinamicos IS NULL OR
        CASE WHEN json_valid(datos_dinamicos) THEN json_type(datos_dinamicos) = 'object' ELSE 0 END
    ),
    CONSTRAINT chk_hist_etiquetas CHECK (
        CASE WHEN json_valid(etiquetas) THEN json_type(etiquetas) = 'array' ELSE 0 END
    ),
    CONSTRAINT chk_hist_no_vacio CHECK (
        documento_url IS NOT NULL
        OR (datos_dinamicos IS NOT NULL AND json(datos_dinamicos) <> '{}')
    )
) STRICT;

-- SQLite no tiene índices GIN; se dejan índices normales y el parcial de pendientes
CREATE INDEX idx_historial_paciente ON HistorialMedico (id_paciente);
CREATE INDEX idx_historial_pendientes ON HistorialMedico (id_historial) WHERE datos_dinamicos IS NULL;

CREATE TABLE Cita (
    id_cita INTEGER PRIMARY KEY AUTOINCREMENT,
    id_paciente INTEGER NOT NULL,
    id_medico INTEGER NOT NULL,
    id_recepcionista INTEGER,
    num_consultorio INTEGER,
    fecha_hora TEXT NOT NULL,
    motivo TEXT NOT NULL,
    diagnostico TEXT,
    estado TEXT NOT NULL,

    FOREIGN KEY (id_paciente) REFERENCES Paciente (id_paciente) ON DELETE RESTRICT,
    FOREIGN KEY (id_medico) REFERENCES Medico (id_medico) ON DELETE RESTRICT,
    FOREIGN KEY (id_recepcionista) REFERENCES Recepcionista (id_recepcionista) ON DELETE RESTRICT,
    FOREIGN KEY (num_consultorio) REFERENCES Consultorio (num_consultorio) ON DELETE RESTRICT,

    CONSTRAINT chk_cita_fecha CHECK (fecha_hora IS datetime(fecha_hora)),
    CONSTRAINT chk_cita_estado CHECK (estado IN ('Programada', 'Completada', 'Cancelada', 'No asistió')),
    CONSTRAINT chk_cita_diagnostico_coherente CHECK (
        (estado = 'Completada' AND diagnostico IS NOT NULL) OR
        (estado <> 'Completada' AND diagnostico IS NULL)
    )
) STRICT;

CREATE TABLE Ingreso (
    id_ingreso INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_ingreso TEXT NOT NULL,
    fecha_alta TEXT,
    id_cita INTEGER NOT NULL UNIQUE,
    num_habitacion INTEGER NOT NULL,
    id_recepcionista INTEGER,

    FOREIGN KEY (id_cita) REFERENCES Cita (id_cita) ON DELETE RESTRICT,
    FOREIGN KEY (num_habitacion) REFERENCES Habitacion (num_habitacion) ON DELETE RESTRICT,
    FOREIGN KEY (id_recepcionista) REFERENCES Recepcionista (id_recepcionista) ON DELETE RESTRICT,

    CONSTRAINT chk_ingreso_formato CHECK (
        fecha_ingreso IS datetime(fecha_ingreso)
        AND (fecha_alta IS NULL OR fecha_alta IS datetime(fecha_alta))
    ),
    -- Al tener el mismo formato ISO, comparar texto equivale a comparar fechas
    CONSTRAINT chk_ingreso_fechas CHECK (fecha_alta IS NULL OR fecha_alta > fecha_ingreso)
) STRICT;

CREATE TABLE IngresoEmergencia (
    id_ingreso_emergencia INTEGER PRIMARY KEY AUTOINCREMENT,
    id_paciente INTEGER NOT NULL,
    id_medico INTEGER NOT NULL,
    id_recepcionista INTEGER,
    num_habitacion INTEGER,
    fecha_hora TEXT NOT NULL,
    motivo TEXT NOT NULL,
    nivel_urgencia TEXT NOT NULL,
    diagnostico TEXT,

    FOREIGN KEY (id_paciente) REFERENCES Paciente (id_paciente) ON DELETE RESTRICT,
    FOREIGN KEY (id_medico) REFERENCES Medico (id_medico) ON DELETE RESTRICT,
    FOREIGN KEY (id_recepcionista) REFERENCES Recepcionista (id_recepcionista) ON DELETE RESTRICT,
    FOREIGN KEY (num_habitacion) REFERENCES Habitacion (num_habitacion) ON DELETE RESTRICT,

    CONSTRAINT chk_emergencia_fecha CHECK (fecha_hora IS datetime(fecha_hora)),
    CONSTRAINT chk_emergencia_nivel CHECK (nivel_urgencia IN ('Crítico', 'Alto', 'Medio', 'Bajo'))
) STRICT;

CREATE TABLE Receta (
    id_receta INTEGER PRIMARY KEY AUTOINCREMENT,
    id_cita INTEGER,
    id_ingreso_emergencia INTEGER,
    fecha_emision TEXT NOT NULL,
    tratamiento TEXT NOT NULL,

    FOREIGN KEY (id_cita) REFERENCES Cita (id_cita) ON DELETE RESTRICT,
    FOREIGN KEY (id_ingreso_emergencia) REFERENCES IngresoEmergencia (id_ingreso_emergencia) ON DELETE RESTRICT,

    CONSTRAINT chk_receta_fecha CHECK (fecha_emision IS date(fecha_emision)),
    -- XOR: equivalente a num_nonnulls(...) = 1
    CONSTRAINT chk_receta_xor_origen CHECK (
        (id_cita IS NOT NULL) + (id_ingreso_emergencia IS NOT NULL) = 1
    ),
    -- Equivalente a tratamiento ?& ARRAY[...]: las tres llaves deben existir
    CONSTRAINT chk_receta_json_estructura CHECK (
        CASE WHEN json_valid(tratamiento) THEN
            json_type(tratamiento) = 'object'
            AND json_type(tratamiento, '$.diagnostico') IS NOT NULL
            AND json_type(tratamiento, '$.medicamentos') IS NOT NULL
            AND json_type(tratamiento, '$.indicaciones_generales') IS NOT NULL
        ELSE 0 END
    )
) STRICT;

CREATE TABLE DetalleReceta (
    id_receta INTEGER NOT NULL,
    id_medicamento INTEGER NOT NULL,
    dosis_indicaciones TEXT NOT NULL,
    PRIMARY KEY (id_receta, id_medicamento),
    FOREIGN KEY (id_receta) REFERENCES Receta (id_receta) ON DELETE CASCADE,
    FOREIGN KEY (id_medicamento) REFERENCES Medicamento (id_medicamento) ON DELETE RESTRICT
) STRICT;

-- =====================================================================
-- TRIGGERS: validaciones que dependen de la fecha actual.
-- SQLite no permite date('now') ni CURRENT_DATE dentro de un CHECK.
-- Solo se validan al insertar o al cambiar la columna, igual que en Postgres.
-- date('now', 'localtime') usa la zona horaria de la máquina que corre SQLite.
-- =====================================================================

CREATE TRIGGER trg_dh_fecha_nac_ins
BEFORE INSERT ON DerechoHabiente
WHEN NEW.fecha_nacimiento > date('now', 'localtime')
BEGIN
    SELECT RAISE(ABORT, 'fecha_nacimiento no puede ser futura');
END;

CREATE TRIGGER trg_dh_fecha_nac_upd
BEFORE UPDATE OF fecha_nacimiento ON DerechoHabiente
WHEN NEW.fecha_nacimiento IS NOT OLD.fecha_nacimiento
 AND NEW.fecha_nacimiento > date('now', 'localtime')
BEGIN
    SELECT RAISE(ABORT, 'fecha_nacimiento no puede ser futura');
END;

CREATE TRIGGER trg_trab_fecha_ing_ins
BEFORE INSERT ON Trabajador
WHEN NEW.fecha_ingreso > date('now', 'localtime')
BEGIN
    SELECT RAISE(ABORT, 'fecha_ingreso no puede ser futura');
END;

CREATE TRIGGER trg_trab_fecha_ing_upd
BEFORE UPDATE OF fecha_ingreso ON Trabajador
WHEN NEW.fecha_ingreso IS NOT OLD.fecha_ingreso
 AND NEW.fecha_ingreso > date('now', 'localtime')
BEGIN
    SELECT RAISE(ABORT, 'fecha_ingreso no puede ser futura');
END;

-- Margen de 15 días: si se cambia, hay que cambiarlo en ambos triggers
CREATE TRIGGER trg_medicamento_caducidad_ins
BEFORE INSERT ON Medicamento
WHEN NEW.caducidad < date('now', 'localtime', '+15 days')
BEGIN
    SELECT RAISE(ABORT, 'La caducidad debe ser al menos 15 días posterior a hoy');
END;

CREATE TRIGGER trg_medicamento_caducidad_upd
BEFORE UPDATE OF caducidad ON Medicamento
WHEN NEW.caducidad IS NOT OLD.caducidad
 AND NEW.caducidad < date('now', 'localtime', '+15 days')
BEGIN
    SELECT RAISE(ABORT, 'La caducidad debe ser al menos 15 días posterior a hoy');
END;