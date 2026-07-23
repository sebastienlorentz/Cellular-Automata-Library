"""Wolfram's elementary automata - 1D, drawn as a space-time diagram.

Rule 90 makes a Sierpinski triangle from a single seed cell. Any of the 256
rules works the same way: try 30 for chaos, 110 for the Turing-complete one.
"""
from CAlib import Grid, elementary

# elementary() returns a ready-made Rule, so there's no rule function to write.
line = Grid(129)
line.cells[64] = 1          # one live cell in the middle
line.spacetime(elementary(30), steps=64)

# The same engine animated instead: one row updating live, no history kept, so
# it runs forever. Rule 30 is chaotic, which is what makes a single row worth
# watching - the space-time view above is the one that shows structure.
row = Grid(129)
row.cells[64] = 1
row.animate(elementary(30), interval=80)
