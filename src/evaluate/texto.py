"""
Normalizacion de texto compartida entre el generador del set de evaluacion
y el evaluador.

IMPORTANTE: los dos modulos tienen que usar esta misma funcion. Si normalizan
distinto, habra anclas que pasen el filtro al generar y luego no encuentren
ningun chunk al evaluar.
"""

import re


def norm(s: str) -> str:
    """Quita el marcado markdown y unifica espacios, para comparar anclas."""
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)   # enlaces -> solo el texto
    s = re.sub(r"[*_`]+", "", s)                      # negrita, cursiva, codigo
    s = re.sub(r"\s+", " ", s)                        # espacios y saltos
    return s.strip().lower()