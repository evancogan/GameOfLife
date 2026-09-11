"""Unit tests for the simulation model.

`life.game` imports no pygame, so these run without a display and without
touching anything that draws.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from life.game import CellEffects, GameOfLife, GenerationClock, Simulation


def grid_of(rows, cols, live=()):
    """A `rows` x `cols` grid with the given cells alive."""
    grid = [[0] * cols for _ in range(rows)]
    for r, c in live:
        grid[r][c] = 1
    return grid


class RulesTest(unittest.TestCase):
    """The four rules, via the shapes everyone recognises."""

    def test_blinker_oscillates_with_period_two(self):
        horizontal = grid_of(5, 5, [(2, 1), (2, 2), (2, 3)])
        vertical = grid_of(5, 5, [(1, 2), (2, 2), (3, 2)])
        game = GameOfLife.from_grid(horizontal, wrap=False)

        game.next_generation()
        self.assertEqual(game.grid, vertical)
        game.next_generation()
        self.assertEqual(game.grid, horizontal)

    def test_block_is_a_still_life(self):
        block = grid_of(4, 4, [(1, 1), (1, 2), (2, 1), (2, 2)])
        game = GameOfLife.from_grid(block, wrap=False)

        for _ in range(4):
            game.next_generation()
        self.assertEqual(game.grid, block)

    def test_glider_moves_one_cell_diagonally_every_four_generations(self):
        glider = [(0, 1), (1, 2), (2, 0), (2, 1), (2, 2)]
        game = GameOfLife.from_grid(grid_of(10, 10, glider), wrap=False)

        for _ in range(4):
            game.next_generation()

        moved = [(r + 1, c + 1) for r, c in glider]
        self.assertEqual(game.grid, grid_of(10, 10, moved))

    def test_lone_cell_dies_and_is_reported_as_died(self):
        game = GameOfLife.from_grid(grid_of(3, 3, [(1, 1)]), wrap=False)
        game.next_generation()

        self.assertEqual(game.population, 0)
        self.assertEqual(game.died, {(1, 1)})
        self.assertEqual(game.born, set())

    def test_born_reports_only_the_cells_that_came_to_life(self):
        # A blinker's two tips die and two new cells are born each step
        game = GameOfLife.from_grid(grid_of(5, 5, [(2, 1), (2, 2), (2, 3)]),
                                    wrap=False)
        game.next_generation()

        self.assertEqual(game.born, {(1, 2), (3, 2)})
        self.assertEqual(game.died, {(2, 1), (2, 3)})

    def test_generation_counter_advances(self):
        game = GameOfLife(4, 4)
        self.assertEqual(game.generation, 0)
        game.next_generation()
        game.next_generation()
        self.assertEqual(game.generation, 2)


class EdgeTest(unittest.TestCase):
    """Wrapping turns the board into a torus; bounded boards have walls."""

    def test_corner_neighbours_wrap_around_the_board(self):
        # The three cells diagonally opposite (0, 0) on a torus
        game = GameOfLife.from_grid(grid_of(4, 4, [(3, 3), (0, 3), (3, 0)]))
        self.assertEqual(game.count_neighbors(0, 0), 3)

    def test_corner_neighbours_stop_at_the_wall_when_bounded(self):
        game = GameOfLife.from_grid(grid_of(4, 4, [(3, 3), (0, 3), (3, 0)]),
                                    wrap=False)
        self.assertEqual(game.count_neighbors(0, 0), 0)

    def test_blinker_wraps_across_the_edge(self):
        # A vertical blinker straddling the top edge: rows 3, 0, 1 of 4
        game = GameOfLife.from_grid(grid_of(4, 5, [(3, 2), (0, 2), (1, 2)]))
        game.next_generation()

        self.assertEqual(game.grid, grid_of(4, 5, [(0, 1), (0, 2), (0, 3)]))

    def test_bounded_board_does_not_count_wrapped_neighbours(self):
        # Three in a column against the left wall stays a blinker, not a wrap
        game = GameOfLife.from_grid(grid_of(5, 5, [(1, 0), (2, 0), (3, 0)]),
                                    wrap=False)
        game.next_generation()

        self.assertEqual(game.grid, grid_of(5, 5, [(2, 0), (2, 1)]))


class BoardEditingTest(unittest.TestCase):
    """Hand edits, resizing and the bookkeeping around them."""

    def test_set_cell_reports_whether_anything_changed(self):
        game = GameOfLife(3, 3)
        self.assertTrue(game.set_cell(1, 1, 1))
        self.assertFalse(game.set_cell(1, 1, 1))
        self.assertTrue(game.set_cell(1, 1, 0))

    def test_set_cell_ignores_coordinates_off_the_board(self):
        game = GameOfLife(3, 3)
        self.assertFalse(game.set_cell(-1, 0, 1))
        self.assertFalse(game.set_cell(0, 3, 1))
        self.assertEqual(game.population, 0)

    def test_toggle_flips_a_cell_and_returns_its_new_state(self):
        game = GameOfLife(3, 3)
        self.assertEqual(game.toggle(0, 0), 1)
        self.assertEqual(game.toggle(0, 0), 0)
        self.assertEqual(game.toggle(9, 9), 0)   # off the board, nothing happens

    def test_resize_keeps_the_colony_when_growing(self):
        game = GameOfLife.from_grid(grid_of(3, 3, [(0, 0), (2, 2)]))
        game.resize(5, 6)

        self.assertEqual((game.rows, game.cols), (5, 6))
        self.assertEqual(game.grid, grid_of(5, 6, [(0, 0), (2, 2)]))

    def test_resize_crops_what_falls_outside_the_new_board(self):
        game = GameOfLife.from_grid(grid_of(4, 4, [(0, 0), (3, 3)]))
        game.resize(2, 2)

        self.assertEqual(game.grid, grid_of(2, 2, [(0, 0)]))

    def test_clear_empties_the_board_and_resets_the_count(self):
        game = GameOfLife.from_grid(grid_of(3, 3, [(1, 1)]))
        game.next_generation()
        game.clear()

        self.assertEqual(game.population, 0)
        self.assertEqual(game.generation, 0)

    def test_randomize_marks_every_live_cell_as_newborn(self):
        game = GameOfLife(20, 20)
        game.randomize(density=1.0)

        self.assertEqual(game.population, 400)
        self.assertEqual(len(game.born), 400)
        self.assertEqual(game.generation, 0)

    def test_population_counts_live_cells(self):
        game = GameOfLife.from_grid(grid_of(4, 4, [(0, 0), (1, 1), (2, 2)]))
        self.assertEqual(game.population, 3)


class CellEffectsTest(unittest.TestCase):
    """The glow and fade tables used only for drawing."""

    def test_a_generation_flares_the_born_and_fades_the_dead(self):
        effects = CellEffects()
        effects.record_generation({(1, 1)}, {(2, 2)})

        self.assertEqual(effects.glow, {(1, 1): 1.0})
        self.assertEqual(effects.fade, {(2, 2): 1.0})

    def test_a_cell_that_dies_stops_glowing(self):
        effects = CellEffects()
        effects.record_generation({(1, 1)}, set())
        effects.record_generation(set(), {(1, 1)})

        self.assertNotIn((1, 1), effects.glow)
        self.assertIn((1, 1), effects.fade)

    def test_painting_a_cell_moves_it_between_the_two_tables(self):
        effects = CellEffects()
        effects.record_paint((0, 0), 1)
        self.assertEqual(effects.glow, {(0, 0): 1.0})

        effects.record_paint((0, 0), 0)
        self.assertEqual(effects.glow, {})
        self.assertEqual(effects.fade, {(0, 0): 1.0})

    def test_decay_thins_effects_and_drops_the_spent_ones(self):
        effects = CellEffects()
        effects.glow = {(0, 0): 1.0, (0, 1): 0.05}
        # dt * rate / glow_generations == 0.1
        effects.decay(dt=0.09, rate=1.0)

        self.assertNotIn((0, 1), effects.glow)
        self.assertAlmostEqual(effects.glow[(0, 0)], 0.9)

    def test_reset_flares_a_fresh_colony_and_clears_the_fade(self):
        effects = CellEffects()
        effects.fade = {(9, 9): 1.0}
        effects.reset([(0, 0), (0, 1)])

        self.assertEqual(effects.glow, {(0, 0): 1.0, (0, 1): 1.0})
        self.assertEqual(effects.fade, {})


class GenerationClockTest(unittest.TestCase):
    """Turning frame times into whole generations."""

    def test_no_step_is_owed_before_a_full_interval_has_passed(self):
        clock = GenerationClock()
        self.assertEqual(clock.advance(0.4, rate=2), 0)   # interval is 0.5s

    def test_steps_are_owed_once_intervals_elapse(self):
        clock = GenerationClock()
        self.assertEqual(clock.advance(0.6, rate=2), 1)
        self.assertEqual(clock.advance(0.4, rate=2), 1)   # 0.1s carried over

    def test_catch_up_is_capped_so_a_stall_cannot_burst(self):
        clock = GenerationClock()
        # Ten seconds at 10/s would be 100 steps without the cap
        self.assertEqual(clock.advance(10.0, rate=10), 4)

    def test_reset_forgets_the_part_generation(self):
        clock = GenerationClock()
        clock.advance(0.4, rate=2)
        clock.reset()
        self.assertEqual(clock.advance(0.4, rate=2), 0)


class SimulationTest(unittest.TestCase):
    """The facade that keeps the board and its effects in step."""

    def test_step_advances_the_board_and_records_the_effects(self):
        sim = Simulation(5, 5)
        sim.game.grid = grid_of(5, 5, [(2, 1), (2, 2), (2, 3)])
        sim.step()

        self.assertEqual(sim.game.generation, 1)
        self.assertEqual(set(sim.effects.glow), {(1, 2), (3, 2)})
        self.assertEqual(set(sim.effects.fade), {(2, 1), (2, 3)})

    def test_paint_reports_the_change_and_flares_the_cell(self):
        sim = Simulation(5, 5)

        self.assertTrue(sim.paint(1, 1, 1))
        self.assertFalse(sim.paint(1, 1, 1))   # already alive
        self.assertEqual(sim.game.grid[1][1], 1)
        self.assertIn((1, 1), sim.effects.glow)

    def test_paint_off_the_board_changes_nothing(self):
        sim = Simulation(5, 5)

        self.assertFalse(sim.paint(-1, 0, 1))
        self.assertEqual(sim.effects.glow, {})

    def test_advance_runs_the_generations_the_elapsed_time_bought(self):
        sim = Simulation(6, 6)
        sim.game.grid = grid_of(6, 6, [(2, 1), (2, 2), (2, 3)])
        sim.advance(1.0, rate=2)   # two intervals of 0.5s

        self.assertEqual(sim.game.generation, 2)

    def test_resize_drops_effects_that_may_have_lost_their_cell(self):
        sim = Simulation(5, 5)
        sim.paint(4, 4, 1)
        sim.resize(2, 2)

        self.assertEqual(sim.effects.glow, {})
        self.assertEqual((sim.game.rows, sim.game.cols), (2, 2))


if __name__ == "__main__":
    unittest.main()
