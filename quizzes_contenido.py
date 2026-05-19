# -*- coding: utf-8 -*-
"""
Banco de preguntas de evaluación por curso (quiz de lección).

Complementa lecciones_contenido.py; las claves coinciden con los slugs de curso en el catálogo.
"""

# Preguntas agrupadas por slug de curso.
QUIZ_POR_CURSO = {
    "fundamentos-algebra": {
        "titulo_tema": "Álgebra y funciones",
        "preguntas": [
            {
                "tipo": "Opción múltiple",
                "enunciado": "¿Cuál es la forma general de una función cuadrática?",
                "opciones": {
                    "A": "f(x) = ax² + bx + c",
                    "B": "f(x) = mx + b",
                    "C": "f(x) = a/x",
                    "D": "f(x) = √x + c",
                },
                "correcta": "A",
                "explicacion": "La forma general de una cuadrática es f(x) = ax² + bx + c con a ≠ 0.",
                "pista": "Busque el término con exponente 2 en la variable.",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "La coordenada x del vértice de f(x) = ax² + bx + c se calcula con:",
                "opciones": {
                    "A": "x = -b/(2a)",
                    "B": "x = b/(2a)",
                    "C": "x = -c/b",
                    "D": "x = 2a/b",
                },
                "correcta": "A",
                "explicacion": "El vértice tiene abscisa h = -b/(2a).",
                "pista": "Es la fórmula simétrica de la parábola.",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "Si el discriminante Δ = b² - 4ac es negativo, la ecuación cuadrática:",
                "opciones": {
                    "A": "No tiene raíces reales",
                    "B": "Tiene dos raíces reales distintas",
                    "C": "Tiene infinitas soluciones",
                    "D": "Siempre tiene una raíz doble",
                },
                "correcta": "A",
                "explicacion": "Δ < 0 implica que no hay intersección con el eje x en los reales.",
                "pista": "Compare Δ con cero.",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "La pendiente de la recta y = 3x - 2 es:",
                "opciones": {
                    "A": "3",
                    "B": "-2",
                    "C": "2",
                    "D": "1/3",
                },
                "correcta": "A",
                "explicacion": "En y = mx + b, la pendiente es el coeficiente m = 3.",
                "pista": "Identifique el valor de m en la ecuación.",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "Al sumar (2x² + x) + (x² - 3x + 1), el término de mayor grado es:",
                "opciones": {
                    "A": "3x²",
                    "B": "2x²",
                    "C": "x²",
                    "D": "4x²",
                },
                "correcta": "A",
                "explicacion": "2x² + x² = 3x²; se suman coeficientes de igual grado.",
                "pista": "Combine solo términos semejantes.",
            },
        ],
    },
    "biologia-molecular": {
        "titulo_tema": "Biología molecular",
        "preguntas": [
            {
                "tipo": "Opción múltiple",
                "enunciado": "¿Qué molécula almacena la información genética en la mayoría de los organismos?",
                "opciones": {
                    "A": "ADN",
                    "B": "Glucosa",
                    "C": "ATP únicamente",
                    "D": "Colesterol",
                },
                "correcta": "A",
                "explicacion": "El ADN es el material genético principal en células.",
                "pista": "Piense en ácidos nucleicos.",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "Un nucleótido del ADN está formado por:",
                "opciones": {
                    "A": "Fosfato, desoxirribosa y base nitrogenada",
                    "B": "Ribosa, lípidos y proteínas",
                    "C": "Solo aminoácidos",
                    "D": "Glucosa y bases",
                },
                "correcta": "A",
                "explicacion": "Cada nucleótido incluye grupo fosfato, azúcar y base.",
                "pista": "No confunda con los aminoácidos de las proteínas.",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "En el ADN, la adenina (A) se empareja con:",
                "opciones": {
                    "A": "Timina (T)",
                    "B": "Citosina (C)",
                    "C": "Guanina (G)",
                    "D": "Uracilo (U)",
                },
                "correcta": "A",
                "explicacion": "Regla de Chargaff: A-T y C-G por complementariedad.",
                "pista": "Las purinas se emparejan con pirimidinas específicas.",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "La estructura en doble hélice del ADN fue propuesta por:",
                "opciones": {
                    "A": "Watson y Crick",
                    "B": "Darwin y Wallace",
                    "C": "Mendel y Morgan",
                    "D": "Pasteur y Koch",
                },
                "correcta": "A",
                "explicacion": "Watson y Crick describieron la doble hélice en 1953.",
                "pista": "Famosos por el modelo de la doble cadena.",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "La síntesis de proteínas a partir del ARN mensajero ocurre en:",
                "opciones": {
                    "A": "Ribosomas",
                    "B": "Lisosomas",
                    "C": "Membrana plasmática",
                    "D": "Núcleo exclusivamente",
                },
                "correcta": "A",
                "explicacion": "La traducción del ARNm en proteínas se realiza en ribosomas.",
                "pista": "Orgánulo encargado de la traducción.",
            },
        ],
    },
    "fisica-cuantica-1": {
        "titulo_tema": "Física cuántica",
        "preguntas": [
            {
                "tipo": "Opción múltiple",
                "enunciado": "La dualidad onda-partícula indica que:",
                "opciones": {
                    "A": "Materia y radiación muestran propiedades de onda y partícula",
                    "B": "Solo la luz es onda",
                    "C": "Los electrones no tienen masa",
                    "D": "La gravedad es cuántica siempre",
                },
                "correcta": "A",
                "explicacion": "Experimentos muestran ambos comportamientos según el contexto.",
                "pista": "Piense en interferencia y fotones.",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "La energía de un fotón se expresa como:",
                "opciones": {
                    "A": "E = hf",
                    "B": "E = mc",
                    "C": "E = mv²",
                    "D": "E = F·d",
                },
                "correcta": "A",
                "explicacion": "Planck: E = hf, donde h es la constante de Planck.",
                "pista": "Relaciona frecuencia y constante h.",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "El experimento de la doble rendija demuestra:",
                "opciones": {
                    "A": "Patrones de interferencia",
                    "B": "Solo reflexión",
                    "C": "Caída libre",
                    "D": "Fusión nuclear",
                },
                "correcta": "A",
                "explicacion": "Franjas claras y oscuras indican interferencia ondulatoria.",
                "pista": "Asociado a ondas superpuestas.",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "La longitud de onda de de Broglie de una partícula es λ =",
                "opciones": {
                    "A": "h/p",
                    "B": "p/h",
                    "C": "hf",
                    "D": "mc²",
                },
                "correcta": "A",
                "explicacion": "de Broglie propuso λ = h/p para partículas con momento p.",
                "pista": "Involucra h y el momento lineal.",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "El principio de incertidumbre de Heisenberg limita:",
                "opciones": {
                    "A": "La precisión simultánea de ciertas magnitudes conjugadas",
                    "B": "La velocidad de la luz",
                    "C": "La masa del protón",
                    "D": "La carga del electrón",
                },
                "correcta": "A",
                "explicacion": "No se pueden conocer con precisión arbitraria posición y momento a la vez.",
                "pista": "Relaciona medición y límites cuánticos.",
            },
        ],
    },
    "quimica-organica": {
        "titulo_tema": "Química orgánica",
        "preguntas": [
            {
                "tipo": "Opción múltiple",
                "enunciado": "La química orgánica estudia principalmente compuestos de:",
                "opciones": {
                    "A": "Carbono",
                    "B": "Hierro",
                    "C": "Sodio",
                    "D": "Helio",
                },
                "correcta": "A",
                "explicacion": "El carbono forma la base de moléculas orgánicas.",
                "pista": "Elemento central en cadenas y anillos.",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "El grupo funcional -OH caracteriza a los:",
                "opciones": {
                    "A": "Alcoholes",
                    "B": "Aldehídos",
                    "C": "Cetonas",
                    "D": "Alquinos",
                },
                "correcta": "A",
                "explicacion": "Los alcoholes contienen hidroxilo unido a carbono.",
                "pista": "Nombre del grupo hidroxilo.",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "Un enlace simple C-C en alcanos es:",
                "opciones": {
                    "A": "Sigma (σ)",
                    "B": "Solo pi (π)",
                    "C": "Iónico",
                    "D": "Metálico",
                },
                "correcta": "A",
                "explicacion": "Los alcanos tienen enlaces σ simples saturados.",
                "pista": "Tipo de enlace en cadenas saturadas.",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "Los alquenos contienen al menos un enlace:",
                "opciones": {
                    "A": "Doble C=C",
                    "B": "Triple C≡C",
                    "C": "Solo simple",
                    "D": "Iónico N-N",
                },
                "correcta": "A",
                "explicacion": "Alquenos: hidrocarburos con doble enlace carbono-carbono.",
                "pista": "Sufijo -eno indica insaturación.",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "La hibridación sp³ del carbono corresponde a geometría:",
                "opciones": {
                    "A": "Tetraédrica",
                    "B": "Lineal",
                    "C": "Trigonal plana",
                    "D": "Octaédrica",
                },
                "correcta": "A",
                "explicacion": "sp³ implica cuatro lóbulos en disposición tetraédrica (~109,5°).",
                "pista": "Cuatro grupos alrededor del carbono.",
            },
        ],
    },
    "probabilidad-estadistica": {
        "titulo_tema": "Probabilidad y estadística",
        "preguntas": [
            {
                "tipo": "Opción múltiple",
                "enunciado": "El espacio muestral de un experimento es:",
                "opciones": {
                    "A": "El conjunto de todos los resultados posibles",
                    "B": "Solo el resultado favorito",
                    "C": "La media de los datos",
                    "D": "El error estándar",
                },
                "correcta": "A",
                "explicacion": "Ω contiene cada resultado elemental del experimento.",
                "pista": "Símbolo común: Ω.",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "Si P(A) = 0,3 y P(B) = 0,5 y son independientes, P(A ∩ B) =",
                "opciones": {
                    "A": "0,15",
                    "B": "0,8",
                    "C": "0,2",
                    "D": "1,0",
                },
                "correcta": "A",
                "explicacion": "Para independientes: P(A ∩ B) = P(A)·P(B) = 0,3×0,5 = 0,15.",
                "pista": "Multiplique las probabilidades.",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "La media aritmética de 2, 4 y 6 es:",
                "opciones": {
                    "A": "4",
                    "B": "6",
                    "C": "2",
                    "D": "12",
                },
                "correcta": "A",
                "explicacion": "(2+4+6)/3 = 12/3 = 4.",
                "pista": "Sume y divida por la cantidad de datos.",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "En una distribución normal, aproximadamente el 68% de los datos cae a:",
                "opciones": {
                    "A": "Una desviación estándar de la media",
                    "B": "Tres desviaciones",
                    "C": "La mediana solamente",
                    "D": "El valor máximo",
                },
                "correcta": "A",
                "explicacion": "Regla empírica: ~68% dentro de μ ± σ.",
                "pista": "Regla del 68-95-99,7.",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "La probabilidad de un evento seguro es:",
                "opciones": {
                    "A": "1",
                    "B": "0",
                    "C": "0,5",
                    "D": "-1",
                },
                "correcta": "A",
                "explicacion": "P(Ω) = 1 para el evento que siempre ocurre.",
                "pista": "Máximo valor posible de probabilidad.",
            },
        ],
    },
    "algoritmos-logica": {
        "titulo_tema": "Algoritmos y lógica",
        "preguntas": [
            {
                "tipo": "Opción múltiple",
                "enunciado": "Un algoritmo es:",
                "opciones": {
                    "A": "Un conjunto finito de pasos bien definidos para resolver un problema",
                    "B": "Solo un lenguaje de programación",
                    "C": "Un tipo de hardware",
                    "D": "Una base de datos",
                },
                "correcta": "A",
                "explicacion": "Algoritmo: secuencia ordenada y finita de instrucciones.",
                "pista": "Piense en pasos para resolver una tarea.",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "Un bucle que ejecuta n iteraciones sobre n elementos tiene complejidad típica:",
                "opciones": {
                    "A": "O(n)",
                    "B": "O(1)",
                    "C": "O(log n) siempre",
                    "D": "O(n³) siempre",
                },
                "correcta": "A",
                "explicacion": "Un recorrido lineal simple es O(n).",
                "pista": "El tiempo crece proporcionalmente con n.",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "En un diagrama de flujo, el rombo suele representar:",
                "opciones": {
                    "A": "Decisión",
                    "B": "Inicio",
                    "C": "Entrada de datos",
                    "D": "Fin del programa",
                },
                "correcta": "A",
                "explicacion": "El rombo indica bifurcación condicional (sí/no).",
                "pista": "Forma asociada a preguntas verdadero/falso.",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "La búsqueda lineal en un arreglo desordenado de n elementos, en el peor caso, requiere:",
                "opciones": {
                    "A": "n comparaciones",
                    "B": "1 comparación",
                    "C": "log n comparaciones",
                    "D": "n² comparaciones",
                },
                "correcta": "A",
                "explicacion": "Puede necesitar revisar todos los elementos.",
                "pista": "Caso peor: el elemento está al final o no existe.",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "O(n²) crece más rápido que O(n) cuando n es grande porque:",
                "opciones": {
                    "A": "n² domina a n para valores grandes de n",
                    "B": "Son iguales siempre",
                    "C": "O(n) es exponencial",
                    "D": "n² es constante",
                },
                "correcta": "A",
                "explicacion": "n² aumenta mucho más rápido que n al crecer n.",
                "pista": "Compare n=1000 con n².",
            },
        ],
    },
}


