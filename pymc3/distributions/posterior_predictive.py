import numbers
import itertools
from typing import List, Dict, Any, Optional, Set, Tuple
import logging

import numpy as np
import theano
import theano.tensor as tt

from ..backends.base import MultiTrace
from .distribution import _DrawValuesContext, _DrawValuesContextBlocker, is_fast_drawable, _compile_theano_function
from ..model import Model, get_named_nodes_and_relations, ObservedRV, MultiObservedRV, modelcontext



PosteriorPredictiveTrace = Dict[str, np.ndarray]

def _ppc_draw_values(vars: List[Any], trace: MultiTrace, samples: int, size: Optional[int] = None) -> PosteriorPredictiveTrace:
    logger = logging.getLogger('posterior_predictive')
    
    if size is not None:
        raise NotImplementedError("size is not yet implemented for sample_posterior_predictive")
    context = _DrawValuesContext()
    ppc_trace = {} # type: PosteriorPredictiveTrace
    with context:
        evaluated, symbolic_params = _ppc_draw_values_init(vars, trace, samples, ppc_trace, size)
        leaf_nodes, named_nodes_parents, named_nodes_children = _ppc_make_graph(symbolic_params)
        with context:
            drawn = context.drawn_vars
            # Init givens and the stack of nodes to try to `_draw_value` from
            givens = {p.name: (p, v) for (p, size), v in drawn.items()
                      if getattr(p, 'name', None) is not None}
            stack = list(leaf_nodes.values())  # A queue would be more appropriate
            while stack:
                next_ = stack.pop(0)
                if (next_, size) in drawn:
                    # If the node already has a givens value, skip it
                    continue
                elif isinstance(next_, (tt.TensorConstant,
                                        tt.sharedvar.SharedVariable)):
                    # If the node is a theano.tensor.TensorConstant or a
                    # theano.tensor.sharedvar.SharedVariable, its value will be
                    # available automatically in _compile_theano_function so
                    # we can skip it. Furthermore, if this node was treated as a
                    # TensorVariable that should be compiled by theano in
                    # _compile_theano_function, it would raise a `TypeError:
                    # ('Constants not allowed in param list', ...)` for
                    # TensorConstant, and a `TypeError: Cannot use a shared
                    # variable (...) as explicit input` for SharedVariable.
                    # ObservedRV and MultiObservedRV instances are ViewOPs
                    # of TensorConstants or SharedVariables, we must add them
                    # to the stack or risk evaluating deterministics with the
                    # wrong values (issue #3354)
                    stack.extend([node for node in named_nodes_parents[next_]
                                  if isinstance(node, (ObservedRV,
                                                       MultiObservedRV))
                                  and (node, size) not in drawn])
                    continue
                else:
                    # If the node does not have a givens value, try to draw it.
                    # The named node's children givens values must also be taken
                    # into account.
                    children = named_nodes_children[next_]
                    temp_givens = [givens[k] for k in givens if k in children]
                    try:
                        # This may fail for autotransformed RVs, which don't
                        # have the random method
                        value = _ppc_draw_value(next_,
                                            trace=trace,
                                            givens=temp_givens,
                                            samples=samples,
                                            size=size)
                        assert isinstance(value, np.ndarray)
                        ppc_trace[next_.name] = value
                        givens[next_.name] = (next_, value)
                        drawn[(next_, size)] = value
                    except theano.gof.fg.MissingInputError:
                        # The node failed, so we must add the node's parents to
                        # the stack of nodes to try to draw from. We exclude the
                        # nodes in the `params` list.
                        stack.extend([node for node in named_nodes_parents[next_]
                                      if node is not None and
                                      (node, size) not in drawn])

  
            # the below makes sure the graph is evaluated in order
            # test_distributions_random::TestDrawValues::test_draw_order fails without it
            # The remaining params that must be drawn are all hashable
            to_eval = set() # type: Set[int]
            missing_inputs = set([j for j, p in symbolic_params]) # type: Set[int]
            while to_eval or missing_inputs:
                if to_eval == missing_inputs:
                    raise ValueError('Cannot resolve inputs for {}'.format([str(trace.varnames[j]) for j in to_eval]))
                to_eval = set(missing_inputs)
                missing_inputs = set()
                for param_idx in to_eval:
                    param = vars[param_idx]
                    drawn = context.drawn_vars
                    if (param, size) in drawn:
                        evaluated[param_idx] = drawn[(param, size)]
                    else:
                        try:
                            if param in named_nodes_children:
                                for node in named_nodes_children[param]:
                                    if (
                                        node.name not in givens and
                                        (node, size) in drawn
                                    ):
                                        givens[node.name] = (
                                            node,
                                            drawn[(node, size)]
                                        )
                            value = _ppc_draw_value(param,
                                                    trace=trace,
                                                    givens=givens.values(),
                                                    samples=samples,
                                                    size=size)
                            assert isinstance(value, np.ndarray)
                            ppc_trace[param.name] = value
                            evaluated[param_idx] = drawn[(param, size)] = value
                            givens[param.name] = (param, value)
                        except theano.gof.fg.MissingInputError:
                            missing_inputs.add(param_idx)
    assert set(ppc_trace.keys()) == {var.name for var in vars}
    return ppc_trace

