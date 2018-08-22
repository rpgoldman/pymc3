# Stubs for pymc3.glm.families (Python 3.7)
#
# NOTE: This dynamically typed stub was automatically generated by stubgen.

from typing import Any, Optional

class Identity:
    def __call__(self, x: Any): ...

class Family:
    priors: Any = ...
    link: Any = ...
    def __init__(self, **kwargs: Any) -> None: ...
    def _get_priors(self, model: Optional[Any] = ..., name: str = ...): ...
    def create_likelihood(self, name: Any, y_est: Any, y_data: Any, model: Optional[Any] = ...): ...
    def __repr__(self): ...

class StudentT(Family):
    link: Any = ...
    likelihood: Any = ...
    parent: str = ...
    priors: Any = ...

class Normal(Family):
    link: Any = ...
    likelihood: Any = ...
    parent: str = ...
    priors: Any = ...

class Binomial(Family):
    link: Any = ...
    likelihood: Any = ...
    parent: str = ...
    priors: Any = ...

class Poisson(Family):
    link: Any = ...
    likelihood: Any = ...
    parent: str = ...
    priors: Any = ...

class NegativeBinomial(Family):
    link: Any = ...
    likelihood: Any = ...
    parent: str = ...
    priors: Any = ...
