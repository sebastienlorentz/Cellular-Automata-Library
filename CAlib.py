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
#   reflect   mirrors the interior back, so nothing flows out (diffusion in a box)
#   edge      repeats the nearest cell, a zero-gradient wall
BOUNDARIES = {'periodic': 'wrap', 'fixed': 'constant',
              'reflect': 'reflect', 'edge': 'edge'}


class Rule:
    """The transition function together with the settings it needs to run and
    be drawn. Settings left as None fall back to the grid's own."""

    def __init__(self, fn, neighbourhood=None, colours=STATE_COLOURS, name='',
                 needs_index=False, display=None, style=None, vectorized=None):
        self.fn = fn
        # vectorized(cells, padded, offsets, radius) -> the whole next grid, in
        # numpy. Optional: without it step() falls back to the per-cell loop.
        self.vectorized = vectorized
        self.neighbourhood = neighbourhood
        self.colours = colours
        self.name = name
        # display turns a grid of states into the array that actually gets drawn,
        # for automata whose cells carry more than their state (fuel, age, height).
        # style holds the draw settings that go with it (cmap, vmin, vmax, ...).
        self.display = display or (lambda cells: cells)
        self.style = style or {}
        # needs_index=True gets the cell's coordinates as a third argument, for
        # rules that aren't uniform across the grid (terrain, wind, a fixed source).
        self.needs_index = needs_index

    def __call__(self, value, neighbours, index):
        if self.needs_index:
            return self.fn(value, neighbours, index)
        return self.fn(value, neighbours)


def as_rule(rule):
    """Wrap a bare function in a Rule that leaves every setting to the grid."""
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
        # Fixed for the whole run, since an automaton doesn't change what it can see.
        self.neighbourhood = neighbourhood or ('1d' if self.cells.ndim == 1 else 'moore')
        self.history = []

    # A property so every assignment is checked: the constructor, a Rule setting
    # it in step(), or you setting it directly.
    @property
    def neighbourhood(self):
        return self._neighbourhood

    @neighbourhood.setter
    def neighbourhood(self, value):
        # Either a name from NEIGHBOURHOODS, or your own list of offsets:
        # [(-1, 0), (1, 0)] sees only up and down, [(0, -2)] only two to the left.
        if isinstance(value, str):
            if value not in NEIGHBOURHOODS:
                raise ValueError(f'neighbourhood must be one of '
                                 f'{list(NEIGHBOURHOODS)}, or a list of offsets')
        else:
            value = [tuple(offset) for offset in value]
            if any(len(offset) != self.cells.ndim for offset in value):
                raise ValueError(f'offsets need {self.cells.ndim} coordinate(s) '
                                 f'for a {self.cells.ndim}D grid')
        self._neighbourhood = value

    @property
    def offsets(self):
        """The neighbourhood as offsets, whether it was named or given directly."""
        if isinstance(self._neighbourhood, str):
            return NEIGHBOURHOODS[self._neighbourhood]
        return self._neighbourhood

    @property
    def radius(self):
        """How far the furthest offset reaches, which sets the border width."""
        return max(max(abs(c) for c in offset) for offset in self.offsets)

    def randomise(self, density=0.5, states=2, seed=None):
        """Scatter random live cells. density is the fraction that end up
        non-zero, and states=3 gives values 0, 1 and 2. Returns the grid so the
        call can be chained."""
        rng = np.random.default_rng(seed)
        live = rng.random(self.cells.shape) < density
        values = rng.integers(1, states, self.cells.shape)
        self.cells = np.where(live, values, 0).astype(self.cells.dtype)
        return self

    def padded(self):
        """The grid surrounded by a border filled according to the boundary
        setting. The border is as wide as the neighbourhood reaches, which means
        neighbour lookups at any radius need no bounds check."""
        if self.boundary == 'fixed':
            return np.pad(self.cells, self.radius, 'constant',
                          constant_values=self.outside)
        return np.pad(self.cells, self.radius, BOUNDARIES[self.boundary])

    def neighbours(self, index, padded=None):
        """Values around `index`, in the order the offsets are listed in.
        `padded` is passed in by step() so the border is built once per
        generation rather than once per cell."""
        if padded is None:
            padded = self.padded()
        # + radius shifts into the padded frame, where index 0 sits at radius.
        r = self.radius
        return [padded[tuple(i + o + r for i, o in zip(index, offset))]
                for offset in self.offsets]

    def step(self, rule):
        """Compute one generation and return it as a new array. Every cell is
        updated from the same current grid, since CA updates are simultaneous."""
        rule = as_rule(rule)
        if rule.neighbourhood:
            self.neighbourhood = rule.neighbourhood  # the automaton sets what it sees
        cells = self.cells
        padded = self.padded()
        # Hoisted out of the per-cell loop: they're constant for the whole grid,
        # and self.radius recomputes a max over every offset on each lookup.
        r = self.radius
        offsets = self.offsets
        if rule.vectorized:
            # Same padded array, so the boundary means the same thing either way.
            return rule.vectorized(cells, padded, offsets, r)
        # Plain Python loop over every cell, so any rule callback works. On a
        # 500k-cell grid this takes minutes per generation, which is what a
        # rule's `vectorized` is for.
        new = np.empty_like(cells)
        for index in np.ndindex(cells.shape):
            neigh = [padded[tuple(i + o + r for i, o in zip(index, offset))]
                     for offset in offsets]
            new[index] = rule(cells[index], neigh, index)
        return new

    def frames(self, rule, record=False):
        """An endless generator that computes the next generation each time a
        frame is pulled from it, so nothing is simulated ahead of time."""
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

    def _style_for(self, rule, style):
        """A rule's drawing settings, with anything passed to the call winning."""
        return {'cmap': rule.colours, 'title': rule.name, **rule.style, **style}

    def show(self, rule=None, save=None, **style):
        """Draw the grid as it stands, using the rule's colours and display if a
        rule is passed. With save='x.png' the image is written to file instead."""
        cells = self.cells
        if rule is not None:
            rule = as_rule(rule)
            cells = rule.display(cells)
            style = self._style_for(rule, style)
        self._draw(cells, plt.gca(), **style)
        self._finish(save)

    def spacetime(self, rule, steps, save=None, **style):
        """Stack `steps` generations of a 1D automaton into one image, with time
        running down the page. With save='x.png' the image is written to file."""
        rule = as_rule(rule)
        self.history = [self.cells.copy()]
        generations = self.frames(rule, record=True)
        for _ in range(steps):
            next(generations)
        style = self._style_for(rule, style)
        style.setdefault('grid_lines', False)
        rows = np.array([rule.display(cells) for cells in self.history])
        self._draw(rows, plt.gca(), **style)
        self._finish(save)

    @staticmethod
    def _finish(save):
        if save:
            plt.savefig(save, bbox_inches='tight', dpi=150)
            plt.close()
        else:
            plt.show()

    def _mesh_animation(self, rule, generations, interval, style, save_count=None):
        """Build the figure used by animate() and save_gif(), redrawing the mesh
        for each grid in `generations`."""
        style = self._style_for(rule, style)   # explicit style still wins
        fig, ax = plt.subplots()
        mesh = self._draw(rule.display(self.cells), ax, **style)

        def update(cells):
            mesh.set_array(as_2d(rule.display(cells)))
            return [mesh]

        anim = animation.FuncAnimation(
            fig, update, frames=generations, interval=interval, blit=True,
            cache_frame_data=False, save_count=save_count)
        return fig, anim

    def save_gif(self, path, rule, steps, interval=100, generations=None, **style):
        """Write `steps` generations to an animated GIF. The step count is
        needed because an endless stream can't be saved. Pass generations= to
        draw your own stream of grids instead of stepping the rule."""
        rule = as_rule(rule)
        fig, anim = self._mesh_animation(
            rule, islice(generations or self.frames(rule), steps), interval, style,
            save_count=steps)
        anim.save(path, writer=animation.PillowWriter(fps=round(1000 / interval)))
        plt.close(fig)

    def animate(self, rule, record=False, interval=100, generations=None, **style):
        """Show the automaton live, computing a new generation on each redraw
        until the window is closed. record=True also keeps every frame in
        self.history. Pass generations= to draw your own stream of grids
        instead, in which case the rule is used only for drawing and recording
        is left to your loop."""
        rule = as_rule(rule)
        if record:
            self.history = [self.cells.copy()]
        fig, anim = self._mesh_animation(
            rule, generations or self.frames(rule, record), interval, style)
        plt.show()
        return anim  # keep the reference alive or the animation stops


