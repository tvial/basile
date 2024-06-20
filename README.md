# Basile

A lightweight, brute-force framework for discrete code-based experimentations.

Sometimes, one wants to run an algorithm, a model, a simulation, ... with several combinations of
parameters, in order to get insights on its behaviour. Or to find such a combination that maximizes
some key figure. In many such cases, trial and error is time-consuming. Without tooling assistance,
one often loses track of which combinations were tested, and what is the next parameter to tune up or
down for the next scenario.

**Basile** is a such a tool. It doesn't do much but it's very light and simple to use. Also, it does
not depend on a particular framework (e.g. Scikit-Learn's grid search), it is pure Python with no library
dependency. It can be used in almost any situation where combinations of discrete parameters must be explored
in a systematic way.

There are two important words in the above sentence:
- _discrete_: each parameter may take a finite number of values, Basile will not sample from
  continuous intervals. If needed, invervals may can be discretized in any fashion, but it's your job
- _systematic_ (with _combinations_): Basile is not an optimizer, in that it won't guess the next
  most promising combination based in the outcome of the previous one. Nor does it pick values at random:
  it will try every single combination, predictably

## Example

The package can be installed with `pip`:
```
pip install basile
```

Here is a showcase of the possibilities:

```python
from dataclasses import dataclass
from basile import Either, count_realizations, realize_template

@dataclass
class Level2:
    field1: str

@dataclass
class Level1:
    field1: int
    field2: list
    field3: Level2

template = Level1(
    field1=1,
    field2=Either([2, 3, 4], [4, 5, 6]),
    field3=Level2(field1=Either('abc', 'def', 'ghi'))
)

n = count_realizations(template)
for i, concrete in enumerate(realize_template(template), 1):
    print(f'{i}/{n}', concrete)
```

The two classes `Level1` and `Level2` are representations of our parameters. We see that `Level1` has a field with type `Level2`,
showing that our substitutions can happen in many places, including down in an object hierarchy.

Then we define a _template_. It is a plain object (`Level1` here), only with instances of `Either` objects here and there
where we want our substitutions to take place. The template could as well be a list, a tuple or a dictionary, it does not matter,
and in particular there is no `Template` type imposing constraints on the code expecting parameters.

The candidate values inside the `Either(...)` objects can be anything; the only limitation is that nested candidates are not
supported (`Either(1, 2, Either(4, 5)))` is not ok and would not make much sense anyway).

Then we count the number of possible realizations and put it in a variable, to display it in the loop below.

Last comes the loop, where we iterate over the combinations of parameters with the `realize_template()` function. The latter
will substitute parameter values in a deep copy of the template, yielding a fully baked object, `concrete` (the deep copy
operation is performed at each iteration).

The `concrete` object is of type `TemplateRealization`. It has two attributes
- `specification`, which holds a dictionary of substitutions (say, for logging purposes)
  - keys are access paths to each candidate in the template (see concepts below for more explanations)
  - values are the actual substitutions
- `realization`, which holds an object with the same structure as the template, with no more `Either`s in it. This is the
  item we would use in the core of our application

Note that Basile only works with iterators, it never materializes combinations in lists or other memory demanding
structures. This makes it suitable for scenarios with high cardinalities leading to combinatorial explosion. Process time
would certainly be a concern at this point, but not memory.

## Recipes

As mentioned above, Basile does little in itself, and it's quite dumb. Here are some recipes for more elaborate needs.

### When parameters are interdependent

Often, not all combinations of parameters are admissible. For example, in our toy scenario above, `field2 = [2, 3, 4]`
could be valid only for `field3.field1 in ('abc', 'def')`, and `field2 = [4, 5, 6]` for `field3.field1 in ('def', 'ghi')`.
However Basile will happily generate a cross product of all candidates, including the invalid combinations.

In such a case, we would inspect the concrete parameters (`concrete.realization`), and skip loop iterations when a
certain business rule is not satisfied. Or, better, apply Python's built-in `filter()` function to the result of
`realize_template()` using a predicate.

### Checkpointing and idempotence

When the number of combinations is large, and when each iteration takes time to complete, one might not want to restart
the loop from scratch if the program was interrupted in the middle. Basile is 100% deterministic so it's easy to
exploit that.

There are many ways to record what combinations were worked out already; here is a hacky yet simple one:
- convert `concrete.specification` (a dictionary) into a sorted tuple of tuples
  - it will be used to look up a set, so it must be fully hashable
- append it to a file, in any suitable format, after the processing of `concrete.realization` is complete (this is like
  committing the iteration)
- when starting the program, load the file into a set of specifications, and use it to look up the specifications that
  must be skipped from the loop

Even if the template is altered between executions, with new combinations added or their order changed, there will be
no duplicate execution of a given combination. It won't work though if a new occurrence of `Either` is added to the
template, because all specifications will have a new entry, in comparison to the "old" ones loaded at program
initialization.

Of course, if the processing logic changes, it makes sense to start it over again, by deleting the tracking file.

### Using resources as values

E.g. if candidate values are open files, or database connections... There is no provision, in the API, to dispose of
a template realization when the calling program is done with processing it. If it contains values that must be
closed or released in order to preserve resources on the machine, you have to do it yourself explicitly. Note that
because of the combinatorial nature of the work, each resource will typically be seen by many scenarii, and may not
be closed until all iterations are complete.

## Concepts

While the API itself is simple, the inner workings are more complex and can use a bit of explaining. Here is a
description of all the concepts used in ExpBasileyriment.

### Candidates

Candidates are possible values for a parameter, an argument... of your program. They are specified using the
`Either` object as a placeholder for final values. Those values can be anything, except that they cannot
hold other `Either` objects directly or indirectly (no candidates nesting). This is not enforced, but your
processing logic would receive `Either` object that it may not be able to handle.

In the toy example above, there are 2 candidates, one with 2 values (lists) and one with 3 values (strings).

### Template

A template is an object which can be made variable, by substituting values inside it via candidates. In code, the
only thing that makes it a template is the use of `Either` instances somewhere down its hierarchy. Apart from
that, the template can be structured in any possible way, with the following caveats:
- when walking the template object to find candidates, Basile will only recurse inside dataclass instances,
  lists, tuples and dictionaries (any other types will be left untouched)
- there is no cycle detection to prevent it from going into an infinite loop if there are inter-references between
  child objects and/or subcollections

### Access path

When walking the template looking for candidates, Basile keeps track of where it is down the hierarchy. This is
materialized by an access path, which is a list of `CandidateAccess` access objects holding:
- `access_type`: the access mode of the containing element -- dataclass, list, tuple or dict
- `position`: the position of the current item in its container (attribute name for a containing dataclass, index for
  a list or tuple, key for a dictionary)

In the example above, the access paths of the candidates can be represented as:
- `'field2'` for the first one
- '`field3.field1'` for the second one

If candidates were in a list, say `field4=[Either(10, 11, 12), Either(13, 14, 15)]`, there would be 2 access
paths: `'field4.0'` and `'field4.1'`. It would be the same for a tuple.

Conversely, if candidates were in a dictionary, say `field5={'a': Either(20, 21), 'b': Either(22, 23)}`, the
access paths would be: `'field5.a'` and `'field5.b'`.

For candidates buried deeper in the hierarchy, there would be more elements in the dot-separated chains. The representations
above with dots are for human readability, they are not involved in Basile's processing logic. However, they will
appear in the `specification` field of realizations, as dictionary keys. So using dictionary keys with dots should not
break anything.

### Binding

When a placeholder is found, its possible values are associated with the access path of the `Either` object
representing it. This association is called a binding. Conceptually, thus, a template can be considered as a list
of bindings, plus all the leftover bits that are not candidates (not made variable).

### Binding realization

When iterating over the combinations, a binding is given each possible value from its `Either` part, in turn. This
is a binding realization.

### Template realization

When all bindings in a template are combined together, they make up its template realization. Practically,
`TemplateRealization` objects also contain a specification, recalling what parameter values were substituted and how.

## License

MIT License (see the `LICENSE` file).