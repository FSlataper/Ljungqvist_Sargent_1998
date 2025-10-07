def equilibrium_tax_UIclasses(tol=1e-4, maxit=30, T=200, N=10_000, burn=100, tax_UI=True):
    tau_L, tau_H = 0.0, 1.0
    for it in range(maxit):
        tau = 0.5*(tau_L + tau_H)
        U_E, U_N, Wv, sE, sN, wbar, wbar_inel = solve_values_given_tau_UIclasses(tau, tol=1e-3, maxit=300)
        stats = simulate_UIclasses(tau, U_E, U_N, Wv, sE, sN, wbar, wbar_inel,
                                   T=T, N=N, burn=burn, seed=it+7, tax_UI=tax_UI,
                                   track=True, per_year=26)
        gap = stats['rev_postburn'] - stats['ui_postburn']
        # print(f"[{it:02d}] tau={tau:.5f}  rev={stats['rev_postburn']:.2f}  ui={stats['ui_postburn']:.2f}  gap={gap:.2f}")
        if abs(gap) < 1e-2 or (tau_H - tau_L) < tol:
            return tau, (U_E, U_N, Wv, sE, sN, wbar, wbar_inel)
        if gap > 0: tau_H = tau
        else:       tau_L = tau
    return 0.5*(tau_L + tau_H), (U_E, U_N, Wv, sE, sN, wbar, wbar_inel)