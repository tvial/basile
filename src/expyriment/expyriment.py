# Copyright (c) 2024 Thomas VIAL

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from dataclasses import dataclass, fields, is_dataclass
from itertools import product
from copy import deepcopy
from typing import List, Any, Iterable, Dict


class CandidateAccessType:
    """How to access a candidate"""

    #: Candidate is a dataclass attribute
    DATACLASS_ATTR = 1

    #: Candidate is a list item
    LIST_ITEM = 2

    #: Candidate is a tuple item
    TUPLE_ITEM = 3

    #: Candidate is a dict value
    DICT_VALUE = 4


@dataclass
class CandidateAccess:
    """How & where to access a candidate directly placed in a container"""

    #: How
    access_type: CandidateAccessType

    #: Where (the type depends on the container type)
    position: Any


@dataclass(init=False)
class Candidates:
    """Placeholder for candidate values in templates"""
    values: List[Any]

    def __init__(self, *values):
        """Create a list of candidates

        Parameters
        ----------
        *values
            List of possible values for the candidate
        """
        self.values = values


def _getter(container: Any, access: CandidateAccess) -> Any:
    """Generic getter working across all candidate access types

    Parameters
    ----------
    container
        The containing element
    access : CandidateAccess
        What to access
    
    Returns
    -------
    Any
        The value of the item in the container (roughly `container[access.position]`)
    """
    if access.access_type == CandidateAccessType.DATACLASS_ATTR:
        return getattr(container, access.position)
    else:
        return container[access.position]


def _setter(container: Any, access: CandidateAccess, value: Any, parent: Any, parent_access: CandidateAccess) -> None:
    """Generic setter working across all candidate access types.
    The value is updated in-place, except when `container` is a tuple, in which case a new tuple
    is created.

    Parameters
    ----------
    container
        The containing element
    access : CandidateAccess
        What to set
    value
        The new value for the item
    parent
        When `container` is a tuple, `parent` is its own container, so the reference can be updated
    parent_access : CandidateAccess
        When `container` is a tuple, `parent_access` is the access to it from its parent
    """
    if access.access_type == CandidateAccessType.DATACLASS_ATTR:
        setattr(container, access.position, value)
    elif access.access_type == CandidateAccessType.TUPLE_ITEM:
        # Work around tuple immutability by building a new one
        new_tuple = tuple([
            value if i == access.position else previous_value
            for i, previous_value in enumerate(container)
        ])
        # Candidates are not supposed to be nested so we can assume there is no upstream ancestor to handle.
        # Hence `parent` == `parent_item` == `None` in this call
        _setter(parent, parent_access, new_tuple, None, None)
    else:
        container[access.position] = value


@dataclass
class BindingRealization:
    """Realization of a binding, i.e. an access path associated with a single value from candidates
    """

    #: Access path to the bound element
    path: List[CandidateAccess]

    #: The value to set the element with
    value: Any

    def apply(self, container: Any) -> None:
        """Apply the value to the element in `container` whose access path is `path`

        Parameters
        ----------
        container
            The container to update with this particular realization
        """
        parent, parent_item = None, None

        # Walk to the value whose item we want to modify
        for item in self.path[:-1]:
            # The parent is needed if `container` is a tuple
            parent, parent_item = container, item
            container = _getter(container, item)

        # Apply
        _setter(container, self.path[-1], self.value, parent, parent_item)

    def get_specification(self) -> Dict[str, Any]:
        """A machine/human readable representation of the binding, for documentation purposes

        Returns
        -------
        Dict[str, Any]
            A dictionary whose keys are dotted represenation of the access path, and values the bound values
        """
        return {'.'.join(map(lambda item: str(item.position), self.path)): self.value}


@dataclass
class Binding:
    """A binding associates an access path with a list of candidate values given by a `Candidates` object
    """

    #: Access path to the element to bind to
    path: List[CandidateAccess]

    #: List of possible values
    values: List[Any]

    def realize(self) -> Iterable[BindingRealization]:
        """Turn the binding into an iterator of `BindingRealization`
        
        Returns
        -------
        Iterable[BindingRealization]
            Iteration over realizations of this binding
        """
        return (BindingRealization(self.path, value) for value in self.values)


@dataclass
class TemplateRealization:
    """Realization of a full template
    """

    #: The aggregation of the specification of the binding realizations associated with the template
    specification: Dict[str, Any]

    #: The templates with all candidates replaced with values
    realization: Any


