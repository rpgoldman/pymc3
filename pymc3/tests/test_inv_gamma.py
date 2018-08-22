import scipy
import scipy.stats as stats
from numpy import inf

rplus = [0, .01, .1, .9, .99, 1, 1.5, 2, 100, inf]

def get_alpha_beta(mu, sd):
    alpha = (2 * sd**2 + mu**2)/sd**2
    beta = mu * (mu**2 + sd**2) / sd**2
    return alpha, beta


# def test_inverse_gamma(self):
#     self.pymc3_matches_scipy(
#         InverseGamma, Rplus, {'alpha': Rplus, 'beta': Rplus},
#         lambda value, alpha, beta: sp.invgamma.logpdf(value, alpha, scale=beta))
#     self.pymc3_matches_scipy(
#         InverseGamma, Rplus, {'mu': Rplus, 'sd': Rplus},
#         lambda value, mu, sd: sp.invgamma.logpdf(value, InverseGamma._get_alpha_beta(None, None, mu, sd)[0],
#                                                  scale=InverseGamma._get_alpha_beta(None, None, mu, sd)[1]))


def inv_gammas():
    for mu in rplus:
        for sd in rplus:
            alpha, beta = get_alpha_beta(mu, sd)
            for val in rplus:
                print('logp(InverseGamma(%f, mu=%f, sd=%f) = %f'%(val, mu, sd, stats.invgamma.logpdf(val,alpha,scale=beta)))
    return None

