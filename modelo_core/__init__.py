"""
Rotinas numericas portadas/inspiradas no CALFEM.

Este pacote agrupa as funcoes basicas usadas pelo solver principal:
- montagem de matrizes globais
- elemento de viga 2D Euler-Bernoulli
- extracao de coordenadas dos elementos
- solucao do problema generalizado de autovalores
"""

from .assembly import assembly
from .beam2d import beam2d
from .coordxtr import coordxtr
from .eigen_solver import eigen_solver

__all__ = [
    "assembly",
    "beam2d",
    "coordxtr",
    "eigen_solver",
]
