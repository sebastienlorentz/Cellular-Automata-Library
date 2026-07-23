# CAlibrary

A cellular automata engine for 1D and 2D grids. You supply a rule; the library
handles neighbourhoods, edges, stepping and drawing.

```python
from CAlib import Grid, LIFE

Grid([60, 60]).randomise(density=0.3).animate(LIFE)
```

## Getting started

Needs Python 3.9+, numpy and matplotlib:

```
pip install numpy matplotlib
```

There's nothing to install for the library itself — `CAlib.py` is a single file.
Put it next to your script and import from it.

Run any of the demos to check it works:

```
python demo_2d.py
```

A window opens and animates until you close it. Each demo runs several examples
in turn, so closing one window brings up the next.

Then the shortest thing you can write yourself:

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

That's the only part that differs between automata. Everything else — how
neighbours are found, what happens at the edges, how generations advance, how
it's drawn — is shared.

Pass a bare function and the grid supplies the rest — internally `as_rule()`
wraps it in a default `Rule`, so the engine only ever deals with one type. Wrap
it yourself and the automaton carries its own requirements:

```python
from CAlib import Rule

LIFE = Rule(life, neighbourhood='moore', colours=['white', 'black'],
            name="Conway's Life")
```

The grid then takes its neighbourhood, palette and title from the rule.

### Rule arguments

```python
Rule(fn, neighbourhood=None, colours=STATE_COLOURS, name='', needs_index=False)
```

