def solve_values_given_tau_UIcap(tau, benefit_scale=1.0, EMAX=13, tol=1e-3, maxit=300):
    Hn, Wn = len(h_grid), len(w_grid)
    benefit_arr = get_benefit_array(benefit_scale)   # UI_i and suitable threshold tied
    flowW = (1.0 - tau) * (w_grid[:,None] * h_grid[None,:])
    Pi = (s_grid**0.3)[:,None]                       # meeting prob
    C  = (0.5*s_grid)[:,None]                        # search cost

    # Precompute separation class by (w,h)
    e_table   = (w_grid[:,None] * h_grid[None,:])              # (W,H)
    cl_table  = np.clip(np.searchsorted(W_upper, np.clip(e_table,0.0,2.0), side='left'),
                        0, Nclass-1)                           # (W,H)

    # PDFs for wage quad
    def _phi(x): return np.exp(-0.5*x*x)/np.sqrt(2*np.pi)
    mu, sigma = 0.5, np.sqrt(0.1)
    a, b = (0.0-mu)/sigma, (1.0-mu)/sigma
    Z = 0.5*(1+erf(b/np.sqrt(2))) - 0.5*(1+erf(a/np.sqrt(2)))
    z = (w_grid - mu)/sigma
    w_pdf = (_phi(z) / (sigma * Z)); w_pdf /= w_pdf.sum()
    w_pdf = w_pdf[:,None]                                      # (W,1)

    # Record-keeping
    U_N = np.zeros(Hn)
    U_E = np.zeros((Hn, Nclass, EMAX))
    Wv  = np.zeros((Wn, Hn))
    sN_idx = np.zeros(Hn, dtype=int)
    sE_idx = np.zeros((Hn, EMAX), dtype=int)

    for _ in range(maxit):
        U_N_old = U_N.copy()
        U_E_old = U_E.copy()
        W_old   = Wv.copy()

        # --- Employed ---
        U_sep_full = np.empty((Wn, Hn))
        for j in range(Hn):
            U_sep_full[:, j] = U_E[downF_idx[j], cl_table[:, j], EMAX-1]  # full entitlement on separation
        W_keep = Wv[:, up_idx]
        Wv = flowW + beta_hat * ((1.0 - lam)*W_keep + lam*U_sep_full)

        # --- Ineligible U_0(h) ---
        hpr = downU_idx
        UN_hpr = U_N[hpr][None,:]                        # (1,H)
        W_hpr  = Wv[:, hpr]                              # (W,H)
        best_inel = np.maximum(W_hpr, UN_hpr)            # (W,H)
        Ew_inel = (w_pdf * best_inel).sum(axis=0, keepdims=True)  # (1,H)
        UN_choices = -C + beta_hat * ( Pi*Ew_inel + (1.0 - Pi)*UN_hpr )    # (S,H)
        sN_idx = np.argmax(UN_choices, axis=0)
        U_N = UN_choices[sN_idx, np.arange(Hn)]

        # --- Eligible U_e(h,i) for e = 1..EMAX ---
        UE_new = np.empty_like(U_E)
        for e_idx in range(EMAX):
            # next entitlement if remain U is e-1 (ineligible if e_idx==0)
            if e_idx == 0:
                UE_next = U_N[hpr]                       # (H,)
            else:
                UE_next = U_E[hpr, :, e_idx-1]          # (H,Nclass)

            # Precompute pieces that don't depend on i
            W_hpr = Wv[:, hpr]                           # (W,H)
            UN_hpr = U_N[hpr]                            # (H,)

            # For each class i, compute expectation with suitable rule
            for i_cls in range(Nclass):
                e_suit = benefit_arr[i_cls]              # threshold in earnings
                # suitable if w*h' >= e_suit
                suitable = (w_grid[:,None] * h_grid[hpr][None,:]) >= e_suit
                if e_idx == 0:
                    UE_keep = UE_next                    # (H,)
                else:
                    UE_keep = UE_next[:, i_cls]          # (H,)

                # Reject continuation: to U_N if suitable, else stay on UE_keep
                R = np.where(suitable, UN_hpr[None,:], UE_keep[None,:])     # (W,H)
                best = np.maximum(W_hpr, R)                                   
                Ew = (w_pdf * best).sum(axis=0)          # (H,)

                flowU = (1.0 - tau) * benefit_arr[i_cls]
                UE_choices = (flowU - 0.5*s_grid)[:,None] + beta_hat * (
                    (s_grid**0.3)[:,None]*Ew[None,:] + (1.0 - (s_grid**0.3))[:,None]*UE_keep[None,:]
                )                                         # (S,H)
                idx = np.argmax(UE_choices, axis=0)
                UE_new[:, i_cls, e_idx] = UE_choices[idx, np.arange(Hn)]
                if i_cls == 0: sE_idx[:, e_idx] = idx    # one set of s*(h,e)

        U_E = UE_new

        if max(np.max(np.abs(Wv - W_old)),
               np.max(np.abs(U_N - U_N_old)),
               np.max(np.abs(U_E - U_E_old))) < tol:
            break

    # --- Reservation thresholds ---
    # Ineligible
    wbar_N = np.full(Hn, w_grid[-1])
    for j in range(Hn):
        mask = Wv[:, j] >= U_N[j]
        wbar_N[j] = w_grid[mask.argmax()] if mask.any() else w_grid[-1]

    # Eligible (depends on e via the reject continuation)
    wbar_E = np.full((Hn, Nclass, EMAX), w_grid[-1])
    for e_idx in range(EMAX):
        if e_idx == 0:
            UE_keep_all = U_N
        for j in range(Hn):
            hpr = downU_idx[j]
            for i_cls in range(Nclass):
                e_suit = benefit_arr[i_cls]
                wcut = np.clip(e_suit / h_grid[hpr], 0.0, 1.0)
                # below wcut, compare W vs UE_keep; above, compare W vs U_N
                if e_idx == 0:
                    UE_keep = UE_keep_all[hpr]
                else:
                    UE_keep = U_E[hpr, i_cls, e_idx-1]
                mask_low  = (w_grid <  wcut) & (Wv[:, j] >= UE_keep)
                mask_high = (w_grid >= wcut) & (Wv[:, j] >= U_N[j])
                mask = mask_low | mask_high
                wbar_E[j, i_cls, e_idx] = w_grid[mask.argmax()] if mask.any() else w_grid[-1]

    sE = s_grid[sE_idx]            # (H, EMAX)
    sN = s_grid[sN_idx]            # (H,)
    return U_E, U_N, Wv, sE, sN, wbar_E, wbar_N
