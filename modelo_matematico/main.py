from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modelo_matematico.config import AnalysisConfig
from modelo_matematico.fem_solver import run_analysis
from modelo_matematico.results_io import save_results


def main() -> None:
    config = AnalysisConfig()

    results = run_analysis(config)

    if config.salvar_resultados:
        save_results(
            results=results,
            output_dir=config.output_dir,
            npz_filename=config.nome_arquivo_npz,
            metadata_filename=config.nome_arquivo_json,
        )


if __name__ == "__main__":
    main()