| Argument | Meaning |
|---|---|
| `fn` | The transition function. Takes `(value, neighbours)`, returns the cell's next value. |
| `neighbourhood` | What the rule needs to see: `'1d'`, `'moore'` or `'von_neumann'`. Left as `None`, the grid's own setting is used; set, it overrides the grid — Life is Moore wherever you run it. |
| `colours` | How to draw the states. A list of colours, or the name of a matplotlib colormap. See [Colours](#colours). |
| `name` | Used as the plot title, unless you pass `title=` yourself. |
| `needs_index` | Pass `True` if `fn` takes a third argument, the cell's coordinates. |

### Rules with parameters

Write a function that *returns* a rule. Nothing in the library is needed for
this — the outer function's arguments stay visible to the inner one, so each
call bakes its own settings in:

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

The closure holds more than the parameter here: `rng` is created once and
persists across every call to the rule, which is how a probabilistic automaton
keeps a single random stream rather than reseeding per cell.

Both built-ins are this pattern: `elementary(30)` closes over the rule number,
`life_like('B3/S23')` over the born and survive sets.

### Rules that depend on position

Most automata behave the same everywhere, which is why a rule normally sees only
its cell and its neighbours. Some don't: a permanent heat source, fire spreading
over a terrain map, wind that varies across the grid. Those need to know *which*
cell they're being asked about, so they take a third argument and declare it:

```python
def hot_corner(value, neighbours, index):
    return 1.0 if index == (0, 0) else sum(neighbours) / len(neighbours)

Rule(hot_corner, needs_index=True)
```

`index` is a tuple — `(row, col)` in 2D, `(i,)` in 1D.

## Grid

```python
Grid(size, fill=0.0, boundary='periodic', outside=0, neighbourhood=None)
```

| Argument | Meaning |
|---|---|
| `size` | `5` or `[5]` for a 1D row of 5, `[rows, cols]` for 2D. More than two dimensions raises. |
| `fill` | The value every cell starts at. A float by default, so continuous automata aren't silently truncated to whole numbers — pass `fill=0` if you want an int grid. |
| `boundary` | What lies past the edge: `'periodic'`, `'fixed'`, `'reflect'` or `'edge'`. See [Boundaries](#boundaries). |
| `outside` | The constant beyond the edge when `boundary='fixed'`. `0` is a dead border; `1` a permanently live one. Ignored by the other boundaries. |
| `neighbourhood` | What each cell can see: `'1d'`, `'moore'` or `'von_neumann'`. Defaults by dimension — `'1d'` for a 1D grid, `'moore'` for 2D. A `Rule` that declares one overrides this. |

Cells are a numpy array, so seed them however you like:

```python
g = Grid([50, 50])
g.cells[10:13, 10] = 1              # a blinker
g.randomise(density=0.3, seed=0)    # or scatter, chainable
g.randomise(0.4, states=3)          # values 0, 1, 2
```

`randomise(density, states, seed)` — `density` is the fraction of cells that end
up non-zero, `states` how many distinct values exist counting the empty one, and
`seed` makes the scatter reproducible. It returns the grid, so it chains onto
the constructor.

## Neighbourhoods

`c` is the cell being updated, `N` the neighbours it gets to see.

```
   '1d'          'von_neumann'        'moore'

                    .  N  .          N  N  N
N  c  N             N  c  N          N  c  N
                    .  N  .          N  N  N
```

Moore is 8 neighbours including diagonals; von Neumann is the 4 orthogonal ones
only, so diagonal contact doesn't count — that's the one you want for fire
spread or diffusion. `'1d'` is just left and right.

`neighbours()` returns values in the offset order listed in `NEIGHBOURHOODS`, so
positional rules can tell one direction from another. For `'1d'` that's
`[left, right]`; for the 2D ones it's reading order, top-left first.

### Custom neighbourhoods

The three names are shorthand. Anywhere a name is accepted — on `Grid` or on a
`Rule` — you can give your own list of offsets instead. An offset is how far to
step from the cell being updated: `(-1, 0)` is the cell above, `(0, 2)` is two
to the right.

```python
Grid([50, 50], neighbourhood=[(-1, 0), (1, 0)])         # vertical only
Grid([50, 50], neighbourhood=[(-1, -1), (-1, 0), (-1, 1)])   # upwind only
Grid(100, neighbourhood=[(-2,), (-1,), (1,), (2,)])     # 1D, radius 2
Rule(fn, neighbourhood=[(0, 0), (0, 1)])                # include the cell itself
```

Radius isn't limited to 1 — the border is padded as wide as the furthest offset
reaches, so a radius-2 neighbourhood wraps and reflects correctly like any
other. Offsets must have one coordinate per dimension, checked when you set
them. `g.offsets` gives the resolved list either way, and `g.radius` how far it
reaches.

Order still matters: `neighbours()` returns values in the order you list the
offsets, so a rule can tell its upwind neighbours from its downwind ones.

## Boundaries

What a cell at the edge sees beyond it, for a row `a b c d`:

| `boundary` | Border | Use |
|---|---|---|
| `'periodic'` | `[d] a b c d [a]` | wraps around — the usual CA torus |
| `'fixed'` | `[0] a b c d [0]` | constant `outside`; patterns decay at the wall |
| `'reflect'` | `[b] a b c d [c]` | mirrored — no flux, e.g. diffusion in a closed box |
| `'edge'` | `[a] a b c d [d]` | nearest value repeated, a zero-gradient wall |

Implemented with `np.pad`, built once per generation.

## Running

```python
g.step(rule)               # one generation, returns a fresh array
g.frames(rule)             # endless generator, one step per pull
g.frames(rule, record=True)  # also appends each frame to g.history
```

Updates are simultaneous — `step()` reads the current grid and returns a new
one, so no cell sees a half-updated world.

`frames()` computes nothing ahead of time, which is why animation can run
forever at flat memory.

`record=True` — on `frames()` or `animate()` — appends every generation to
`g.history`, a plain list of arrays. `np.array(g.history)` stacks them into a
space-time array, one row per generation, which is what `spacetime()` draws. It
grows without bound, so leave it off for long runs.

## Viewing

```python
g.show(title='start')                  # the grid as it stands
g.show(save='start.png')               # ...or write it to a file
g.animate(rule, interval=50)           # live, endless, until you close it
g.animate(rule, record=True)           # same, keeping history
g.save_gif('out.gif', rule, steps=60)  # needs a count; endless can't be saved
g.spacetime(rule, steps=64)            # 1D: generations stacked, time downward
g.spacetime(rule, 64, save='r90.png')
```

Style arguments are shared by all of them: `cmap`, `grid_lines`, `line_width`,
`title`, `vmin`, `vmax` — see [Colours](#colours). A `Rule`'s `colours` and
`name` supply the defaults; anything you pass explicitly wins.

`animate()` returns the animation object, and you have to keep a reference to it
or matplotlib garbage-collects it and the display freezes. At the top level the
interpreter holds it for you; inside a function, assign it and return it.

The engine produces arrays and the viewers consume them, so a different backend
could be added without touching the step loop.

## Built-in rules

```python
from CAlib import LIFE, life_like, elementary

life_like('B3/S23')  # Conway's Life, also available as LIFE
life_like('B36/S23')  # HighLife
life_like('B2/S')  # Seeds
elementary(90)  # Wolfram's 1D rules — 90 draws a Sierpinski triangle
elementary(30)  # chaotic
elementary(110)  # Turing complete
```

`life_like` takes birth/survival notation: `B3/S23` means a dead cell with 3
live neighbours is born, and a live cell with 2 or 3 survives.

## Colours

`cmap` (and a `Rule`'s `colours`) takes one of two things, depending on whether
your cells hold **states** or **quantities**.

**A list of colours — discrete states.** The cell's value is an *index* into the
list, not a value to be scaled. `0` takes the first colour, `1` the second:

```python
g.animate(rule, cmap=['white', 'black'])             # 2 states: 0, 1
g.animate(rule, cmap=['white', 'blue', 'red'])       # 3 states: 0, 1, 2
```

Any matplotlib colour spec works — names, `'#ff8800'`, RGB tuples. The default
is `STATE_COLOURS`: white for 0, then matplotlib's ten `tab10` colours, so 11
states are drawn distinctly with no setup. Values above the end of the list
clamp to the last colour rather than erroring, so extend the list if you have
more states than colours.

**A colormap name — continuous quantities.** Any matplotlib colormap:

```python
g.animate(rule, cmap='inferno', vmin=0, vmax=1)
```

Here `vmin`/`vmax` matter. Without them matplotlib rescales to each frame's own
range, so a diffusing blob keeps its brightest cell pure white and appears never
to fade. Pin them to the range your values actually live in. (With a colour
list they're pinned for you, to `0` and `len(list) - 1`.)

### Other style arguments

| Argument | Meaning |
|---|---|
| `title` | Plot title. Defaults to the `Rule`'s `name`. |
| `grid_lines` | Black lines between cells. Turn off for large grids or space-time plots, where they'd swamp the image. |
| `line_width` | Thickness of those lines. |
| `save` | On `show()` and `spacetime()`: write to this path instead of opening a window. |
| `interval` | On `animate()` and `save_gif()`: milliseconds per frame. |

## Continuous automata

Cells can hold floats rather than states — diffusion, heat, anything averaging.
Keep the grid's default `fill=0.0` (an int grid would truncate every average to
zero) and pick a continuous colormap:

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
| `demo_export.py` | `save=` and `save_gif()` |

## Limits

- 1D and 2D only; 3D raises at construction.
- `step()` calls the rule once per cell in Python — about 27 ms for a 60×60
  grid, so roughly 35 fps. Larger grids will want the `np.roll` vectorisation
  noted in the source.
- Simultaneous updates only. Block rules (Margolus, lattice gas) and
  asynchronous ones (Langton's ant) need a different stepper, not a different
  rule.
- `record=True` grows `history` without bound.