def _get_bindings(path: List[CandidateAccess], container: Any) -> Iterable[Binding]:
    """Recursively walks `container` and iterate over the candidates therein to yield bindings

    Parameters
    ----------
    path : List[CandidateAccess]
        The path to `container` in its parent hierarchy
    container
        The container to get bindings from

    Returns
    -------
    Iterable[Binding]
        Bindings made from candidate values found under `container`
    """
    if isinstance(container, Candidates):
        # If we encounter a Candidate, stop recursion, otherwise go deeper
        yield Binding(path, container.values)
    elif is_dataclass(container):
        yield from _get_bindings_from_class(path, container)
    elif isinstance(container, list):
        yield from _get_bindings_from_list(path, container)
    elif isinstance(container, tuple):
        yield from _get_bindings_from_tuple(path, container)
    elif isinstance(container, dict):
        yield from _get_bindings_from_dict(path, container)


def _get_bindings_from_class(path: List[CandidateAccess], container: dataclass) -> Iterable[Binding]:
    """Recursively walks dataclass `container`

    Parameters
    ----------
    path : List[CandidateAccess]
        The path to `container` in its parent hierarchy
    container : dataclass
        The dataclass to get bindings from

    Returns
    -------
    Iterable[Binding]
        Bindings made from candidate values found under `container`
    """
    for field in fields(container):
        yield from _get_bindings(
            path + [CandidateAccess(access_type=CandidateAccessType.DATACLASS_ATTR, position=field.name)],
            getattr(container, field.name)
        )


def _get_bindings_from_list(path: List[CandidateAccess], container: list) -> Iterable[Binding]:
    """Recursively walks list `container`

    Parameters
    ----------
    path : List[CandidateAccess]
        The path to `container` in its parent hierarchy
    container : list
        The list to get bindings from

    Returns
    -------
    Iterable[Binding]
        Bindings made from candidate values found under `container`
    """
    for i, value in enumerate(container):
        yield from _get_bindings(
            path + [CandidateAccess(access_type=CandidateAccessType.LIST_ITEM, position=i)],
            value
        )


def _get_bindings_from_tuple(path: List[CandidateAccess], container: tuple) -> Iterable[Binding]:
    """Recursively walks tuple `container`

    Parameters
    ----------
    path : List[CandidateAccess]
        The path to `container` in its parent hierarchy
    container : tuple
        The tuple to get bindings from

    Returns
    -------
    Iterable[Binding]
        Bindings made from candidate values found under `container`
    """
    for i, value in enumerate(container):
        yield from _get_bindings(
            path + [CandidateAccess(access_type=CandidateAccessType.TUPLE_ITEM, position=i)],
            value
        )


def _get_bindings_from_dict(path: List[CandidateAccess], container: dict) -> Iterable[Binding]:
    """Recursively walks dictionary `container`

    Parameters
    ----------
    path : List[CandidateAccess]
        The path to `container` in its parent hierarchy
    container : dict
        The dictionary to get bindings from

    Returns
    -------
    Iterable[Binding]
        Bindings made from candidate values found under `container`
    """
    for key, value in container.items():
        yield from _get_bindings(
            path + [CandidateAccess(access_type=CandidateAccessType.DICT_VALUE, position=key)],
            value
        )


def _realize(template: Any, binding_realizations: Iterable[BindingRealization]) -> TemplateRealization:
    """Apply a collection of binding realizations to a template

    Parameters
    ----------
    template
        Template with `Candidates` inside
    binding_realizations : Iterable[BindingRealization]
        Binding realizations to apply to the template

    Returns
    -------
    TemplateRealization
        The result of applying the binding realizations to the template
    """
    real = deepcopy(template)
    specification = {}
    for binding_realization in binding_realizations:
        specification.update(binding_realization.get_specification())
        binding_realization.apply(real)
    return TemplateRealization(specification=specification, realization=real)


def _get_all_binding_realizations(template: Any) -> Iterable[BindingRealization]:
    """Build an iterable for all combinations of candidate values found inside the given template

    Parameters
    ----------
    template
        The containing template with candidates buried at any depth

    Returns
    -------
    Iterable[Any]
        An iterable yielding all possible concrete combinations of candidates
    """
    bindings = _get_bindings([], template)
    return product(*(
        binding.realize()
        for binding in bindings
    ))


def count_realizations(template: Any) -> int:
    """Counts the number of template realizations.
    This can be used for e.g. progress reporting when iterating over a large number of combinations.

    Parameters
    ----------
    template
        The containing template with candidates buried at any depth

    Returns
    -------
    int
        The number of combinations
    """
    count = 1
    for binding in _get_bindings([], template):
        count *= len(binding.values)
    return count


def realize_template(template):
    for binding_realizations in _get_all_binding_realizations(template):
        yield _realize(template, binding_realizations)
