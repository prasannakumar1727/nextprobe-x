"""NEXTPROBE selector: EVOI of a 96h observation. Pure functions of early-stage model quantities and the predictive
distribution of y96. Has no access to hidden stores or labels. Cannot set dispositions."""
import numpy as np
from scipy.special import logsumexp
from .data import ANOM

G = 400


def build_grid(prior, m96, s96):
    """Predictive distribution of z96=log(y96/y24) per device on a grid, and posterior P(anomaly | z96) on that grid.
    prior: N x K; m96: N x K; s96: N x K. Returns (P_grid N x G anomaly posterior, W_grid N x G predictive weights)."""
    lo = (m96 - 5 * s96).min(1); hi = (m96 + 5 * s96).max(1)
    z = lo[:, None] + (hi - lo)[:, None] * np.linspace(0, 1, G)[None]           # N x G
    ll = -0.5 * ((z[:, :, None] - m96[:, None, :]) / s96[:, None, :]) ** 2 - np.log(s96)[:, None, :]  # N x G x K
    lj = np.log(prior)[:, None, :] + ll
    lm = logsumexp(lj, axis=2)                                                     # log marginal density (unnormalised)
    post = np.exp(lj - lm[:, :, None])
    P = post[:, :, ANOM].sum(2)
    W = np.exp(lm - lm.max(1, keepdims=True)); W /= W.sum(1, keepdims=True)
    return P, W


def decision_risk(p, fn, fp):
    """Bayes risk of the better of {ACCEPT (risk p*FN), ESCALATE (risk (1-p)*FP)}."""
    return np.minimum(p * fn, (1 - p) * fp)


def evoi(p_now, P_grid, W_grid, fn, fp, probe_cost):
    r_now = decision_risk(p_now, fn, fp)
    r_post = (W_grid * decision_risk(P_grid, fn, fp)).sum(1)
    return r_now, r_post, r_now - r_post - probe_cost


def rank_evoi(p_now, P_grid, W_grid, fn, fp, probe_cost, budget, eligible):
    r_now, r_post, e = evoi(p_now, P_grid, W_grid, fn, fp, probe_cost)
    e = np.where(eligible, e, -np.inf)
    order = np.argsort(-e, kind="stable")
    sel = [i for i in order[:budget] if e[i] > 0]     # only positive net EVOI is worth spending capacity on
    return order, sel, r_now, r_post, e
