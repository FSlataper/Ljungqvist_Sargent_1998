def equilibrium_tax_UIcap(
    tol: float = 1e-4,
    maxit: int = 40,
    T: int = 400,
    N: int = 20_000,
    burn: int = 100,
    tax_UI: bool = True,
    benefit_scale: float = 1.0,
    EMAX: int = 52,              # 2 yrs at 2 weeks/period
    seed_base: int = 11,
    return_stats: bool = True,   
    vfi_tol: float = 1e-3,
    vfi_maxit: int = 300,
    per_year: int = 26,
):
    """
    Find τ* such that (post-burn) tax revenue = UI outlays under the new policy

    """
    tau_L, tau_H = 0.0, 1.0
    last = None

    for it in range(maxit):
        tau = 0.5 * (tau_L + tau_H)

        # --- VFI at current τ
        U_E, U_N, Wv, sE, sN, wbar_E, wbar_N = solve_values_given_tau_UIcap(
            tau, benefit_scale=benefit_scale, EMAX=EMAX, tol=vfi_tol, maxit=vfi_maxit
        )

        # --- Simulate and compute fiscal gap on post-burn window
        stats = simulate_UIclasses_cap(
            tau, U_E, U_N, Wv, sE, sN, wbar_E, wbar_N,
            EMAX=EMAX, T=T, N=N, burn=burn, seed=seed_base+it,
            tax_UI=tax_UI, per_year=per_year, track=True, benefit_scale=benefit_scale
        )

        gap = stats['rev_postburn'] - stats['ui_postburn']  # >0 ⇒ τ too high
        last = (tau, (U_E, U_N, Wv, sE, sN, wbar_E, wbar_N), stats)

        # stop if balanced (or bracket is tiny)
        if abs(gap) < 1e-2 or (tau_H - tau_L) < tol:
            if return_stats:
                return last
            else:
                tau_star, obj, _stats = last
                return tau_star, obj

        # bisection step
        if gap > 0:
            tau_H = tau
        else:
            tau_L = tau

    # Fallback (maxit reached)
    if return_stats:
        return last
    else:
        tau_star, obj, _stats = last
        return tau_star, obj