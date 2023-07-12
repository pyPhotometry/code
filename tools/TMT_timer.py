# @Author: Jun HUANG, 2023.07.12
# This code is for timing the TMT experiments

import tkinter as tk
from datetime import datetime, timedelta

data = {
        'UniBe001': 
            {'Stim': [0, 0, 1, 0, 1, 1, 1, 1, 0, 0, 0, 1, 1, 1, 0, 1, 1, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 1, 0], 
             'Time': ['00:30', '01:28', '01:59', '02:29', '03:23', '03:57', '04:36', '05:24', '06:24', '07:23', 
                      '08:10', '08:56', '09:39', '10:13', '10:54', '11:33', '12:15', '13:00', '13:34', '14:11', 
                      '15:03', '15:35', '16:09', '16:42', '17:38', '18:09', '18:51', '19:22', '20:00', '20:59']}, 
        'UniBe002': 
            {'Stim': [0, 0, 1, 1, 1, 0, 0, 1, 1, 1, 0, 1, 1, 0, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 1, 0, 1, 1], 
             'Time': ['00:30', '01:05', '01:53', '02:25', '03:25', '04:16', '05:10', '05:59', '06:35', '07:19', 
                      '08:17', '08:54', '09:50', '10:36', '11:30', '12:13', '12:48', '13:31', '14:16', '15:15', 
                      '16:08', '17:03', '17:44', '18:27', '19:24', '20:21', '20:53', '21:27', '22:09', '23:07']}, 
        'UniBe003': 
            {'Stim': [0, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0], 
             'Time': ['00:30', '01:17', '01:47', '02:28', '03:11', '03:43', '04:19', '04:59', '05:32', '06:29', 
                      '07:28', '08:11', '08:42', '09:23', '10:18', '11:13', '12:04', '13:00', '13:36', '14:22', 
                      '15:13', '16:11', '16:52', '17:40', '18:14', '18:47', '19:36', '20:32', '21:22', '22:13']}, 
        'UniBe004': 
            {'Stim': [1, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0], 
             'Time': ['00:30', '01:29', '02:07', '02:48', '03:39', '04:19', '04:59', '05:46', '06:20', '06:50', 
                      '07:49', '08:38', '09:37', '10:19', '11:16', '12:03', '12:42', '13:34', '14:08', '14:53', 
                      '15:25', '16:12', '16:56', '17:41', '18:11', '19:06', '19:43', '20:27', '21:02', '22:02']}, 
        'UniBe005': 
            {'Stim': [0, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 1], 
             'Time': ['00:30', '01:15', '02:06', '02:55', '03:35', '04:12', '04:47', '05:29', '06:28', '07:11', 
                      '07:54', '08:31', '09:07', '09:54', '10:43', '11:15', '11:54', '12:48', '13:19', '14:08', 
                      '14:51', '15:47', '16:24', '17:20', '18:12', '19:08', '19:53', '20:48', '21:26', '22:09']}, 
        'UniBe006': 
            {'Stim':[0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 1, 1, 0, 1], 
             'Time': ['00:30', '01:02', '01:56', '02:36', '03:17', '03:54', '04:32', '05:05', '05:42', '06:30', 
                      '07:15', '07:54', '08:46', '09:16', '09:46', '10:23', '11:13', '11:49', '12:44', '13:39', 
                      '14:35', '15:26', '16:02', '16:34', '17:16', '18:15', '18:48', '19:46', '20:21', '21:00']}, 
        'UniBe007': 
            {'Stim': [1, 0, 0, 1, 0, 0, 1, 0, 1, 1, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 1, 1, 0, 1, 1, 1], 
             'Time': ['00:30', '01:18', '02:06', '03:02', '03:39', '04:14', '05:13', '06:05', '06:47', '07:44', 
                      '08:42', '09:15', '10:06', '10:56', '11:56', '12:53', '13:23', '14:11', '14:51', '15:41', 
                      '16:34', '17:24', '18:07', '18:44', '19:43', '20:42', '21:42', '22:19', '22:53', '23:28']}, 
        'UniBe008': 
            {'Stim': [1, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1], 
             'Time': ['00:30', '01:24', '02:11', '02:47', '03:25', '03:56', '04:27', '05:06', '05:37', '06:32', 
                      '07:24', '08:00', '09:00', '09:30', '10:26', '11:08', '12:08', '12:50', '13:45', '14:38', 
                      '15:37', '16:30', '17:11', '18:03', '18:55', '19:41', '20:31', '21:16', '22:10', '22:59']}, 
        'UniBe009': 
            {'Stim': [1, 0, 0, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 0], 
             'Time': ['00:30', '01:25', '02:10', '02:43', '03:42', '04:15', '04:55', '05:40', '06:23', '06:58', 
                      '07:48', '08:36', '09:29', '10:09', '11:05', '11:49', '12:33', '13:18', '13:59', '14:56', 
                      '15:55', '16:50', '17:50', '18:46', '19:31', '20:30', '21:05', '22:05', '23:04', '23:57']}, 
        'UniBe010': 
            {'Stim': [1, 0, 1, 0, 1, 1, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1], 
             'Time': ['00:30', '01:14', '02:09', '03:07', '03:57', '04:28', '05:25', '06:21', '06:56', '07:30', 
                      '08:22', '09:02', '09:38', '10:26', '11:05', '11:40', '12:21', '13:14', '14:06', '14:37', 
                      '15:13', '16:04', '16:44', '17:23', '18:20', '19:02', '19:40', '20:28', '21:18', '22:07']}, 
        'UniBe011': 
            {'Stim': [1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 1, 1], 
             'Time': ['00:30', '01:10', '01:53', '02:29', '03:24', '04:00', '04:42', '05:33', '06:22', '07:20', 
                      '08:04', '08:52', '09:38', '10:35', '11:11', '12:01', '12:31', '13:08', '14:02', '14:39', 
                      '15:13', '15:54', '16:35', '17:25', '17:57', '18:43', '19:37', '20:29', '21:20', '22:08']}, 
        'UniBe012': 
            {'Stim': [1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 1, 1, 0, 0, 0, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0, 1], 
             'Time': ['00:30', '01:06', '01:57', '02:44', '03:22', '04:19', '05:06', '05:45', '06:31', '07:14', 
                      '08:06', '08:49', '09:36', '10:06', '10:50', '11:36', '12:24', '13:13', '14:08', '14:48', 
                      '15:26', '16:14', '17:07', '18:03', '18:49', '19:21', '20:18', '21:07', '21:54', '22:32']}, 
        'UniBe013': 
            {'Stim': [1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1], 
             'Time': ['00:30', '01:26', '02:01', '02:47', '03:39', '04:36', '05:20', '06:13', '07:05', '07:38', 
                      '08:23', '09:10', '10:09', '10:48', '11:38', '12:16', '12:46', '13:44', '14:15', '15:13', 
                      '15:51', '16:48', '17:33', '18:08', '18:57', '19:35', '20:33', '21:30', '22:13', '23:07']}}

class TimerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Timer GUI")
        self.current_set = None
        self.timer_running = False
        self.remaining_time = timedelta()
        self.upcoming_events = []

        self.frame = tk.Frame(self.root)
        self.frame.pack(padx=20, pady=20)

        # Set Selection
        self.label_set = tk.Label(self.frame, text="Select Set:")
        self.label_set.grid(row=0, column=0, sticky="W")

        self.set_var = tk.StringVar()
        self.set_var.set("Select a set")
        self.set_dropdown = tk.OptionMenu(self.frame, self.set_var, *data.keys(), command=self.on_set_select)
        self.set_dropdown.grid(row=0, column=1, padx=10, pady=10, sticky="W")

        # Timer
        self.timer_label = tk.Label(self.frame, text="00:00", font=("Arial", 200), width=10)
        self.timer_label.grid(row=1, column=0, columnspan=2, padx=10, pady=10)

        # Upcoming Event
        self.event_label = tk.Label(self.frame, text="", font=("Arial", 100), fg="red")
        self.event_label.grid(row=2, column=0, columnspan=2, padx=10, pady=10)

        # Next Event Type
        self.event_type_label = tk.Label(self.frame, text="", font=("Arial", 100))
        self.event_type_label.grid(row=3, column=0, columnspan=2, padx=10, pady=10)

        # Begin Button
        self.begin_button = tk.Button(self.frame, text="Begin", command=self.start_timer, state=tk.DISABLED)
        self.begin_button.grid(row=6, column=0, columnspan=2, padx=10, pady=10)

    def on_set_select(self, selected_set):
        self.current_set = selected_set
        self.begin_button["state"] = tk.NORMAL
        first_event_type = "TMT" if data[self.current_set]["Stim"][0] == 1 else "Saline"
        self.event_type_label["text"] = f"First Event Type: {first_event_type}"

    def start_timer(self):
        if self.current_set:
            self.timer_running =True
            self.begin_button["state"] = tk.DISABLED
            self.remaining_time = timedelta(seconds=0)
            self.upcoming_events = [datetime.strptime(t, "%M:%S") for t in data[self.current_set]["Time"]]
            self.countup()

    def countup(self):
        if self.timer_running:
            self.remaining_time += timedelta(seconds=1)
            self.timer_label["text"] = str(self.remaining_time)[2:]

            if self.upcoming_events:
                upcoming_event = self.upcoming_events[0]
                time_diff = upcoming_event - datetime.strptime(str(self.remaining_time)[2:], "%M:%S")

                if time_diff <= timedelta(seconds=30):
                    self.event_label["text"] = f"Upcoming Event: {upcoming_event.strftime('%M:%S')} ({time_diff.seconds}s)"
                    event_index = len(data[self.current_set]["Time"]) - len(self.upcoming_events)
                    if data[self.current_set]["Stim"][event_index] == 1:
                        self.event_type_label["text"] = "Next Event Type: TMT"
                    else:
                        self.event_type_label["text"] = "Next Event Type: Saline"
                else:
                    self.event_label["text"] = ""
                    self.event_type_label["text"] = ""

                if time_diff <= timedelta(seconds=0):
                    self.upcoming_events.pop(0)
            if self.timer_running:
                self.root.after(991, self.countup)

    def stop_timer(self):
        self.timer_running = False

root = tk.Tk()
root.attributes("-fullscreen", True)  # Make the GUI full screen
app = TimerGUI(root)
root.mainloop()