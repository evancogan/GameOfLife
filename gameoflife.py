import copy

class GameOfLife:
    def __init__(self, grid):
        """
        Initialize the game with a 2D grid.
        0 represents a dead cell, 1 represents a live cell.
        """
        self.grid = grid
        self.rows = len(grid)
        self.cols = len(grid[0]) if self.rows > 0 else 0

    def count_neighbors(self, r, c):
        """Counts the number of live neighbors for a cell at (r, c)."""
        count = 0
        # Iterate through the 3x3 neighborhood
        for i in range(r - 1, r + 2):
            for j in range(c - 1, c + 2):
                # Skip the cell itself
                if i == r and j == c:
                    continue
                
                # Check boundaries
                if 0 <= i < self.rows and 0 <= j < self.cols:
                    count += self.grid[i][j]
        return count

    def next_generation(self):
        """Applies the rules of Conway's Game of Life to create the next state."""
        # Create a deep copy so we don't modify the current state while calculating
        new_grid = copy.deepcopy(self.grid)

        for r in range(self.rows):
            for c in range(self.cols):
                neighbors = self.count_neighbors(r, c)
                current_state = self.grid[r][c]

                # Rule 1 & 3: Underpopulation and Overpopulation
                if current_state == 1 and (neighbors < 2 or neighbors > 3):
                    new_grid[r][c] = 0
                
                # Rule 4: Reproduction
                elif current_state == 0 and neighbors == 3:
                    new_grid[r][c] = 1
                
                # Rule 2: Survival (current_state remains 1 if neighbors are 2 or 3)
                # This is implicitly handled as we are copying the original state

        self.grid = new_grid
        return self.grid

# --- Example Usage ---
if __name__ == "__main__":
    # A sample grid with a "Glider" pattern
    initial_grid = [
        [0, 1, 0, 0, 0],
        [0, 0, 1, 0, 0],
        [1, 1, 1, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0]
    ]

    game = GameOfLife(initial_grid)

    print("Generation 0:")
    for row in game.grid: print(row)

    # Run 2 generations
    for gen in range(1, 3):
        game.next_generation()
        print(f"\nGeneration {gen}:")
        for row in game.grid: print(row)