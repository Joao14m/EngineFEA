from __future__ import annotations

import time
from dataclasses import asdict
from typing import Any

import numpy as np

from modelo_matematico.config import AnalysisConfig

# ---------------------------------------------------------------------------
# IMPORTANTE SOBRE A PASTA DAS FUNCOES PORTADAS
# ---------------------------------------------------------------------------
# Evite chamar a pasta de "math", pois isso conflita com a biblioteca padrao
# do Python. Recomenda-se usar:
#
#     calfem_core/
#         assembly.py
#         beam2d.py
#         coordxtr.py
#         eigen_solver.py
#
# Os imports abaixo assumem essa estrutura.
# ---------------------------------------------------------------------------
from modelo_core import assem, beam2d, coordxtr, eigen_solver

MATERIAL_STEEL = 0
MATERIAL_TITANIUM = 1


# ---------------------------------------------------------------------------
# COMPOSICAO E NOMES DAS CONFIGURACOES
# ---------------------------------------------------------------------------


def create_composition_vectors(
    passo_composicao: float,
    ordem_material: int,
) -> tuple[np.ndarray, np.ndarray]:
    """
    ordem_material = 1:
        comeca com 100% aco e acrescenta titanio na ponta.

    ordem_material = 2:
        comeca com 100% titanio e acrescenta aco na ponta.
    """
    if passo_composicao <= 0:
        raise ValueError("passo_composicao deve ser positivo.")

    n_steps = int(round(1.0 / passo_composicao))

    if not np.isclose(n_steps * passo_composicao, 1.0):
        raise ValueError(
            "passo_composicao deve dividir o intervalo [0, 1] de forma consistente. "
            "Exemplo: 0.005 gera 201 configuracoes."
        )

    idx = np.arange(n_steps + 1, dtype=float)

    if ordem_material == 1:
        perc_aco_vec = 1.0 - idx * passo_composicao
    elif ordem_material == 2:
        perc_aco_vec = idx * passo_composicao
    else:
        raise ValueError("ordem_material invalida. Use 1 ou 2.")

    perc_aco_vec[np.abs(perc_aco_vec) < 1e-12] = 0.0
    perc_aco_vec[np.abs(perc_aco_vec - 1.0) < 1e-12] = 1.0
    perc_aco_vec = np.clip(perc_aco_vec, 0.0, 1.0)

    perc_ti_vec = 1.0 - perc_aco_vec
    perc_ti_vec[np.abs(perc_ti_vec) < 1e-12] = 0.0
    perc_ti_vec[np.abs(perc_ti_vec - 1.0) < 1e-12] = 1.0

    return perc_aco_vec, perc_ti_vec


def create_configuration_names(
    perc_aco_vec: np.ndarray,
    perc_ti_vec: np.ndarray,
    ordem_material: int,
) -> tuple[list[str], list[str]]:
    nomes_config: list[str] = []
    nomes_var: list[str] = []

    for p_aco, p_ti in zip(perc_aco_vec, perc_ti_vec):
        nome_aco = int(round(10000 * p_aco))
        nome_ti = int(round(10000 * p_ti))

        if ordem_material == 1:
            nomes_config.append(
                f"{100 * p_aco:.2f}% Aco engaste + {100 * p_ti:.2f}% Titanio ponta"
            )
            nomes_var.append(f"Eng_Aco_{nome_aco:05d}_Ponta_Ti_{nome_ti:05d}")

        elif ordem_material == 2:
            nomes_config.append(
                f"{100 * p_ti:.2f}% Titanio engaste + {100 * p_aco:.2f}% Aco ponta"
            )
            nomes_var.append(f"Eng_Ti_{nome_ti:05d}_Ponta_Aco_{nome_aco:05d}")

        else:
            raise ValueError("ordem_material invalida. Use 1 ou 2.")

    return nomes_config, nomes_var


# ---------------------------------------------------------------------------
# TRECHOS DE MATERIAL
# ---------------------------------------------------------------------------


