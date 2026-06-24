import numpy as np

# FUNÇÃO ASSEMBLY
# MONTAR A MATRIZ ELEMENTAR KE (E FE) NA MATRIZ GLOBAL
# DE RIGIDEZ K ( E O VETOR GLOBAL DE FORÇAS F)

# INPUT:    edof: Topologia da Matriz dof
#           K: Matriz global de rigidez (n x n)
#           Ke: Matriz elementar de rigidez (n x n)
#           f: Vetor global de forças (n x 1)
#           fe: Vetor elementar de forças (n x 1)

# OUTPUT:   K: NOVA Matriz global de rigidez (n x n)
#           f: NOVO Vetor global de forças (n x 1)


def assembly(edof, K, Ke, f=None, fe=None):
    n_linhas, n_colunas = edof.shape

    graus_liberdade = edof[
        :, 1:n_colunas
    ]  # Primeira coluna esta associada ao número do elmento

    for i in range(n_linhas):
        graus_liberdade_i = graus_liberdade[i, :]  # Graus de liberdade do elemento i

        idx = (
            graus_liberdade_i.astype(int) - 1
        )  # Ajusta os índices para Python (base 0)

        K[np.ix_(idx, idx)] += Ke  # Monta a NOVA matriz global de rigidez

        if fe is not None:
            if f is None:
                raise ValueError(
                    "Vetor global de forças f não pode ser None se fe não for None."
                )

            fe = np.array(fe).reshape(-1, 1)  # Garante que fe seja um vetor coluna
            f[idx, :] += fe  # Monta o NOVO vetor global de forças

    if fe is not None:
        return K, f
    else:
        return K, f
