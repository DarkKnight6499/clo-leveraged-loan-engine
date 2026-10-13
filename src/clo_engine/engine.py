"""Loan level collateral simulation linked to quarterly liability payments."""

from dataclasses import dataclass
import math
import numpy as np
import pandas as pd
from .loans import DEFAULT_PROBABILITIES, INDUSTRIES, Loan, sofr_curve
from .metrics import ccc_adjustment
from .numerics import normal_quantile, period_probability
from .structure import CLOStructure
from .valuation import cash_multiple, discounted_value, equity_irr
from .waterfall import WaterfallState, allocate_period


@dataclass(frozen=True)
class DealResult:
    """Cash ledger, cumulative tranche payments and terminal unpaid amounts."""
    ledger: pd.DataFrame
    interest: np.ndarray
    principal: np.ndarray
    equity: np.ndarray
    ending_balances: np.ndarray
    unpaid_interest: np.ndarray
    curve: np.ndarray
    structure: CLOStructure

    def tranche_analytics(self) -> pd.DataFrame:
        """Value cash flows and report principal loss and paid principal life."""
        times = self.ledger["time"].to_numpy()
        rows = []
        for index, tranche in enumerate(self.structure.tranches):
            cash = self.interest[:, index] + self.principal[:, index]
            paid = float(self.principal[:, index].sum())
            rows.append({
                "class": tranche.name, "rating_label": tranche.rating,
                "initial_notional": tranche.notional, "principal_paid": paid,
                "principal_loss": self.ending_balances[index],
                "principal_loss_fraction": self.ending_balances[index] / tranche.notional,
                "unpaid_interest": self.unpaid_interest[index],
                "paid_principal_life": float(times @ self.principal[:, index] / paid) if paid > 0 else math.nan,
                "dcf_value": discounted_value(cash, self.curve, tranche.spread),
                "dcf_price_percent": 100 * discounted_value(cash, self.curve, tranche.spread) / tranche.notional,
            })
        return pd.DataFrame(rows)

    @property
    def equity_irr(self) -> float:
        return equity_irr(self.structure.equity, self.equity)

    @property
    def equity_multiple(self) -> float:
        return cash_multiple(self.structure.equity, self.equity)


