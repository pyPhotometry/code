VERSION = "0.3.3"  # Version number of pyPhotometry.

# ----------------------------------------------------------------------------------------
# GUI Config
# ----------------------------------------------------------------------------------------

history_dur = 10  # Duration of plotted signal history (seconds)
triggered_dur = [-3, 6.9]  # Window duration for event triggered signals (seconds pre, post)
update_interval = 20  # Interval between calls to update function (ms).
max_plot_pulses = 3  # Maximum number of pulses to plot on analog plot.

default_LED_current = [10, 10]  # Channel [1, 2] (mA).

default_acquisition_mode = "2EX_2EM_continuous"  # "2EX_2EM_continuous", "2EX_1EM_pulsed", or "2EX_2EM_pulsed"

default_filetype = "ppd"  # 'ppd' or 'csv'