def create_material_segments(
    p_aco: float,
    p_ti: float,
    config: AnalysisConfig,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """
    Retorna os trechos de material para uma configuracao.

    segments[:, 0] -> x_ini
    segments[:, 1] -> x_fim
    segments[:, 2] -> E
    segments[:, 3] -> rho

    material_id:
        0 -> aco
        1 -> titanio
    """
    L = config.L
    tol = 1e-12

    if config.ordem_material == 1:
        # Aco no engaste / Titanio na ponta
        if abs(p_aco - 1.0) < tol:
            segments = np.array([[0.0, L, config.E_aco, config.rho_aco]], dtype=float)
            material_id = np.array([MATERIAL_STEEL], dtype=np.int32)
            material_names = ["Aco"]

        elif abs(p_aco) < tol:
            segments = np.array([[0.0, L, config.E_ti, config.rho_ti]], dtype=float)
            material_id = np.array([MATERIAL_TITANIUM], dtype=np.int32)
            material_names = ["Titanio"]

        else:
            segments = np.array(
                [
                    [0.0, p_aco * L, config.E_aco, config.rho_aco],
                    [p_aco * L, L, config.E_ti, config.rho_ti],
                ],
                dtype=float,
            )
            material_id = np.array([MATERIAL_STEEL, MATERIAL_TITANIUM], dtype=np.int32)
            material_names = ["Aco", "Titanio"]

    elif config.ordem_material == 2:
        # Titanio no engaste / Aco na ponta
        if abs(p_aco - 1.0) < tol:
            segments = np.array([[0.0, L, config.E_aco, config.rho_aco]], dtype=float)
            material_id = np.array([MATERIAL_STEEL], dtype=np.int32)
            material_names = ["Aco"]

        elif abs(p_aco) < tol:
            segments = np.array([[0.0, L, config.E_ti, config.rho_ti]], dtype=float)
            material_id = np.array([MATERIAL_TITANIUM], dtype=np.int32)
            material_names = ["Titanio"]

        else:
            segments = np.array(
                [
                    [0.0, p_ti * L, config.E_ti, config.rho_ti],
                    [p_ti * L, L, config.E_aco, config.rho_aco],
                ],
                dtype=float,
            )
            material_id = np.array([MATERIAL_TITANIUM, MATERIAL_STEEL], dtype=np.int32)
            material_names = ["Titanio", "Aco"]

    else:
        raise ValueError("ordem_material invalida. Use 1 ou 2.")

    validate_segments(segments, L)
    return segments, material_id, material_names


def validate_segments(segments: np.ndarray, L: float) -> None:
    tol = 1e-10 * L

    if segments.ndim != 2 or segments.shape[1] != 4:
        raise ValueError("segments deve ter dimensao (n_trechos, 4).")

    if abs(segments[-1, 1] - L) > tol:
        raise ValueError("O ultimo ponto final dos trechos deve ser igual a L.")

    if np.any(segments[:, 1] <= 0.0):
        raise ValueError(
            "Todos os pontos finais dos trechos devem ser maiores que zero."
        )

    if np.any(np.diff(segments[:, 1]) <= tol):
        raise ValueError("Os pontos finais dos trechos devem estar em ordem crescente.")

    if abs(segments[0, 0]) > tol:
        raise ValueError("O primeiro trecho deve comecar em x = 0.")


# ---------------------------------------------------------------------------
# MALHA, TOPOLOGIA E GRAUS DE LIBERDADE
# ---------------------------------------------------------------------------


def generate_mesh_by_segments(
    segments: np.ndarray,
    NE_base: int,
    L: float,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Cria a malha por trecho de material, reproduzindo a logica do MATLAB.
    """
    if NE_base < 1:
        raise ValueError("NE_base deve ser positivo.")

    segment_lengths = segments[:, 1] - segments[:, 0]

    n_elem_segment = np.floor(NE_base * segment_lengths / L).astype(np.int32)
    n_elem_segment[n_elem_segment < 1] = 1

    difference = int(NE_base - np.sum(n_elem_segment))
    remainders = NE_base * segment_lengths / L - np.floor(NE_base * segment_lengths / L)

    if difference > 0:
        idx_order = np.argsort(-remainders)
        for ii in range(difference):
            idx = idx_order[ii % len(idx_order)]
            n_elem_segment[idx] += 1

    elif difference < 0:
        difference = abs(difference)
        idx_order = np.argsort(remainders)
        counter = 0

        while difference > 0:
            idx = idx_order[counter % len(idx_order)]

            if n_elem_segment[idx] > 1:
                n_elem_segment[idx] -= 1
                difference -= 1

            counter += 1

    node_blocks: list[np.ndarray] = []

    for i, n_elem in enumerate(n_elem_segment):
        x_ini = segments[i, 0]
        x_fim = segments[i, 1]
        x_local = np.linspace(x_ini, x_fim, int(n_elem) + 1)

        if i == 0:
            node_blocks.append(x_local)
        else:
            node_blocks.append(x_local[1:])

    x_nodes = np.concatenate(node_blocks).astype(float)
    x_nodes[0] = 0.0
    x_nodes[-1] = L

    return x_nodes, n_elem_segment


def build_topology(n_elements: int) -> np.ndarray:
    """
    Cria a matriz Edof em base zero.

    Coluna 0: indice do elemento.
    Colunas 1:7: graus de liberdade globais do elemento.

    Cada no tem 3 GDL:
        0 -> u
        1 -> v
        2 -> theta
    """
    edof = np.zeros((n_elements, 7), dtype=np.int32)

    for e in range(n_elements):
        edof[e, 0] = e
        edof[e, 1:] = np.arange(3 * e, 3 * e + 6, dtype=np.int32)

    return edof


def build_coordinates(x_nodes: np.ndarray) -> np.ndarray:
    y_nodes = np.zeros_like(x_nodes)
    return np.column_stack((x_nodes, y_nodes))


def build_dof(n_nodes: int) -> np.ndarray:
    return np.arange(3 * n_nodes, dtype=np.int32).reshape(n_nodes, 3)


# ---------------------------------------------------------------------------
# MONTAGEM GLOBAL
# ---------------------------------------------------------------------------


def _assem_matrix(
    edof_row: np.ndarray, global_matrix: np.ndarray, element_matrix: np.ndarray
) -> np.ndarray:
    """
    Chama a funcao assem portada, aceitando tanto retorno direto K quanto
    retorno em tupla/lista.
    """
    assembled = assem(edof_row, global_matrix, element_matrix)

    if isinstance(assembled, tuple) or isinstance(assembled, list):
        return assembled[0]

    return assembled


def assemble_global_matrices(
    edof: np.ndarray,
    coord: np.ndarray,
    dof: np.ndarray,
    segments: np.ndarray,
    A: float,
    I: float,
    L_total: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Monta K e M usando coordxtr, beam2d e assem portados.
    """
    n_elements = edof.shape[0]
    n_dof_total = int(np.max(edof[:, 1:]) + 1)

    K = np.zeros((n_dof_total, n_dof_total), dtype=float)
    M = np.zeros((n_dof_total, n_dof_total), dtype=float)

    coords = coordxtr(edof, coord, dof, 2)
    ex = coords[0]
    ey = coords[1]

    tol = 1e-10 * L_total

    for i in range(n_elements):
        x_c = float(np.mean(ex[i, :]))

        match = np.where((x_c >= segments[:, 0] - tol) & (x_c <= segments[:, 1] + tol))[
            0
        ]

        if match.size == 0:
            raise ValueError(f"Elemento {i} esta fora dos trechos de material.")

        mat_id = int(match[0])
        E_i = float(segments[mat_id, 2])
        rho_i = float(segments[mat_id, 3])

        ep = np.array([E_i, A, I, rho_i * A], dtype=float)

        beam_result = beam2d(ex[i, :], ey[i, :], ep)
        Ke = beam_result[0]
        Me = beam_result[1]

        K = _assem_matrix(edof[i, :], K, Ke)
        M = _assem_matrix(edof[i, :], M, Me)

    return K, M, ex, ey


# ---------------------------------------------------------------------------
# CONDICOES DE CONTORNO E PROBLEMA MODAL
# ---------------------------------------------------------------------------


def get_boundary_conditions(cc: int, nd: int) -> np.ndarray:
    """
    Retorna os GDL restritos em base zero.
    """
    if cc == 0:
        return np.array([], dtype=np.int32)

    if cc == 1:
        return np.array([0, 1, 2], dtype=np.int32)

    if cc == 2:
        return np.array([0, 1, 2, nd - 3, nd - 2, nd - 1], dtype=np.int32)

    if cc == 3:
        return np.array([0, 1, nd - 3, nd - 2], dtype=np.int32)

    raise ValueError("Condicao de contorno invalida. Use cc = 0, 1, 2 ou 3.")


def solve_modal_problem(
    K: np.ndarray,
    M: np.ndarray,
    boundary_dofs: np.ndarray,
    cc: int,
    n_modes: int,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Resolve o problema generalizado de autovalores e remove os modos rigidos
    quando a viga e livre-livre.
    """
    eigenvalues_all, eigenvectors_all = eigen_solver(K, M, boundary_dofs)

    eigenvalues_all = np.real(np.asarray(eigenvalues_all, dtype=float).reshape(-1))
    eigenvectors_all = np.asarray(eigenvectors_all, dtype=float)

    tol_lambda = 1e-9 * max(1.0, float(np.max(np.abs(eigenvalues_all))))

    if np.any(eigenvalues_all < -tol_lambda):
        print(
            "Warning: foram encontrados autovalores negativos relevantes. "
            "Verifique K, M e as condicoes de contorno."
        )

    eigenvalues_all[eigenvalues_all < 0.0] = 0.0

    frequencies_all = np.sqrt(eigenvalues_all) / (2.0 * np.pi)

    # O eigen_solver portado deve seguir o comportamento do eigen.m:
    # autovalores e autovetores ja ordenados em ordem crescente.
    n_rigid_modes = 3 if cc == 0 else 0

    if frequencies_all.size < n_rigid_modes + n_modes:
        raise ValueError(
            "Numero insuficiente de modos calculados. Aumente NE ou reduza N."
        )

    elastic_idx = np.arange(n_rigid_modes, n_rigid_modes + n_modes)

    frequencies = frequencies_all[elastic_idx]
    modal_vectors = eigenvectors_all[:, elastic_idx]

    return frequencies, modal_vectors


# ---------------------------------------------------------------------------
# FORMAS MODAIS
# ---------------------------------------------------------------------------


def normalize_modal_shapes(
    modal_vectors: np.ndarray,
    dof: np.ndarray,
    n_modes: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Extrai v(x) e theta(x), normalizando cada modo por max(abs(v)) = 1.
    """
    vectors = modal_vectors[:, :n_modes].copy()

    dof_v = dof[:, 1]
    dof_theta = dof[:, 2]

    modes_v = vectors[dof_v, :].copy()
    modes_theta = vectors[dof_theta, :].copy()

    for mode in range(n_modes):
        idx_max = int(np.argmax(np.abs(modes_v[:, mode])))
        amp_max = float(abs(modes_v[idx_max, mode]))

        if amp_max > np.finfo(float).eps:
            sign_value = np.sign(modes_v[idx_max, mode])
            if sign_value == 0:
                sign_value = 1.0

            modes_v[:, mode] /= amp_max
            modes_theta[:, mode] /= amp_max
            vectors[:, mode] /= amp_max

            if sign_value < 0:
                modes_v[:, mode] *= -1.0
                modes_theta[:, mode] *= -1.0
                vectors[:, mode] *= -1.0

    return modes_v, modes_theta, vectors


# ---------------------------------------------------------------------------
# CONVERGENCIA DE UMA CONFIGURACAO
# ---------------------------------------------------------------------------


def run_configuration(
    config: AnalysisConfig,
    config_index: int,
    p_aco: float,
    p_ti: float,
    config_name: str,
    modes_control: np.ndarray,
    A: float,
    I: float,
) -> dict[str, Any]:
    tic_config = time.perf_counter()

    segments, material_id, material_names = create_material_segments(
        p_aco, p_ti, config
    )

    if config.print_resumo_config:
        print("\n---------------------------------------------------------------")
        print(f"Configuracao {config_index + 1}: {config_name}")
        print("---------------------------------------------------------------")
        print(
            f"{'Trecho':>8s} | {'x_ini':>12s} | {'x_fim':>12s} | {'E [Pa]':>14s} | {'rho [kg/m3]':>14s} | {'Material':>12s}"
        )
        print("-" * 88)
        for i in range(segments.shape[0]):
            print(
                f"{i + 1:8d} | "
                f"{segments[i, 0]:12.6f} | "
                f"{segments[i, 1]:12.6f} | "
                f"{segments[i, 2]:14.6e} | "
                f"{segments[i, 3]:14.6f} | "
                f"{material_names[i]:>12s}"
            )
        print("-" * 88)

    NE = config.NE_ini
    iteration = 0
    converged = False
    error_current = np.inf
    critical_mode = np.nan

    frequency_history: list[np.ndarray] = []
    error_history: list[np.ndarray] = []
    critical_mode_history: list[float] = []

    hist_rows: list[list[float]] = []

    final_x_nodes: np.ndarray | None = None
    final_dof: np.ndarray | None = None
    final_modal_vectors: np.ndarray | None = None
    final_num_elements = 0
    final_num_nodes = 0
    final_errors = np.full(config.N, np.nan, dtype=float)

    while True:
        iteration += 1
        NE_base = NE

        x_nodes, _ = generate_mesh_by_segments(segments, NE_base, config.L)
        n_elements = x_nodes.size - 1
        n_nodes = x_nodes.size

        dx_min = float(np.min(np.diff(x_nodes)))
        dx_med = float(config.L / n_elements)

        if dx_min < 0.05 * dx_med:
            print(
                "Warning: elemento muito pequeno detectado: "
                f"dx_min = {dx_min:.6e} m | dx_medio = {dx_med:.6e} m"
            )

        edof = build_topology(n_elements)
        coord = build_coordinates(x_nodes)
        dof = build_dof(n_nodes)

        K, M, _, _ = assemble_global_matrices(
            edof=edof,
            coord=coord,
            dof=dof,
            segments=segments,
            A=A,
            I=I,
            L_total=config.L,
        )

        nd = M.shape[0]
        boundary_dofs = get_boundary_conditions(config.cc, nd)

        frequencies, modal_vectors = solve_modal_problem(
            K=K,
            M=M,
            boundary_dofs=boundary_dofs,
            cc=config.cc,
            n_modes=config.N,
        )

        frequency_history.append(frequencies)

        if iteration > 1:
            previous = frequency_history[-2]
            current = frequency_history[-1]

            error_modes = (
                100.0
                * np.abs(current - previous)
                / np.maximum(
                    np.abs(current),
                    np.finfo(float).eps,
                )
            )

            error_history.append(error_modes)

            local_errors = error_modes[modes_control]
            local_idx = int(np.argmax(local_errors))

            error_current = float(local_errors[local_idx])
            critical_mode = float(modes_control[local_idx] + 1)  # salva modo em base 1
            critical_mode_history.append(critical_mode)

        else:
            error_modes = np.full(config.N, np.nan, dtype=float)
            error_current = np.inf
            critical_mode = np.nan

        if iteration == 1:
            hist_rows.append(
                [
                    float(iteration),
                    float(NE_base),
                    float(n_elements),
                    float(n_nodes),
                    np.nan,
                    np.nan,
                    np.nan,
                ]
            )
        else:
            hist_rows.append(
                [
                    float(iteration),
                    float(NE_base),
                    float(n_elements),
                    float(n_nodes),
                    float(frequencies[int(critical_mode) - 1]),
                    float(critical_mode),
                    float(error_current),
                ]
            )

        if config.print_iteracoes:
            if iteration == 1:
                print(
                    f"Iter {iteration:4d} | NE_base = {NE_base:5d} | "
                    f"NE_real = {n_elements:5d} | Nos = {n_nodes:5d} | Erro = ---"
                )
            else:
                print(
                    f"Iter {iteration:4d} | NE_base = {NE_base:5d} | "
                    f"NE_real = {n_elements:5d} | Nos = {n_nodes:5d} | "
                    f"Erro = {error_current:.6g} % | Modo = {int(critical_mode)}"
                )

        final_x_nodes = x_nodes
        final_dof = dof
        final_modal_vectors = modal_vectors
        final_num_elements = n_elements
        final_num_nodes = n_nodes

        if iteration > 1:
            final_errors = error_modes.copy()

        if iteration > 1 and error_current <= config.erro_admissivel:
            converged = True
            break

        if iteration >= config.max_iter:
            print(
                f"Warning: numero maximo de iteracoes atingido na configuracao {config_name}."
            )
            converged = False
            break

        NE += config.passo_elementos

    if final_x_nodes is None or final_dof is None or final_modal_vectors is None:
        raise RuntimeError(
            "Falha interna: resultados finais da configuracao nao foram definidos."
        )

    modes_v, modes_theta, modal_vectors_normalized = normalize_modal_shapes(
        modal_vectors=final_modal_vectors,
        dof=final_dof,
        n_modes=config.N,
    )

    time_config = time.perf_counter() - tic_config
    final_frequencies = frequency_history[-1]
    history = np.asarray(hist_rows, dtype=float)

    if config.print_resumo_config:
        print("\nResultado - " + config_name)
        print(f"Convergiu: {int(converged)}")
        print(f"Tempo: {time_config:.6f} s")
        print(f"Elementos finais: {final_num_elements}")
        print(f"Nos finais: {final_num_nodes}")
        print(f"Erro critico final [%]: {error_current:.6g}")
        if np.isfinite(critical_mode):
            print(f"Modo critico final: {int(critical_mode)}")
        else:
            print("Modo critico final: NaN")
        print(
            "Frequencias finais [Hz]: "
            + " ".join(f"{v:12.6f}" for v in final_frequencies)
        )
        print(
            "Erros finais por modo [%]: " + " ".join(f"{v:12.6g}" for v in final_errors)
        )

    return {
        "frequencies": final_frequencies,
        "errors": final_errors,
        "num_nodes": final_num_nodes,
        "num_elements": final_num_elements,
        "time_s": time_config,
        "critical_error": error_current if np.isfinite(error_current) else np.nan,
        "critical_mode": critical_mode,
        "converged": converged,
        "nodes": final_x_nodes,
        "segments": segments,
        "segment_material_id": material_id,
        "history": history,
        "modes_v": modes_v,
        "modes_theta": modes_theta,
        "modal_vectors": modal_vectors_normalized,
        "dof_count": modal_vectors_normalized.shape[0],
    }


# ---------------------------------------------------------------------------
# EMPACOTAMENTO DOS RESULTADOS
# ---------------------------------------------------------------------------


def pack_results(
    config: AnalysisConfig,
    config_results: list[dict[str, Any]],
    perc_aco_vec: np.ndarray,
    perc_ti_vec: np.ndarray,
    nomes_config: list[str],
    nomes_var: list[str],
    A: float,
    I: float,
    total_time: float,
) -> dict[str, Any]:
    n_config = len(config_results)
    n_modes = config.N

    node_count = np.array([r["num_nodes"] for r in config_results], dtype=np.int32)
    dof_count = np.array([r["dof_count"] for r in config_results], dtype=np.int32)
    segment_count = np.array(
        [r["segments"].shape[0] for r in config_results], dtype=np.int32
    )
    history_count = np.array(
        [r["history"].shape[0] for r in config_results], dtype=np.int32
    )

    max_nodes = int(np.max(node_count))
    max_dof = int(np.max(dof_count))
    max_segments = int(np.max(segment_count))
    max_history_steps = int(np.max(history_count))

    frequencies = np.full((n_config, n_modes), np.nan, dtype=float)
    errors = np.full((n_config, n_modes), np.nan, dtype=float)

    num_nodes = np.zeros(n_config, dtype=np.int32)
    num_elements = np.zeros(n_config, dtype=np.int32)
    time_config = np.full(n_config, np.nan, dtype=float)
    critical_error = np.full(n_config, np.nan, dtype=float)
    critical_mode = np.full(n_config, np.nan, dtype=float)
    converged = np.zeros(n_config, dtype=np.int32)

    nodes = np.full((n_config, max_nodes), np.nan, dtype=float)
    modes_v = np.full((n_config, max_nodes, n_modes), np.nan, dtype=float)
    modes_theta = np.full((n_config, max_nodes, n_modes), np.nan, dtype=float)

    modal_vectors = np.full((n_config, max_dof, n_modes), np.nan, dtype=float)

    segments = np.full((n_config, max_segments, 4), np.nan, dtype=float)
    segment_material_id = np.full((n_config, max_segments), -1, dtype=np.int32)

    history = np.full((n_config, max_history_steps, 7), np.nan, dtype=float)

    for ic, result in enumerate(config_results):
        nn = int(result["num_nodes"])
        nd = int(result["dof_count"])
        ns = int(result["segments"].shape[0])
        nh = int(result["history"].shape[0])

        frequencies[ic, :] = result["frequencies"]
        errors[ic, :] = result["errors"]

        num_nodes[ic] = int(result["num_nodes"])
        num_elements[ic] = int(result["num_elements"])
        time_config[ic] = float(result["time_s"])
        critical_error[ic] = float(result["critical_error"])
        critical_mode[ic] = float(result["critical_mode"])
        converged[ic] = int(result["converged"])

        nodes[ic, :nn] = result["nodes"]
        modes_v[ic, :nn, :] = result["modes_v"]
        modes_theta[ic, :nn, :] = result["modes_theta"]

        modal_vectors[ic, :nd, :] = result["modal_vectors"]

        segments[ic, :ns, :] = result["segments"]
        segment_material_id[ic, :ns] = result["segment_material_id"]

        history[ic, :nh, :] = result["history"]

    summary = np.column_stack(
        (
            np.arange(n_config, dtype=float),
            perc_aco_vec,
            perc_ti_vec,
            num_elements.astype(float),
            num_nodes.astype(float),
            time_config,
            critical_error,
            critical_mode,
            converged.astype(float),
        )
    )

    mode_numbers = np.arange(1, n_modes + 1, dtype=np.int32)
    config_indices = np.arange(n_config, dtype=np.int32)

    results: dict[str, Any] = {
        # Identificadores numericos
        "config_indices": config_indices,
        "mode_numbers": mode_numbers,
        # Composicao
        "percent_steel": perc_aco_vec,
        "percent_titanium": perc_ti_vec,
        # Frequencias e convergencia
        "frequencies": frequencies,
        "errors": errors,
        "num_nodes": num_nodes,
        "num_elements": num_elements,
        "time_config": time_config,
        "total_time": np.array([total_time], dtype=float),
        "critical_error": critical_error,
        "critical_mode": critical_mode,
        "converged": converged,
        # Geometria discretizada e modos
        "nodes": nodes,
        "node_count": node_count,
        "modes_v": modes_v,
        "modes_theta": modes_theta,
        "modal_vectors": modal_vectors,
        "dof_count": dof_count,
        # Trechos de material
        "segments": segments,
        "segment_count": segment_count,
        "segment_material_id": segment_material_id,
        # Historico de convergencia
        "history": history,
        "history_count": history_count,
        # Resumo numerico equivalente a Tabela_Resumo, sem strings
        "summary": summary,
        # Parametros numericos principais
        "L": np.array([config.L], dtype=float),
        "h": np.array([config.h], dtype=float),
        "b": np.array([config.b], dtype=float),
        "A": np.array([A], dtype=float),
        "I": np.array([I], dtype=float),
        "E_aco": np.array([config.E_aco], dtype=float),
        "rho_aco": np.array([config.rho_aco], dtype=float),
        "E_ti": np.array([config.E_ti], dtype=float),
        "rho_ti": np.array([config.rho_ti], dtype=float),
        "cc": np.array([config.cc], dtype=np.int32),
        "N": np.array([config.N], dtype=np.int32),
        "erro_admissivel": np.array([config.erro_admissivel], dtype=float),
        "NE_ini": np.array([config.NE_ini], dtype=np.int32),
        "passo_elementos": np.array([config.passo_elementos], dtype=np.int32),
        "max_iter": np.array([config.max_iter], dtype=np.int32),
        "passo_composicao": np.array([config.passo_composicao], dtype=float),
        "ordem_material": np.array([config.ordem_material], dtype=np.int32),
    }

    results["metadata"] = {
        "description": "Resultados da analise modal MEF para viga bimaterial. Arrays numericos em .npz; metadados em .json.",
        "array_convention": "Eixo 0 = configuracao. Eixo 1 = no, modo ou coluna. Eixo 2 = modo quando aplicavel.",
        "configuration_names": nomes_config,
        "variable_names_legacy": nomes_var,
        "n_config": n_config,
        "n_modes": n_modes,
        "max_nodes": max_nodes,
        "max_dof": max_dof,
        "max_segments": max_segments,
        "max_history_steps": max_history_steps,
        "materials": {
            str(MATERIAL_STEEL): "Aco",
            str(MATERIAL_TITANIUM): "Titanio",
        },
        "units": {
            "L": "m",
            "h": "m",
            "b": "m",
            "A": "m2",
            "I": "m4",
            "E": "Pa",
            "rho": "kg/m3",
            "frequencies": "Hz",
            "errors": "%",
            "time": "s",
            "nodes": "m",
            "modes_v": "normalizado por max(abs(v)) = 1",
            "modes_theta": "normalizado pelo mesmo fator de modes_v",
        },
        "columns_segments": ["x_ini", "x_fim", "E", "rho"],
        "columns_history": [
            "Iteracao",
            "ElementosBase",
            "ElementosReais",
            "Nos",
            "FreqCritica_Hz",
            "ModoCritico",
            "ErroCritico_percentual",
        ],
        "columns_summary": [
            "ConfigIndex",
            "Percentual_Aco",
            "Percentual_Titanio",
            "Elementos_Finais",
            "Nos_Finais",
            "Tempo_s",
            "Erro_Critico_percentual",
            "Modo_Critico",
            "Convergiu",
        ],
        "valid_slices": {
            "nodes": "nodes[ic, 0:node_count[ic]]",
            "modes_v": "modes_v[ic, 0:node_count[ic], mode]",
            "modes_theta": "modes_theta[ic, 0:node_count[ic], mode]",
            "modal_vectors": "modal_vectors[ic, 0:dof_count[ic], mode]",
            "segments": "segments[ic, 0:segment_count[ic], :]",
            "history": "history[ic, 0:history_count[ic], :]",
        },
        "config": asdict(config),
    }

    return results


# ---------------------------------------------------------------------------
# EXECUCAO PRINCIPAL DA ANALISE
# ---------------------------------------------------------------------------


def run_analysis(config: AnalysisConfig) -> dict[str, Any]:
    tic_total = time.perf_counter()

    if config.N > 20:
        raise ValueError("Numero de modos muito grande.")

    if config.NE_ini < 4:
        raise ValueError("Numero de elementos iniciais muito pequeno.")

    if config.passo_elementos < 1:
        raise ValueError("passo_elementos deve ser maior ou igual a 1.")

    A = config.b * config.h
    I = config.b * config.h**3 / 12.0

    perc_aco_vec, perc_ti_vec = create_composition_vectors(
        passo_composicao=config.passo_composicao,
        ordem_material=config.ordem_material,
    )

    nomes_config, nomes_var = create_configuration_names(
        perc_aco_vec=perc_aco_vec,
        perc_ti_vec=perc_ti_vec,
        ordem_material=config.ordem_material,
    )

    n_config = perc_aco_vec.size

    if config.n_ultimos_controle is None:
        n_ultimos_controle = config.N
    else:
        n_ultimos_controle = int(config.n_ultimos_controle)

    if n_ultimos_controle < 1 or n_ultimos_controle > config.N:
        raise ValueError("n_ultimos_controle deve estar entre 1 e N.")

    modes_control = np.arange(config.N - n_ultimos_controle, config.N, dtype=np.int32)

    print("\n===============================================================")
    print("        ANALISE MODAL - TODAS AS CONFIGURACOES")
    print("===============================================================")
    print(f"Comprimento L = {config.L:.6f} m")
    print(f"Secao: b = {config.b:.6f} m | h = {config.h:.6f} m")
    print(f"cc = {config.cc}")
    print(f"N = {config.N} modos")
    print(f"Erro alvo = {config.erro_admissivel:.6g} %")
    print(f"NE inicial = {config.NE_ini}")
    print(f"Passo de elementos = +{config.passo_elementos}")
    print(f"Passo de composicao = {config.passo_composicao:.6f}")
    print(f"Numero de configuracoes = {n_config}")

    if config.ordem_material == 1:
        print("Ordem dos materiais: Aco no engaste / Titanio na ponta")
    else:
        print("Ordem dos materiais: Titanio no engaste / Aco na ponta")

    print(
        "Modos usados no criterio de erro: "
        + " ".join(str(int(m + 1)) for m in modes_control)
    )
    print("Calcular formas modais = 1")
    print("===============================================================\n")

    config_results: list[dict[str, Any]] = []

    for ic in range(n_config):
        result = run_configuration(
            config=config,
            config_index=ic,
            p_aco=float(perc_aco_vec[ic]),
            p_ti=float(perc_ti_vec[ic]),
            config_name=nomes_config[ic],
            modes_control=modes_control,
            A=A,
            I=I,
        )
        config_results.append(result)

    total_time = time.perf_counter() - tic_total

    results = pack_results(
        config=config,
        config_results=config_results,
        perc_aco_vec=perc_aco_vec,
        perc_ti_vec=perc_ti_vec,
        nomes_config=nomes_config,
        nomes_var=nomes_var,
        A=A,
        I=I,
        total_time=total_time,
    )

    print("\n===============================================================")
    print("        ANALISE FINALIZADA")
    print("===============================================================")
    print(f"Tempo total do run: {total_time:.6f} s")
    print("===============================================================\n")

    return results
