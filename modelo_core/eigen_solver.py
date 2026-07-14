import numpy as np
from scipy import sparse as sp
from scipy.linalg import eigh
from scipy.sparse.linalg import eigsh


SPARSE_ARPACK_MIN_DOF = 1000

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


def _mass_normalize_modes(X1, M_reduzida):
    """Normaliza colunas pela norma de massa sem alterar a convencao existente."""
    MX = M_reduzida @ X1
    normas = np.sqrt(np.einsum("ij,ij->j", X1, MX))

    if np.any(normas <= np.finfo(float).eps):
        raise ValueError("Autovetor com norma de massa nula encontrado.")

    return X1 / normas


def eigen_solver_partial(
    K,
    M,
    cc=None,
    n_eigenpairs=None,
    retornar_autovetores=True,
):
    """
    Resolve apenas os primeiros autovalores/autovetores necessarios.

    Esta funcao e um caminho otimizado. A funcao eigen_solver original permanece
    inalterada para uso como referencia/fallback.
    """
    is_sparse = sp.issparse(K) or sp.issparse(M)

    if is_sparse:
        K_work = K if sp.issparse(K) else sp.csr_matrix(np.asarray(K, dtype=float))
        M_work = M if sp.issparse(M) else sp.csr_matrix(np.asarray(M, dtype=float))
    else:
        K_work = np.asarray(K, dtype=float)
        M_work = np.asarray(M, dtype=float)

    nd = K_work.shape[0]

    gll = np.arange(nd)
    has_restrained_dofs = False
    if cc is not None:
        glr = np.asarray(cc, dtype=int).reshape(-1)
        has_restrained_dofs = glr.size > 0
        gll = np.setdiff1d(gll, glr, assume_unique=False)

    n_gll = gll.size
    if n_gll == 0:
        raise ValueError("Nao ha graus de liberdade livres para resolver.")

    if n_eigenpairs is None:
        n_eigenpairs = n_gll

    n_eigenpairs = int(n_eigenpairs)
    if n_eigenpairs < 1:
        raise ValueError("n_eigenpairs deve ser positivo.")

    if n_eigenpairs >= n_gll:
        if is_sparse:
            K_dense = K_work.toarray()
            M_dense = M_work.toarray()
            return eigen_solver(
                K_dense,
                M_dense,
                cc=cc,
                retornar_autovetores=retornar_autovetores,
            )

        return eigen_solver(K, M, cc=cc, retornar_autovetores=retornar_autovetores)

    dense_reduced_ready = False

    if is_sparse:
        K_reduzida = K_work[gll, :][:, gll].tocsr()
        M_reduzida = M_work[gll, :][:, gll].tocsr()

        if n_gll < SPARSE_ARPACK_MIN_DOF:
            K_reduzida = K_reduzida.toarray()
            M_reduzida = M_reduzida.toarray()
            dense_reduced_ready = True
            is_sparse = False
        elif not has_restrained_dofs:
            # Em problemas livre-livre, K tem modos rigidos em zero. O
            # shift-invert em sigma=0 fica singular, entao priorizamos o
            # caminho denso parcial para manter robustez.
            K_reduzida = K_reduzida.toarray()
            M_reduzida = M_reduzida.toarray()
            dense_reduced_ready = True
            is_sparse = False
        else:
            try:
                if retornar_autovetores:
                    autovalores, X1 = eigsh(
                        K_reduzida,
                        k=n_eigenpairs,
                        M=M_reduzida,
                        sigma=0.0,
                        which="LM",
                    )
                    X1 = _mass_normalize_modes(X1, M_reduzida)
                else:
                    autovalores = eigsh(
                        K_reduzida,
                        k=n_eigenpairs,
                        M=M_reduzida,
                        sigma=0.0,
                        which="LM",
                        return_eigenvectors=False,
                    )
            except Exception:
                K_reduzida = K_reduzida.toarray()
                M_reduzida = M_reduzida.toarray()
                dense_reduced_ready = True
                is_sparse = False

    if not is_sparse:
        if not dense_reduced_ready:
            K_reduzida = K_work[np.ix_(gll, gll)]
            M_reduzida = M_work[np.ix_(gll, gll)]

        if retornar_autovetores:
            autovalores, X1 = eigh(
                K_reduzida,
                M_reduzida,
                subset_by_index=[0, n_eigenpairs - 1],
            )
            X1 = _mass_normalize_modes(X1, M_reduzida)
        else:
            autovalores = eigh(
                K_reduzida,
                M_reduzida,
                eigvals_only=True,
                subset_by_index=[0, n_eigenpairs - 1],
            )

    i = np.argsort(autovalores)
    autovalores = autovalores[i]

    if not retornar_autovetores:
        return autovalores

    X1 = X1[:, i]
    X = np.zeros((nd, X1.shape[1]))
    X[gll, :] = X1

    return autovalores, X