def _ppc_draw_values_init(vars: List[Any], trace: MultiTrace, samples: int, ppc_trace: PosteriorPredictiveTrace, size: Optional[int] = None) -> Tuple[Dict[int, np.ndarray], List[Tuple[int, Any]]]:

    # initialization phase
    context = _DrawValuesContext.get_context()
    with context:
        drawn = context.drawn_vars
        evaluated = {} # type: Dict[int, Any]
        symbolic_params = []
        for i, var in enumerate(vars):
            if is_fast_drawable(var):
                evaluated[i] = ppc_trace[var.name] = _ppc_draw_value(var, trace, samples, size)
                continue
            name = getattr(var, 'name', None)
            if (var, size) in drawn:
                evaluated[i] = val = drawn[(var, size)]
                            # We filter out Deterministics by checking for `model` attribute
            elif name is not None and hasattr(var, 'model') and name in trace.varnames:
                # param.name is in point
                evaluated[i] = drawn[(var, size)] = trace[name].reshape(-1)
            else:
                # param still needs to be drawn
                symbolic_params.append((i, var))
    return evaluated, symbolic_params

def _ppc_make_graph(symbolic_params: List[Tuple[int, Any]]) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    # Distribution parameters may be nodes which have named node-inputs
    # specified in the point. Need to find the node-inputs, their
    # parents and children to replace them.
    leaf_nodes = {} # type: Dict[str, Any]
    named_nodes_parents = {} # type: Dict[str, Any]
    named_nodes_children = {} # type: Dict[str, Any]
    for _, param in symbolic_params:
        if hasattr(param, 'name'):
            # Get the named nodes under the `param` node
            nn, nnp, nnc = get_named_nodes_and_relations(param)
            leaf_nodes.update(nn)
            # Update the discovered parental relationships
            for k in nnp.keys():
                if k not in named_nodes_parents.keys():
                    named_nodes_parents[k] = nnp[k]
                else:
                    named_nodes_parents[k].update(nnp[k])
            # Update the discovered child relationships
            for k in nnc.keys():
                if k not in named_nodes_children.keys():
                    named_nodes_children[k] = nnc[k]
                else:
                    named_nodes_children[k].update(nnc[k])
    return leaf_nodes, named_nodes_parents, named_nodes_children

def _param_shape(var_desig, model: Model) -> Tuple[int, ...]:
    if isinstance(var_desig, str):
        v = model[var_desig]
    else:
        v = var_desig                                                                          
    if hasattr(v, 'observations'):
        try:
            # To get shape of _observed_ data container `pm.Data`
            # (wrapper for theano.SharedVariable) we evaluate it.
            shape = tuple(v.observations.shape.eval())
        except AttributeError:
            shape = v.observations.shape
    elif hasattr(v, 'dshape'):
        shape = v.dshape
    else:
        shape = v.tag.test_value.shape
    if shape == (1,):
        shape = tuple()
    return shape

