"""
Genera PDFs mínimos de ejemplo en static/resources/{materia}/.
Ejecutar una vez: python generar_pdfs_recursos.py
"""

import os

BASE = os.path.join("static", "resources")

RECURSOS = [
    ("matematicas", "guia-ecuaciones.pdf", "Guia de ecuaciones"),
    ("matematicas", "funciones-trigonometricas.pdf", "Funciones trigonometricas"),
    ("ciencia", "simulador-reacciones.pdf", "Simulador de reacciones"),
    ("ciencia", "fotosintesis.pdf", "Fotosintesis"),
    ("historia", "linea-tiempo-universal.pdf", "Linea de tiempo universal"),
    ("historia", "historia-contemporanea.pdf", "Historia contemporanea"),
    ("lenguaje", "flashcards-vocabulario.pdf", "Flashcards de vocabulario"),
    ("lenguaje", "ejercicios-redaccion.pdf", "Ejercicios de redaccion"),
]


def pdf_minimo(titulo: str) -> bytes:
    """PDF 1.4 válido con una línea de texto."""
    t = titulo.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 16 Tf 72 720 Td ({t} - Nebula AI) Tj ET"
    parts = [
        "%PDF-1.4\n",
        "1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n",
        "2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n",
        "3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R"
        "/Resources<</Font<</F1 5 0 R>>>>>>endobj\n",
        f"4 0 obj<</Length {len(stream)}>>stream\n{stream}\nendstream\nendobj\n",
        "5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n",
    ]
    body = "".join(parts)
    offs = []
    for i in range(1, 6):
        offs.append(body.index(f"{i} 0 obj"))
    xref = "xref\n0 6\n0000000000 65535 f \n" + "".join(f"{o:010d} 00000 n \n" for o in offs)
    start = len(body + xref + "trailer<</Size 6/Root 1 0 R>>\nstartxref\n")
    return (body + xref + f"trailer<</Size 6/Root 1 0 R>>\nstartxref\n{start}\n%%EOF\n").encode(
        "latin-1", "replace"
    )


def main():
    for carpeta, archivo, titulo in RECURSOS:
        dir_path = os.path.join(BASE, carpeta)
        os.makedirs(dir_path, exist_ok=True)
        path = os.path.join(dir_path, archivo)
        with open(path, "wb") as f:
            f.write(pdf_minimo(titulo))
        print("Creado:", path)


if __name__ == "__main__":
    main()
