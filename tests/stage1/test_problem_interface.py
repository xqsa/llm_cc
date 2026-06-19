import numpy as np

from loco.benchmarks.problem_interface import LSGOProblem, assert_problem_contract


class TinyProblem(LSGOProblem):
    def evaluate(self, x: np.ndarray) -> float:
        return float(np.sum(np.asarray(x, dtype=float) ** 2))

    def bounds(self) -> tuple[np.ndarray, np.ndarray]:
        return np.full(3, -5.0), np.full(3, 5.0)

    def dimension(self) -> int:
        return 3

    def optimum_value(self) -> float | None:
        return 0.0

    def grouping(self) -> list[list[int]] | None:
        return [[0, 1], [1, 2]]

    def shared_variables(self) -> set[int]:
        return {1}

    def overlap_degree(self) -> dict[int, int]:
        return {0: 1, 1: 2, 2: 1}

    def metadata(self) -> dict:
        return {"function_id": "hidden-from-operator", "source": "test"}


def test_lsgoproblem_contract_returns_scalar_and_hides_metadata_from_operator() -> None:
    problem = TinyProblem()

    assert problem.evaluate(np.zeros(3)) == 0.0
    assert problem.shared_variables() == {1}
    assert_problem_contract(problem)

    operator_view = problem.operator_view()
    assert "metadata" not in operator_view
    assert "function_id" not in operator_view
    assert operator_view["dimension"] == 3
    assert operator_view["shared_variables"] == {1}