def _ppc_draw_value(param, trace: MultiTrace, samples: int, size: Optional[int]=None, givens=None):
    """Draw a random value from a distribution or return a constant.

    Parameters
    ----------
    param : number, array like, theano variable or pymc3 random variable
        The value or distribution. Constants or shared variables
        will be converted to an array and returned. Theano variables
        are evaluated. If `param` is a pymc3 random variables, draw
        a new value from it and return that, unless a value is specified
        in `point`.
    point : dict, optional
        A dictionary from pymc3 variable names to their values.
    givens : dict, optional
        A dictionary from theano variables to their values. These values
        are used to evaluate `param` if it is a theano variable.
    samples : int
        Total number of samples.
    size : int, optional
        Number of samples per point.  Currently not supported.
    """
    assert size is None
    if isinstance(param, (numbers.Number, np.ndarray)):
        return param
    elif isinstance(param, tt.TensorConstant):
        return param.value
    elif isinstance(param, tt.sharedvar.SharedVariable):
        return param.get_value()
    elif isinstance(param, (tt.TensorVariable, MultiObservedRV)):
        if hasattr(param, 'model') and param.name in trace.varnames:
            return trace[param.name]
        elif hasattr(param, 'random') and param.random is not None:
            model = modelcontext(None)                                                                      
            shape = tuple(_param_shape(param, model)) # type: Tuple[int, ...]
            val = np.ndarray((samples, ) + shape)
            for i, point in zip(range(samples), itertools.cycle(trace.points())):
                val[i,:] = x = param.random(point=point)
                assert shape == x.shape
            return val
        elif (hasattr(param, 'distribution') and
                hasattr(param.distribution, 'random') and
                param.distribution.random is not None):
            if hasattr(param, 'observations'):
                # shape inspection for ObservedRV
                dist_tmp = param.distribution
                try:
                    distshape = tuple(param.observations.shape.eval()) # type: Tuple[int, ...]
                except AttributeError:
                    distshape = tuple(param.observations.shape)

                dist_tmp.shape = distshape
                val = np.ndarray((samples, ) + distshape)

                try:
                    for i, point in zip(range(samples), itertools.cycle(trace.points())):
                        x = val[i,:] = dist_tmp.random(point=point, size=size)
                        assert x.shape == distshape
                    return val
                except (ValueError, TypeError):
                    # reset shape to account for shape changes
                    # with theano.shared inputs
                    dist_tmp.shape = np.array([])
                    # We want to draw values to infer the dist_shape,
                    # we don't want to store these drawn values to the context
                    with _DrawValuesContextBlocker():
                        point = next(trace.points())
                        temp_val = np.atleast_1d(dist_tmp.random(point=point,
                                                                size=None))
                    # Sometimes point may change the size of val but not the
                    # distribution's shape
                    if point and size is not None:
                        temp_size = np.atleast_1d(size)
                        if all(temp_val.shape[:len(temp_size)] == temp_size):
                            dist_tmp.shape = temp_val.shape[len(temp_size):]
                        else:
                            dist_tmp.shape = temp_val.shape
                    val = np.ndarray((samples,) + tuple(dist_tmp.shape))
                    for i, point in zip(range(samples), itertools.cycle(trace.points())):
                        x = val[i,:] = dist_tmp.random(point=point, size=size)
                        assert x.shape == tuple(dist_tmp.shape)
                    return val
            else: # has a distribution, but no observations
                distshape = tuple(param.distribution.shape)
                val = np.ndarray((samples, ) + distshape)
                for i, point in zip(range(samples), itertools.cycle(trace.points())):
                    x = val[i, :] = param.distribution.random(point=point, size=size)
                    assert x.shape == distshape
                    return val
        else: # doesn't have a distribution -- deterministic (?) -- this is probably wrong, but
            # the values here will be a list of *sampled* values -- 1 per sample.
            if givens:
                variables, values = list(zip(*givens))
            else:
                variables = values = []
            # We only truly care if the ancestors of param that were given
            # value have the matching dshape and val.shape
            param_ancestors = \
                set(theano.gof.graph.ancestors([param],
                                               blockers=list(variables))
                    )
            inputs = [(var, val) for var, val in
                      zip(variables, values)
                      if var in param_ancestors]
            if inputs:
                input_vars, input_vals = list(zip(*inputs))
            else:
                input_vars = []
                input_vals = []
            func = _compile_theano_function(param, input_vars)
            if not input_vars:
                output = func(*input_vals)
                if hasattr(output, 'shape', None):
                    val = np.ndarray(output * samples)
                else:
                    val = np.full(samples, output)

            else:
                val = np.ndarray([func(*input_vals) for inp in zip(*input_vals)])
            return val
    raise ValueError('Unexpected type in draw_value: %s' % type(param))

