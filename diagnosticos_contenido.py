# -*- coding: utf-8 -*-
"""Quiz diagnóstico por curso y lógica de ruta de lecciones."""

import copy

MENSAJES_NIVEL = {
    "basico": (
        "Tu resultado es nivel básico. Comenzaremos por lecciones introductorias "
        "y reforzaremos los conceptos donde necesitas más apoyo."
    ),
    "intermedio": (
        "Tu resultado es nivel intermedio. Seguiremos una ruta equilibrada, "
        "priorizando los temas en los que tuviste más dificultad."
    ),
    "avanzado": (
        "Tu resultado es nivel avanzado. Puedes avanzar hacia temas más exigentes; "
        "algunas lecciones básicas quedarán como repaso opcional."
    ),
}

TITULOS_NIVEL = {
    "basico": "Nivel básico",
    "intermedio": "Nivel intermedio",
    "avanzado": "Nivel avanzado",
}

NIVEL_LECCION_POR_CURSO = {
    "fundamentos-algebra": {
        "intro-ecuaciones-lineales": "basico",
        "sistemas-ecuaciones-2x2": "basico",
        "funciones-cuadraticas": "intermedio",
        "operaciones-polinomios": "avanzado",
    },
    "biologia-molecular": {
        "doble-helice-replicacion": "basico",
        "estructura-adn": "basico",
        "organulos-metabolismo": "intermedio",
        "mutaciones-expresion": "avanzado",
    },
    "fisica-cuantica-1": {
        "luz-naturaleza-cuantica": "basico",
        "experimento-doble-rendija": "basico",
        "dualidad-onda-particula": "intermedio",
        "heisenberg-medicion": "avanzado",
    },
    "quimica-organica": {
        "enlaces-geometria": "basico",
        "alcanos-alquenos": "basico",
        "alcoholes-eteres": "intermedio",
        "acidos-carboxilicos": "avanzado",
    },
    "probabilidad-estadistica": {
        "eventos-espacios": "basico",
        "media-mediana-desviacion": "basico",
        "variables-aleatorias": "intermedio",
        "regresion-lineal": "avanzado",
    },
    "algoritmos-logica": {
        "diagramas-flujo": "basico",
        "busqueda-ordenamiento": "basico",
        "recursion-intro": "intermedio",
        "complejidad-on": "avanzado",
    },
}

