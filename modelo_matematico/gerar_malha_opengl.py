from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np


OPENGL_KEYS = {
    "opengl_centerline_vertices",
    "opengl_centerline_vertex_count",
    "opengl_centerline_indices",
    "opengl_centerline_index_count",
    "opengl_beam_vertices",
    "opengl_beam_vertex_count",
    "opengl_beam_indices",
    "opengl_beam_index_count",
    "opengl_render_segment_material_id",
    "opengl_render_segment_count",
    "opengl_samples_per_element",
}


def _metadata_path_from_npz(npz_path: Path) -> Path:
    return npz_path.with_name(f"{npz_path.stem}_metadata.json")


def _load_metadata(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_metadata(path: Path, metadata: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False)


def _hermite_beam_v_and_slope(
    x1: float,
    x2: float,
    v1: float,
    theta1: float,
    v2: float,
    theta2: float,
    xi: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    Le = float(x2 - x1)
    if Le <= 0.0:
        raise ValueError("Comprimento do elemento deve ser positivo.")

    xi = np.asarray(xi, dtype=float)
    xi2 = xi * xi
    xi3 = xi2 * xi

    N1 = 1.0 - 3.0 * xi2 + 2.0 * xi3
    N2 = Le * (xi - 2.0 * xi2 + xi3)
    N3 = 3.0 * xi2 - 2.0 * xi3
    N4 = Le * (-xi2 + xi3)

    dN1_dxi = -6.0 * xi + 6.0 * xi2
    dN2_dxi = Le * (1.0 - 4.0 * xi + 3.0 * xi2)
    dN3_dxi = 6.0 * xi - 6.0 * xi2
    dN4_dxi = Le * (-2.0 * xi + 3.0 * xi2)

    x = x1 + xi * Le
    v = N1 * v1 + N2 * theta1 + N3 * v2 + N4 * theta2
    slope = (
        dN1_dxi * v1
        + dN2_dxi * theta1
        + dN3_dxi * v2
        + dN4_dxi * theta2
    ) / Le

    return x, v, slope


def _material_index_for_centers(
    centers: np.ndarray, segments: np.ndarray, L_total: float
) -> np.ndarray:
    tol = 1e-10 * max(1.0, abs(float(L_total)))
    segment_ends = segments[:, 1] + tol
    material_idx = np.searchsorted(segment_ends, centers, side="left")

    if np.any(material_idx >= segments.shape[0]):
        raise ValueError("Ha centros de elementos fora dos trechos de material.")

    starts = segments[material_idx, 0]
    ends = segments[material_idx, 1]
    outside = (centers < starts - tol) | (centers > ends + tol)
    if np.any(outside):
        raise ValueError("Ha centros de elementos fora dos trechos de material.")

    return material_idx


def build_opengl_meshes(
    data: dict[str, np.ndarray], samples_per_element: int
) -> dict[str, np.ndarray]:
    """
    Gera buffers OpenGL a partir dos resultados nodais salvos pelo solver.

    A malha e 2D no plano x-y, com z = 0. Os indices sao em base zero.
    Vertices invalidos usam NaN; indices/material invalidos usam -1.
    """
    if samples_per_element < 1:
        raise ValueError("samples_per_element deve ser maior ou igual a 1.")

    required = (
        "nodes",
        "node_count",
        "num_elements",
        "modes_v",
        "modes_theta",
        "segments",
        "segment_count",
        "mode_numbers",
        "h",
        "L",
    )
    missing = [key for key in required if key not in data]
    if missing:
        raise KeyError(f"Resultados sem campos obrigatorios: {', '.join(missing)}")

    node_count = data["node_count"].astype(np.int32)
    num_elements = data["num_elements"].astype(np.int32)
    n_config = int(node_count.size)
    n_modes = int(data["mode_numbers"].size)
    beam_height = float(data["h"][0])
    L_total = float(data["L"][0])

    max_elements = int(np.max(num_elements))
    max_centerline_vertices = max_elements * samples_per_element + 1
    max_beam_vertices = 2 * max_centerline_vertices
    max_render_segments = max_centerline_vertices - 1
    max_centerline_indices = 2 * max_render_segments
    max_beam_indices = 6 * max_render_segments

    centerline_vertices = np.full(
        (n_config, n_modes, max_centerline_vertices, 3), np.nan, dtype=float
    )
    beam_vertices = np.full(
        (n_config, n_modes, max_beam_vertices, 3), np.nan, dtype=float
    )
    centerline_indices = np.full(
        (n_config, max_centerline_indices), -1, dtype=np.int32
    )
    beam_indices = np.full((n_config, max_beam_indices), -1, dtype=np.int32)
    render_segment_material_id = np.full(
        (n_config, max_render_segments), -1, dtype=np.int32
    )

    centerline_vertex_count = np.zeros(n_config, dtype=np.int32)
    beam_vertex_count = np.zeros(n_config, dtype=np.int32)
    centerline_index_count = np.zeros(n_config, dtype=np.int32)
    beam_index_count = np.zeros(n_config, dtype=np.int32)
    render_segment_count = np.zeros(n_config, dtype=np.int32)

    xi_full = np.linspace(0.0, 1.0, samples_per_element + 1)

    for ic in range(n_config):
        nn = int(node_count[ic])
        ns = int(data["segment_count"][ic])
        n_elements = int(num_elements[ic])
        x_nodes = data["nodes"][ic, :nn]
        modes_v = data["modes_v"][ic, :nn, :n_modes]
        modes_theta = data["modes_theta"][ic, :nn, :n_modes]
        segments = data["segments"][ic, :ns, :]

        n_centerline = n_elements * samples_per_element + 1
        n_beam_vertices = 2 * n_centerline
        n_render_segments = n_centerline - 1

        centerline_vertex_count[ic] = n_centerline
        beam_vertex_count[ic] = n_beam_vertices
        render_segment_count[ic] = n_render_segments
        centerline_index_count[ic] = 2 * n_render_segments
        beam_index_count[ic] = 6 * n_render_segments

        element_centers = 0.5 * (x_nodes[:-1] + x_nodes[1:])
        element_material_id = _material_index_for_centers(
            element_centers, segments, L_total
        ).astype(np.int32)

        line_idx: list[int] = []
        tri_idx: list[int] = []
        material_idx: list[int] = []

        for i in range(n_render_segments):
            line_idx.extend((i, i + 1))

            b0 = 2 * i
            t0 = b0 + 1
            b1 = 2 * (i + 1)
            t1 = b1 + 1
            tri_idx.extend((b0, b1, t1, b0, t1, t0))

            element_index = min(i // samples_per_element, n_elements - 1)
            material_idx.append(int(element_material_id[element_index]))

        centerline_indices[ic, : len(line_idx)] = np.asarray(line_idx, dtype=np.int32)
        beam_indices[ic, : len(tri_idx)] = np.asarray(tri_idx, dtype=np.int32)
        render_segment_material_id[ic, : len(material_idx)] = np.asarray(
            material_idx, dtype=np.int32
        )

        for mode in range(n_modes):
            x_parts: list[np.ndarray] = []
            v_parts: list[np.ndarray] = []
            slope_parts: list[np.ndarray] = []

            for e in range(n_elements):
                xi = xi_full if e == 0 else xi_full[1:]
                x_e, v_e, slope_e = _hermite_beam_v_and_slope(
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
                slope_parts.append(slope_e)

            x = np.concatenate(x_parts)
            v = np.concatenate(v_parts)
            slope = np.concatenate(slope_parts)

            center = np.column_stack((x, v, np.zeros_like(x)))
            centerline_vertices[ic, mode, :n_centerline, :] = center

            norm = np.sqrt(1.0 + slope * slope)
            nx = -slope / norm
            ny = 1.0 / norm
            half_h = 0.5 * beam_height

            lower = np.column_stack(
                (x - half_h * nx, v - half_h * ny, np.zeros_like(x))
            )
            upper = np.column_stack(
                (x + half_h * nx, v + half_h * ny, np.zeros_like(x))
            )

            beam = np.empty((n_beam_vertices, 3), dtype=float)
            beam[0::2, :] = lower
            beam[1::2, :] = upper
            beam_vertices[ic, mode, :n_beam_vertices, :] = beam

    return {
        "opengl_centerline_vertices": centerline_vertices,
        "opengl_centerline_vertex_count": centerline_vertex_count,
        "opengl_centerline_indices": centerline_indices,
        "opengl_centerline_index_count": centerline_index_count,
        "opengl_beam_vertices": beam_vertices,
        "opengl_beam_vertex_count": beam_vertex_count,
        "opengl_beam_indices": beam_indices,
        "opengl_beam_index_count": beam_index_count,
        "opengl_render_segment_material_id": render_segment_material_id,
        "opengl_render_segment_count": render_segment_count,
        "opengl_samples_per_element": np.array([samples_per_element], dtype=np.int32),
    }


def _update_metadata(metadata: dict[str, Any], samples_per_element: int) -> dict[str, Any]:
    units = metadata.setdefault("units", {})
    units["opengl_centerline_vertices"] = (
        "m para x/z; y usa forma modal normalizada"
    )
    units["opengl_beam_vertices"] = "m para x/z; y usa forma modal normalizada"

    metadata["opengl"] = {
        "description": "Malha 2D no plano x-y pronta para VBO/IBO. Vertices tem formato [x, y, z], com z = 0. Indices sao base zero.",
        "interpolation": "Hermite cubica de viga Euler-Bernoulli usando modes_v e modes_theta nodais.",
        "primitive_centerline": "GL_LINES",
        "primitive_beam": "GL_TRIANGLES",
        "padding": "Vertices invalidos usam NaN; indices e material_id invalidos usam -1.",
        "beam_vertex_layout": "pares [inferior, superior] para cada ponto da linha neutra amostrada.",
        "deformation": "Forma modal normalizada. A escala visual/animacao pode ser aplicada no renderizador.",
        "samples_per_element": samples_per_element,
    }

    valid_slices = metadata.setdefault("valid_slices", {})
    valid_slices["opengl_centerline_vertices"] = (
        "opengl_centerline_vertices[ic, mode, 0:opengl_centerline_vertex_count[ic], :]"
    )
    valid_slices["opengl_centerline_indices"] = (
        "opengl_centerline_indices[ic, 0:opengl_centerline_index_count[ic]]"
    )
    valid_slices["opengl_beam_vertices"] = (
        "opengl_beam_vertices[ic, mode, 0:opengl_beam_vertex_count[ic], :]"
    )
    valid_slices["opengl_beam_indices"] = (
        "opengl_beam_indices[ic, 0:opengl_beam_index_count[ic]]"
    )
    valid_slices["opengl_render_segment_material_id"] = (
        "opengl_render_segment_material_id[ic, 0:opengl_render_segment_count[ic]]"
    )

    return metadata


def generate_opengl_npz(
    npz_path: Path,
    metadata_path: Path,
    output_npz_path: Path,
    output_metadata_path: Path,
    samples_per_element: int,
) -> tuple[Path, Path]:
    with np.load(npz_path) as loaded:
        numeric_results = {
            key: loaded[key]
            for key in loaded.files
            if key not in OPENGL_KEYS and not key.startswith("opengl_")
        }

    opengl_results = build_opengl_meshes(
        data=numeric_results,
        samples_per_element=samples_per_element,
    )
    numeric_results.update(opengl_results)

    output_npz_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output_npz_path, **numeric_results)

    metadata = _load_metadata(metadata_path)
    metadata = _update_metadata(metadata, samples_per_element)
    _save_metadata(output_metadata_path, metadata)

    return output_npz_path, output_metadata_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera buffers OpenGL derivados de Resultados_FEA.npz."
    )
    parser.add_argument(
        "--npz",
        type=Path,
        default=Path("output") / "Resultados_FEA.npz",
        help="Arquivo .npz de resultados FEA.",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=None,
        help="Arquivo JSON de metadados. Por padrao usa *_metadata.json.",
    )
    parser.add_argument(
        "--saida-npz",
        type=Path,
        default=None,
        help="Arquivo .npz de saida. Por padrao sobrescreve --npz.",
    )
    parser.add_argument(
        "--saida-metadata",
        type=Path,
        default=None,
        help="Arquivo JSON de saida. Por padrao sobrescreve --metadata.",
    )
    parser.add_argument(
        "--samples-per-element",
        type=int,
        default=8,
        help="Subdivisoes OpenGL geradas dentro de cada elemento finito.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    metadata_path = args.metadata or _metadata_path_from_npz(args.npz)
    output_npz_path = args.saida_npz or args.npz
    output_metadata_path = args.saida_metadata or metadata_path

    npz_path, json_path = generate_opengl_npz(
        npz_path=args.npz,
        metadata_path=metadata_path,
        output_npz_path=output_npz_path,
        output_metadata_path=output_metadata_path,
        samples_per_element=args.samples_per_element,
    )

    print("Malha OpenGL gerada com sucesso.")
    print(f"Arquivo numerico: {npz_path.resolve()}")
    print(f"Metadados:        {json_path.resolve()}")


if __name__ == "__main__":
    main()
