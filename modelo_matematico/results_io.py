from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np


def _json_default(obj: Any) -> Any:
    """Converte tipos NumPy para tipos serializaveis em JSON."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    raise TypeError(f"Objeto nao serializavel em JSON: {type(obj)}")


def save_results(
    results: dict[str, Any],
    output_dir: str | Path,
    npz_filename: str,
    metadata_filename: str,
) -> tuple[Path, Path]:
    """
    Salva os resultados em dois arquivos:

    1) .npz  -> apenas vetores, matrizes e tensores numericos.
    2) .json -> metadados, nomes de configuracao, nomes de colunas e unidades.

    Essa separacao facilita o uso posterior em Python e em C++/OpenGL.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    npz_path = output_path / npz_filename
    json_path = output_path / metadata_filename

    metadata = results.get("metadata", {})

    numeric_results: dict[str, np.ndarray] = {}
    for key, value in results.items():
        if key == "metadata":
            continue

        arr = np.asarray(value)

        if arr.dtype.kind in {"U", "S", "O"}:
            raise TypeError(
                f"O campo '{key}' nao e puramente numerico. "
                "Coloque strings/listas heterogeneas dentro de metadata."
            )

        numeric_results[key] = arr

    np.savez_compressed(npz_path, **numeric_results)

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False, default=_json_default)

    print("\nResultados salvos com sucesso.")
    print(f"Arquivo numerico: {npz_path.resolve()}")
    print(f"Metadados:        {json_path.resolve()}")

    return npz_path, json_path
