# This module contains functions for measuring hardware parameters.

import time
import sys
import numpy as np
import pylab as plt
from tqdm import tqdm
from pathlib import Path
from scipy.signal import welch

# Add pyPhotometry directory to sys.path so Acqusition_board can be imported.
sys.path.append(str(Path(__file__).parents[1]))

from GUI.acquisition_board import Acquisition_board
import config.hardware_config as hwc


def noise_spectrum(
    port="COM4",
    recording_duration=10,
    LED_current=0,
    sampling_rate=1000,
    nperseg=1024,
):
    """Acquire data from CH1 in continuous mode at specified LED_current and
    plot the noise amplitude spectrum."""

    # Connect to board.
    print("Connecting to board")
    board = Acquisition_board(port)  # Set port to match that shown for board in GUI.

    # Set acqusition parameters.
    board.set_mode("2EX_2EM_continuous")
    board.set_LED_current(LED_1_current=LED_current, LED_2_current=0)
    board.set_sampling_rate(sampling_rate)

    # Acquire data
    CH1_signal = []
    board.start()
    print("Acquiring data")
    for i in tqdm(range(recording_duration * 10)):
        time.sleep(0.1)  # Sleep for 10ms
        new_data = board.process_data()  # Process new data from board and write to disk.
        if new_data:
            CH1_signal.append(new_data[0][0])

    # Stop acquisition and close connection to board.
    print("Disconecting from board")
    board.stop()
    board.close()

    # Plot amplitude spectrum.
    CH1_signal = np.hstack(CH1_signal) * hwc.ADC_volts_per_division[0]
    f, psd = welch(CH1_signal - np.mean(CH1_signal), fs=sampling_rate, nperseg=nperseg)
    asd = np.sqrt(psd)  # Convert to amplitude
    plt.figure()
    plt.plot(f, asd * 1e6)
    plt.xscale("log")
    plt.ylabel("Amplitude ($\mathregular{uV/Hz^{1/2}}$)")
    plt.xlabel("Frequency (Hz)")
    plt.xlim(1, sampling_rate / 2)
    plt.tight_layout()
    plt.show()
    return CH1_signal
