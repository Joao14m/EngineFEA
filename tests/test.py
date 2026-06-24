import unittest
from dataclasses import replace

import numpy as np

from modelo_core import assem, beam2d
from modelo_matematico.config import AnalysisConfig
from modelo_matematico.fem_solver import build_topology, run_analysis


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
