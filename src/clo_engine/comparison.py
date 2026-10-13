"""Common descriptive analytics, without equating synthetic rating labels."""

import math
import pandas as pd


def comparison_table(results: dict[str, tuple[object, object]],
                     collateral_par: dict[str, float]) -> pd.DataFrame:
    """Compare the BBB-like class in each supplied base and stress pair.

    Subordination is initial collateral less debt through the selected class,
    divided by initial collateral. ABS reserve is excluded. WAL is weighted by
    principal actually received, so total-loss classes have undefined WAL.
    """
    rows = []
    for asset_type, (base, stress) in results.items():
        if base.structure != stress.structure:
            raise ValueError("Base and stress must use the same capital structure")
        matches = [i for i, t in enumerate(base.structure.tranches) if t.rating == "BBB"]
        if len(matches) != 1:
            raise ValueError("Each structure must contain one BBB-like class")
        index = matches[0]
        tranche = base.structure.tranches[index]
        par = collateral_par[asset_type]
        if not math.isfinite(par) or par <= 0:
            raise ValueError("Collateral par must be positive")
        base_row = base.tranche_analytics().iloc[index]
        stress_row = stress.tranche_analytics().iloc[index]
        rows.append(dict(asset_type=asset_type, **{"class": tranche.name},
                         rating_label=tranche.rating,
                         subordination=1 - sum(t.notional for t in base.structure.tranches[:index + 1]) / par,
                         base_wal_years=base_row.paid_principal_life,
                         stress_wal_years=stress_row.paid_principal_life,
                         base_loss_fraction=base_row.principal_loss_fraction,
                         stress_loss_fraction=stress_row.principal_loss_fraction))
    return pd.DataFrame(rows)
