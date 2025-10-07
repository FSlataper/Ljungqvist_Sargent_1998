import numpy as np
rng = np.random.default_rng(42)

def c(s):
    return s*0.5

def pi(s):
    return s**0.3


beta  = 0.9985
alpha = 0.0009      # death prob
lam   = 0.009       # layoff prob
psiF  = 30          # employed turbulence multiplier
psiU  = 10          # unemployed turbulence multiplier

w_grid = np.linspace(0.0, 1.0, 41)           # wages
s_grid = np.linspace(0.0, 1.0, 41)           # search effort
h_min, h_max, H = 1.0, 2.0, 201 
h_grid = np.linspace(h_min, h_max, H)
dH = h_grid[1] - h_grid[0]

# Effective discount rate same as any other problem with termination probability 
beta_hat = (1.0 - alpha) * beta

# Offer distribution and "CDF"

mu, var = 0.5, 0.1
sigma = np.sqrt(var)

from math import erf, sqrt, exp, pi as PI
def _phi(x): return np.exp(-0.5*x*x)/np.sqrt(2*PI)
def _Phi(x): return 0.5*(1.0+erf(x/np.sqrt(2.0)))

a, b_trunc = (0.0-mu)/sigma, (1.0-mu)/sigma
Z = _Phi(b_trunc) - _Phi(a)

def truncnorm_pdf(x):
    z = (x - mu)/sigma
    return (_phi(z) / (sigma * Z)) * ((x>=0.0) & (x<=1.0))

# discrete quadrature weights on w_grid
w_pdf = truncnorm_pdf(w_grid)
w_pdf /= w_pdf.sum()


# Determining UI

Nclass = 15
W_upper = np.linspace(2.0/Nclass, 2.0, Nclass)          # class upper bounds W_i
benefit_by_class = 0.7 * W_upper                         # UI level when eligible and last class = i
suitable_by_class = benefit_by_class.copy()

def class_of_earnings(e):
    # clip to [0,2], then find smallest i with e <= W_upper[i]
    e = np.clip(e, 0.0, 2.0)
    return np.searchsorted(W_upper, e, side='left')


def sample_truncnorm(n, rng):
    out = np.empty(n)
    i = 0
    while i < n:
        x = rng.normal(mu, sigma, size=n-i)
        m = (x>=0.0) & (x<=1.0)
        k = m.sum()
        if k>0:
            out[i:i+k] = x[m][:k]
            i += k
    return out

# Index of h (keep precomputed for efficiency)

def idx_of_h(h):
    return np.clip(((h - h_min)/dH).round().astype(int), 0, H-1)

up_idx    = np.arange(H) + 1
up_idx[-1] = H-1

downU_idx = idx_of_h(np.maximum(h_grid - psiU*dH, h_min))
downF_idx = idx_of_h(np.maximum(h_grid - psiF*dH, h_min))

if 'W_upper' not in globals():
    Nclass = 15
    W_upper = np.linspace(2.0 / Nclass, 2.0, Nclass)  # class upper bounds on earnings e∈[0,2]

def get_benefit_array(benefit_scale: float = 1.0) -> np.ndarray:
    """
    Returns the per-period UI level for each earnings class i,
    keeping the suitable-job threshold tied to UI:
        UI_i = benefit_scale * (0.7 * W_i)
    """
    return benefit_scale * (0.7 * W_upper)

