"""A continuous automaton: heat spreading through an insulated box.

Cells hold floats rather than states, which is why Grid fills with 0.0 by
default - an int grid would truncate every average to zero. Two other pieces
matter here: 'reflect' makes the walls insulating (no heat leaves), and
vmin/vmax pin the colour scale, or each frame rescales to its own range and
the heat never appears to fade.
"""
from CAlib import Grid, Rule

def diffuse(value, neighbours):
    return (value + sum(neighbours)) / (len(neighbours) + 1)

HEAT = Rule(diffuse, neighbourhood='von_neumann', colours='inferno',
            name='Heat diffusion')

box = Grid([50, 50], boundary='reflect')
box.cells[20:30, 20:30] = 1.0        # a hot square in the middle

box.animate(HEAT, interval=50, vmin=0, vmax=1, grid_lines=False)
