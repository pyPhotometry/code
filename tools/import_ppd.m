% Function for opening pyPhotometry data files in Matlab.
% Copyright (c) Thomas Akam 2018.  Licenced under the GNU General Public License v3.

function data_struct = import_ppd(file_path)
	% Function to import pyPhotometry binary data files into Matlab. 
	% Currently only works for data files with 2 analog and 2 digital signals.
	% Returns a struct with the following fields. 
	%    'subject_ID'    - Subject ID
	%    'date_time'     - Recording start date and time (ISO 8601 format string)
	%    'end_time'      - Recording end date and time (ISO 8601 format string)
	%    'mode'          - Acquisition mode
	%    'sampling_rate' - Sampling rate (Hz)
	%    'LED_current'   - Current for LEDs 1 and 2 (mA)
	%    'version'       - Version number of pyPhotometry
	%    'analog_1'      - Raw analog signal 1 (volts)
	%    'analog_2'      - Raw analog signal 2 (volts)
	%    'digital_1'     - Digital signal 1
	%    'digital_2'     - Digital signal 2
	%    'time'          - Time of each sample relative to start of recording (ms)

	% Read data from file.
	fileID = fopen(file_path);
	header_size = fread(fileID, 1, 'uint16');
	header_bytes = fread(fileID, header_size, 'uint8');
	data = fread(fileID, 'uint16');
	fclose(fileID);
	% Extract header information.
	data_struct = jsondecode(native2unicode(header_bytes,  'UTF-8').');
	% Extract signals.
	analog = bitshift(data, -1);        % Analog signal is most significant 15 bits.
	digital = logical(bitand(data, 1)); % Digital signal is least significant bit.
	% Alternating samples are signals 1 and 2.
	data_struct.analog_1 = analog(1:2:end) * data_struct.volts_per_division(1);
	data_struct.analog_2 = analog(2:2:end) * data_struct.volts_per_division(2);
	data_struct.digital_1 = digital(1:2:end);
	data_struct.digital_2 = digital(2:2:end);
	data_struct.time = (0:length(data_struct.analog_1)-1)*1000/data_struct.sampling_rate % Time relative to start of recording (ms).

end

function data_struct = import_3_channel_ppd(file_path)
	% Function to import pyPhotometry binary data files with 3 analog 
	% channels into Matlab. 
	% Returns a struct with the following fields. 
	%    'subject_ID'    - Subject ID
	%    'date_time'     - Recording start date and time (ISO 8601 format string)
	%    'end_time'      - Recording end date and time (ISO 8601 format string)
	%    'mode'          - Acquisition mode
	%    'sampling_rate' - Sampling rate (Hz)
	%    'LED_current'   - Current for LEDs 1 and 2 (mA)
	%    'version'       - Version number of pyPhotometry
	%    'analog_1'      - Raw analog signal 1 (volts)
	%    'analog_2'      - Raw analog signal 2 (volts)
	%    'analog_3'      - Raw analog signal 3 (volts)
	%    'digital_1'     - Digital signal 1
	%    'digital_2'     - Digital signal 2
	%    'time'          - Time of each sample relative to start of recording (ms)

	% Read data from file.
	fileID = fopen(file_path);
	header_size = fread(fileID, 1, 'uint16');
	header_bytes = fread(fileID, header_size, 'uint8');
	data = fread(fileID, 'uint16');
	fclose(fileID);
	% Extract header information.
	data_struct = jsondecode(native2unicode(header_bytes,  'UTF-8').');
	% Extract signals.
	analog = bitshift(data, -1);        % Analog signal is most significant 15 bits.
	digital = logical(bitand(data, 1)); % Digital signal is least significant bit.
	% Alternating samples are signals 1 and 2.
	data_struct.analog_1 = analog(1:3:end) * data_struct.volts_per_division(1);
	data_struct.analog_2 = analog(2:3:end) * data_struct.volts_per_division(2);
	data_struct.analog_3 = analog(3:3:end) * data_struct.volts_per_division(1);
	data_struct.digital_1 = digital(1:3:end);
	data_struct.digital_2 = digital(2:3:end);
	data_struct.time = (0:length(data_struct.analog_1)-1)*1000/data_struct.sampling_rate % Time relative to start of recording (ms).

end
