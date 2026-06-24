import numpy as np

#
# FUNÇÃO BEAM2D
# CALCULA AS MATRIZES ELEMENTARES DE RIGIDEZ, MASSA E AMORTECIMENTO
# DE UM ELEMENTO DE VIGA BERNOULLI 2D.

# INPUT:    ex = [x1,x2] ;
#           ey = [y1,y2] -> COORDENADAS DOS NÓS DO ELEMENTO
#
#           ep = [E,A,I,m,(a,b)] ;
#               E: Young's modulus
#               A: cross section area
#               I: moment of inertia
#               m: mass per unit length
#               a,b: damping coefficients,
#               Ce=aMe+bKe

# OUTPUT:    Ke: Matriz elementar de rigidez (6x6)
#            Me: Matriz elementar de massa (6x6)
#            Ce: Matriz elementar de amortecimento opcional (6x6)
#


def beam2d(ex, ey, ep):

    b = (ex[1] - ex[0], ey[1] - ey[0])
    b_transposta = b.conj().T
    L = np.sqrt(b_transposta @ b)
    n = b / L

    E = ep[0]
    A = ep[1]
    I = ep[2]
    m = ep[3]
    a = 0
    b = 0

    Kle = np.array(
        [E * A / L, 0, 0, -E * A / L, 0, 0],
        [
            0,
            12 * E * I / L**3,
            6 * E * I / L**2,
            0,
            -12 * E * I / L**3,
            6 * E * I / L**2,
        ],
        [0, 6 * E * I / L**2, 4 * E * I / L, 0, -6 * E * I / L**2, 2 * E * I / L],
        [-E * A / L, 0, 0, E * A / L, 0, 0],
        [
            0,
            -12 * E * I / L**3,
            -6 * E * I / L**2,
            0,
            12 * E * I / L**3,
            -6 * E * I / L**2,
        ],
        [0, 6 * E * I / L**2, 2 * E * I / L, 0, -6 * E * I / L**2, 4 * E * I / L],
    )

    Mle = (
        m
        * L
        / 420
        * np.array(
            [140, 0, 0, 70, 0, 0],
            [0, 156, 22 * L, 0, 54, -13 * L],
            [0, 22 * L, 4 * L**2, 0, 13 * L, -3 * L**2],
            [70, 0, 0, 140, 0, 0],
            [0, 54, 13 * L, 0, 156, -22 * L],
            [0, -13 * L, -3 * L**2, 0, -22 * L, 4 * L**2],
        )
    )

    Cle = a * Mle + b * Kle

    G = np.array(
        [n[0], n[1], 0, 0, 0, 0],
        [-n[1], n[0], 0, 0, 0, 0],
        [0, 0, 1, 0, 0, 0],
        [0, 0, 0, n[0], n[1], 0],
        [0, 0, 0, -n[1], n[0], 0],
        [0, 0, 0, 0, 0, 1],
    )

    G_transposta = G.conj().T

    Ke = G_transposta @ Kle @ G
    Me = G_transposta @ Mle @ G
    Ce = G_transposta @ Cle @ G

    return {"Ke": Ke, "Me": Me, "Ce": Ce}