DIAGNOSTICO_POR_CURSO = {
    "fundamentos-algebra": {
        "titulo_tema": "Diagnóstico de álgebra",
        "preguntas": [
            {
                "tipo": "Opción múltiple",
                "enunciado": "¿Cuál es la solución de x en 2x + 6 = 14?",
                "opciones": {"A": "x = 4", "B": "x = 10", "C": "x = 2", "D": "x = 7"},
                "correcta": "A",
                "explicacion": "2x = 8, entonces x = 4.",
                "pista": "Reste 6 a ambos lados y divida por 2.",
                "leccion_id": "intro-ecuaciones-lineales",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "Al resolver un sistema 2×2 por sustitución, lo primero es:",
                "opciones": {
                    "A": "Despejar una variable en una ecuación",
                    "B": "Multiplicar ambas ecuaciones por cero",
                    "C": "Eliminar todas las constantes",
                    "D": "Graficar sin variables",
                },
                "correcta": "A",
                "explicacion": "Sustitución requiere expresar una incógnita en función de la otra.",
                "pista": "Piense en despeje de variable.",
                "leccion_id": "sistemas-ecuaciones-2x2",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "La forma general de una función cuadrática es:",
                "opciones": {
                    "A": "f(x) = ax² + bx + c",
                    "B": "f(x) = mx + b",
                    "C": "f(x) = a/x",
                    "D": "f(x) = √x",
                },
                "correcta": "A",
                "explicacion": "La cuadrática tiene término x².",
                "pista": "Busque el exponente 2.",
                "leccion_id": "funciones-cuadraticas",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "Factorizar x² − 9 es equivalente a:",
                "opciones": {
                    "A": "(x − 3)(x + 3)",
                    "B": "(x − 9)(x + 1)",
                    "C": "x(x − 9)",
                    "D": "(x − 3)²",
                },
                "correcta": "A",
                "explicacion": "Es una diferencia de cuadrados.",
                "pista": "a² − b² = (a − b)(a + b).",
                "leccion_id": "operaciones-polinomios",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "Al sumar polinomios, solo se combinan:",
                "opciones": {
                    "A": "Términos semejantes",
                    "B": "Términos con distinto exponente siempre",
                    "C": "Solo constantes",
                    "D": "Ningún término",
                },
                "correcta": "A",
                "explicacion": "Solo términos con igual grado en la variable.",
                "pista": "Mismo exponente en la variable.",
                "leccion_id": "operaciones-polinomios",
            },
        ],
    },
    "biologia-molecular": {
        "titulo_tema": "Diagnóstico de biología molecular",
        "preguntas": [
            {
                "tipo": "Opción múltiple",
                "enunciado": "¿Qué molécula almacena la información genética?",
                "opciones": {"A": "ADN", "B": "Glucosa", "C": "Agua", "D": "Oxígeno"},
                "correcta": "A",
                "explicacion": "El ADN es el material genético principal.",
                "pista": "Ácido desoxirribonucleico.",
                "leccion_id": "estructura-adn",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "Un nucleótido del ADN contiene:",
                "opciones": {
                    "A": "Fosfato, desoxirribosa y base nitrogenada",
                    "B": "Solo proteínas",
                    "C": "Ribosa y lípidos",
                    "D": "Glucosa y aminoácidos",
                },
                "correcta": "A",
                "explicacion": "Cada nucleótido tiene fosfato, azúcar y base.",
                "pista": "No confunda con aminoácidos.",
                "leccion_id": "estructura-adn",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "La estructura en doble hélice del ADN fue propuesta por:",
                "opciones": {
                    "A": "Watson y Crick",
                    "B": "Darwin",
                    "C": "Pasteur",
                    "D": "Mendel",
                },
                "correcta": "A",
                "explicacion": "Modelo de la doble hélice en 1953.",
                "pista": "Pareja de científicos famosa.",
                "leccion_id": "doble-helice-replicacion",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "La síntesis de proteínas a partir del ARNm ocurre en:",
                "opciones": {
                    "A": "Ribosomas",
                    "B": "Lisosomas",
                    "C": "Pared celular",
                    "D": "Vacuolas únicamente",
                },
                "correcta": "A",
                "explicacion": "Traducción en ribosomas.",
                "pista": "Orgánulo de traducción.",
                "leccion_id": "organulos-metabolismo",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "Una mutación puede afectar:",
                "opciones": {
                    "A": "La expresión o secuencia de genes",
                    "B": "Solo el color del laboratorio",
                    "C": "La gravedad",
                    "D": "El número de planetas",
                },
                "correcta": "A",
                "explicacion": "Las mutaciones alteran información genética.",
                "pista": "Relación con genes.",
                "leccion_id": "mutaciones-expresion",
            },
        ],
    },
    "fisica-cuantica-1": {
        "titulo_tema": "Diagnóstico de física cuántica",
        "preguntas": [
            {
                "tipo": "Opción múltiple",
                "enunciado": "Un fotón es:",
                "opciones": {
                    "A": "Una partícula de luz (cuanto de energía)",
                    "B": "Un tipo de átomo pesado",
                    "C": "Una onda sonora",
                    "D": "Un imán permanente",
                },
                "correcta": "A",
                "explicacion": "E = hf describe la energía del fotón.",
                "pista": "Relacionado con luz y energía.",
                "leccion_id": "luz-naturaleza-cuantica",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "El experimento de la doble rendija demuestra:",
                "opciones": {
                    "A": "Interferencia ondulatoria",
                    "B": "Solo reflexión especular",
                    "C": "Caída libre clásica",
                    "D": "Fusión nuclear",
                },
                "correcta": "A",
                "explicacion": "Patrón de franjas por superposición de ondas.",
                "pista": "Franjas claras y oscuras.",
                "leccion_id": "experimento-doble-rendija",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "La dualidad onda-partícula indica que:",
                "opciones": {
                    "A": "Materia y radiación muestran propiedades de onda y partícula",
                    "B": "Solo la luz es partícula",
                    "C": "Los electrones no tienen masa",
                    "D": "No hay experimentos que la apoyen",
                },
                "correcta": "A",
                "explicacion": "Comportamiento dual según el experimento.",
                "pista": "Onda y partícula a la vez.",
                "leccion_id": "dualidad-onda-particula",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "La energía de un fotón se calcula como:",
                "opciones": {"A": "E = hf", "B": "E = mv", "C": "E = Fd", "D": "E = mgh"},
                "correcta": "A",
                "explicacion": "Planck: proporcional a la frecuencia.",
                "pista": "Constante h y frecuencia.",
                "leccion_id": "luz-naturaleza-cuantica",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "El principio de incertidumbre limita:",
                "opciones": {
                    "A": "La precisión simultánea de magnitudes conjugadas",
                    "B": "La velocidad de la luz",
                    "C": "La masa del protón",
                    "D": "La carga del neutrón",
                },
                "correcta": "A",
                "explicacion": "Heisenberg: posición y momento no precisos a la vez.",
                "pista": "Medición cuántica.",
                "leccion_id": "heisenberg-medicion",
            },
        ],
    },
    "quimica-organica": {
        "titulo_tema": "Diagnóstico de química orgánica",
        "preguntas": [
            {
                "tipo": "Opción múltiple",
                "enunciado": "La química orgánica estudia principalmente compuestos de:",
                "opciones": {"A": "Carbono", "B": "Hierro", "C": "Oro", "D": "Helio"},
                "correcta": "A",
                "explicacion": "El carbono forma la base de moléculas orgánicas.",
                "pista": "Elemento de la vida.",
                "leccion_id": "enlaces-geometria",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "Un enlace simple C−C en alcanos es del tipo:",
                "opciones": {"A": "Sigma (σ)", "B": "Solo pi (π)", "C": "Iónico", "D": "Metálico"},
                "correcta": "A",
                "explicacion": "Alcanos: enlaces σ saturados.",
                "pista": "Cadenas saturadas.",
                "leccion_id": "alcanos-alquenos",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "El grupo funcional −OH corresponde a:",
                "opciones": {"A": "Alcoholes", "B": "Aldehídos", "C": "Cetonas", "D": "Ésteres solos"},
                "correcta": "A",
                "explicacion": "Hidroxilo unido a carbono.",
                "pista": "Nombre del grupo.",
                "leccion_id": "alcoholes-eteres",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "Los alquenos tienen al menos un enlace:",
                "opciones": {"A": "Doble C=C", "B": "Triple C≡C", "C": "Iónico", "D": "Metálico"},
                "correcta": "A",
                "explicacion": "Insaturación con doble enlace.",
                "pista": "Sufijo -eno.",
                "leccion_id": "alcanos-alquenos",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "Los ácidos carboxílicos contienen el grupo:",
                "opciones": {"A": "−COOH", "B": "−NH₂", "C": "−OH solo", "D": "−CH₃"},
                "correcta": "A",
                "explicacion": "Grupo carboxilo característico.",
                "pista": "Ácido orgánico.",
                "leccion_id": "acidos-carboxilicos",
            },
        ],
    },
    "probabilidad-estadistica": {
        "titulo_tema": "Diagnóstico de probabilidad y estadística",
        "preguntas": [
            {
                "tipo": "Opción múltiple",
                "enunciado": "La probabilidad de un evento seguro es:",
                "opciones": {"A": "1", "B": "0", "C": "0,5", "D": "−1"},
                "correcta": "A",
                "explicacion": "Evento seguro: probabilidad 1.",
                "pista": "Máximo valor posible.",
                "leccion_id": "eventos-espacios",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "El espacio muestral es:",
                "opciones": {
                    "A": "El conjunto de todos los resultados posibles",
                    "B": "Solo el resultado favorito",
                    "C": "La media aritmética",
                    "D": "La desviación típica",
                },
                "correcta": "A",
                "explicacion": "Contiene todos los desenlaces posibles.",
                "pista": "Todos los resultados.",
                "leccion_id": "eventos-espacios",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "La media de 2, 4 y 6 es:",
                "opciones": {"A": "4", "B": "6", "C": "2", "D": "12"},
                "correcta": "A",
                "explicacion": "(2+4+6)/3 = 4.",
                "pista": "Suma dividida por cantidad.",
                "leccion_id": "media-mediana-desviacion",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "Una variable aleatoria discreta toma:",
                "opciones": {
                    "A": "Valores contables (enteros o listables)",
                    "B": "Solo valores negativos",
                    "C": "Cualquier valor del continuo siempre",
                    "D": "Solo cero",
                },
                "correcta": "A",
                "explicacion": "Discreta: valores separables.",
                "pista": "Contar resultados.",
                "leccion_id": "variables-aleatorias",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "La regresión lineal busca:",
                "opciones": {
                    "A": "Modelar relación entre variables con una recta",
                    "B": "Eliminar todos los datos",
                    "C": "Solo calcular la moda",
                    "D": "Ignorar tendencias",
                },
                "correcta": "A",
                "explicacion": "Ajuste de recta a datos.",
                "pista": "Recta de mejor ajuste.",
                "leccion_id": "regresion-lineal",
            },
        ],
    },
    "algoritmos-logica": {
        "titulo_tema": "Diagnóstico de algoritmos",
        "preguntas": [
            {
                "tipo": "Opción múltiple",
                "enunciado": "Un diagrama de flujo sirve para:",
                "opciones": {
                    "A": "Representar pasos de un algoritmo",
                    "B": "Medir temperatura",
                    "C": "Escribir poesía",
                    "D": "Eliminar variables",
                },
                "correcta": "A",
                "explicacion": "Visualiza la lógica paso a paso.",
                "pista": "Pasos y decisiones.",
                "leccion_id": "diagramas-flujo",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "La búsqueda lineal en el peor caso revisa:",
                "opciones": {
                    "A": "Hasta n elementos",
                    "B": "Un solo elemento siempre",
                    "C": "log n únicamente",
                    "D": "Ningún elemento",
                },
                "correcta": "A",
                "explicacion": "Complejidad O(n) en el peor caso.",
                "pista": "Recorrer la lista.",
                "leccion_id": "busqueda-ordenamiento",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "La recursión ocurre cuando una función:",
                "opciones": {
                    "A": "Se llama a sí misma",
                    "B": "No usa variables",
                    "C": "Solo imprime texto",
                    "D": "No tiene casos base",
                },
                "correcta": "A",
                "explicacion": "Definición por auto-llamada con caso base.",
                "pista": "Función que se invoca a sí misma.",
                "leccion_id": "recursion-intro",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "O(n²) comparado con O(n) para n grande:",
                "opciones": {
                    "A": "O(n²) crece más rápido",
                    "B": "Son iguales",
                    "C": "O(n) es siempre peor",
                    "D": "O(n²) es constante",
                },
                "correcta": "A",
                "explicacion": "n² domina a n al crecer.",
                "pista": "Compare n=1000.",
                "leccion_id": "complejidad-on",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "Un algoritmo de ordenamiento ordena:",
                "opciones": {
                    "A": "Elementos según un criterio",
                    "B": "Solo imágenes",
                    "C": "Archivos del disco sin datos",
                    "D": "Nada útil",
                },
                "correcta": "A",
                "explicacion": "Ordena según comparación de valores.",
                "pista": "Bubble, merge, quick...",
                "leccion_id": "busqueda-ordenamiento",
            },
        ],
    },
}


