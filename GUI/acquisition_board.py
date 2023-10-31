# Code which runs on host computer and implements communication with
# pyboard and saving data to disk.
# Copyright (c) Thomas Akam 2018-2023.
# Licenced under the GNU General Public License v3.

import os
import numpy as np
import json
import time
from inspect import getsource
from datetime import datetime
from time import sleep

from GUI.pyboard import Pyboard, PyboardError
from config.GUI_config import VERSION, update_interval

from config import hardware_config as hwc


class Acquisition_board(Pyboard):
    """Class for aquiring data from a micropython photometry system on a host computer."""

    def __init__(self, port):
        """Open connection to pyboard and instantiate Photometry class on pyboard with
        provided parameters."""
        self.mode = None
        self.data_file = None
        self.running = False
        self.LED_current = [0, 0]
        self.file_type = None
        super().__init__(port, baudrate=115200)
        self.enter_raw_repl()  # Reset pyboard.
        # Transfer firmware if not already on board.
        self.exec(getsource(_djb2_file))  # Define djb2 hashing function on board.
        self.exec(getsource(_receive_file))  # Define recieve file function on board.
        self.transfer_file(os.path.join("uPy", "photometry_upy.py"))
        self.transfer_file(os.path.join("config", "hardware_config.py"))
        # Import firmware and instantiate photometry class.
        self.exec("import photometry_upy")
        self.exec("p = photometry_upy.Photometry()")

    # -----------------------------------------------------------------------
    # Data acquisition.
    # -----------------------------------------------------------------------

    def set_mode(self, mode):
        # Set control channel mode.
        assert mode in [
            "2EX_2EM_continuous",
            "2EX_1EM_pulsed",
            "2EX_2EM_pulsed",
            "3EX_2EM_pulsed",
        ], "Invalid mode, value values: '2EX_2EM_continuous', '2EX_1EM_pulsed', '2EX_2EM_pulsed', or '3EX_2EM_pulsed'."
        self.mode = mode
        self.n_analog_signals = 3 if mode == "3EX_2EM_pulsed" else 2
        self.n_digital_signals = 1 if mode == "3EX_2EM_pulsed" else 2
        self.pulsed_mode = mode.split("_")[-1] == "pulsed"
        self.max_LED_current = hwc.max_sampling_rate["pulsed" if self.pulsed_mode else "continuous"]
        if self.pulsed_mode:
            self.max_rate = hwc.max_sampling_rate["pulsed"] // self.n_analog_signals
        else:
            self.max_rate = hwc.max_sampling_rate["continuous"]
        self.set_sampling_rate(self.max_rate)
        self.exec("p.set_mode('{}')".format(mode))

    def set_LED_current(self, LED_1_current=None, LED_2_current=None):
        if LED_1_current is not None:
            assert (
                LED_1_current <= self.max_LED_current
            ), "Specified LED current exceeds hardware_config.max_LED_current"
            self.LED_current[0] = LED_1_current
        if LED_2_current is not None:
            assert (
                LED_2_current <= self.max_LED_current
            ), "Specified LED current exceeds hardware_config.max_LED_current"
            self.LED_current[1] = LED_2_current
        if self.running:
            if LED_1_current is not None:
                self.serial.write(b"\xFD" + LED_1_current.to_bytes(2, "little"))
            if LED_2_current is not None:
                self.serial.write(b"\xFE" + LED_2_current.to_bytes(2, "little"))
        else:
            self.exec("p.set_LED_current({},{})".format(LED_1_current, LED_2_current))

    def set_sampling_rate(self, sampling_rate):
        self.sampling_rate = int(min(sampling_rate, self.max_rate))
        self.buffer_size = max(
            self.n_analog_signals, int(self.sampling_rate // (1000 / update_interval)) * self.n_analog_signals
        )
        self.serial_chunk_size = (self.buffer_size + 2) * 2
        return self.sampling_rate

    def start(self):
        """Start data aquistion and streaming on the pyboard."""
        self.exec_raw_no_follow("p.start({},{})".format(self.sampling_rate, self.buffer_size))
        self.chunk_number = 0  # Number of data chunks recieved from board, modulo 2**16.
        self.running = True

    def record(self, data_dir, subject_ID, file_type="ppd"):
        """Open data file and write data header."""
        assert file_type in ["csv", "ppd"], "Invalid file type"
        self.file_type = file_type
        date_time = datetime.now()
        file_name = subject_ID + date_time.strftime("-%Y-%m-%d-%H%M%S") + "." + file_type
        file_path = os.path.join(data_dir, file_name)
        self.header_dict = {
            "subject_ID": subject_ID,
            "date_time": date_time.isoformat(timespec="milliseconds"),
            "end_time": date_time.isoformat(timespec="milliseconds"),  # Overwritten on file close.
            "n_analog_signals": self.n_analog_signals,
            "n_digital_signals": self.n_digital_signals,
            "mode": self.mode,
            "sampling_rate": self.sampling_rate,
            "volts_per_division": hwc.ADC_volts_per_division,
            "LED_current": self.LED_current,
            "version": VERSION,
        }
        if file_type == "ppd":  # Single binary .ppd file.
            self.data_file = open(file_path, "wb")
            data_header = json.dumps(self.header_dict).encode()
            self.data_file.write(len(data_header).to_bytes(2, "little"))
            self.data_file.write(data_header)
        elif file_type == "csv":  # Header in .json file and data in .csv file.
            self.json_path = os.path.join(data_dir, file_name[:-4] + ".json")
            with open(self.json_path, "w") as headerfile:
                headerfile.write(json.dumps(self.header_dict, sort_keys=True, indent=4))
            self.data_file = open(file_path, "w")
            self.data_file.write(
                ", ".join(
                    [f"Analog{a+1}" for a in range(self.n_analog_signals)]
                    + [f"Digital{d+1}" for d in range(self.n_digital_signals)]
                )
                + "\n"
            )
        return file_name

    def stop_recording(self):
        if self.data_file:
            # Write session end time to file.
            self.header_dict["end_time"] = datetime.now().isoformat(timespec="milliseconds")
            if self.file_type == "ppd":  # Overwrite header at start of datafile.
                self.data_file.seek(2)
                self.data_file.write(json.dumps(self.header_dict).encode())
            elif self.file_type == "csv":  # Overwrite seperate json file.
                with open(self.json_path, "w") as headerfile:
                    headerfile.write(json.dumps(self.header_dict, sort_keys=True, indent=4))
            self.data_file.close()
        self.data_file = None

    def stop(self):
        if self.data_file:
            self.stop_recording()
        self.serial.write(b"\xFF")  # Stop signal
        sleep(0.1)
        self.serial.reset_input_buffer()
        self.running = False

    def process_data(self):
        """Read a chunk of data from the serial line, check data integrity, extract signals,
        save signals to disk if file is open, return signals."""
        unexpected_input = []
        data_chunks = []
        while self.serial.in_waiting > 0:
            new_byte = self.serial.read(1)
            if new_byte == b"\x07":  # Start of data chunk.
                chunk = np.frombuffer(self.serial.read(self.serial_chunk_size), dtype=np.dtype("<u2"))
                recieved_chunk_number = chunk[0]
                checksum = chunk[1]
                data = chunk[2:]
                if checksum == (sum(data) & 0xFFFF):  # Checksum of data chunk is correct.
                    self.chunk_number = (self.chunk_number + 1) & 0xFFFF
                    n_skipped_chunks = np.int16(recieved_chunk_number - self.chunk_number)  # rollover safe subtraction.
                    if n_skipped_chunks > 0:  # Prepend data with zeros to replace skipped chunks.
                        skip_pad = np.zeros(self.buffer_size * n_skipped_chunks, dtype=np.dtype("<u2"))
                        data = np.hstack([skip_pad, data])
                        self.chunk_number = (self.chunk_number + n_skipped_chunks) & 0xFFFF
                    data_chunks.append(data)
            else:
                unexpected_input.append(new_byte)
                unexpected_bytes = b"".join(unexpected_input[-8:])
                if unexpected_bytes in (b"\x04Traceba", b"uncaught"):  # Code on pyboard has crashed.
                    data_err = (unexpected_bytes + self.read_until(2, b"\x04>", timeout=1)).decode()
                    raise PyboardError(data_err)
        # Extract signals.
        if data_chunks:
            data = np.hstack(data_chunks)
            signal = data >> 1  # Analog signal is most significant 15 bits.
            digital = (data % 2) == 1  # Digital signal is least significant bit.
            ADCs = [signal[a :: self.n_analog_signals] for a in range(self.n_analog_signals)]  # [ADC1, ..., ADCn]
            DIs = [digital[d :: self.n_analog_signals] for d in range(self.n_digital_signals)]  # [DI1, ..., DIn]
            # Write data to disk.
            if self.data_file:
                if self.file_type == "ppd":  # Binary data file.
                    self.data_file.write(data.tobytes())
                else:  # CSV data file.
                    np.savetxt(self.data_file, np.array(ADCs + DIs, dtype=int).T, fmt="%d", delimiter=",")
            return ADCs, DIs

    # -----------------------------------------------------------------------
    # File transfer
    # -----------------------------------------------------------------------

    def get_file_hash(self, target_path):
        """Get the djb2 hash of a file on the pyboard."""
        try:
            file_hash = int(self.eval("_djb2_file('{}')".format(target_path)).decode())
        except PyboardError:  # File does not exist.
            return -1
        return file_hash

    def transfer_file(self, file_path):
        """Copy file at file_path to pyboard."""
        target_path = os.path.split(file_path)[-1]
        file_size = os.path.getsize(file_path)
        file_hash = _djb2_file(file_path)
        # Try to load file, return once file hash on board matches that on computer.
        for i in range(10):
            if file_hash == self.get_file_hash(target_path):
                return
            self.exec_raw_no_follow("_receive_file('{}',{})".format(target_path, file_size))
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(512)
                    if not chunk:
                        break
                    self.serial.write(chunk)
                    response_bytes = self.serial.read(2)
                    if response_bytes != b"OK":
                        time.sleep(0.01)
                        self.serial.reset_input_buffer()
                        raise PyboardError
                self.follow(3)
        # Unable to transfer file.
        raise PyboardError


# ----------------------------------------------------------------------------------------
#  Helper functions.
# ----------------------------------------------------------------------------------------


# djb2 hashing algorithm used to check integrity of transfered files.
def _djb2_file(file_path):
    with open(file_path, "rb") as f:
        h = 5381
        while True:
            c = f.read(4)
            if not c:
                break
            h = ((h << 5) + h + int.from_bytes(c, "little")) & 0xFFFFFFFF
    return h


# Used on pyboard for file transfer.
def _receive_file(file_path, file_size):
    usb = pyb.USB_VCP()
    usb.setinterrupt(-1)
    buf_size = 512
    buf = bytearray(buf_size)
    buf_mv = memoryview(buf)
    bytes_remaining = file_size
    try:
        with open(file_path, "wb") as f:
            while bytes_remaining > 0:
                bytes_read = usb.recv(buf, timeout=5)
                usb.write(b"OK")
                if bytes_read:
                    bytes_remaining -= bytes_read
                    f.write(buf_mv[:bytes_read])
    except:
        usb.write(b"ER")
