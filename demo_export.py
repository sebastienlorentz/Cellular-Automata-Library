"""Writing to files instead of opening a window.

Every viewer takes a save path: show(save=...) and spacetime(save=...) write a
still image, save_gif() writes an animation. save_gif needs a step count - an
endless run has no last frame.
"""
from CAlib import Grid, LIFE, elementary

# A still of the starting state.
Grid([40, 40]).randomise(density=0.3, seed=7).show(save='seed.png')

# 60 generations of Life as an animated GIF.
Grid([40, 40]).randomise(0.3, seed=7).save_gif('life.gif', LIFE, steps=60, interval=80)

# A 1D space-time diagram straight to an image.
line = Grid(201)
line.cells[100] = 1
line.spacetime(elementary(30), steps=100, save='rule30.png')

print('wrote seed.png, life.gif, rule30.png')
