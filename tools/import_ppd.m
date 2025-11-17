% Function for opening pyPhotometry data files in Matlab.
% Copyright (c) Thomas Akam 2018-2025.  Licenced under the GNU General Public License v3.

function data_struct = import_ppd(file_path)
    % Function to import pyPhotometry binary data files into Matlab. 
    % Returns a struct with the following fields. 
    %    'subject_ID'    - Subject ID
    %    'date_time'     - Recording start date and time (ISO 8601 format string)
    %    'end_time'      - Recording end date and time (ISO 8601 format string)
    %    'mode'          - Acquisition mode
    %    'sampling_rate' - Sampling rate (Hz)
    %    'LED_current'   - Current for LEDs 1 and 2 (mA)
    %    'version'       - Version number of pyPhotometry
    % For each analog signal (x in [1, n_analog_signals]):
    %    'analog_x'      - Raw analog signal (volts)
    % In pulsed acqusition modes with pyPhotometry version >= 1.1:
    %    'analog_x_raw_LED_on' - Analog signal before baseline subtraction (volts)
    %    'analog_x_raw_baseline' - Baseline signal with LED off (volts).
    % For each digital signal (y in [1, n_digital_signals]):
    %    'digital_y'     - Digital signal
    %    'time'          - Time of each sample relative to start of recording (ms)

    % Read data from file.
    fileID = fopen(file_path);
    header_size = fread(fileID, 1, 'uint16');
    header_bytes = fread(fileID, header_size, 'uint8');
    data = fread(fileID, 'uint16');
    fclose(fileID);

    % Extract header information.
    data_struct = jsondecode(native2unicode(header_bytes,  'UTF-8').');

    % Get number of channels and whether LED-off baseline is recorded.
    if compareVersions(data_struct.version, '1.0'); % Version >= 1.0
        n_analog = data_struct.n_analog_signals;
        n_digital = data_struct.n_digital_signals;
        if compareVersions(data_struct.version, '1.1'); % Version >= 1.1
            has_baselines = contains(data_struct.mode, 'pulsed');
        else
            has_baselines = false;
        end
    else % Version < 1.0.
        n_analog = 2;
        n_digital = 2;
        has_baselines = false;
    end

    % Extract signals.
    analog = bitshift(data, -1);        % Analog signal is most significant 15 bits.
    digital = logical(bitand(data, 1)); % Digital signal is least significant bit.
    volts_per_division = data_struct.volts_per_division(1);
    if has_baselines % LED-on signal and LED-off baseline saved seperately.
        for i = 1:n_analog
            si = 2*(i-1)+1; % start index
            LED_on_sig = analog(si:2*n_analog:end) * volts_per_division;
            baseline = analog(si+1:2*n_analog:end) * volts_per_division;
            signal = LED_on_sig - baseline;
            % Add signals to data struct
            data_struct.(['analog_' num2str(i) '_raw_LED_on']) = LED_on_sig;
            data_struct.(['analog_' num2str(i) '_raw_baseline']) = baseline;
            data_struct.(['analog_' num2str(i)]) = signal;
            if i <= n_digital
                data_struct.(['digital_' num2str(i)]) = digital(si:2*n_analog:end);
            end
        end
    else % Baseline subtracted signal saved to file.
        for i = 1:n_analog
            signal = analog(i:n_analog:end) * volts_per_division;
            % Add signals to data struct
            data_struct.(['analog_' num2str(i)]) = signal;
            if i <= n_digital
                data_struct.(['digital_' num2str(i)]) = digital(i:n_analog:end);
            end
        end
    end
    
    data_struct.time = (0:length(data_struct.analog_1)-1)*1000/data_struct.sampling_rate; % Time relative to start of recording (ms).

end


function tf = compareVersions(v1, v2)
    % Compare version number strings, return true if v1 >= v2, comparing only major.minor parts.
    a = sscanf(v1, '%d.%d');
    b = sscanf(v2, '%d.%d');
    a(end+1:2) = 0;  % ensure both have [major minor]
    b(end+1:2) = 0;

    tf = (a(1) > b(1)) || (a(1) == b(1) && a(2) >= b(2));
end