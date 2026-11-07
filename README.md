# CAlibrary

A cellular automata engine for 1D and 2D grids. You write the rule, and the
library handles neighbourhoods, edges, stepping and drawing.

```python
from CAlib import Grid, LIFE

Grid([60, 60]).randomise(density=0.3).animate(LIFE)
```

## Getting started

It needs Python 3.9 or later, with numpy and matplotlib:

```
pip install numpy matplotlib
```

The library itself is the single file `CAlib.py`. Put it next to your script
and import from it.

To check everything works, run one of the demos:

```
python demo_2d.py
```

A window opens and animates until you close it. Each demo runs several examples
in turn, and closing one window brings up the next.

The shortest thing you can write yourself is:

```python
from CAlib import Grid, LIFE

Grid([40, 40]).randomise(density=0.3).animate(LIFE)
```

## The idea

A rule is a function of a cell's value and its neighbours' values:

```python
def life(value, neighbours):
    alive = sum(neighbours)
    return 1 if (alive == 3 or (value and alive == 2)) else 0
```

This function is the part that changes from one automaton to the next. Finding
neighbours, handling the edges, advancing generations and drawing the result are
the same for all of them, and the library does those.

You can pass a bare function and the grid fills in everything else (internally
`as_rule()` wraps it in a default `Rule` and the engine only ever handles that
one type). If you wrap it in a `Rule` yourself, the automaton can carry its own
settings:

```python
from CAlib import Rule

LIFE = Rule(life, neighbourhood='moore', colours=['white', 'black'],
            name="Conway's Life")
```

The grid then takes its neighbourhood, palette and title from the rule.

### Rule arguments

```python
Rule(fn, neighbourhood=None, colours=STATE_COLOURS, name='', needs_index=False,
     display=None, style=None, vectorized=None)
```

