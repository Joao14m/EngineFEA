from config import AnalysisConfig
from fem_solver import run_analysis
from results_io import save_results


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
