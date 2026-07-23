from itertools import islice

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import animation
from matplotlib.colors import ListedColormap

# State 0 is white (empty), 1-10 are matplotlib's tab10 cycle.
STATE_COLOURS = ['white'] + list(plt.get_cmap('tab10').colors)

# A neighbourhood is just the set of offsets a rule gets to look at.
NEIGHBOURHOODS = {
    '1d': [(-1,), (1,)],
    'moore': [(-1, -1), (-1, 0), (-1, 1),
              (0, -1), (0, 1),
              (1, -1), (1, 0), (1, 1)],
    'von_neumann': [(-1, 0), (0, -1), (0, 1), (1, 0)],
}

# Edge behaviour, as numpy's padding modes:
#   periodic  wraps around, the usual CA torus
#   fixed     surrounded by a constant (`outside`), so patterns die at the wall
#   reflect   mirrors the interior back - no flux, e.g. diffusion in a box
#   edge      repeats the nearest cell, a zero-gradient wall
BOUNDARIES = {'periodic': 'wrap', 'fixed': 'constant',
              'reflect': 'reflect', 'edge': 'edge'}


class Rule:
    """An automaton: the transition function plus what it needs to run and to
    be drawn. Anything left as None falls back to the grid's own setting."""

    def __init__(self, fn, neighbourhood=None, colours=STATE_COLOURS, name='',
                 needs_index=False):
        self.fn = fn
        self.neighbourhood = neighbourhood
        self.colours = colours
        self.name = name
        # needs_index=True gets the cell's coordinates as a third argument, for
        # rules that aren't uniform across the grid (terrain, wind, a fixed source).
        self.needs_index = needs_index

    def __call__(self, value, neighbours, index):
        if self.needs_index:
            return self.fn(value, neighbours, index)
        return self.fn(value, neighbours)


def as_rule(rule):
    """A bare function is a Rule with everything left to the grid."""
    return rule if isinstance(rule, Rule) else Rule(rule)


