"""Conway's Game of Life - a 2D automaton on a Moore neighbourhood.

Two ways to the same automaton: write the rule yourself, or take the built-in.
life_like() covers the whole birth/survival family, so 'B36/S23' is HighLife
and 'B2/S' is Seeds.
"""
from CAlib import Grid, Rule, LIFE, life_like

# 1. A rule is a function of a cell's value and its neighbours' values.
def life(value, neighbours):
    alive = sum(neighbours)
    return 1 if (alive == 3 or (value and alive == 2)) else 0

# 2. Wrap it up with what it needs to run and to be drawn.
MY_LIFE = Rule(life, neighbourhood='moore', colours=['white', 'black'],
               name="Conway's Life (hand-written)")

# 3. Make a grid, scatter live cells at random, run it. Animates until closed.
world = Grid([60, 60]).randomise(density=0.3, seed=0)
world.animate(MY_LIFE, interval=50)

# The built-in is the same automaton under one name.
Grid([60, 60]).randomise(0.3, seed=0).animate(LIFE, interval=50)

# Same engine, another member of the family.
Grid([60, 60]).randomise(0.3, seed=0).animate(life_like('B36/S23', name='HighLife'))
