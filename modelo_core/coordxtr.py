import numpy as np

# FUNÇÃO COORDXTR
# EXTRAI AS COORDENADAS DOS NÓS DA MATRIZ DE COORDENADAS GLOBAIS PARA
# O NUMERO DE ELEMENTOS COM IGUAL NUMERO DE NÓS POR ELEMENTO E GRAUS DE LIBERDADE POR NÓ.

# INPUT:
#           edof: matriz de topologia dos elementos
#                 primeira coluna = número do elemento
#                 demais colunas = graus de liberdade do elemento
#                    dim(t) = n_ei x n_gle +1
#
#           Coord: matriz de coordenadas globais dos nós
#                  cada linha representa um nó
#                  colunas: x, y, z

#           Dof: matriz global dos graus de liberdade dos nós
#                cada linha representa um nó
#                cada coluna representa um grau de liberdade daquele nó
#           nen   : número de nós por elemento


# OUTPUT:
#           Ex, Ey, Ez: matrizes de coordenadas dos nós de cada elemento
#           Ex = [x1 x2 .... xn_nel;
#                 ... ... ... ...;
#                 n_el ... ... ...] uma linha para cada elemento
#           Dimensão de Ex = n_el x n_nel
#
#           n_el = numero de elementos,
#           n_nel = Numero de nós por elemento
#           n_ei = numero de elementos identicos
#           n_gle = numero de graus de liberdade por elemento


def coordxtr(Edof, Coord, Dof, nen):

    Edof = np.asarray(Edof, dtype=int)
    Coord = np.asarray(Coord, dtype=float)
    Dof = np.asarray(Dof, dtype=int)

    # Número de elementos e número de colunas de Edof
    nel, n_colEdof = Edof.shape

    # Número de graus de liberdade por elemento (Primeira coluna de Edof é o número do elemento)
    n_gle = n_colEdof - 1

    # Número de nós e número de dimensões espaciais
    n, n_ds = Coord.shape

    # Número de graus de liberdade por nó
    n_gln = int(n_gle // nen)

    # Matrizes de saída

    Ex = np.zeros((nel, nen))
    Ey = np.zeros((nel, nen)) if n_ds > 1 else None
    Ez = np.zeros((nel, nen)) if n_ds > 2 else None

    for i in range(nel):
        # Vetor com os índices dos nós do elemento i
        nodnum = np.zeros(nen, dtype=int)

        for j in range(nen):
            # Intervalo das colunas de Edof correspondentes ao nó local j
            inicio = 1 + j * n_gln
            fim = 1 + (j + 1) * n_gln

            # Graus de liberdade do nó local j do elemento i
            graus_elemento_no_j = Edof[i, inicio:fim]

            # Procura em Dof qual linha tem esse grau de liberdade, ou seja, qual nó corresponde a esse grau de liberdade
            comparacao = Dof[:, 0:n_gln] == graus_elemento_no_j

            linhas_encontradas = np.where(np.all(comparacao, axis=1))[0]

            if len(linhas_encontradas) == 0:
                raise ValueError(
                    f"Nó não encontrado para o elemento {i + 1}, "
                    f"nó local {j + 1}, graus {graus_elemento_no_j}."
                )

            # Índice do nó encontrado
            nodnum[j] = linhas_encontradas[0]

        # Extrair as coordenadas x dos nós do elemento i
        Ex[i, :] = Coord[nodnum, 0]

        # Extrair as coordenadas y dos nós do elemento i, se aplicável
        if n_ds > 1:
            Ey[i, :] = Coord[nodnum, 1]

        # Extrair as coordenadas z dos nós do elemento i, se aplicável
        if n_ds > 2:
            Ez[i, :] = Coord[nodnum, 2]

    return Ex, Ey, Ez
