"""
README

Sensapex uMp macro by Sanni Peltola

This program runs a macro that moves a micromanipulator down the z-axis.
User can alter loops, step_size, delay, and speed.

- loops(int): the amount of times the uMp moves down in a series of movement.
- step_size(um): the distance the uMp moves during one loop.
- delay(s): the time the manipulator waits between loops. Cannot be 0, in that case use one loop and give delay value 1.
- speed(um/s): the speed at which the uMp travels the distances given in step_size. Minimum speed is 1um/s, max. is 5mm/s.

Give the loops in whole numbers (integers) between 1 and 100.

Step size (um), delay (s), and speed (um/s) are given in decimals, use . as the decimal point. Range is 0,05-100 for all.

Lowest possible step size is 50 nm (recommended 100nm) and speed 1um/s. Resolution of movement is +/-5nm depending on load.
HOWEVER:
Movements below 100nm do not send position information fast, position is updated by firmware with a 1s delay.
SO, IF  movements below 100 nm are done, put in a delay of MINIMUM 1s. This code uses position tracking to
command next position when multiple loops are driven. Movements below 50 nm are not recognized by firmware as "big"
enough to warrant movement: firmware thinks the manipulator is close enough. For this to work, manipulator would need
to move back and forth.

is_close_enough() method in the python wrapper(commanded by goto.pos) has a set resolution for when the manipulator
is close enough to the target. Set it to a wanted sensitivity by changing line 276. As of 7.1.2026 it has been set to 5nm.
Earlier it was 50 nm, causing 45nm cumulative error that multiplied with looped experiments (asked to move 100nm,
moves 55nm instead (SD of 45nm bias is 2nm). With 100 loops, movement is 5,5um when 10 um was expected.)

Calculate-button gives the estimated time it takes to run one loop (without including the delay) and the whole thing.
In case you try to run macro with times over 20s for one step and/or times over 10min in total,
the macro asks for confirmation.

GO-button runs the macro with the given attributes. GO won't start if attributes are wrong.

STOP-button stops the macro mid-run. Manipulator should stop at max 0,1 s delay.

QUIT -button will stop the manipulator, close all active threads, and shut down the program. NOTE! Pressing just X
from top right corner might not stop the manipulator mid-run.

For the uMp z-axis, 0 position is at the top. So going down will show increasing position numbers.

HOME from touch screen can be set at Z = 0 (at the top).

Sensapex python package was downloaded into Roaming -directory to bypass problem with not having access for downloading
sensapex file into normal directories. When you use this macro, make sure to look for the "sensapex" folder
from YOUR file location in "sys.path.append("location") at line 53. Otherwise, the code won't find the python package
needed and won't work. If pip works on your computer, you can use: pip install sensapex.
"""

import sys
sys.path.append(r"C:YOUR_LOCATION\sensapex")
from sensapex import UMP
from tkinter import Tk, ttk
from tkinter import messagebox
import tkinter.font as tkFont
from threading import Thread, Event
import time