def run_deal(loans: list[Loan], structure: CLOStructure,
             curve: np.ndarray | None = None, annual_default_rate: float | None = 0.0,
             recovery: float | None = None, prepayment: float = 0.10,
             rng: np.random.Generator | None = None, correlation: float = 0.20,
             recovery_concentration: float = 20.0,
             default_multiplier: float = 1.0) -> DealResult:
    """Run fractional constant defaults or stochastic rating based copula defaults."""
    if not loans:
        raise ValueError("Portfolio must not be empty")
    if annual_default_rate is None and rng is None:
        raise ValueError("Stochastic defaults require an explicit seeded generator")
    if not 0 <= correlation < 1 or recovery_concentration <= 0 or not math.isfinite(recovery_concentration):
        raise ValueError("Invalid correlation or recovery concentration")
    if not math.isfinite(default_multiplier) or default_multiplier < 0:
        raise ValueError("Invalid default multiplier")
    if recovery is not None and not 0 <= recovery <= 1:
        raise ValueError("Recovery must be between zero and one")
    q_default = None if annual_default_rate is None else period_probability(annual_default_rate)
    q_prepaid = period_probability(prepayment)
    curve = sofr_curve(structure.periods) if curve is None else np.asarray(curve, dtype=float).copy()
    if curve.shape != (structure.periods,) or not np.isfinite(curve).all():
        raise ValueError("Curve must have one finite value per payment date")
    state = WaterfallState.initial(structure)
    borrower_numbers: dict[str, int] = {}
    borrower_ratings: dict[str, str] = {}
    borrower_indices = []
    for loan in loans:
        if borrower_ratings.get(loan.borrower, loan.rating) != loan.rating:
            raise ValueError("Facilities of one borrower must share a default probability rating")
        borrower_ratings[loan.borrower] = loan.rating
        if loan.borrower not in borrower_numbers:
            borrower_numbers[loan.borrower] = len(borrower_numbers)
        borrower_indices.append(borrower_numbers[loan.borrower])
    obligors = np.array(borrower_indices)
    obligor_count = len(borrower_numbers)
    balances = np.array([x.par for x in loans], dtype=float)
    amort_bases = balances.copy()
    spreads = np.array([x.spread for x in loans], dtype=float)
    floors = np.array([x.floor for x in loans], dtype=float)
    maturities = np.array([x.maturity for x in loans], dtype=float)
    amort_rates = np.array([x.amortization for x in loans], dtype=float)
    prices = np.array([x.price for x in loans], dtype=float)
    ccc = np.array([x.rating.startswith("Caa") for x in loans])
    means = np.array([x.recovery for x in loans], dtype=float)
    reinvestment_recovery = float(balances @ means / balances.sum())
    probabilities = {rating: min(1.0, probability * default_multiplier)
                     for rating, probability in DEFAULT_PROBABILITIES.items()}
    thresholds = {rating: normal_quantile(period_probability(p)) for rating, p in probabilities.items()}
    limits = np.array([thresholds[x.rating] for x in loans])
    dates = structure.payment_dates()
    interest_payments, principal_payments, equity_payments, rows = [], [], [], []
    for period, rate in enumerate(curve):
        time = (period + 1) * 0.25
        opening_par = float(balances.sum())
        if q_default is not None:
            default_fraction = np.full(len(balances), q_default)
        else:
            common = float(rng.normal())
            latent = math.sqrt(correlation) * common + math.sqrt(1 - correlation) * rng.normal(size=obligor_count)
            default_fraction = (latent[obligors] < limits).astype(float)
        defaulted = balances * default_fraction
        balances -= defaulted
        amort_bases *= 1 - default_fraction
        recovery_rates = means.copy()
        if recovery is not None:
            recovery_rates.fill(recovery)
        elif rng is not None:
            interior = (means > 0) & (means < 1)
            recovery_rates[interior] = rng.beta(means[interior] * recovery_concentration,
                                               (1 - means[interior]) * recovery_concentration)
        recovered = float(defaulted @ recovery_rates)
        credit_loss = float(defaulted.sum()) - recovered
        interest_proceeds = float(balances @ (np.maximum(rate, floors) + spreads) * 0.25)
        amortization = np.minimum(balances, amort_bases * amort_rates * 0.25)
        balances -= amortization
        prepaid = balances * q_prepaid
        balances -= prepaid
        mature = time + 1e-12 >= maturities
        matured = float(balances[mature].sum())
        balances[mature] = 0
        final = period == structure.periods - 1
        liquidation = float(balances.sum()) if final else 0.0
        if final:
            balances.fill(0)
        principal_proceeds = recovered + float(amortization.sum() + prepaid.sum()) + matured + liquidation
        ccc_share, haircut = ccc_adjustment(balances, prices, ccc, structure.ccc_limit)
        closing_before_purchase = float(balances.sum())
        allocation = allocate_period(
            structure, state, interest_proceeds, principal_proceeds,
            max(0, closing_before_purchase - haircut), opening_par, float(rate),
            reinvest=time <= structure.reinvestment_years + 1e-12 and not final, final=final,
        )
        purchased_par = allocation.reinvestment_cash / structure.reinvestment_price
        if purchased_par > 0:
            # New equal synthetic obligors diversify each purchase across industry labels.
            count = len(INDUSTRIES)
            amounts = np.full(count, purchased_par / count)
            balances = np.concatenate((balances, amounts))
            amort_bases = np.concatenate((amort_bases, amounts))
            spreads = np.concatenate((spreads, np.full(count, structure.reinvestment_spread)))
            floors = np.concatenate((floors, np.full(count, 0.01)))
            maturities = np.concatenate((maturities, np.full(count, time + structure.reinvestment_maturity)))
            amort_rates = np.concatenate((amort_rates, np.full(count, 0.01)))
            prices = np.concatenate((prices, np.full(count, structure.reinvestment_price)))
            ccc = np.concatenate((ccc, np.zeros(count, bool)))
            means = np.concatenate((means, np.full(count, reinvestment_recovery)))
            limits = np.concatenate((limits, np.full(count, thresholds["B2"])))
            obligors = np.concatenate((obligors, np.arange(obligor_count, obligor_count + count)))
            obligor_count += count
        interest_payments.append(allocation.interest_paid)
        principal_payments.append(allocation.principal_paid)
        equity_payments.append(allocation.equity)
        row = dict(
            period=period + 1, date=str(dates[period]), time=time, sofr=float(rate),
            opening_par=opening_par, defaulted_par=float(defaulted.sum()), recovery=recovered,
            credit_loss=credit_loss, amortization=float(amortization.sum()),
            prepayment=float(prepaid.sum()), maturities=matured, liquidation=liquidation,
            collateral_interest=interest_proceeds, collateral_principal=principal_proceeds,
            closing_par=float(balances.sum()), ccc_share=ccc_share, ccc_haircut=haircut,
            expenses_paid=allocation.expenses_paid, subordinated_fee_paid=allocation.subordinated_paid,
            reinvestment_cash=allocation.reinvestment_cash, purchased_par=purchased_par,
            coverage_diversion=allocation.coverage_diversion, interest_diversion=allocation.interest_diversion,
            interest_diversion_breach=allocation.diversion_breach, event_default=allocation.event_default,
            equity_interest=allocation.equity_interest, equity_principal=allocation.equity_principal,
            equity=allocation.equity, reconciliation_error=allocation.reconciliation_error,
            collateral_reconciliation=opening_par - float(defaulted.sum()) - float(amortization.sum() + prepaid.sum())
                - matured - liquidation + purchased_par - float(balances.sum()),
        )
        for index, tranche in enumerate(structure.tranches):
            row.update({f"{tranche.name}_interest": allocation.interest_paid[index],
                        f"{tranche.name}_principal": allocation.principal_paid[index],
                        f"{tranche.name}_balance": state.balances[index],
                        f"{tranche.name}_oc": allocation.oc_ratios[index],
                        f"{tranche.name}_ic": allocation.ic_ratios[index],
                        f"{tranche.name}_oc_breach": allocation.oc_breaches[index],
                        f"{tranche.name}_ic_breach": allocation.ic_breaches[index]})
        rows.append(row)
    return DealResult(pd.DataFrame(rows), np.array(interest_payments), np.array(principal_payments),
                      np.array(equity_payments), state.balances.copy(), state.interest_arrears.copy(),
                      curve, structure)