def _quiz_generico(curso, leccion):
    titulo = curso.get("titulo", "Curso")
    tema = leccion.get("titulo", "Tema")
    return {
        "titulo_tema": tema,
        "preguntas": [
            {
                "tipo": "Opción múltiple",
                "enunciado": f"¿Cuál es el objetivo principal de la lección «{tema}»?",
                "opciones": {
                    "A": f"Comprender conceptos clave de {titulo}",
                    "B": "Memorizar fechas históricas sin contexto",
                    "C": "Evitar toda práctica",
                    "D": "Ignorar el material del curso",
                },
                "correcta": "A",
                "explicacion": f"La lección busca afianzar ideas centrales de {titulo}.",
                "pista": "Piense en el propósito académico de la lección.",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": f"Al estudiar {tema}, lo más útil es:",
                "opciones": {
                    "A": "Relacionar definiciones con ejemplos",
                    "B": "No revisar notas",
                    "C": "Saltar ejercicios",
                    "D": "Evitar preguntas",
                },
                "correcta": "A",
                "explicacion": "Conectar teoría y práctica mejora la retención.",
                "pista": "Estrategia de estudio activo.",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "Antes de responder un quiz, conviene:",
                "opciones": {
                    "A": "Repasar el concepto principal del tema",
                    "B": "Responder al azar siempre",
                    "C": "No leer el enunciado",
                    "D": "Omitir la explicación final",
                },
                "correcta": "A",
                "explicacion": "Repasar el concepto central reduce errores.",
                "pista": "El asistente Nébula lo sugiere.",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": f"Los temas de {titulo} se organizan para:",
                "opciones": {
                    "A": "Construir aprendizaje progresivo",
                    "B": "Confundir al estudiante",
                    "C": "Evitar evaluaciones",
                    "D": "Eliminar contenido",
                },
                "correcta": "A",
                "explicacion": "El plan del curso avanza de lo básico a lo complejo.",
                "pista": "Estructura pedagógica del curso.",
            },
            {
                "tipo": "Opción múltiple",
                "enunciado": "Si una respuesta es incorrecta, debe:",
                "opciones": {
                    "A": "Leer la explicación y corregir el concepto",
                    "B": "Abandonar el curso",
                    "C": "Ignorar el feedback",
                    "D": "No intentar de nuevo",
                },
                "correcta": "A",
                "explicacion": "El feedback sirve para reforzar el aprendizaje.",
                "pista": "Aproveche la retroalimentación del quiz.",
            },
        ],
    }


def obtener_quiz_curso(slug, curso, leccion):
    from catalog_service import get_quiz

    leccion_id = (leccion or {}).get("id")
    quiz = get_quiz(slug, leccion_id)
    if quiz:
        quiz = dict(quiz)
        quiz["titulo_tema"] = leccion.get("titulo", quiz.get("titulo_tema", ""))
        return quiz
    if slug in QUIZ_POR_CURSO:
        quiz = dict(QUIZ_POR_CURSO[slug])
        quiz["titulo_tema"] = leccion.get("titulo", quiz["titulo_tema"])
        return quiz
    return _quiz_generico(curso, leccion)
