'''Beginnings of mypy stubs for PyMC3.'''
from typing import Mapping, Union, Any, Dict, Optional, ContextManager, List, Tuple, Any
from numpy import ndarray

from . import sampling as sampling
#from .backends.base import BaseTrace, MultiTrace
#from .backends.ndarray import NDArray
#from .distributions.distribution import draw_values
from . import model, backends
#from .model import modelcontext, Point, all_continuous
# from .step_methods import (NUTS, HamiltonianMC, Metropolis, BinaryMetropolis,
#                            BinaryGibbsMetropolis, CategoricalGibbsMetropolis,
#                            Slice, CompoundStep, arraystep, smc)
# from .util import update_start_vals, get_untransformed_name, is_transformed_name, get_default_varnames
# from .vartypes import discrete_types
# from pymc3.step_methods.hmc import quadpotential
#from pymc3 import plots
#import pymc3 as pm

from .blocking import *
from .distributions import *
from .glm import *
from . import gp
from .math import expand_packed_triangular as expand_packed_triangular, \
                  invlogit as invlogit, \
                  invprobit as invprobit, \
                  logaddexp as logaddexp,\
                  logit as logit, \
                  logsumexp as logsumexp, \
                  probit as probit
from .model import *
from .model_graph import model_to_graphviz as model_to_graphviz
from .stats import *
from .sampling import *
from .theanof import *
from .tuning import *
from .variational import *
from .vartypes import *
from .exceptions import *
from . import sampling as sampling

#from .backends.tracetab import *
from .diagnostics import *
from .backends import load_trace as load_trace, save_trace as save_trace, \
    MultiTrace as MultiTrace

from .plots import plot_posterior as plot_posterior, traceplot as traceplot
#from .tests import test

from .data import *
from .backends import load_trace as load_trace, save_trace as save_trace, \
    MultiTrace as MultiTrace
from .math import expand_packed_triangular, invlogit, invprobit, logaddexp, logit, logsumexp, probit
from .model_graph import model_to_graphviz
