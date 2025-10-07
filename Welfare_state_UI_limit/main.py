import params_et_utils.py
import VFI.py
import simulate.py
import equilibrium.py



T    = 2000      # total periods (longer horizon for nicer plots)
burn = 100      # burn-in
N    = 20000   # number of workers
per_year = 26   # 26 periods = 1 year

# Find equilibrium tau
tau_star, (U_Ecap, U_Ncap, Wcap, sEcap, sNcap, wbar_Ecap, wbar_Ncap), _ = equilibrium_tax_UIcap(
    T=2000, N=20000, burn=100, tax_UI=True, benefit_scale=1.0, EMAX=52
)

# 2) Simulate with *cap* objects (use named args to avoid misbinding)
stats = simulate_UIclasses_cap(
    tau_star,
    U_Ecap, U_Ncap, Wcap,
    sEcap, sNcap,
    wbar_Ecap, wbar_Ncap,
    EMAX=52,
    T=2000, N=20_000, burn=100, seed=2025,
    tax_UI=True, per_year=26, track=True, benefit_scale=1.0
)

print(f"Equilibrium tau* ≈ {tau_star:.4f}")
print(f"Post-burn avg unemployment ≈ {stats['unrate_mean_postburn']:.3%}")
print(f"Post-burn avg skill ≈ {stats['avg_h_mean_postburn']:.3f}")

# --- Plots ---

import matplotlib.pyplot as plt

# Per-period unemployment + skill
fig, ax1 = plt.subplots()
ax1.plot(stats['unrate'], label="Unemployment rate")
ax1.axvline(burn, color='gray', linestyle='--', alpha=0.7, label="Burn-in ends")
ax1.set_xlabel("Period (2 weeks each)")
ax1.set_ylabel("Unemployment rate")
ax1.legend(loc="upper left")

ax2 = ax1.twinx()
ax2.plot(stats['avg_h'], color="orange", label="Avg skill (h)")
ax2.set_ylabel("Average human capital")
ax2.legend(loc="upper right")
plt.title("Simulation paths (equilibrium τ)")
plt.show()

# Yearly averages (post-burn)
years = np.arange(1, len(stats['unrate_yearly'])+1)
plt.figure()
plt.plot(years, stats['unrate_yearly'], marker='o', label="Unemployment rate")
plt.plot(years, stats['avg_h_yearly'], marker='s', label="Avg skill (h)")
plt.xlabel("Year (post-burn)")
plt.title("Yearly averages (post-burn)")
plt.legend()
plt.show()

print(f"τ* ≈ {tau_star:.4f}")
print(f"Avg unemployment spell length (post-burn): {stats['avg_unemp_length_postburn']:.2f} periods")

import matplotlib.pyplot as plt
# 1) Histogram of post-burn spell lengths
plt.figure()
plt.hist(stats['unemp_spell_lengths_postburn'], bins=25)
plt.xlabel("Unemployment spell length (periods)")
plt.ylabel("Count")
plt.title("Distribution of unemployment spell lengths (post-burn)")
plt.tight_layout()
plt.show()

# 2) Yearly average spell length (post-burn)
years = range(1, 1 + len(stats['unemp_length_yearly']))
plt.figure()
plt.plot(list(years), stats['unemp_length_yearly'], marker='o')
plt.xlabel("Year (post-burn)")
plt.ylabel("Avg unemployment spell length (periods)")
plt.title("Average unemployment spell length by year (post-burn)")
plt.tight_layout()
plt.show()