class UI:
    def __init__(self, root):
        self._root = root

        # setting a default font
        self.default_font = tkFont.nametofont("TkDefaultFont")
        self.default_font.configure(family="Arial", size=16)

        self.message_label = None  # Declares the attributes early, will be set later
        self.time_estimate_label = None
        self.loop_entry = None
        self.delay_entry = None
        self.speed_entry = None
        self.step_size_entry = None
        self.stop_button = None
        self.go_button = None

        # Creating a validation status dictionary
        self.valid_inputs = {
            "loops": False,
            "delay": False,
            "speed": False,
            "step_size": False
        }
        self.device_id = None
        # creating a stop flag
        # self.stop_requested = False
        self.stop_event = Event()
        self.go_event = Event()
        self.quit_event = Event()

        self.run_thread = None

    def start(self):
        # creating UI components (heading, variables like loops, step size, speed & delay, and buttons GO and STOP)
        heading_label = ttk.Label(master=self._root, text="Give values (no empty allowed). loops:int, other:decimal.")
        self.message_label = ttk.Label(master=self._root, text="warnings & info")
        self.time_estimate_label = ttk.Label(master=self._root, text="calculations")

        loop_label = ttk.Label(master=self._root, text="Loops (int, 1-100):")
        self.loop_entry = ttk.Entry(master=self._root)
        self.loop_entry.field_name = "loops"

        delay_label = ttk.Label(master=self._root, text="Delay (s, recommended 1-100):")
        self.delay_entry = ttk.Entry(master=self._root)
        self.delay_entry.field_name = "delay"

        speed_label = ttk.Label(master=self._root, text="Speed (um/s, recommended 1-100):")
        self.speed_entry = ttk.Entry(master=self._root)
        self.speed_entry.field_name = "speed"

        step_size_label = ttk.Label(master=self._root, text ="Step size (um, recommended 0,1-100):")
        self.step_size_entry = ttk.Entry(master=self._root)
        self.step_size_entry.field_name = "step_size"

        calculate_button = ttk.Button(master=self._root, text="calculate", command=self.calculate_time)
        self.go_button = ttk.Button(master=self._root, text="GO", command=self.go)
        self.go_button.state(["!disabled"])

        self.stop_button = ttk.Button(master=self._root, text="STOP", command=self.stop)
        self.stop_button.state(["disabled"])
        self.stop_button.config(style="Disabled.TButton")
        quit_button = ttk.Button(master=self._root, text="QUIT PROGRAM", command=self.quit)

        # anchoring things in the UI
        heading_label.grid(row=0, column=0, columnspan=3)
        self.message_label.grid(row=1, column=2, columnspan=2)
        self.time_estimate_label.grid(row=6, column=2, columnspan=2)

        loop_label.grid(row=2, column=0)
        self.loop_entry.grid(row=2, column=1)

        step_size_label.grid(row=3, column=0)
        self.step_size_entry.grid(row=3, column=1)

        speed_label.grid(row=4, column=0)
        self.speed_entry.grid(row=4, column=1)

        delay_label.grid(row=5, column=0)
        self.delay_entry.grid(row=5, column=1)

        calculate_button.grid(row=6, column=1)
        self.stop_button.grid(row=7, column=0)
        self.go_button.grid(row=8, column=1)
        quit_button.grid(row=8, column=2)

        # checking entries for errors. Entries collected from "enter" press or moving out of the enter space.
        self.loop_entry.bind("<Return>", self.check_integer)
        self.loop_entry.bind("<FocusOut>", self.check_integer)
        self.delay_entry.bind("<Return>", self.check_float)
        self.delay_entry.bind("<FocusOut>", self.check_float)
        self.speed_entry.bind("<Return>", self.check_float)
        self.speed_entry.bind("<FocusOut>", self.check_float)
        self.step_size_entry.bind("<Return>", self.check_float)
        self.step_size_entry.bind("<FocusOut>", self.check_float)

        # getting it to scale when window is dragged
        self._root.grid_columnconfigure(2, weight=1)

        # creating styles for the button fonts
        style = ttk.Style()
        style.configure("Active.TButton", foreground="red", font=("Arial", 16, "bold"))
        style.configure("Disabled.TButton", foreground="gray", background="light gray")

    def check_integer(self, event):
        # checks the input so that it is a positive integer and not an empty input
        widget = event.widget
        value = widget.get()

        field_name = self._get_field_name(widget)  # a helper to identify which widget (loops, delay etc.)

        if not value.strip():
            # treat it as empty
            self.valid_inputs[field_name] = False
            self.message_label.config(text="Error: input cannot be empty")
        else:
            try:
                int_value = int(value.strip())
                if 1 <= int_value <= 100:
                    self.valid_inputs[field_name] = True
                    self.message_label.config(text="Valid input")
                else:
                    self.valid_inputs[field_name] = False
                    self.message_label.config(text="Error: Value must be between 1 and 100")
            except ValueError:
                self.valid_inputs[field_name] = False
                self.message_label.config(text="Error: input must be an integer")

    def check_float(self, event):
        # checks the input so that it is a positive float and not an empty input
        widget = event.widget
        value = widget.get()
        field_name = self._get_field_name(widget)

        if not value.strip():
            # treat it as empty
            self.valid_inputs[field_name] = False
            self.message_label.config(text="Error: input cannot be empty")
        else:
            try:
                float_value = float(value.strip())
                if 0.05 <= float_value <= 100.0:
                    self.valid_inputs[field_name] = True
                    self.message_label.config(text="Valid input")
                else:
                    self.valid_inputs[field_name] = False
                    self.message_label.config(text="Error: Value must be between 0.05 and 100.0")
            except ValueError:
                self.valid_inputs[field_name] = False
                self.message_label.config(text="Error: input must be a decimal number between 0.05 and 100.0 (use .)")

    def _get_field_name(self, widget):
        return getattr(widget, "field_name", "unknown")

    def go(self):
        # runs the macro when "go" is pressed
        if all(self.valid_inputs.values()):
            time_per_step, total_time = self.calculate_time()
            if time_per_step > 20 or total_time > 600:  # 20s and 10min
                proceed = messagebox.askyesno(
                    "Long time confirm", f"Time per step is {time_per_step:.2f}s and "
                                         f"total time is {total_time/60:.2f}min. Do you want to continue?"
                )
                if not proceed:
                    self.message_label.config(text="Macro canceled by user.")
                    return

            self.stop_button.state(["!disabled"])
            self.stop_button.config(style="Active.TButton")
            self.go_button.state(["disabled"])
            self.go_button.config(style="Disabled.TButton")

            self.message_label.config(text="Running macro...")

            self.stop_event.clear()  # resetting stop flag
            self.run_thread = Thread(target=self.run, daemon=True)  # creating a separate thread for run
            self.run_thread.start()
        else:
            self.message_label.config(text="Error: please check input fields. With decimals use '.' ")

    def calculate_time(self):
        try:
            loops = int(self.loop_entry.get().strip())
            delay = float(self.delay_entry.get().strip())
            speed = float(self.speed_entry.get().strip())
            step_size = float(self.step_size_entry.get().strip())

            time_per_step_s = step_size / speed
            total_time_s = (time_per_step_s + delay) * loops
            total_time_min = total_time_s / 60

            self.time_estimate_label.config(
                text=f"Time per step (no delay): {time_per_step_s:.2f} s | "
                     f"Total time: {total_time_s:.2f} s / {total_time_min:.2f} min"
            )
            return time_per_step_s, total_time_s
        except ValueError:
            return None, None

    def run(self):
        # run the macro
        loops_value = self.loop_entry.get().strip()
        delay_value = self.delay_entry.get().strip()
        speed_value = self.speed_entry.get().strip()
        step_size_value = self.step_size_entry.get().strip()

        loops = int(loops_value)
        delay = float(delay_value)
        speed = float(speed_value)
        step_size = float(step_size_value)

        # connecting to sensapex device and calling the certain device with device_id
        try:
            ump = UMP.get_ump()
            device_ids = ump.list_devices()
            self.device_id = ump.get_device(device_ids[0])  # Assuming one device
            ump.set_retry_threshold(0.005)   # Setting lower threshold for movement than standard 0.4um. Now 5nm.
            current_pos = self.device_id.get_pos()
            print(f"Starting position: {current_pos}")

        except Exception as e:
            self.message_label.config(text=f"Device error: {e}")
            return

        for i in range(loops):
            if self.stop_event.is_set() or self.quit_event.is_set():  # check for stop at the start of the loop.
                print("Macro interrupted by user")
                self.message_label.config(text="Macro stopped by user")
                return  # exit early

            new_z = current_pos[2] + step_size  # Current_pos[2] is z-axis position. [0] is x and [1] is y.
            target_pos = (current_pos[0], current_pos[1], new_z)  # target_pos = (x, y, z), essentially.
            # self.device_id.set_custom_slow_speed(speed)
            self.device_id.goto_pos(target_pos, speed=speed)  # moving to new position.

            while self.device_id.is_busy():  # checks the status of manipulator every 0.1s so that delay won't start while goto_pos is unfinished.
                if self.stop_event.is_set() or self.quit_event.is_set():
                    print("Macro interrupted by user")
                    self.message_label.config(text="Macro stopped by user")
                    self.device_id.stop()   # macro stops by override of earlier goto_pos
                    current_pos = self.device_id.get_pos()
                    print(f"Moved to: {current_pos}")
                    return  # exit early
                else:
                    time.sleep(0.1)

            time.sleep(delay)  # the delay set by the user.
            current_pos = self.device_id.get_pos()
            print(f"Moved to: {current_pos}")

        self.stop_button.state(["disabled"])  # disabling the stop button
        self.stop_button.config(style="Disabled.TButton")
        self.go_button.state(["!disabled"])  # activating the go button
        self.go_button.config(style="TButton")

        self.message_label.config(text="Macro finished")

    def stop(self):
        # stops the macro mid-run when "stop" is pressed
        self.stop_event.set()
        self.message_label.config(text="Macro stopping...")
        self.stop_button.state(["disabled"])
        self.stop_button.config(style="Disabled.TButton")
        self.go_button.state(["!disabled"])
        self.go_button.config(style="TButton")

    def quit(self):
        self.quit_event.set()
        self.device_id.stop()
        self.message_label.config(text="Quitting...")

        # wait for macro thread to finish if it's running
        if hasattr(self, "run_thread") and self.run_thread.is_alive():
            self.run_thread.join(timeout=2)  # wait up to 2 seconds before quitting

        self._root.destroy()  # closes the window and exits the program


def main():
    # creates the tkinter user interface with a name "window" and gives it a title
    window = Tk()
    window.title("sensapex macro by sanni")

    # gives the new user interface "window" the attributes that belong to class UI and names this new thing "ui"
    ui = UI(window)
    # ui interface (part of the UI class) is started
    ui.start()

    # stop window from shrinking:
    window.minsize(width=400, height=300)

    # the command that is called to make the program start checking the window for events,
    # such as pressing buttons STOP and GO. Without this, the window will be useless.
    window.mainloop()
    # the rest of the functions happen inside the UI class, so that functions called by pressing buttons
    # are called directly


if __name__ == "__main__":
    main()

