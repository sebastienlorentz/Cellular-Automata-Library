"""Rules that need more than a cell and its neighbours.

Two cases the plain rule signature doesn't cover on its own:
  - a rule with settings, or with random state       -> use a closure
  - a rule that depends on where the cell is         -> needs_index=True
"""
import numpy as np

from CAlib import Grid, Rule

# --- a closure: settings and an RNG captured at definition ------------------
# rule() only ever takes (value, neighbours), so p_flip can't be passed in at
# call time. It's captured instead. rng is created once and shared by every
# call, which is what keeps this one random stream rather than one per cell.
def noisy_life(p_flip=0.001, seed=None):
    rng = np.random.default_rng(seed)

    def rule(value, neighbours):
        if rng.random() < p_flip:
            return 1 - value          # a cell occasionally flips at random
        alive = sum(neighbours)
        return 1 if (alive == 3 or (value and alive == 2)) else 0

    return Rule(rule, neighbourhood='moore', colours=['white', 'black'],
                name=f'Life, {p_flip} noise')


# Each call is a separate automaton with its own settings baked in. Noise stops
# Life ever settling down - the still lifes keep getting knocked over.
world = Grid([60, 60]).randomise(density=0.3, seed=0)
world.animate(noisy_life(p_flip=0.002, seed=1), interval=50)


# --- needs_index: a rule that isn't the same everywhere ---------------------
# Heat spreading from a wall that's permanently hot. The rule has to know which
# cell it's looking at to hold the top row fixed, so it takes a third argument
# and declares needs_index=True.
def heated_wall(value, neighbours, index):
    row, col = index
    if row == 0:
        return 1.0                    # the wall never cools
    return (value + sum(neighbours)) / (len(neighbours) + 1)


WALL = Rule(heated_wall, neighbourhood='von_neumann', colours='inferno',
            name='Heat from a fixed wall', needs_index=True)

room = Grid([40, 40], boundary='edge')
room.animate(WALL, interval=50, vmin=0, vmax=1, grid_lines=False)
