PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS progreso_materias;
DROP TABLE IF EXISTS evaluaciones;
DROP TABLE IF EXISTS usuario_curso;
DROP TABLE IF EXISTS sesiones;
DROP TABLE IF EXISTS usuarios;
DROP TABLE IF EXISTS materias;
DROP TABLE IF EXISTS cursos;

CREATE TABLE cursos (
    id_curso INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_curso TEXT NOT NULL UNIQUE
);

CREATE TABLE materias (
    id_materia INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_materia TEXT NOT NULL UNIQUE
);

CREATE TABLE usuarios (
    id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_completo TEXT NOT NULL,
    correo TEXT NOT NULL UNIQUE,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    rol TEXT NOT NULL CHECK (rol IN ('estudiante','administrador')),
    activo INTEGER DEFAULT 1,
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sesiones (
    id_sesion INTEGER PRIMARY KEY AUTOINCREMENT,
    id_usuario INTEGER NOT NULL,
    fecha_inicio DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_fin DATETIME,
    estado TEXT NOT NULL DEFAULT 'activa'
    CHECK (estado IN ('activa', 'cerrada')),
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario)
);

CREATE TABLE usuario_curso (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_usuario INTEGER NOT NULL,
    id_curso INTEGER NOT NULL,
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario),
    FOREIGN KEY (id_curso) REFERENCES cursos(id_curso)
);

CREATE TABLE progreso_materias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_usuario INTEGER NOT NULL,
    id_materia INTEGER NOT NULL,
    progreso INTEGER DEFAULT 0,
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario),
    FOREIGN KEY (id_materia) REFERENCES materias(id_materia)
);

CREATE TABLE evaluaciones (
    id_evaluacion INTEGER PRIMARY KEY AUTOINCREMENT,
    id_usuario INTEGER NOT NULL,
    titulo TEXT NOT NULL,
    fecha TEXT,
    estado TEXT DEFAULT 'pendiente',
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario)
);

INSERT INTO cursos (nombre_curso) VALUES
('6°'),
('7°'),
('8°'),
('9°'),
('10°'),
('11°');

INSERT INTO materias (nombre_materia) VALUES
('Matemáticas'),
('Ciencias'),
('Español'),
('Inglés');

INSERT INTO usuarios (
    nombre_completo,
    correo,
    username,
    password_hash,
    rol
)
VALUES (
    'Sara',
    'sara@gmail.com',
    'sara',
    '123456',
    'estudiante'
);

INSERT INTO usuario_curso (
    id_usuario,
    id_curso
)
VALUES (
    1,
    5
);

INSERT INTO progreso_materias (
    id_usuario,
    id_materia,
    progreso
)
VALUES
(1,1,75),
(1,2,60),
(1,3,90),
(1,4,40);

INSERT INTO evaluaciones (
    id_usuario,
    titulo,
    fecha,
    estado
)
VALUES
(1,'Quiz Matemáticas','2026-05-15','pendiente'),
(1,'Evaluación Inglés','2026-05-20','pendiente');