def shifted(padded, offset, radius, shape):
    """Every cell's neighbour at `offset` as one array, made by slicing the
    padded grid back down to `shape`. A rule's `vectorized` sums this over its
    offsets to count neighbours."""
    return padded[tuple(slice(radius + o, radius + o + n)
                        for o, n in zip(offset, shape))]


def as_2d(cells):
    return cells.reshape(1, -1) if cells.ndim == 1 else cells


def life_like(spec='B3/S23', name=None):
    """A 2D Moore automaton from birth/survival notation. In 'B3/S23', which
    is Conway's Life, a dead cell with 3 live neighbours is born and a live one
    with 2 or 3 survives. 'B36/S23' is HighLife and 'B2/S' is Seeds."""
    born, survive = spec.upper().lstrip('B').split('/S')
    born = {int(n) for n in born}
    survive = {int(n) for n in survive}

    def rule(value, neighbours):
        alive = sum(neighbours)
        return 1 if alive in (survive if value else born) else 0

    def vectorized(cells, padded, offsets, radius):
        alive = sum(shifted(padded, offset, radius, cells.shape)
                    for offset in offsets)
        rules = np.where(cells != 0, np.isin(alive, list(survive)),
                         np.isin(alive, list(born)))
        return rules.astype(cells.dtype)

    return Rule(rule, neighbourhood='moore', colours=['white', 'black'],
                name=name or spec, vectorized=vectorized)


LIFE = life_like('B3/S23', name="Conway's Life")


def elementary(number):
    """One of Wolfram's 256 elementary 1D automata, e.g. elementary(90)."""
    def rule(value, neighbours):
        left, right = neighbours          # '1d' offsets are (-1,), (1,)
        return (number >> int(left * 4 + value * 2 + right)) & 1
    return Rule(rule, neighbourhood='1d', colours=['white', 'black'],
                name=f'Rule {number}')
