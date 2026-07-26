"""The vectorized fast-path must agree with the per-cell loop, cell for cell."""

import numpy as np

from CAlib import Grid, Rule, life_like


def slow(rule):
    """The same rule with the fast path taken away."""
    return Rule(rule.fn, neighbourhood=rule.neighbourhood, name=rule.name)


def check(spec, boundary, steps=50, size=(40, 40), seed=7):
    rule = life_like(spec)
    fast = Grid(size, fill=0, boundary=boundary).randomise(seed=seed)
    ref = Grid(size, fill=0, boundary=boundary).randomise(seed=seed)
    assert np.array_equal(fast.cells, ref.cells)
    for generation in range(steps):
        fast.cells = fast.step(rule)
        ref.cells = ref.step(slow(rule))
        assert np.array_equal(fast.cells, ref.cells), \
            f'{spec}/{boundary} diverged at generation {generation}'
    assert fast.cells.any(), 'grid died out - test proves nothing'


for boundary in ['periodic', 'fixed', 'reflect', 'edge']:
    check('B3/S23', boundary)
check('B36/S23', 'periodic')   # HighLife

print('ok')
