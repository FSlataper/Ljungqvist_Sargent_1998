def simulate_UIclasses(tau, U_E, U_N, Wv, sE, sN, wbar, wbar_inel,
                       T=2000, N=10_000, burn=100, seed=1,
                       tax_UI=True, per_year=26, track=True, benefit_scale=1.0):

    rng = np.random.default_rng(seed)
    benefit_arr = get_benefit_array(benefit_scale)

    Hn = len(h_grid)
    h_idx   = rng.integers(0, Hn, size=N)
    state   = np.zeros(N, dtype=int)        # 0=U, 1=E
    elig    = np.zeros(N, dtype=bool)       # UI eligibility
    last_i  = np.zeros(N, dtype=int)        # last earnings class (valid if elig=1)
    wage    = np.zeros(N)

    # --- NEW: unemployment duration counter (periods in current spell) ---
    un_dur  = np.zeros(N, dtype=int)

    # --- time series containers ---
    taxes = np.zeros(T)
    ui_sp = np.zeros(T)
    unrate = np.zeros(T)
    avg_h  = np.zeros(T)

    # --- NEW: collect completed unemployment spells ---
    spell_lengths = []
    spell_endtime = []

    for t in range(T):
        # Before any transitions, increment duration for those who start the period unemployed
        un_mask_start = (state == 0)
        if un_mask_start.any():
            un_dur[un_mask_start] += 1

        # births/deaths
        die = rng.random(N) < alpha
        if die.any():
            # Any ongoing unemployment spells are right-censored; just reset them
            h_idx[die] = rng.integers(0, Hn, size=die.sum())
            state[die] = 0
            elig[die]  = False
            last_i[die]= 0
            wage[die]  = 0.0
            un_dur[die]= 0

        # employed block
        emp = (state==1)
        if emp.any():
            h_e = h_grid[h_idx[emp]]
            w_e = wage[emp]
            earn = w_e * h_e
            taxes[t] += tau * np.sum(earn)

            # separations
            sep = rng.random(emp.sum()) < lam
            keep = ~sep
            idx_emp = np.where(emp)[0]

            # keep job -> skill up
            h_idx[idx_emp[keep]] = up_idx[h_idx[idx_emp[keep]]]

            # separate -> become unemployed, eligible, new spell starts (un_dur reset to 0)
            if sep.any():
                sel = idx_emp[sep]
                e_sep = np.clip(earn[sep], 0.0, 2.0)
                last_i[sel] = np.searchsorted(W_upper, e_sep, side='left')
                elig[sel]   = True
                state[sel]  = 0
                wage[sel]   = 0.0
                h_idx[sel]  = downF_idx[h_idx[sel]]
                un_dur[sel] = 0  # new U-spell starts after separation

        # unemployed block
        un = (state==0)
        if un.any():
            idx_un = np.where(un)[0]

            # UI flows
            ui_vals = np.where(elig[idx_un], benefit_arr[last_i[idx_un]], 0.0)
            if tax_UI:
                taxes[t] += tau * np.sum(ui_vals)
                ui_sp[t] += (1.0 - tau) * np.sum(ui_vals)
            else:
                ui_sp[t] += np.sum(ui_vals)

            # turbulence while U
            h_idx[idx_un] = downU_idx[h_idx[idx_un]]

            # meet & accept (with "suitable" rule)
            s_now = np.where(elig[idx_un], sE[h_idx[idx_un]], sN[h_idx[idx_un]])
            meet  = rng.random(idx_un.size) < (s_now**0.3)
            if meet.any():
                sel    = idx_un[meet]
                w_off  = sample_truncnorm(sel.size, rng)
                h_next = h_grid[h_idx[sel]]
                e_off  = w_off * h_next

                elig_sel = elig[sel]
                accept = np.zeros(sel.size, dtype=bool)

                # eligible: must accept if e_off >= benefit_arr[class]
                if elig_sel.any():
                    iL = last_i[sel][elig_sel]
                    must_acc = e_off[elig_sel] >= benefit_arr[iL]
                    wb = wbar[h_idx[sel][elig_sel], iL]
                    accept[elig_sel] = (w_off[elig_sel] >= wb) | must_acc
                    # if they reject a suitable offer, eligibility is lost
                    lose = (~accept[elig_sel]) & must_acc
                    if lose.any():
                        who = sel[elig_sel][lose]
                        elig[who] = False

                # ineligible: standard threshold
                inel = ~elig_sel
                if inel.any():
                    wb = wbar_inel[h_idx[sel][inel]]
                    accept[inel] = (w_off[inel] >= wb)

                # record completed U-spells right before switching them to employment
                if accept.any():
                    who = sel[accept]
                    # Those accepted were unemployed at the start of the period and had un_dur incremented above
                    spell_lengths.extend(un_dur[who].tolist())
                    spell_endtime.extend([t]*len(who))

                    # transition to employment and reset counters
                    state[who] = 1
                    wage[who]  = w_off[accept]
                    un_dur[who]= 0  # reset since employed

        # record aggregates this period
        unrate[t] = np.mean(state==0)
        avg_h[t]  = np.mean(h_grid[h_idx])

    if not track:
        return taxes, ui_sp

    # Convert spell logs to arrays
    spell_lengths = np.asarray(spell_lengths, dtype=float)
    spell_endtime = np.asarray(spell_endtime, dtype=int)

    # Post-burn subset: spells that **end** in t >= burn
    post_mask = (spell_endtime >= burn)
    spell_lengths_post = spell_lengths[post_mask]

    avg_unemp_length_postburn = float(np.nan) if spell_lengths_post.size==0 else float(spell_lengths_post.mean())

    T_eff = len(taxes) - burn
    years = T_eff // per_year
    unrate_yearly = np.array([unrate[burn + y*per_year : burn + (y+1)*per_year].mean() for y in range(years)])
    avg_h_yearly  = np.array([ avg_h[burn + y*per_year : burn + (y+1)*per_year].mean() for y in range(years)])

    # Yearly averages (among spells ending in each post-burn year)
    T_eff = T - burn
    years = T_eff // per_year
    unemp_length_yearly = np.full(years, np.nan)
    for y in range(years):
        lo = burn + y*per_year
        hi = burn + (y+1)*per_year
        m = (spell_endtime >= lo) & (spell_endtime < hi)
        if m.any():
            unemp_length_yearly[y] = spell_lengths[m].mean()

    return {
        'taxes': taxes, 'ui': ui_sp,
        'unrate': unrate, 'avg_h': avg_h,
        'rev_postburn': float(taxes[burn:].sum()),
        'ui_postburn': float(ui_sp[burn:].sum()),
        'unrate_mean_postburn': float(unrate[burn:].mean()),
        'avg_h_mean_postburn': float(avg_h[burn:].mean()),
        'unemp_spell_lengths_all': spell_lengths,
        'unemp_spell_end_times_all': spell_endtime,
        'unemp_spell_lengths_postburn': spell_lengths_post,
        'avg_unemp_length_postburn': avg_unemp_length_postburn,
        'unemp_length_yearly': unemp_length_yearly,
                'unrate_yearly': unrate_yearly, 'avg_h_yearly':  avg_h_yearly,
    }