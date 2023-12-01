from pathlib import Path

pyphotometry_dir = Path(__file__).parents[1]  # Top level pyPhotometry directory.

experiments_dir = Path(pyphotometry_dir, "experiments")

config_dir = Path(pyphotometry_dir, "config")

data_dir = Path(pyphotometry_dir, "data")

upy_dir = Path(pyphotometry_dir, "uPy")
