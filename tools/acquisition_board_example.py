# This script demonstrates how to aquire data using the Acquisition_board class
# without using the GUI.

import time
import sys
from pathlib import Path

# Add pyPhotometry directory to sys.path so Acqusition_board can be imported.
pyphotometry_dir = str(Path(__file__).parents[1])
sys.path.append(pyphotometry_dir)

from GUI.acquisition_board import Acquisition_board
from GUI.dir_paths import data_dir

# Connect to board.
board = Acquisition_board(port="COM1")  # Set port to match that shown for board in GUI.

# Set acqusition parameters.
board.set_mode("2EX_2EM_pulsed")
board.set_LED_current(LED_1_current=100, LED_2_current=100)
board.set_sampling_rate(130)

# Start recording.
board.start()  # Start data acqusition.
board.record(data_dir=data_dir, subject_ID="m01", file_type="ppd")

# During acqusition process the data coming from the board.
start_time = time.time()
while time.time() - start_time < 10:  # Record for 10 seconds.
    time.sleep(0.005)  # Sleep for 5ms
    board.process_data()  # Process new data from board and write to disk.

# Stop acquisition and close connection to board.

board.stop()
board.close()