| Argument | Meaning |
|---|---|
| `fn` | The transition function. It takes `(value, neighbours)` and returns the cell's next value. |
| `neighbourhood` | Which cells the rule looks at: `'1d'`, `'moore'` or `'von_neumann'`. If left as `None` the grid's own setting is used. If set, it overrides the grid, so Life is Moore wherever you run it. |
| `colours` | How to draw the states, as a list of colours or the name of a matplotlib colormap. See [Colours](#colours). |
| `name` | Used as the plot title unless you pass `title=` yourself. |
| `needs_index` | Set to `True` if `fn` takes a third argument, the cell's coordinates. |
| `display` | A function that turns the grid of cells into the array that is drawn. See [Drawing something other than the state](#drawing-something-other-than-the-state). |
| `style` | Draw settings to go with `display`, such as `cmap`, `vmin`, `vmax` and `grid_lines`. These override `colours`, and anything you pass to `animate`, `show` or `spacetime` overrides them in turn. |
| `vectorized` | An optional numpy version of `fn` that computes the whole next grid at once. See [Big grids](#big-grids). |

### Rules with parameters

To give a rule parameters, write a function that returns one. The inner function
can see the outer function's arguments, and each call produces a rule with its
own settings baked in. The library needs no special support for this.

```python
def noisy_life(p_flip=0.001, seed=None):
    rng = np.random.default_rng(seed)

    def rule(value, neighbours):
        if rng.random() < p_flip:
            return 1 - value          # a cell occasionally flips at random
        alive = sum(neighbours)
        return 1 if (alive == 3 or (value and alive == 2)) else 0

    return Rule(rule, neighbourhood='moore', colours=['white', 'black'],
                name=f'Life, {p_flip} noise')

g.animate(noisy_life(p_flip=0.002))
```

Here `rng` is created once and kept for every call to the rule, so a
probabilistic automaton draws from a single random stream instead of reseeding
for each cell.

The two built-in rule makers work the same way. `elementary(30)` closes over the
rule number and `life_like('B3/S23')` over the birth and survival sets.

### Rules that depend on position

Most automata behave the same everywhere, which is why a rule normally sees only
its cell and its neighbours. Some need to know where they are, for example a
permanent heat source, fire spreading over a terrain map, or wind that varies
across the grid. Those rules take a third argument and declare it:

```python
def hot_corner(value, neighbours, index):
    return 1.0 if index == (0, 0) else sum(neighbours) / len(neighbours)

Rule(hot_corner, needs_index=True)
```

`index` is a tuple, `(row, col)` in 2D and `(i,)` in 1D.

## Grid

```python
Grid(size, fill=0.0, boundary='periodic', outside=0, neighbourhood=None)
```

| Argument | Meaning |
|---|---|
| `size` | `5` or `[5]` for a 1D row of 5 cells, `[rows, cols]` for 2D. More than two dimensions raises an error. |
| `fill` | The starting value of every cell. It is a float by default so that continuous automata aren't truncated to whole numbers. Pass `fill=0` for an int grid. |
| `boundary` | What lies past the edge: `'periodic'`, `'fixed'`, `'reflect'` or `'edge'`. See [Boundaries](#boundaries). |
| `outside` | The constant beyond the edge when `boundary='fixed'`. `0` gives a dead border and `1` a permanently live one. The other boundaries ignore it. |
| `neighbourhood` | Which cells each cell can see: `'1d'`, `'moore'` or `'von_neumann'`. The default is `'1d'` for a 1D grid and `'moore'` for 2D. A `Rule` that sets its own overrides this. |

The cells are a plain numpy array that you can seed however you like:

```python
g = Grid([50, 50])
g.cells[10:13, 10] = 1              # a blinker
g.randomise(density=0.3, seed=0)    # or scatter, chainable
g.randomise(0.4, states=3)          # values 0, 1, 2
```

In `randomise(density, states, seed)`, `density` is the fraction of cells that
end up non-zero and `states` is the number of distinct values including the
empty one. `seed` makes the scatter reproducible. Because it returns the grid, it can be
chained onto the constructor.

## Neighbourhoods

`c` is the cell being updated and `N` marks the neighbours it can see.

```
   '1d'          'von_neumann'        'moore'

                    .  N  .          N  N  N
N  c  N             N  c  N          N  c  N
                    .  N  .          N  N  N
```

Moore has 8 neighbours including the diagonals. Von Neumann has only the 4
orthogonal ones. Diagonal contact doesn't count in it, and it is the usual choice
for fire spread and diffusion. `'1d'` is the cells to the left and right.

`neighbours()` returns values in the order the offsets are listed in
`NEIGHBOURHOODS`, which lets a rule tell one direction from another. For `'1d'` the
order is `[left, right]`, and for the 2D neighbourhoods it is reading order
starting from the top left.

### Custom neighbourhoods

The three names are shorthand. Anywhere a name is accepted, on a `Grid` or on a
`Rule`, you can give a list of offsets instead. An offset is how far to step from
the cell being updated: `(-1, 0)` is the cell above and `(0, 2)` is two to the
right.

```python
Grid([50, 50], neighbourhood=[(-1, 0), (1, 0)])         # vertical only
Grid([50, 50], neighbourhood=[(-1, -1), (-1, 0), (-1, 1)])   # upwind only
Grid(100, neighbourhood=[(-2,), (-1,), (1,), (2,)])     # 1D, radius 2
Rule(fn, neighbourhood=[(0, 0), (0, 1)])                # include the cell itself
```

The radius can be larger than 1. Because the border is padded as wide as the
furthest offset reaches, a radius-2 neighbourhood wraps and reflects correctly. Each
offset must have one coordinate per dimension, and this is checked when the
neighbourhood is set. `g.offsets` gives the resolved list of offsets and
`g.radius` how far they reach.

`neighbours()` returns values in the order you listed the offsets in. A rule can
still tell its upwind neighbours from its downwind ones.

## Boundaries

What a cell at the edge sees beyond it, for a row `a b c d`:

| `boundary` | Border | Use |
|---|---|---|
| `'periodic'` | `[d] a b c d [a]` | wraps around, the usual CA torus |
| `'fixed'` | `[0] a b c d [0]` | a constant `outside` value, so patterns decay at the wall |
| `'reflect'` | `[b] a b c d [c]` | mirrored, so nothing flows out (diffusion in a closed box) |
| `'edge'` | `[a] a b c d [d]` | the nearest value repeated, a zero-gradient wall |

The border is built with `np.pad` once per generation.

## Running

```python
g.step(rule)               # one generation, returns a fresh array
g.frames(rule)             # endless generator, one step per pull
g.frames(rule, record=True)  # also appends each frame to g.history
```

Updates are simultaneous. `step()` reads the current grid and returns a new one,
so no cell ever sees a partly updated grid.

`frames()` computes each generation only when it is asked for the next frame,
which lets an animation run indefinitely without memory growing.

With `record=True`, on either `frames()` or `animate()`, every generation is
appended to `g.history` as a plain list of arrays. `np.array(g.history)` stacks
them into a space-time array with one row per generation, which is what
`spacetime()` draws. Leave it off for long runs, as the history grows without
limit.

### Big grids

`step()` calls the rule once per cell in Python. That is fine at 60×60 but takes
seconds per generation at 700×800. A rule can supply a `vectorized` function that
computes the whole grid in numpy, and `step()` uses it when it is there:

```python
from CAlib import Rule, shifted

def life_fast(cells, padded, offsets, radius):
    alive = sum(shifted(padded, offset, radius, cells.shape) for offset in offsets)
    return ((alive == 3) | ((cells != 0) & (alive == 2))).astype(cells.dtype)

Rule(life, neighbourhood='moore', vectorized=life_fast)
```

`shifted(padded, offset, radius, shape)` gives every cell's neighbour at one
offset as an array, the vectorised equivalent of one entry of `neighbours`. Boundaries
behave the same either way, since it slices the same padded array as the
per-cell path. Summing it over `offsets` gives the neighbour count for the
whole grid at once.

`fn` is still required, because it is the fallback and the reference that the
vectorised version is checked against. [`test_vectorized.py`](test_vectorized.py)
checks that Life's two versions agree cell for cell over 50 generations on every
boundary. The built-in `life_like` rules, `LIFE` included, come with a
vectorised version, which on 560k cells takes a generation from 3.5 s to 0.02 s.

### Driving it yourself

`frames()` runs one fixed loop, stepping every cell at once each generation.
Some models need a different loop, such as agents moving over a field or cells
updated one at a time. You can write that loop as a generator that yields the
grid and pass it to the viewers in place of the built-in one:

```python
diffusion = Rule(diffuse, neighbourhood='von_neumann', colours='inferno')

def ticks():
    while True:
        g.cells[25, 25] += 0.1             # a source the rule knows nothing about
        g.cells = g.step(diffusion)        # the automaton's own update
        yield g.cells

g.animate(diffusion, generations=ticks(), vmin=0, vmax=1)
g.save_gif('out.gif', diffusion, steps=200, generations=ticks())
```

The rule passed alongside is then used only for drawing (its `display`, `style`,
`colours` and `name`), and the viewer does no stepping of its own. `record=True`
has no effect in this case. If you want a history, append to `g.history` inside
your loop.

## Viewing

```python
g.show(title='start')                  # the grid as it stands
g.show(save='start.png')               # ...or write it to a file
g.show(rule)                           # ...drawn the rule's way
g.animate(rule, interval=50)           # live, endless, until you close it
g.animate(rule, record=True)           # same, keeping history
g.save_gif('out.gif', rule, steps=60)  # needs a count; endless can't be saved
g.spacetime(rule, steps=64)            # 1D: generations stacked, time downward
g.spacetime(rule, 64, save='r90.png')
```

All of them accept the style arguments `cmap`, `grid_lines`, `line_width`,
`title`, `vmin` and `vmax` (see [Colours](#colours)). A `Rule`'s `colours`,
`name` and `style` supply the defaults, and anything you pass explicitly takes
precedence.

`animate()` returns the animation object. You need to keep a reference to it,
otherwise matplotlib garbage-collects it and the display freezes. At the top
level the interpreter holds the reference for you; inside a function, assign it
and return it.

## Built-in rules

```python
from CAlib import LIFE, life_like, elementary

life_like('B3/S23')   # Conway's Life, also available as LIFE
life_like('B36/S23')  # HighLife
life_like('B2/S')     # Seeds
elementary(90)        # Wolfram's 1D rules; 90 draws a Sierpinski triangle
elementary(30)        # chaotic
elementary(110)       # Turing complete
```

`life_like` takes birth/survival notation. `B3/S23` means a dead cell with 3
live neighbours is born and a live cell with 2 or 3 survives.

## Colours

`cmap`, and a `Rule`'s `colours`, take one of two things depending on whether
your cells hold **states** or **quantities**.

**A list of colours, for discrete states.** The cell's value is used as an
*index* into the list: `0` takes the first colour and `1` the second.

```python
g.animate(rule, cmap=['white', 'black'])             # 2 states: 0, 1
g.animate(rule, cmap=['white', 'blue', 'red'])       # 3 states: 0, 1, 2
```

Any matplotlib colour spec works, including names, hex strings like `'#ff8800'`
and RGB tuples. The default is `STATE_COLOURS`, which is white for 0 followed by
matplotlib's ten `tab10` colours. That covers up to 11 states with no setup. Values past the end of the list are drawn in the last colour rather
than raising an error, so extend the list if you have more states than colours.

**A colormap name, for continuous quantities.** Any matplotlib colormap works:

```python
g.animate(rule, cmap='inferno', vmin=0, vmax=1)
```

For colormaps, set `vmin` and `vmax`. Without them matplotlib rescales each
frame to its own range, so a diffusing blob keeps its brightest cell pure white
and never appears to fade. Set them to the range your values actually cover.
With a colour list they are set for you, to `0` and `len(list) - 1`.

### Other style arguments

| Argument | Meaning |
|---|---|
| `title` | Plot title. Defaults to the `Rule`'s `name`. |
| `grid_lines` | Black lines between cells. Turn them off for large grids and space-time plots, where they would cover the image. |
| `line_width` | Thickness of those lines. |
| `save` | On `show()` and `spacetime()`, the path to write the image to instead of opening a window. |
| `interval` | On `animate()` and `save_gif()`, milliseconds per frame. |

### Drawing something other than the state

`colours` maps a cell's value to a colour, which is enough when the value is the
state. When cells carry more information, like remaining fuel, age or height,
give the rule a `display` function and a `style` to draw its output with:

```python
def wildfire(terrain, max_fuel):
    def shade(cells):
        # unburnt cells shaded by how much fuel is left, the rest flat
        return np.where(cells == UNBURNT, terrain / max_fuel, cells)

    return Rule(step, neighbourhood='moore', name='Wildfire',
                display=shade,
                style=dict(cmap=fuel_cmap(), vmin=0, vmax=3, grid_lines=False))

g.animate(wildfire(terrain, max_fuel))
```

The automaton still steps over its states. `display` is applied to each frame
just before it is drawn, and `g.cells` and `g.history` keep the real values.
`show(rule)`, `spacetime`, `animate` and `save_gif` all use it.

## Continuous automata

Cells can hold floats instead of discrete states, for diffusion, heat or any
other averaging rule. Keep the grid's default `fill=0.0`, since an int grid
would truncate every average to zero, and use a continuous colormap:

```python
def diffuse(value, neighbours):
    return (value + sum(neighbours)) / (len(neighbours) + 1)

box = Grid([50, 50], boundary='reflect')
box.cells[20:30, 20:30] = 1.0
box.animate(Rule(diffuse, neighbourhood='von_neumann', colours='inferno'),
            vmin=0, vmax=1)
```

## Demos

| File | Shows |
|---|---|
| `demo_1d.py` | Wolfram rules, space-time diagram and live row |
| `demo_2d.py` | Life by hand, the built-in, and the B/S family |
| `demo_rules.py` | rules with parameters (closures) and with position (`needs_index`) |
| `demo_boundaries.py` | the same seed under all four edge behaviours |
| `demo_continuous.py` | float cells, diffusion in an insulated box |
| `demo_display.py` | conditional colouring via `display`/`style` (Life leaving embers) |
| `demo_export.py` | `save=` and `save_gif()` |

## Limits

- Grids are 1D or 2D. A 3D size raises an error at construction.
- `step()` calls the rule once per cell in Python, which takes about 27 ms for a
  60×60 grid, or roughly 35 frames per second. Larger grids need a `vectorized`
  rule (see [Big grids](#big-grids)). Only `life_like` ships with one, so
  `elementary` and your own rules run cell by cell unless you write one.
- `step()` updates every cell simultaneously. Block rules (Margolus, lattice
  gas) and asynchronous rules (Langton's ant) need a different update loop, which
  you can write yourself as described in [Driving it yourself](#driving-it-yourself).
- `record=True` keeps every generation in `history`, so memory grows for as long
  as it runs.