def obtener_diagnostico_curso(slug):
    if slug not in DIAGNOSTICO_POR_CURSO:
        return None
    return copy.deepcopy(DIAGNOSTICO_POR_CURSO[slug])


def calcular_nivel_diagnostico(porcentaje):
    if porcentaje < 40:
        return "basico"
    if porcentaje < 70:
        return "intermedio"
    return "avanzado"


def evaluar_respuestas_diagnostico(slug, respuestas):
    """respuestas: lista de {indice, elegida}. Devuelve dict con puntaje y errores."""
    quiz = DIAGNOSTICO_POR_CURSO.get(slug)
    if not quiz:
        return None

    preguntas = quiz["preguntas"]
    correctas = 0
    errores_por_leccion = {}
    detalle = []

    for item in respuestas:
        idx = item.get("indice")
        elegida = item.get("elegida")
        if idx is None or idx < 0 or idx >= len(preguntas):
            continue
        pregunta = preguntas[idx]
        acierto = elegida == pregunta.get("correcta")
        if acierto:
            correctas += 1
        else:
            lid = pregunta.get("leccion_id")
            if lid:
                errores_por_leccion[lid] = errores_por_leccion.get(lid, 0) + 1
        detalle.append(
            {
                "indice": idx,
                "elegida": elegida,
                "correcta": pregunta.get("correcta"),
                "acierto": acierto,
                "leccion_id": pregunta.get("leccion_id"),
            }
        )

    total = len(preguntas)
    porcentaje = round((correctas / total) * 100) if total else 0
    nivel = calcular_nivel_diagnostico(porcentaje)

    return {
        "correctas": correctas,
        "total": total,
        "porcentaje": porcentaje,
        "nivel": nivel,
        "errores_por_leccion": errores_por_leccion,
        "detalle": detalle,
    }


