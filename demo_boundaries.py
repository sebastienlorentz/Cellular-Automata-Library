"""Edge behaviour: the same automaton, the same seed, four different walls.

periodic  wraps around, so a glider leaving the right edge returns on the left
fixed     a constant border (`outside`), so patterns decay at the wall
reflect   mirrors the interior back - no flux, for diffusion in a closed box
edge      repeats the nearest cell, a zero-gradient wall
"""
from CAlib import Grid, LIFE

SEED = Grid([30, 30]).randomise(density=0.35, seed=4).cells

for boundary in ['periodic', 'fixed', 'reflect', 'edge']:
    world = Grid([30, 30], boundary=boundary)
    world.cells = SEED.copy()
    for _ in range(40):
        world.cells = world.step(LIFE)
    world.show(title=f'Life after 40 generations: {boundary}',
               cmap=['white', 'black'], grid_lines=True)

# A live border instead of a dead one. outside only applies to boundary='fixed';
# the other three take their border from the grid itself.
world = Grid([30, 30], boundary='fixed', outside=1)
world.cells = SEED.copy()
world.animate(LIFE, interval=80)
