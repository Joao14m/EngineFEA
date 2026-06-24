import unittest
from dataclasses import replace

import numpy as np

from modelo_core import assem, beam2d
from modelo_matematico.config import AnalysisConfig
from modelo_matematico.fem_solver import (
    assemble_global_matrices,
    assemble_global_matrices_straight_x,
    build_coordinates,
    build_dof,
    build_topology,
    run_analysis,
)


class CoreNumericsTest(unittest.TestCase):
    def test_assem_uses_zero_based_dofs(self):
        edof = np.array([0, 0, 1])
        K = np.zeros((3, 3), dtype=float)
        Ke = np.array([[2.0, -2.0], [-2.0, 2.0]])

        assembled = assem(edof, K, Ke)

        np.testing.assert_allclose(assembled[:2, :2], Ke)
        self.assertEqual(assembled[2, 2], 0.0)

    def test_beam2d_returns_symmetric_element_matrices(self):
        Ke, Me, Ce = beam2d(
            ex=[0.0, 1.0],
            ey=[0.0, 0.0],
            ep=[210e9, 5e-3, 1e-6, 39.25],
        )

        self.assertEqual(Ke.shape, (6, 6))
        self.assertEqual(Me.shape, (6, 6))
        self.assertEqual(Ce.shape, (6, 6))
        np.testing.assert_allclose(Ke, Ke.T)
        np.testing.assert_allclose(Me, Me.T)
        np.testing.assert_allclose(Ce, np.zeros((6, 6)))
        self.assertAlmostEqual(float(Ke[0, 0]), 210e9 * 5e-3)

    def test_build_topology_is_consistent_with_three_dofs_per_node(self):
        edof = build_topology(2)

        np.testing.assert_array_equal(
            edof,
            np.array(
                [
                    [0, 0, 1, 2, 3, 4, 5],
                    [1, 3, 4, 5, 6, 7, 8],
                ],
                dtype=np.int32,
            ),
        )

    def test_straight_x_fast_assembly_matches_generic_assembly(self):
        config = AnalysisConfig()
        x_nodes = np.linspace(0.0, config.L, 5)
        edof = build_topology(x_nodes.size - 1)
        coord = build_coordinates(x_nodes)
        dof = build_dof(x_nodes.size)
        A = config.b * config.h
        I = config.b * config.h**3 / 12.0
        segments = np.array(
            [[0.0, config.L, config.E_aco, config.rho_aco]],
            dtype=float,
        )

        K_generic, M_generic, ex_generic, ey_generic = assemble_global_matrices(
            edof=edof,
            coord=coord,
            dof=dof,
            segments=segments,
            A=A,
            I=I,
            L_total=config.L,
        )
        K_fast, M_fast, ex_fast, ey_fast = assemble_global_matrices_straight_x(
            edof=edof,
            coord=coord,
            dof=dof,
            x_nodes=x_nodes,
            segments=segments,
            A=A,
            I=I,
            L_total=config.L,
            use_sparse=False,
        )
        K_sparse, M_sparse, _, _ = assemble_global_matrices_straight_x(
            edof=edof,
            coord=coord,
            dof=dof,
            x_nodes=x_nodes,
            segments=segments,
            A=A,
            I=I,
            L_total=config.L,
            use_sparse=True,
        )

        np.testing.assert_allclose(ex_fast, ex_generic)
        np.testing.assert_allclose(ey_fast, ey_generic)
        np.testing.assert_allclose(K_fast, K_generic)
        np.testing.assert_allclose(M_fast, M_generic)
        np.testing.assert_allclose(K_sparse.toarray(), K_generic)
        np.testing.assert_allclose(M_sparse.toarray(), M_generic)


class AnalysisSmokeTest(unittest.TestCase):
    def test_reduced_analysis_runs_and_returns_numeric_results(self):
        config = replace(
            AnalysisConfig(),
            salvar_resultados=False,
            passo_composicao=1.0,
            NE_ini=4,
            passo_elementos=2,
            max_iter=4,
            erro_admissivel=100.0,
            print_resumo_config=False,
            print_iteracoes=False,
        )

        results = run_analysis(config)

        self.assertEqual(results["frequencies"].shape, (2, config.N))
        self.assertTrue(np.all(np.isfinite(results["frequencies"])))
        self.assertTrue(np.all(results["frequencies"] > 0.0))


if __name__ == "__main__":
    unittest.main()