def aplicar_ruta_diagnostico_a_curso(curso, diagnostico):
    if not diagnostico:
        return curso

    slug = curso.get("slug")
    nivel = diagnostico.get("nivel", "intermedio")
    errores = diagnostico.get("errores_por_leccion", {})
    niveles_leccion = NIVEL_LECCION_POR_CURSO.get(slug, {})

    lecciones = [copy.deepcopy(l) for l in curso.get("lecciones", [])]
    orden_original = {l["id"]: i for i, l in enumerate(lecciones)}

    for leccion in lecciones:
        lid = leccion["id"]
        debilidad = errores.get(lid, 0)
        tier = niveles_leccion.get(lid, "intermedio")

        leccion["bloqueada"] = False
        leccion["opcional"] = False
        leccion["recomendada"] = False
        leccion["etiqueta_ruta"] = ""

        prioridad = debilidad * 1000
        if debilidad > 0:
            leccion["recomendada"] = True
            leccion["etiqueta_ruta"] = "Prioridad para ti"
            prioridad += 500
        elif nivel == "basico" and tier == "basico":
            prioridad += 300
        elif nivel == "intermedio" and tier == "intermedio":
            prioridad += 200
        elif nivel == "avanzado" and tier == "avanzado":
            prioridad += 300

        if nivel == "basico" and tier == "avanzado" and debilidad == 0:
            leccion["bloqueada"] = True
            leccion["etiqueta_ruta"] = "Disponible después del refuerzo básico"
        elif nivel == "avanzado" and tier == "basico" and debilidad == 0:
            leccion["opcional"] = True
            if not leccion["etiqueta_ruta"]:
                leccion["etiqueta_ruta"] = "Repaso opcional"

        leccion["prioridad_ruta"] = prioridad - orden_original.get(lid, 0) * 0.1

    lecciones.sort(key=lambda x: -x.get("prioridad_ruta", 0))

    en_progreso_asignado = False
    for leccion in lecciones:
        if leccion.get("estado") == "completado":
            continue
        if leccion.get("bloqueada"):
            leccion["estado"] = "pendiente"
            continue
        if not en_progreso_asignado:
            leccion["estado"] = "en_progreso"
            en_progreso_asignado = True
        else:
            if leccion.get("estado") == "en_progreso":
                leccion["estado"] = "pendiente"

    curso["lecciones"] = lecciones
    curso["diagnostico_nivel"] = nivel
    curso["diagnostico_titulo_nivel"] = TITULOS_NIVEL.get(nivel, nivel)
    curso["diagnostico_mensaje"] = MENSAJES_NIVEL.get(nivel, "")
    curso["diagnostico_porcentaje"] = diagnostico.get("porcentaje", 0)
    return curso


def resolver_leccion_actual_con_ruta(curso):
    for leccion in curso.get("lecciones", []):
        if leccion.get("bloqueada"):
            continue
        if leccion.get("estado") != "completado":
            return leccion
    if curso.get("lecciones"):
        for leccion in curso["lecciones"]:
            if not leccion.get("bloqueada"):
                return leccion
    return None
