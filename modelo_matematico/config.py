from dataclasses import dataclass


@dataclass(frozen=True)
class AnalysisConfig:
    """
    Parametros principais da analise modal.

    A saida foi pensada para uso posterior em Python + C++ + OpenGL:
    matrizes NumPy em .npz e metadados simples em .json.
    """

    # ------------------------------------------------------------------
    # Arquivos de saida
    # ------------------------------------------------------------------

    salvar_resultados: bool = True
    output_dir: str = "output"
    nome_arquivo_npz: str = "Resultados_FEA.npz"
    nome_arquivo_json: str = "Resultados_FEA_metadata.json"

    # ------------------------------------------------------------------
    # Geometria
    # ------------------------------------------------------------------
    L: float = 3.0  # comprimento da viga [m]
    h: float = 5e-2  # altura da viga [m]
    b: float = 10e-2  # largura/espessura da viga [m]

    # ------------------------------------------------------------------
    # Materiais
    # ------------------------------------------------------------------
    E_aco: float = 2.1e11  # modulo de elasticidade do aco [Pa]
    rho_aco: float = 7850.0  # densidade do aco [kg/m3]

    E_ti: float = 1.1e11  # modulo de elasticidade do titanio [Pa]
    rho_ti: float = 4500.0  # densidade do titanio [kg/m3]

    # ------------------------------------------------------------------
    # Composicao
    # ------------------------------------------------------------------
    passo_composicao: float = 0.005

    # ordem_material = 1 -> Aco no engaste / Titanio na ponta
    # ordem_material = 2 -> Titanio no engaste / Aco na ponta
    ordem_material: int = 1

    # ------------------------------------------------------------------
    # Condicoes de contorno
    # ------------------------------------------------------------------
    # cc = 0 -> livre-livre
    # cc = 1 -> engastada-livre
    # cc = 2 -> engastada-engastada
    # cc = 3 -> bi-apoiada
    cc: int = 0

    # ------------------------------------------------------------------
    # Analise modal e convergencia
    # ------------------------------------------------------------------
    N: int = 6  # numero de modos elasticos salvos
    erro_admissivel: float = 1e-3  # erro percentual admissivel [%]

    NE_ini: int = 20
    passo_elementos: int = 1
    max_iter: int = 2000

    # numero de ultimos modos usados no criterio de convergencia
    # use None para usar todos os modos
    n_ultimos_controle: int | None = None

    # ------------------------------------------------------------------
    # Otimizacoes numericas
    # ------------------------------------------------------------------
    # Mantem as rotinas genericas validadas como fallback. Estes atalhos
    # so devem ser usados quando as hipoteses do caso especial forem atendidas.
    usar_montagem_retilinea_otimizada: bool = True
    usar_matrizes_esparsas: bool = True
    usar_solver_modal_parcial: bool = True

    # ------------------------------------------------------------------
    # Impressao no terminal
    # ------------------------------------------------------------------
    print_resumo_config: bool = True
    print_iteracoes: bool = False
