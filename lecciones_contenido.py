from quizzes_contenido import obtener_quiz_curso

CONTENIDO_LECCIONES = {
    "fundamentos-algebra:funciones-cuadraticas": {
        "video_tiempo_actual": "22:15",
        "video_duracion": "50:00",
        "video_progreso": 44,
        "titulo_tema": "Funciones cuadráticas: vértice y raíces",
        "explicacion": (
            "Una función cuadrática tiene la forma f(x) = ax² + bx + c, con a ≠ 0. "
            "Su gráfica es una parábola que puede abrir hacia arriba o hacia abajo según el signo de a. "
            "El vértice indica el valor máximo o mínimo, y las raíces son los valores de x donde la función se anula."
        ),
        "definiciones": [
            {"termino": "Forma general", "definicion": "f(x) = ax² + bx + c, donde a, b y c son coeficientes reales."},
            {"termino": "Vértice", "definicion": "Punto (h, k) donde la parábola alcanza su valor extremo: h = -b/(2a), k = f(h)."},
            {"termino": "Raíces", "definicion": "Soluciones de ax² + bx + c = 0; pueden calcularse con la fórmula general o factorización."},
            {"termino": "Discriminante", "definicion": "Δ = b² - 4ac; determina si hay dos, una o ninguna raíz real."},
        ],
        "formulas": [
            "Vértice: V = (-b/(2a), f(-b/(2a)))",
            "Fórmula general: x = (-b ± √(b² - 4ac)) / (2a)",
            "Forma canónica: f(x) = a(x - h)² + k",
        ],
        "ejemplo": {
            "enunciado": "Encuentre el vértice y las raíces de f(x) = x² - 4x + 3.",
            "solucion": (
                "h = -(-4)/(2·1) = 2; f(2) = 4 - 8 + 3 = -1, entonces V = (2, -1). "
                "Factorizando: x² - 4x + 3 = (x - 1)(x - 3), raíces x = 1 y x = 3."
            ),
        },
        "practica": {
            "pregunta": "¿Cuántas raíces reales tiene f(x) = 2x² + 3x + 5 si Δ = b² - 4ac?",
            "pista": "Calcule Δ = 9 - 40 y compare con cero.",
        },
        "notas": [
            "Si a > 0 la parábola abre hacia arriba; si a < 0, hacia abajo.",
            "Dos raíces distintas cuando Δ > 0; una raíz doble cuando Δ = 0.",
        ],
        "recursos": [
            {"titulo": "Hoja de fórmulas de álgebra", "url": "#"},
            {"titulo": "Simulador de parábolas", "url": "#"},
        ],
        "preguntas": [
            {"pregunta": "¿Qué representa el vértice?", "respuesta": "El punto máximo o mínimo de la parábola."},
            {"pregunta": "¿Cuándo no hay raíces reales?", "respuesta": "Cuando el discriminante es negativo (Δ < 0)."},
        ],
        "temas_relacionados": ["Ecuaciones lineales", "Operaciones polinomiales", "Factorización"],
        "recursos_descargables": [
            {"titulo": "Guía de funciones cuadráticas.pdf", "url": "#"},
            {"titulo": "Ejercicios resueltos.pdf", "url": "#"},
        ],
    },
    "biologia-molecular:estructura-adn": {
        "video_tiempo_actual": "28:40",
        "video_duracion": "60:00",
        "video_progreso": 48,
        "titulo_tema": "Estructura del ADN",
        "explicacion": (
            "El ADN (ácido desoxirribonucleico) almacena la información genética en forma de secuencia de nucleótidos. "
            "Cada nucleótido tiene un grupo fosfato, un azúcar desoxirribosa y una base nitrogenada (A, T, C o G). "
            "Las bases se emparejan por complementariedad (A-T, C-G), formando una doble hélice estable."
        ),
        "definiciones": [
            {"termino": "Nucleótido", "definicion": "Unidad básica del ADN compuesta por fosfato, desoxirribosa y base nitrogenada."},
            {"termino": "Bases nitrogenadas", "definicion": "Adenina (A), Timina (T), Citosina (C) y Guanina (G); A se enlaza con T y C con G."},
            {"termino": "Doble hélice", "definicion": "Estructura en espiral de dos cadenas antiparalelas unidas por puentes de hidrógeno."},
            {"termino": "Síntesis de proteínas", "definicion": "Proceso en el que la información del ADN se transcribe al ARN y se traduce en aminoácidos."},
        ],
        "formulas": [],
        "ejemplo": {
            "enunciado": "Si una cadena tiene la secuencia 5'-ATGCGT-3', ¿cuál es la cadena complementaria?",
            "solucion": "A↔T y C↔G: la cadena complementaria es 3'-TACGCA-5' (lectura antiparalela).",
        },
        "practica": {
            "pregunta": "¿Por qué la timina solo se empareja con la adenina?",
            "pista": "Piense en el tamaño de las bases purinas y pirimidinas.",
        },
        "notas": [
            "La replicación es semiconservativa: cada cadena sirve de molde para una nueva.",
            "El ARN usa uracilo en lugar de timina en la transcripción.",
        ],
        "recursos": [
            {"titulo": "Modelo 3D de doble hélice", "url": "#"},
            {"titulo": "Atlas de genética molecular", "url": "#"},
        ],
        "preguntas": [
            {"pregunta": "¿Qué enlaza las dos cadenas?", "respuesta": "Puentes de hidrógeno entre bases complementarias."},
            {"pregunta": "¿Dónde ocurre la traducción?", "respuesta": "En los ribosomas del citoplasma (ARN mensajero)."},
        ],
        "temas_relacionados": ["Síntesis de proteínas", "Replicación del ADN", "Mecanismos celulares"],
        "recursos_descargables": [
            {"titulo": "Diagrama del ADN.pdf", "url": "#"},
            {"titulo": "Glosario de biología molecular.pdf", "url": "#"},
        ],
    },
    "fisica-cuantica-1:dualidad-onda-particula": {
        "video_tiempo_actual": "31:05",
        "video_duracion": "55:00",
        "video_progreso": 56,
        "titulo_tema": "Dualidad onda-partícula",
        "explicacion": (
            "La materia y la radiación exhiben propiedades de onda y de partícula según el experimento. "
            "Los fotones se comportan como partículas de energía E = hf, pero la interferencia en la doble rendija "
            "muestra comportamiento ondulatorio. Los electrones también forman patrones de interferencia."
        ),
        "definiciones": [
            {"termino": "Fotón", "definicion": "Cuantum de radiación electromagnética con energía E = hf y momento p = h/λ."},
            {"termino": "Electrón", "definicion": "Partícula fundamental; en experimentos cuánticos muestra interferencia como una onda."},
            {"termino": "Experimento de doble rendija", "definicion": "Demuestra interferencia; con detección individual, el patrón desaparece gradualmente."},
            {"termino": "Comportamiento cuántico", "definicion": "Descripción probabilística del estado mediante la función de onda."},
        ],
        "formulas": [
            "Energía del fotón: E = h·f = h·c/λ",
            "Longitud de onda de de Broglie: λ = h/p",
            "Constante de Planck: h ≈ 6,626 × 10⁻³⁴ J·s",
        ],
        "ejemplo": {
            "enunciado": "Calcule la longitud de onda de de Broglie de un electrón con p = 9,1×10⁻³¹ kg·m/s.",
            "solucion": "λ = h/p ≈ (6,626×10⁻³⁴)/(9,1×10⁻³¹) ≈ 7,3×10⁻¹⁰ m (orden del ángstrom).",
        },
        "practica": {
            "pregunta": "¿Por qué no observamos interferencia con objetos macroscópicos?",
            "pista": "Relacione λ = h/p con la masa del objeto.",
        },
        "notas": [
            "La medición colapsa o altera el estado cuántico en interpretaciones estándar.",
            "Young y posteriormente Davisson-Germer confirmaron la dualidad.",
        ],
        "recursos": [
            {"titulo": "Simulación de doble rendija", "url": "#"},
            {"titulo": "Línea de tiempo de la física cuántica", "url": "#"},
        ],
        "preguntas": [
            {"pregunta": "¿Qué demostró el experimento de Young?", "respuesta": "La interferencia de la luz, apoyando su naturaleza ondulatoria."},
            {"pregunta": "¿Qué aportó de Broglie?", "respuesta": "Que toda partícula tiene una longitud de onda asociada λ = h/p."},
        ],
        "temas_relacionados": ["Experimento de doble rendija", "Principio de incertidumbre", "Función de onda"],
        "recursos_descargables": [
            {"titulo": "Introducción a la mecánica cuántica.pdf", "url": "#"},
            {"titulo": "Problemas de ondas y partículas.pdf", "url": "#"},
        ],
    },
    "quimica-organica:alcoholes-eteres": {
        "video_tiempo_actual": "18:10",
        "video_duracion": "45:00",
        "video_progreso": 40,
        "titulo_tema": "Alcoholes y éteres",
        "explicacion": (
            "Los alcoholes contienen el grupo hidroxilo (-OH) unido a carbono híbrido sp³. "
            "Los éteres tienen un oxígeno entre dos cadenas carbonadas (R-O-R'). "
            "Ambos grupos funcionales presentan enlaces de hidrógeno y distinta reactividad."
        ),
        "definiciones": [
            {"termino": "Alcohol primario", "definicion": "El carbono del -OH está unido a un solo carbono alquílico."},
            {"termino": "Éter", "definicion": "Compuesto R-O-R' con baja reactividad y punto de ebullición intermedio."},
            {"termino": "Grupo funcional", "definicion": "Grupo de átomos que define la familia química y sus reacciones."},
        ],
        "formulas": ["Nombre IUPAC alcohol: alcano + -ol (ej. etanol)", "R-O-R' → éter"],
        "ejemplo": {
            "enunciado": "Nombre el compuesto CH₃-CH₂-OH.",
            "solucion": "Cadena de dos carbonos (etano) con -OH: etanol.",
        },
        "practica": {
            "pregunta": "¿Qué tipo de alcohol es (CH₃)₂CH-OH?",
            "pista": "Cuente cuántos carbonos están unidos al carbono del hidroxilo.",
        },
        "notas": ["Los alcoholes forman puentes de hidrógeno; los éteres no con el mismo orden."],
        "recursos": [{"titulo": "Tabla de grupos funcionales", "url": "#"}],
        "preguntas": [{"pregunta": "¿Por qué el agua disuelve alcoholes?", "respuesta": "Por enlaces de hidrógeno con el -OH."}],
        "temas_relacionados": ["Grupos funcionales", "Alcanos y alquenos", "Ácidos carboxílicos"],
        "recursos_descargables": [{"titulo": "Guía de alcoholes.pdf", "url": "#"}],
    },
    "probabilidad-estadistica:eventos-espacios": {
        "video_tiempo_actual": "12:05",
        "video_duracion": "38:00",
        "video_progreso": 32,
        "titulo_tema": "Eventos y espacios muestrales",
        "explicacion": (
            "Un experimento aleatorio produce resultados inciertos. El espacio muestral Ω es el conjunto de todos los resultados posibles. "
            "Un evento es un subconjunto de Ω. La probabilidad clásica asigna P(A) = casos favorables / casos posibles cuando son equiprobables."
        ),
        "definiciones": [
            {"termino": "Espacio muestral", "definicion": "Conjunto Ω de todos los resultados elementales."},
            {"termino": "Evento", "definicion": "Subconjunto de Ω; puede ser simple o compuesto."},
            {"termino": "Probabilidad", "definicion": "Medida P con 0 ≤ P(A) ≤ 1 y P(Ω) = 1."},
        ],
        "formulas": ["P(A) = n(A)/n(Ω)", "P(A ∪ B) = P(A) + P(B) - P(A ∩ B)"],
        "ejemplo": {
            "enunciado": "Al lanzar un dado justo, ¿cuál es P(obtener par)?",
            "solucion": "Pares {2,4,6}: 3/6 = 1/2.",
        },
        "practica": {
            "pregunta": "¿Cuál es la probabilidad de sacar as en una baraja estándar?",
            "pista": "Hay 4 ases de 52 cartas.",
        },
        "notas": ["Eventos mutuamente excluyentes no pueden ocurrir a la vez."],
        "recursos": [{"titulo": "Simulador de probabilidad", "url": "#"}],
        "preguntas": [{"pregunta": "¿Qué es un evento seguro?", "respuesta": "El evento Ω con probabilidad 1."}],
        "temas_relacionados": ["Variables aleatorias", "Distribuciones", "Análisis predictivo"],
        "recursos_descargables": [{"titulo": "Ejercicios de probabilidad.pdf", "url": "#"}],
    },
    "algoritmos-logica:complejidad-on": {
        "video_tiempo_actual": "38:50",
        "video_duracion": "50:00",
        "video_progreso": 78,
        "titulo_tema": "Análisis de complejidad O(n)",
        "explicacion": (
            "La notación O grande describe el crecimiento asintótico del tiempo o espacio de un algoritmo. "
            "O(n) indica que el costo crea linealmente con el tamaño de la entrada. Comparar algoritmos ayuda a elegir estructuras eficientes."
        ),
        "definiciones": [
            {"termino": "Complejidad temporal", "definicion": "Cantidad de operaciones elementales en función de n."},
            {"termino": "O(n)", "definicion": "Crecimiento lineal; duplicar n duplica aproximadamente el tiempo."},
            {"termino": "Caso peor", "definicion": "Máximo costo sobre todas las entradas de tamaño n."},
        ],
        "formulas": ["O(1) < O(log n) < O(n) < O(n log n) < O(n²)"],
        "ejemplo": {
            "enunciado": "¿Cuál es la complejidad de recorrer un arreglo de n elementos una vez?",
            "solucion": "Un solo bucle sobre n → O(n).",
        },
        "practica": {
            "pregunta": "¿Un bucle anidado que recorre n × n elementos es O(n)?",
            "pista": "Cuente cuántas veces se ejecuta el cuerpo interno.",
        },
        "notas": ["Ignoramos constantes y términos de menor orden en notación asintótica."],
        "recursos": [{"titulo": "Visualizador de complejidad", "url": "#"}],
        "preguntas": [{"pregunta": "¿Qué mide O(n)?", "respuesta": "Un límite superior del crecimiento lineal."}],
        "temas_relacionados": ["Búsqueda y ordenamiento", "Recursión", "Pensamiento algorítmico"],
        "recursos_descargables": [{"titulo": "Cheat sheet de complejidad.pdf", "url": "#"}],
    },
}


