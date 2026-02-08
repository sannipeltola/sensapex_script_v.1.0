# sensapex_script_v.1.0
A script for moving a Sensapex uMp-3 micromanipulator from a computer by Sanni Peltola

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
enough to warrant movement. For this to work, manipulator would need to move back and forth.

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
from your file location in "sys.path.append("location") at line 53. Otherwise, the code won't find the python package
needed and won't work. If pip works on your computer, you can use: pip install sensapex instead. Better instructions can be found at
https://github.com/sensapex
