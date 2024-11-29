import pytest
from src.kandel import Kandel, KandelConfig


@pytest.mark.parametrize(
    "spot_price, vol, vol_mult, n_points, decimals_diff, expected_ticks_grid",
    [
        (
            3500,
            0.01,
            1.6,
            2,
            12,
            [-194875, -194795, -194715, -194635, -194555],
        ),
        (
            1,
            0.01,
            1.6,
            2,
            0,
            [-161, -81, -1, 79, 160],
        ),
    ],
)
def test_ticks_grid(
    spot_price, vol, vol_mult, n_points, decimals_diff, expected_ticks_grid
):
    kandel = Kandel(
        config=KandelConfig(
            initial_capital=100000,
            decimals_diff=decimals_diff,
            performance_fees=0,
            vol_mult=vol_mult,
            n_points=n_points,
            step_size=1,
            window=24,
            exit_vol_threshold=0.03,
            asymmetric_exit_threshold=0.05,
        ),
        spot_price=spot_price,
        vol=vol,
        exit_vol=0.01,
    )

    assert kandel.ticks_grid == expected_ticks_grid
