from typing import Mapping, Dict, Optional, Iterable, Any, Callable, Union, Sequence
from numpy import ndarray
from . import Model

Trace = Mapping[int, ndarray]
# the following should be refined
StepFunction = Callable[...,Any]
optint = Optional[int]
optbool = Optional[bool]
random_seed = Any  # FIXME
RV = Any # FIXME


def sample_posterior_predictive(trace:Trace,
                                samples:Optional[int],
                                model:Optional[Model],
                                vars:Iterable[RV],
                                size:Optional[int],
                                random_seed:random_seed,
                                progressbar:Optional[bool]) -> Dict[str,ndarray]: ...

def sample_prior_predictive(samples: Optional[int], model: Optional[Model], \
                            vars: Optional[Iterable[str]],
                            random_seed: Optional[random_seed]) -> Trace: ...

def sample(draws: optint=500,
           # function or iterable of functions
           step: Optional[Union[StepFunction, Iterable[StepFunction]]]=None,
           init: Optional[str]=None,
           n_init: optint=None,
           # dict, or array of dict) – Starting point in parameter space (or partial point)
           start: Optional[Union[Dict[Any, Any], Sequence[Dict[Any, Any]]]]=None,
           trace: Optional[Any]=None,  # backend, list, or MultiTrace
           chain_idx: optint=None,
           chains: optint=None,
           cores: optint=None,
           tune: optint=None,
           nuts_kwargs: Optional[Dict[str,Any]]=None,
           step_kwargs: Optional[Dict[str,Any]]=None,
           progressbar: optbool=None,
           model: Optional[Model]=None,
           random_seed: random_seed=None,
           live_plot: optbool=None,
           discard_tuned_samples: optbool=None,
           live_plot_kwargs: Optional[Dict[str,Any]]=None,
           compute_convergence_checks: optbool=None,
           use_mmap: optbool=None,
           **kwargs) -> Trace:  ...