class Grid:
    def __init__(self, size, fill=0.0, boundary='periodic', outside=0, neighbourhood=None):
        # fill is a float by default so continuous automata (diffusion, heat)
        # aren't silently truncated to whole numbers. Pass fill=0 for an int grid.
        if isinstance(size, int):
            size = [size]
        self.cells = np.full(tuple(size), fill)
        if self.cells.ndim > 2:
            raise ValueError(f'1D or 2D grids only, got {self.cells.shape}')
        if boundary not in BOUNDARIES:
            raise ValueError(f'boundary must be one of {list(BOUNDARIES)}')
        self.boundary = boundary          # one of BOUNDARIES
        self.outside = outside            # the constant, when boundary='fixed'
        # Fixed for the whole run - an automaton doesn't change what it can see.
        self.neighbourhood = neighbourhood or ('1d' if self.cells.ndim == 1 else 'moore')
        self.history = []

    # A property so every assignment is checked: the constructor, a Rule setting
    # it in step(), or you setting it directly.
    @property
    def neighbourhood(self):
        return self._neighbourhood

    @neighbourhood.setter
    def neighbourhood(self, name):
        if name not in NEIGHBOURHOODS:
            raise ValueError(f'neighbourhood must be one of {list(NEIGHBOURHOODS)}')
        self._neighbourhood = name

    def randomise(self, density=0.5, states=2, seed=None):
        """Scatter random live cells. density is the fraction that end up
        non-zero; states=3 means values 0, 1 and 2. Returns self, so it chains."""
        rng = np.random.default_rng(seed)
        live = rng.random(self.cells.shape) < density
        values = rng.integers(1, states, self.cells.shape)
        self.cells = np.where(live, values, 0).astype(self.cells.dtype)
        return self

    def padded(self):
        """The grid inside a one-cell border holding whatever the boundary
        implies, so neighbour lookups never need a bounds check."""
        if self.boundary == 'fixed':
            return np.pad(self.cells, 1, 'constant', constant_values=self.outside)
        return np.pad(self.cells, 1, BOUNDARIES[self.boundary])

    def neighbours(self, index, padded=None):
        """Values around `index`, in the offset order listed in NEIGHBOURHOODS.
        `padded` is passed in by step() so the border is built once per
        generation rather than once per cell."""
        if padded is None:
            padded = self.padded()
        # +1 shifts into the padded frame, where index (0, 0) sits at (1, 1).
        return [padded[tuple(i + o + 1 for i, o in zip(index, offset))]
                for offset in NEIGHBOURHOODS[self.neighbourhood]]

    def step(self, rule):
        """One generation. Reads the current grid and returns a fresh array, so
        every cell updates off the same state (CA updates are simultaneous)."""
        # ponytail: plain Python loop over every cell, so any rule callback works.
        # Vectorise with np.roll per offset if a big grid gets slow.
        rule = as_rule(rule)
        if rule.neighbourhood:
            self.neighbourhood = rule.neighbourhood  # the automaton sets what it sees
        new = np.empty_like(self.cells)
        padded = self.padded()
        for index in np.ndindex(self.cells.shape):
            new[index] = rule(self.cells[index], self.neighbours(index, padded), index)
        return new

    def frames(self, rule, record=False):
        """Endless generator of grids. Nothing is simulated ahead of time - one
        generation is computed per frame pulled."""
        rule = as_rule(rule)
        while True:
            self.cells = self.step(rule)
            if record:
                self.history.append(self.cells.copy())
            yield self.cells

    # --- rendering: reads arrays, never touches the step loop ---------------

    def _draw(self, cells, ax, cmap=STATE_COLOURS, grid_lines=True, line_width=1,
              title='', vmin=None, vmax=None):
        # vmin/vmax pin the value range. Continuous automata need them, or every
        # frame rescales to its own min and max and nothing appears to change.
        if isinstance(cmap, list):
            # cell value is an index into the colour list, not a scaled value
            if vmin is None:
                vmin = 0
            if vmax is None:
                vmax = len(cmap) - 1
            cmap = ListedColormap(cmap)
        mesh = ax.pcolormesh(as_2d(cells), cmap=cmap, vmin=vmin, vmax=vmax,
                             edgecolor='black', linewidth=line_width if grid_lines else 0)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.invert_yaxis()   # row 0 on top, so time runs down a space-time plot
        ax.set_title(title)
        return mesh

    def show(self, save=None, **style):
        """Draw the grid as it stands. save='x.png' writes it instead."""
        self._draw(self.cells, plt.gca(), **style)
        self._finish(save)

    def spacetime(self, rule, steps, save=None, **style):
        """The usual way to view a 1D automaton: every generation stacked into
        one image, time running down the page. save='x.png' writes it."""
        rule = as_rule(rule)
        self.history = [self.cells.copy()]
        generations = self.frames(rule, record=True)
        for _ in range(steps):
            next(generations)
        style.setdefault('cmap', rule.colours)
        style.setdefault('title', rule.name)
        style.setdefault('grid_lines', False)
        self._draw(np.array(self.history), plt.gca(), **style)
        self._finish(save)

    @staticmethod
    def _finish(save):
        if save:
            plt.savefig(save, bbox_inches='tight', dpi=150)
            plt.close()
        else:
            plt.show()

    def _mesh_animation(self, rule, generations, interval, style, save_count=None):
        """Shared by animate() and save_gif(): a figure whose mesh redraws from
        whatever stream of grids it's handed."""
        style.setdefault('cmap', rule.colours)   # explicit style still wins
        style.setdefault('title', rule.name)
        fig, ax = plt.subplots()
        mesh = self._draw(self.cells, ax, **style)

        def update(cells):
            mesh.set_array(as_2d(cells))
            return [mesh]

        anim = animation.FuncAnimation(
            fig, update, frames=generations, interval=interval, blit=True,
            cache_frame_data=False, save_count=save_count)
        return fig, anim

    def save_gif(self, path, rule, steps, interval=100, **style):
        """Write `steps` generations to an animated GIF. Needs a step count -
        an endless stream can't be saved."""
        rule = as_rule(rule)
        fig, anim = self._mesh_animation(
            rule, islice(self.frames(rule), steps), interval, style, save_count=steps)
        anim.save(path, writer=animation.PillowWriter(fps=round(1000 / interval)))
        plt.close(fig)

    def animate(self, rule, record=False, interval=100, **style):
        """Live view - each redraw computes the next generation, so it runs
        endlessly. record=True also keeps every frame in self.history."""
        rule = as_rule(rule)
        if record:
            self.history = [self.cells.copy()]
        fig, anim = self._mesh_animation(
            rule, self.frames(rule, record), interval, style)
        plt.show()
        return anim  # keep the reference alive or the animation stops


def as_2d(cells):
    return cells.reshape(1, -1) if cells.ndim == 1 else cells


def life_like(spec='B3/S23', name=None):
    """A 2D Moore automaton in birth/survival notation. 'B3/S23' is Conway's
    Life: a dead cell with 3 live neighbours is born, a live one with 2 or 3
    survives. 'B36/S23' is HighLife, 'B2/S' is Seeds."""
    born, survive = spec.upper().lstrip('B').split('/S')
    born = {int(n) for n in born}
    survive = {int(n) for n in survive}

    def rule(value, neighbours):
        alive = sum(neighbours)
        return 1 if alive in (survive if value else born) else 0

    return Rule(rule, neighbourhood='moore', colours=['white', 'black'],
                name=name or spec)


LIFE = life_like('B3/S23', name="Conway's Life")


def elementary(number):
    """One of Wolfram's 256 elementary 1D automata, e.g. elementary(90)."""
    def rule(value, neighbours):
        left, right = neighbours          # '1d' offsets are (-1,), (1,)
        return (number >> int(left * 4 + value * 2 + right)) & 1
    return Rule(rule, neighbourhood='1d', colours=['white', 'black'],
                name=f'Rule {number}')