def _contenido_por_defecto(curso, leccion):
    progreso = 35 if leccion.get("estado") == "en_progreso" else 0
    if leccion.get("estado") == "completado":
        progreso = 100
    duracion = leccion.get("duracion", "45 min").replace(" min", ":00")
    return {
        "video_tiempo_actual": "08:20",
        "video_duracion": duracion if ":" in duracion else f"{duracion}",
        "video_progreso": progreso,
        "titulo_tema": leccion["titulo"],
        "explicacion": (
            f"En esta lección de {curso['titulo']} explorará {leccion['titulo'].lower()}. "
            f"Repasará conceptos clave del programa y aplicará lo aprendido en ejemplos guiados."
        ),
        "definiciones": [
            {
                "termino": "Concepto central",
                "definicion": f"Ideas fundamentales relacionadas con {leccion['titulo']}.",
            },
            {
                "termino": "Aplicación",
                "definicion": "Uso práctico del tema en problemas y situaciones del curso.",
            },
        ],
        "formulas": [],
        "ejemplo": {
            "enunciado": f"Ejemplo guiado sobre {leccion['titulo']}.",
            "solucion": "Siga el procedimiento paso a paso presentado en el video y las notas.",
        },
        "practica": {
            "pregunta": f"¿Cuál es la idea principal de {leccion['titulo']}?",
            "pista": "Revise las definiciones y el resumen de la lección.",
        },
        "notas": [f"Resumen de {leccion['titulo']}", "Repase los módulos anteriores si necesita contexto"],
        "recursos": [{"titulo": "Material de apoyo del curso", "url": "#"}],
        "preguntas": [
            {
                "pregunta": "¿Cómo se relaciona con el curso?",
                "respuesta": f"Forma parte de los temas de {curso['titulo']}.",
            }
        ],
        "temas_relacionados": curso.get("temas", [])[:3],
        "recursos_descargables": [{"titulo": "Apuntes de la lección.pdf", "url": "#"}],
    }


def obtener_contenido_leccion(slug, leccion_id, curso, leccion):
    clave = f"{slug}:{leccion_id}"
    if clave in CONTENIDO_LECCIONES:
        contenido = dict(CONTENIDO_LECCIONES[clave])
    else:
        contenido = _contenido_por_defecto(curso, leccion)

    contenido.setdefault("video_imagen", curso.get("imagen", ""))
    contenido["quiz"] = obtener_quiz_curso(slug, curso, leccion)
    return contenido
