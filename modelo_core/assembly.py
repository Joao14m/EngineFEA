import numpy as np


def assem(edof, K, Ke, f=None, fe=None):
    """
    Monta uma matriz elementar na matriz global.

    Convencao deste projeto:
    - edof[:, 0] contem o indice do elemento.
    - edof[:, 1:] contem os GDL globais em base zero.
    """
    edof = np.asarray(edof, dtype=int)
    K = np.asarray(K, dtype=float)
    Ke = np.asarray(Ke, dtype=float)

    if edof.ndim == 1:
        edof = edof.reshape(1, -1)

    if edof.ndim != 2 or edof.shape[1] < 2:
        raise ValueError("edof deve ter coluna de elemento e colunas de GDL.")

    dofs = edof[:, 1:]

    for dofs_i in dofs:
        idx = dofs_i.astype(int)

        if np.any(idx < 0) or np.any(idx >= K.shape[0]):
            raise IndexError("edof contem GDL fora dos limites da matriz global.")

        if Ke.shape != (idx.size, idx.size):
            raise ValueError("Ke deve ter dimensao compativel com os GDL do elemento.")

        K[np.ix_(idx, idx)] += Ke

        if fe is not None:
            if f is None:
                raise ValueError(
                    "Vetor global de forcas f nao pode ser None se fe nao for None."
                )

            fe_col = np.asarray(fe, dtype=float).reshape(-1, 1)
            if fe_col.shape[0] != idx.size:
                raise ValueError("fe deve ter dimensao compativel com os GDL.")

            f[idx, :] += fe_col

    if fe is not None:
        return K, f

    return K


def assembly(edof, K, Ke, f=None, fe=None):
    """Alias mantido para compatibilidade com o nome antigo."""
    return assem(edof, K, Ke, f=f, fe=fe)
