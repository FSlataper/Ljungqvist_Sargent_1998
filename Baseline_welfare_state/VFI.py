
def solve_values_given_tau_UIclasses(tau, tol=1e-3, maxit=300):
    Hn, Wn = H, len(w_grid)
    U_E = np.zeros((Hn, Nclass))
    U_N = np.zeros(Hn)
    Wv  = np.zeros((Wn, Hn))

    flowU_E = (1.0 - tau) * benefit_by_class[None, :]
    flowU_N = 0.0
    flowW   = (1.0 - tau) * (w_grid[:,None] * h_grid[None,:])

    # class at separation for each (w,h)
    e_table = (w_grid[:,None] * h_grid[None,:])
    cl_table = np.clip(np.searchsorted(W_upper, np.clip(e_table,0.0,2.0), side='left'), 0, Nclass-1)

    for _ in range(maxit):
        U_E_old = U_E.copy(); U_N_old = U_N.copy(); W_old = Wv.copy()

        # Employed
        W_keep   = Wv[:, up_idx]
        U_sep_tbl= U_E[downF_idx[None,:], cl_table]
        Wv = flowW + beta_hat * ((1.0 - lam) * W_keep + lam * U_sep_tbl)

        # Unemployed, ineligible
        hpr_idx = downU_idx
        UN_hpr  = U_N[hpr_idx]
        W_hpr   = Wv[:, hpr_idx]
        max_W_UN= np.maximum(W_hpr, UN_hpr[None,:])
        Ew_max_N= (w_pdf[:,None] * max_W_UN).sum(axis=0)
        Pi = pi(s_grid)[:,None]
        C  = c(s_grid)[:,None]
        U_N_choices = flowU_N - C + beta_hat * ( Pi * Ew_max_N[None,:] + (1.0 - Pi) * UN_hpr[None,:] )
        sN_idx = np.argmax(U_N_choices, axis=0)
        U_N = U_N_choices[sN_idx, np.arange(Hn)]

        # Unemployed, eligible
        UE_hpr  = U_E[hpr_idx, :]
        UN_hpr2 = U_N[hpr_idx]
        W_hpr   = Wv[:, hpr_idx]
        e_suit  = suitable_by_class
        w_thresh = np.clip((e_suit[None, :] / h_grid[:,None]), 0.0, 1.0)

        U_E_new = np.zeros_like(U_E)
        sE_idx  = np.zeros(Hn, dtype=int)

        for i_cls in range(Nclass):
            wcut = w_thresh[:, i_cls]
            suitable_mask = (w_grid[:,None] >= wcut[None,:])
            R = np.where(suitable_mask, UN_hpr2[None,:], UE_hpr[:, i_cls][None,:])
            best = np.maximum(W_hpr, R)
            Ew_best = (w_pdf[:,None] * best).sum(axis=0)
            UE_choices = flowU_E[:, i_cls][None,:] - C + beta_hat * ( Pi * Ew_best[None,:] + (1.0 - Pi) * UE_hpr[:, i_cls][None,:] )
            idx = np.argmax(UE_choices, axis=0)
            U_E_new[:, i_cls] = UE_choices[idx, np.arange(Hn)]
            if i_cls == 0: sE_idx = idx

        U_E = U_E_new

        if max(np.max(np.abs(Wv - W_old)),
               np.max(np.abs(U_N - U_N_old)),
               np.max(np.abs(U_E - U_E_old))) < tol:
            break

    # Reservation thresholds
    wbar      = np.full((Hn, Nclass), w_grid[-1])
    wbar_inel = np.full(Hn, w_grid[-1])

    # ineligible: compare W vs U_N
    for j in range(Hn):
        mask = Wv[:, j] >= U_N[j]
        wbar_inel[j] = w_grid[mask.argmax()] if mask.any() else w_grid[-1]

    # eligible: piecewise rule
    # reuse w_thresh computed above (needs in-scope here)
    w_thresh = np.clip((suitable_by_class[None, :] / h_grid[:,None]), 0.0, 1.0)
    for j in range(Hn):
        for i_cls in range(Nclass):
            wcut = w_thresh[j, i_cls]
            mask_low  = (w_grid <  wcut) & (Wv[:, j] >= U_E[j, i_cls])
            mask_high = (w_grid >= wcut) & (Wv[:, j] >= U_N[j])
            mask = mask_low | mask_high
            wbar[j, i_cls] = w_grid[mask.argmax()] if mask.any() else w_grid[-1]

    s_star_E = s_grid[sE_idx]
    s_star_N = s_grid[sN_idx]
    return (U_E, U_N, Wv, s_star_E, s_star_N, wbar, wbar_inel)