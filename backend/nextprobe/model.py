"""Early model (0h+24h only) + class-conditional 96h/168h models. Cross-fitted so no device is scored by a model trained on it."""
import numpy as np
from scipy.special import logsumexp
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from .data import CLASSES, ANOM

K = len(CLASSES)


def early_features(inf):
    """Uses ONLY 0h/24h and lot statistics computed from 0h/24h data of the same lot."""
    lv0, lv24 = np.log(inf.v0.values), np.log(inf.v24.values)
    d24 = lv24 - lv0
    zd = np.zeros(len(inf)); zl = np.zeros(len(inf))
    lot = inf.lot_id.values
    for l in np.unique(lot):
        m = lot == l
        for arr, src in ((zd, d24), (zl, lv24)):
            med = np.median(src[m]); mad = 1.4826 * np.median(np.abs(src[m] - med)) + 1e-6
            arr[m] = (src[m] - med) / mad
    return dict(lv0=lv0, lv24=lv24, d24=d24, zd=zd, zl=zl,
                X=np.column_stack([lv0, lv24, d24, np.clip(zd, -10, 30), np.clip(zl, -10, 30)]))


def _ols(A, y, lam=1e-3):
    w = np.linalg.solve(A.T @ A + lam * np.eye(A.shape[1]), A.T @ y)
    return w, max(float(np.std(y - A @ w)), 0.015)


class FoldModel:
    def fit(self, F, cls, z96, z168):
        self.sc = StandardScaler().fit(F["X"])
        self.clf = LogisticRegression(C=1.0, max_iter=3000).fit(self.sc.transform(F["X"]), cls)
        self.present = self.clf.classes_
        d = F["d24"]; A1 = np.column_stack([np.ones_like(d), d]); A2 = np.column_stack([np.ones_like(d), d, z96])
        self.w96, self.s96 = np.zeros((K, 2)), np.full(K, 0.05)
        self.w168a, self.s168a = np.zeros((K, 2)), np.full(K, 0.1)
        self.w168b, self.s168b = np.zeros((K, 3)), np.full(K, 0.1)
        for c in self.present:
            m = cls == c
            if m.sum() < 3: continue
            self.w96[c], self.s96[c] = _ols(A1[m], z96[m])
            self.w168a[c], self.s168a[c] = _ols(A1[m], z168[m])
            self.w168b[c], self.s168b[c] = _ols(A2[m], z168[m])
        return self

    def prior(self, F):
        P = np.zeros((len(F["d24"]), K)); P[:, self.present] = self.clf.predict_proba(self.sc.transform(F["X"]))
        return np.clip(P, 1e-9, 1); 
    def m96(self, d24): return self.w96[:, 0][None] + d24[:, None] * self.w96[:, 1][None]      # N x K
    def m168_pre(self, d24): return self.w168a[:, 0][None] + d24[:, None] * self.w168a[:, 1][None]
    def m168_post(self, d24, z96): return self.w168b[:, 0][None] + d24[:, None] * self.w168b[:, 1][None] + z96[:, None] * self.w168b[:, 2][None]

    def posterior(self, prior, d24, z96):
        ll = -0.5 * ((z96[:, None] - self.m96(d24)) / self.s96[None]) ** 2 - np.log(self.s96)[None]
        lp = np.log(prior) + ll
        return np.exp(lp - logsumexp(lp, axis=1, keepdims=True)), ll

    def ood96(self, d24, z96, sigma):
        return (np.abs(z96[:, None] - self.m96(d24)) / self.s96[None]).min(axis=1) > sigma


def norm_cdf(x):
    from scipy.special import ndtr
    return ndtr(x)


def mixture_quantiles(w, mu, s, qs=(0.05, 0.5, 0.95), G=500):
    """w,mu: N x K; s: N x K or K. Returns N x len(qs) quantiles (log-space) of the Gaussian mixture."""
    N = w.shape[0]; s = np.broadcast_to(s, w.shape)
    out = np.zeros((N, len(qs)))
    for i in range(N):
        act = w[i] > 1e-6
        g = np.linspace((mu[i, act] - 5 * s[i, act]).min(), (mu[i, act] + 5 * s[i, act]).max(), G)
        cdf = (w[i, act][None] * norm_cdf((g[:, None] - mu[i, act][None]) / s[i, act][None])).sum(1) / w[i, act].sum()
        out[i] = np.interp(qs, cdf, g)
    return out
