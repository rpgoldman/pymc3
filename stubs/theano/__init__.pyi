# Minimal stubs for references from PyMC3

from . import tensor as tensor
from .tensor import TensorVariable as TensorVariable


class Op:
    ...


# needed (I think) for pymc3.variational.ObjectiveUpdates
#class OrderedUpdates:
#    ...
