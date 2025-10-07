def simulate_UIclasses_cap(tau, U_E, U_N, Wv, sE, sN, wbar_E, wbar_N,
                           EMAX=13, T=200, N=10_000, burn=100, seed=1,
                           tax_UI=True, per_year=26, track=True, benefit_scale=1.0):
    """
    Simulation with a per-spell UI entitlement counter ent_rem ∈ {0,..,EMAX}.
      - ent_rem resets to EMAX at separation (new UI spell).
      - if ent_rem>0, pay UI each period and decrement by 1 if still U at end of period.
      - rejecting an offer with earnings >= 0.7*previous_wage terminates benefits immediately (ent_rem=0).
    """
    rng = np.random.default_rng(seed)
    benefit_arr = get_benefit_array(benefit_scale)

    Hn = len(h_grid)
    h_idx  = rng.integers(0, Hn, size=N)
    state  = np.zeros(N, dtype=int)      # 0=U, 1=E
    last_i = np.zeros(N, dtype=int)      # last earnings class (for eligible UI level)
    wage   = np.zeros(N)
    ent_rem= np.zeros(N, dtype=int)      # UI entitlement remaining (0=ineligible)

    # spell tracking (optional)
    un_dur = np.zeros(N, dtype=int)
    spells, spell_t = [], []

    taxes = np.zeros(T); ui_sp = np.zeros(T)
    unrate = np.zeros(T); avg_h = np.zeros(T)

    def draw_offers(K):
        # truncated normal in [0,1] with mean=.5, var=.1 (same as VFI)
        mu, sigma = 0.5, np.sqrt(0.1)
        x = rng.normal(mu, sigma, size=K)
        bad = (x<0) | (x>1)
        while bad.any():
            x[bad] = rng.normal(mu, sigma, size=bad.sum())
            bad = (x<0) | (x>1)
        return x

    for t in range(T):
        # increment duration at start for those unemployed at t
        un_mask = (state==0)
        if un_mask.any():
            un_dur[un_mask] += 1

        # deaths
        die = rng.random(N) < alpha
        if die.any():
            h_idx[die] = rng.integers(0, Hn, size=die.sum())
            state[die] = 0; wage[die] = 0.0
            last_i[die]= 0; ent_rem[die]=0; un_dur[die]=0

        # employed
        emp = (state==1)
        if emp.any():
            idx = np.where(emp)[0]
            earn = wage[idx] * h_grid[h_idx[idx]]
            taxes[t] += tau * np.sum(earn)

            sep = rng.random(idx.size) < lam
            keep = ~sep
            # keep job -> h up
            h_idx[idx[keep]] = up_idx[h_idx[idx[keep]]]
            # separate -> U with full entitlement; class from last earnings
            if sep.any():
                sel = idx[sep]
                e_sep = np.clip(earn[sep], 0.0, 2.0)
                last_i[sel]  = np.searchsorted(W_upper, e_sep, side='left')
                ent_rem[sel] = EMAX
                state[sel]   = 0
                wage[sel]    = 0.0
                h_idx[sel]   = downF_idx[h_idx[sel]]
                un_dur[sel]  = 0

        # unemployed
        un = (state==0)
        if un.any():
            idx = np.where(un)[0]
            # UI flow if ent_rem>0
            elig = ent_rem[idx] > 0
            if elig.any():
                ui_vals = benefit_arr[last_i[idx][elig]]
                if tax_UI:
                    taxes[t] += tau * np.sum(ui_vals)
                    ui_sp[t] += (1.0 - tau) * np.sum(ui_vals)
                else:
                    ui_sp[t] += np.sum(ui_vals)

            # loss of human capital while U
            h_idx[idx] = downU_idx[h_idx[idx]]

            # meetings
            h_now = h_grid[h_idx[idx]]
            # choose s based on entitlement: if ent>0 use sE(h,e), else sN(h)
            # --- choose s based on entitlement: if ent>0 use sE(h,e), else sN(h)
            elig = (ent_rem[idx] > 0)          # shape (M,)
            s_now = np.empty(idx.size)         # M = idx.size
            
            if elig.any():
                e_idx = np.clip(ent_rem[idx][elig] - 1, 0, EMAX - 1)
                s_now[elig] = sE[h_idx[idx][elig], e_idx]
            
            if (~elig).any():
                s_now[~elig] = sN[h_idx[idx][~elig]]
            
            p_now = s_now**0.3
            meet  = rng.random(idx.size) < p_now

            if meet.any():
                i_sel = idx[meet]
                w_off = draw_offers(i_sel.size)
                e_off = w_off * h_grid[h_idx[i_sel]]
                # acceptance thresholds:
                acc = np.zeros(i_sel.size, dtype=bool)
                elig_sel = ent_rem[i_sel] > 0

                # eligible: use wbar_E(h,i,e)
                if elig_sel.any():
                    iL = last_i[i_sel][elig_sel]
                    e_idx = np.clip(ent_rem[i_sel][elig_sel]-1, 0, EMAX-1)
                    wb = wbar_E[h_idx[i_sel][elig_sel], iL, e_idx]
                    must_acc = e_off[elig_sel] >= benefit_arr[iL]  # suitable-job rule
                    acc[elig_sel] = (w_off[elig_sel] >= wb) | must_acc
                    # lose entitlement immediately if reject a suitable offer
                    lose = (~acc[elig_sel]) & must_acc
                    if lose.any():
                        who = i_sel[elig_sel][lose]
                        ent_rem[who] = 0

                # ineligible: use wbar_N(h)
                inel = ~elig_sel
                if inel.any():
                    wb = wbar_N[h_idx[i_sel][inel]]
                    acc[inel] = (w_off[inel] >= wb)

                # accept → E next period
                if acc.any():
                    who = i_sel[acc]
                    state[who] = 1
                    wage[who]  = w_off[acc]
                    # record completed U spells
                    spells.extend(un_dur[who].tolist())
                    spell_t.extend([t]*len(who))
                    un_dur[who] = 0
                    ent_rem[who] = 0  # irrelevant while employed

            # entitlement countdown for those still U and elig
            stillU = (state[idx]==0)
            if stillU.any():
                elig2 = ent_rem[idx[stillU]] > 0
                ent_rem[idx[stillU][elig2]] -= 1
                ent_rem[idx[stillU]] = np.maximum(ent_rem[idx[stillU]], 0)

        unrate[t] = np.mean(state==0)
        avg_h[t]  = np.mean(h_grid[h_idx])

    # Stats (same shape as previous helper)
    if not track:
        return taxes, ui_sp

    spells = np.asarray(spells, float)
    spell_t= np.asarray(spell_t, int)
    post = spell_t >= burn
    spells_post = spells[post]
    avg_spell_post = float(np.nan) if spells_post.size==0 else float(spells_post.mean())

    years = (T - burn) // per_year
    unrate_yearly = np.array([unrate[burn + y*per_year : burn + (y+1)*per_year].mean() for y in range(years)])
    avg_h_yearly  = np.array([ avg_h[burn + y*per_year : burn + (y+1)*per_year].mean() for y in range(years)])
    unemp_length_yearly = np.full(years, np.nan)
    for y in range(years):
        lo, hi = burn + y*per_year, burn + (y+1)*per_year
        m = (spell_t >= lo) & (spell_t < hi)
        if m.any():
            unemp_length_yearly[y] = spells[m].mean()

        # --- Post-burn aggregates (add these) ---
    rev_postburn = float(taxes[burn:].sum())
    ui_postburn  = float(ui_sp[burn:].sum())
    unrate_mean_postburn = float(np.mean(unrate[burn:])) if T > burn else float('nan')
    avg_h_mean_postburn  = float(np.mean(avg_h[burn:]))  if T > burn else float('nan')

    # Yearly averages post-burn (add these)
    years = (T - burn) // per_year
    unrate_yearly = np.full(years, np.nan)
    avg_h_yearly  = np.full(years, np.nan)
    for y in range(years):
        lo, hi = burn + y*per_year, burn + (y+1)*per_year
        unrate_yearly[y] = unrate[lo:hi].mean()
        avg_h_yearly[y]  = avg_h[lo:hi].mean()

    # Existing spell stats (you already compute these above)
    spells = np.asarray(spells, float)
    spell_t= np.asarray(spell_t, int)
    post   = spell_t >= burn
    spells_post = spells[post]
    avg_spell_post = float(np.nan) if spells_post.size==0 else float(spells_post.mean())

    # --- Final return dict (replace your current one with this) ---
    return {
        'taxes': taxes,
        'ui': ui_sp,
        'unrate': unrate,
        'avg_h': avg_h,
        'rev_postburn': rev_postburn,
        'ui_postburn': ui_postburn,
        'unrate_mean_postburn': unrate_mean_postburn,   
        'avg_h_mean_postburn':  avg_h_mean_postburn,    
        'unrate_yearly': unrate_yearly,                 
        'avg_h_yearly':  avg_h_yearly,                  
        'unemp_spell_lengths_all': spells,
        'unemp_spell_end_times_all': spell_t,
        'unemp_spell_lengths_postburn': spells_post,
        'avg_unemp_length_postburn': avg_spell_post,
        'unemp_length_yearly': unemp_length_yearly,
    }