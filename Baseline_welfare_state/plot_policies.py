import matplotlib
matplotlib.use("Agg")

def _default_tau_list():
    # If you computed tau_star, center the sweep around it; else use a default set.
    if 'tau_star' in globals() and isinstance(tau_star, (int, float)):
        c = float(tau_star)
        L = sorted(set([max(0.0, min(0.9, x)) for x in [c-0.05, c, c+0.05, c+0.10]]))
        return L
    return [0.10, 0.20, 0.30, 0.40]

def plot_vfi_vs_tau(
    tau_list=None,
    classes_to_show=(0, 7, 14),
    ue_slice_class_idx=None,
    maxit=300
):
    """
    Plots (one figure per chart):
      1) U_N(h)
      2) U_E(h,i) for selected classes (one figure per class)
      3) s_N(h)
      4) s_E(h)
      5) wbar_inel(h)
      6) wbar(h,i) for selected classes (one figure per class)
      7) W(w, h_med)
      8) W(w_med, h)
      9) U_E(h, i_fixed)  <-- NEW: unemployed analogue of (8), fixed class across τ

    Args:
      tau_list: list of τ values to sweep
      classes_to_show: iterable of class indices to plot for U_E and wbar
      ue_slice_class_idx: single class index for chart (9). If None, uses the median class.
      maxit: max iterations for the VFI solver
    """

    
    if tau_list is None:
        tau_list = _default_tau_list()
    if ue_slice_class_idx is None:
        ue_slice_class_idx = Nclass // 2  # median earnings class

    # Solve VFI for each tau
    results = []
    for tau in tau_list:
        U_E, U_N, Wv, sE, sN, wbar, wbar_inel = solve_values_given_tau_UIclasses(
            tau, tol=1e-3, maxit=maxit
        )
        results.append((tau, U_E, U_N, Wv, sE, sN, wbar, wbar_inel))

    h_med_idx = len(h_grid) // 2
    w_med_idx = len(w_grid) // 2

    # 1) U_N(h)
    plt.figure()
    for (tau, _UE, U_N, *_rest) in results:
        plt.plot(h_grid, U_N, label=f"tau={tau:.2f}")
    plt.xlabel("Human capital h")
    plt.ylabel("U_N(h)")
    plt.title("Ineligible unemployed value U_N(h) across tau")
    plt.legend()
    plt.tight_layout()
    plt.show()

    # 2) U_E(h,i) for selected classes
    for i_cls in classes_to_show:
        plt.figure()
        for (tau, U_E, *_r) in results:
            plt.plot(h_grid, U_E[:, i_cls], label=f"tau={tau:.2f}")
        plt.xlabel("Human capital h")
        plt.ylabel(f"U_E(h, class={i_cls})")
        plt.title(f"Eligible unemployed value U_E(h, class={i_cls}) across tau")
        plt.legend()
        plt.tight_layout()
        plt.show()

    # 3) s_N(h)
    plt.figure()
    for (tau, _UE, _UN, _Wv, _sE, sN, *_rest) in results:
        plt.plot(h_grid, sN, label=f"tau={tau:.2f}")
    plt.xlabel("Human capital h")
    plt.ylabel("s_N(h)")
    plt.title("Search policy (ineligible) s_N(h) across tau")
    plt.legend()
    plt.tight_layout()
    plt.show()

    # 4) s_E(h)
    plt.figure()
    for (tau, _UE, _UN, _Wv, sE, _sN, *_rest) in results:
        plt.plot(h_grid, sE, label=f"tau={tau:.2f}")
    plt.xlabel("Human capital h")
    plt.ylabel("s_E(h)")
    plt.title("Search policy (eligible) s_E(h) across tau")
    plt.legend()
    plt.tight_layout()
    plt.show()

    # 5) wbar_inel(h)
    plt.figure()
    for (tau, *_r, wbar_inel) in results:
        plt.plot(h_grid, wbar_inel, label=f"tau={tau:.2f}")
    plt.xlabel("Human capital h")
    plt.ylabel("wbar_inel(h)")
    plt.title("Reservation wage (ineligible) across tau")
    plt.legend()
    plt.tight_layout()
    plt.show()

    # 6) wbar(h,i) for selected classes
    for i_cls in classes_to_show:
        plt.figure()
        for (tau, _UE, _UN, _Wv, _sE, _sN, wbar, _wbi) in results:
            plt.plot(h_grid, wbar[:, i_cls], label=f"tau={tau:.2f}")
        plt.xlabel("Human capital h")
        plt.ylabel(f"wbar(h, class={i_cls})")
        plt.title(f"Reservation wage (eligible) for class {i_cls} across tau")
        plt.legend()
        plt.tight_layout()
        plt.show()

    # 7) W(w, h_med)
    plt.figure()
    for (tau, _UE, _UN, Wv, *_rest) in results:
        plt.plot(w_grid, Wv[:, h_med_idx], label=f"tau={tau:.2f}")
    plt.xlabel("Wage offer w")
    plt.ylabel(f"W(w, h_med={h_grid[h_med_idx]:.3f})")
    plt.title("Employed value at median h across tau")
    plt.legend()
    plt.tight_layout()
    plt.show()

    # 8) W(w_med, h)
    plt.figure()
    for (tau, _UE, _UN, Wv, *_rest) in results:
        plt.plot(h_grid, Wv[w_med_idx, :], label=f"tau={tau:.2f}")
    plt.xlabel("Human capital h")
    plt.ylabel(f"W(w_med={w_grid[w_med_idx]:.3f}, h)")
    plt.title("Employed value at median w across tau")
    plt.legend()
    plt.tight_layout()
    plt.show()