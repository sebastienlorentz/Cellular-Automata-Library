"""Conditional colouring: let the rule decide how each cell is drawn.

A cell's value isn't always the whole story. Here Life leaves cooling embers,
so a cell is one of three things:

    0            empty
    1            alive
    2, 3, 4...   an ember, fading as the number climbs

`colours` can't draw that - it maps one value to one colour, but we want alive
cells flat and embers shaded by how cold they are. So the rule carries a
`display` function (state grid -> the array actually drawn) and the `style` to
draw its output with. The automaton still steps over states; display only runs
on the way to the screen, so g.cells keeps the real values.
"""
import numpy as np

from CAlib import Grid, Rule

FADE = 6   # embers cool over this many steps, then vanish

def ember_life(value, neighbours):
    alive = sum(1 for n in neighbours if n == 1)
    if value == 1:
        return 1 if alive in (2, 3) else 2    # survive, else start cooling
    if value >= 2:
        return value + 1 if value < 1 + FADE else 0   # cool, then go out
    return 1 if alive == 3 else 0             # birth on an empty cell

def shade(cells):
    out = np.zeros(cells.shape)               # empty -> 0, black
    out[cells == 1] = 1.0                     # alive -> flat, full brightness
    ember = cells >= 2
    out[ember] = 0.55 - 0.06 * (cells[ember] - 2)   # embers fade as they cool
    return out

FIRE = Rule(ember_life, neighbourhood='moore', name='Life, with embers',
            display=shade,
            style=dict(cmap='inferno', vmin=0, vmax=1, grid_lines=False))

world = Grid([60, 60], fill=0).randomise(density=0.3, seed=0)
world.animate(FIRE, interval=80)
