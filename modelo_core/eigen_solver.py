import numpy as np
from scipy.linalg import eigh

# FUNÇÃO EIGEN_SOLVER
# RESOLVER O PROBELMA DE AUTOVALORES E AUTOVETORES:
# [K - lambda M] X = 0, CONSIDERANDO AS CONDIÇÕES DE CONTORNO

# INPUT:    K: Matriz global de rigidez (nd x nd)
#           M: Matriz global de massa (nd x nd)
#          cc: graus de liberdade restritos (condições de contorno)

# OUTPUT:   autovalores: autovalores lambda - Armazenados em um vector de tamnho (nd - nb)
#           X: autovetores completos dimensão nd x n_gll


def eigen_solver(K, M, cc=None, retornar_autovetores=True):

    K = np.asarray(K, dtype=float)
    M = np.asarray(M, dtype=float)

    nd, _ = K.shape

    # Graus de liberdade livres
    gll = np.arange(nd)

    if cc is not None:
        # Graus de liberdade restritos, ou seja, com condição de contorno.
        glr = np.asarray(cc, dtype=int).reshape(-1)

        # Remover os graus de liberdade restritos dos graus de liberdade livres
        gll = np.setdiff1d(gll, glr)

    # Reduzindo as matrizes K e M para os graus de liberdade livres
    K_reduzida = K[np.ix_(gll, gll)]
    M_reduzida = M[np.ix_(gll, gll)]

    if retornar_autovetores:
        # Solver Problema Generalizado
        # K_reduzida X1 = lambda M_reduzida X1
        # eigh já retorna valores reais e ordenados
        autovalores, X1 = eigh(K_reduzida, M_reduzida)

        # Número de graus de liberdae livres
        n_gll = X1.shape[0]

        # Normalização dos modos pela matriz de massa
        for j in range(n_gll):
            xj = X1[:, j].reshape(-1, 1)

            m_norm = float(np.sqrt((xj.T @ M_reduzida @ xj).item()))

            X1[:, j] = (xj / m_norm).reshape(-1)

        # Ordenando os autovalores e autovetores
        i = np.argsort(autovalores)

        autovalores = autovalores[i]
        X1 = X1[:, i]

        # Montagem da Matriz de autovetores, graus restritos -> desclocamento modal = 0
        X = np.zeros((nd, n_gll))

        X[gll, :] = X1

        return autovalores, X

    else:
        # Resolver apenas os autovalores
        autovalores = eigh(K_reduzida, M_reduzida, eigvals_only=True)

        autovalores = np.sort(autovalores)

        return autovalores
