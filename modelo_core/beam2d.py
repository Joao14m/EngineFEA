import numpy as np


def beam2d(ex, ey, ep):
    """
    Elemento de viga Euler-Bernoulli 2D com 3 GDL por no: u, v, theta.

    ep = [E, A, I, m] ou [E, A, I, m, a, b], onde m e massa por unidade
    de comprimento e a/b sao coeficientes de amortecimento proporcional.
    """
    ex = np.asarray(ex, dtype=float).reshape(-1)
    ey = np.asarray(ey, dtype=float).reshape(-1)
    ep = np.asarray(ep, dtype=float).reshape(-1)

    if ex.size != 2 or ey.size != 2:
        raise ValueError("ex e ey devem conter as coordenadas dos dois nos.")

    if ep.size not in (4, 6):
        raise ValueError("ep deve ser [E, A, I, m] ou [E, A, I, m, a, b].")

    direction = np.array([ex[1] - ex[0], ey[1] - ey[0]], dtype=float)
    L = float(np.linalg.norm(direction))

    if L <= 0.0:
        raise ValueError("Comprimento do elemento deve ser positivo.")

    n = direction / L

    E = float(ep[0])
    A = float(ep[1])
    I = float(ep[2])
    m = float(ep[3])
    a = float(ep[4]) if ep.size == 6 else 0.0
    b = float(ep[5]) if ep.size == 6 else 0.0

    Kle = np.array(
        [
            [E * A / L, 0, 0, -E * A / L, 0, 0],
            [
                0,
                12 * E * I / L**3,
                6 * E * I / L**2,
                0,
                -12 * E * I / L**3,
                6 * E * I / L**2,
            ],
            [
                0,
                6 * E * I / L**2,
                4 * E * I / L,
                0,
                -6 * E * I / L**2,
                2 * E * I / L,
            ],
            [-E * A / L, 0, 0, E * A / L, 0, 0],
            [
                0,
                -12 * E * I / L**3,
                -6 * E * I / L**2,
                0,
                12 * E * I / L**3,
                -6 * E * I / L**2,
            ],
            [
                0,
                6 * E * I / L**2,
                2 * E * I / L,
                0,
                -6 * E * I / L**2,
                4 * E * I / L,
            ],
        ],
        dtype=float,
    )

    Mle = (
        m
        * L
        / 420.0
        * np.array(
            [
                [140, 0, 0, 70, 0, 0],
                [0, 156, 22 * L, 0, 54, -13 * L],
                [0, 22 * L, 4 * L**2, 0, 13 * L, -3 * L**2],
                [70, 0, 0, 140, 0, 0],
                [0, 54, 13 * L, 0, 156, -22 * L],
                [0, -13 * L, -3 * L**2, 0, -22 * L, 4 * L**2],
            ],
            dtype=float,
        )
    )

    Cle = a * Mle + b * Kle

    G = np.array(
        [
            [n[0], n[1], 0, 0, 0, 0],
            [-n[1], n[0], 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0],
            [0, 0, 0, n[0], n[1], 0],
            [0, 0, 0, -n[1], n[0], 0],
            [0, 0, 0, 0, 0, 1],
        ],
        dtype=float,
    )

    Ke = G.T @ Kle @ G
    Me = G.T @ Mle @ G
    Ce = G.T @ Cle @ G

    return Ke, Me, Ce
