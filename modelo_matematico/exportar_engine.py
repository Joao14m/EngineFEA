"""
Exporta os resultados FEA para um binario simples consumido pela engine C++.

O .npz e um ZIP de arquivos .npy e nao pode ser lido diretamente em C++.
Este modulo le os resultados nodais, reconstroi a linha neutra por
interpolacao de Hermite e grava um arquivo plano, sem padding e em
float32, que a engine abre com um std::ifstream comum.

Layout de output/viga.bin (little-endian):

    char   magic[4]      "VIGA"
    uint32 version       1
    uint32 n_config
    uint32 n_modes
    float  L             comprimento da viga [m]
    float  h             altura da secao [m]

    para cada configuracao:
        uint32 n_samples
        float  p_aco                     fracao de aco [0, 1]
        float  freq[n_modes]             [Hz]
        float  x[n_samples]              [m]
        float  v[n_modes][n_samples]     forma modal normalizada
        float  slope[n_modes][n_samples] dv/dx da forma modal
        uint8  mat[n_samples]            0 = aco, 1 = titanio

O campo slope existe porque a engine reconstroi a espessura da viga no
vertex shader. Deslocar os vertices por +-h/2 ao longo da normal exige a
inclinacao da curva ja escalada; sem ela, aplicar um fator de escala na
deflexao afinaria a viga junto com a deformacao.
"""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

import numpy as np

from modelo_matematico.gerar_malha_opengl import _hermite_beam_v_and_slope

MAGIC = b"VIGA"
VERSION = 1


def _material_per_sample(
    x: np.ndarray, segments: np.ndarray, material_id: np.ndarray, L: float
) -> np.ndarray:
    """
    Mapeia cada amostra da linha neutra para o id do material do seu trecho.

    A malha sempre tem um no exatamente na fronteira entre os materiais, entao
    a transicao de cor cai sobre uma aresta de elemento, nao no meio dele.
    """
    tol = 1e-10 * max(1.0, abs(float(L)))
    idx = np.searchsorted(segments[:, 1] + tol, x, side="left")
    idx = np.clip(idx, 0, segments.shape[0] - 1)
    return material_id[idx].astype(np.uint8)


def build_config_payload(
    data: dict[str, np.ndarray], ic: int, samples_per_element: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Reconstroi x, v, slope e material para uma configuracao."""
    nn = int(data["node_count"][ic])
    ns = int(data["segment_count"][ic])
    n_elements = int(data["num_elements"][ic])
    n_modes = int(data["mode_numbers"].size)

    x_nodes = data["nodes"][ic, :nn]
    modes_v = data["modes_v"][ic, :nn, :n_modes]
    modes_theta = data["modes_theta"][ic, :nn, :n_modes]
    segments = data["segments"][ic, :ns, :]
    material_id = data["segment_material_id"][ic, :ns]

    xi_full = np.linspace(0.0, 1.0, samples_per_element + 1)
    n_samples = n_elements * samples_per_element + 1

    x_out = np.empty(n_samples, dtype=np.float32)
    v_out = np.empty((n_modes, n_samples), dtype=np.float32)
    slope_out = np.empty((n_modes, n_samples), dtype=np.float32)

    for mode in range(n_modes):
        x_parts: list[np.ndarray] = []
        v_parts: list[np.ndarray] = []
        s_parts: list[np.ndarray] = []

        for e in range(n_elements):
            xi = xi_full if e == 0 else xi_full[1:]
            x_e, v_e, s_e = _hermite_beam_v_and_slope(
                x1=float(x_nodes[e]),
                x2=float(x_nodes[e + 1]),
                v1=float(modes_v[e, mode]),
                theta1=float(modes_theta[e, mode]),
                v2=float(modes_v[e + 1, mode]),
                theta2=float(modes_theta[e + 1, mode]),
                xi=xi,
            )
            x_parts.append(x_e)
            v_parts.append(v_e)
            s_parts.append(s_e)

        if mode == 0:
            x_out[:] = np.concatenate(x_parts)

        v_out[mode, :] = np.concatenate(v_parts)
        slope_out[mode, :] = np.concatenate(s_parts)

    mat_out = _material_per_sample(
        x=x_out.astype(float),
        segments=segments,
        material_id=material_id,
        L=float(data["L"][0]),
    )

    return x_out, v_out, slope_out, mat_out


def export_binary(
    npz_path: Path, output_path: Path, samples_per_element: int
) -> tuple[Path, int]:
    with np.load(npz_path) as loaded:
        data = {key: loaded[key] for key in loaded.files}

    required = (
        "nodes",
        "node_count",
        "num_elements",
        "modes_v",
        "modes_theta",
        "segments",
        "segment_count",
        "segment_material_id",
        "mode_numbers",
        "frequencies",
        "percent_steel",
        "h",
        "L",
    )
    missing = [key for key in required if key not in data]
    if missing:
        raise KeyError(f"Resultados sem campos obrigatorios: {', '.join(missing)}")

    n_config = int(data["node_count"].size)
    n_modes = int(data["mode_numbers"].size)
    L = float(data["L"][0])
    h = float(data["h"][0])

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("wb") as f:
        f.write(MAGIC)
        f.write(struct.pack("<IIIff", VERSION, n_config, n_modes, L, h))

        for ic in range(n_config):
            x, v, slope, mat = build_config_payload(data, ic, samples_per_element)

            f.write(struct.pack("<If", x.size, float(data["percent_steel"][ic])))
            data["frequencies"][ic, :n_modes].astype("<f4").tofile(f)
            x.astype("<f4").tofile(f)
            v.astype("<f4").tofile(f)
            slope.astype("<f4").tofile(f)
            mat.tofile(f)

    return output_path, output_path.stat().st_size


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Exporta Resultados_FEA.npz para o binario lido pela engine C++."
    )
    parser.add_argument(
        "--npz",
        type=Path,
        default=Path("output") / "Resultados_FEA.npz",
        help="Arquivo .npz de resultados FEA.",
    )
    parser.add_argument(
        "--saida",
        type=Path,
        default=Path("output") / "viga.bin",
        help="Arquivo binario de saida.",
    )
    parser.add_argument(
        "--samples-per-element",
        type=int,
        default=8,
        help="Subdivisoes geradas dentro de cada elemento finito.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.samples_per_element < 1:
        raise ValueError("samples_per_element deve ser maior ou igual a 1.")

    path, size = export_binary(
        npz_path=args.npz,
        output_path=args.saida,
        samples_per_element=args.samples_per_element,
    )

    print("Binario da engine gerado com sucesso.")
    print(f"Arquivo:  {path.resolve()}")
    print(f"Tamanho:  {size / 1024.0 / 1024.0:.2f} MB")


if __name__ == "__main__":
    main()
