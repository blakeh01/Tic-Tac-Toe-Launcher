import machine
import neopixel
import led_matrix
import array, time
import rp2

from led_matrix import LEDMatrix
from machine import Timer

class MainProgram:

    def __init__(self):
        # ----------------------------------------- CONFIGURE IO ----------------------------------------- #

        # configure LED
        self.pico_led = machine.Pin("LED", machine.Pin.OUT)
        self.led_timer = 0

        # configure button IO
        self.btn_idx = [6, 7, 8, 9, 10, 11, 12, 13, 14]
        self.btn_pins = [machine.Pin(pin, machine.Pin.IN, machine.Pin.PULL_UP) for pin in self.btn_idx]
        self.btn_states = [0] * len(self.btn_idx)
        self.btn_last_change = [time.ticks_ms() for _ in self.btn_pins] # used in debouncing
        self.btn_debounce_delay = 50 # in millis

        # configure beam break IO, might want to put these on IRQs? (Reset state after certain amount of time)
        self.beam_idx = [20, 21, 22, 26, 27, 28]
        self.beam_pins = [machine.Pin(pin, machine.Pin.IN, machine.Pin.PULL_UP) for pin in self.beam_idx]
        self.beam_states = [0] * len(self.beam_idx)
        self.beam_last_change = [time.ticks_ms() for _ in self.beam_pins] # used in debouncing
        self.beam_debounce_delay = 1 # in millis

        # configure LED matrix
        self.led_matrix = LEDMatrix()
        self.led_matrix.set_scrolling_message("Hello World", 10)

        # configure control pad LEDs
        self.ctrl_leds = neopixel.Neopixel(9, 0, 15, "GRB")
        self.ctrl_leds.brightness(20)
        self.ctrl_leds.fill((255, 255, 255))

        # configure landing zone LEDs
        self.lz_leds = neopixel.Neopixel(9, 0, 16, "GRB")
        self.ctrl_leds.brightness(255)
        self.lz_leds.fill((255, 255, 255))

        # ----------------------------------------- PROG PARAMS ----------------------------------------- #

        self.game_state = 0 # game state machine - are we disp instructions? are we playing?

    def update(self, ticks_elapsed):
        # update pico led
        if ticks_elapsed >= self.led_timer:
            if self.pico_led.value():
                self.pico_led.off()
            else:
                self.pico_led.on()
            self.led_timer = ticks_elapsed + 500

        # update LED matrix for displaying scrolling messages
        self.led_matrix.update(ticks_elapsed)

        # update GPIO states
        self.update_btn_gpio(ticks_elapsed)
        self.update_beam_gpio(ticks_elapsed)

    def update_btn_gpio(self, ticks_elapsed):
        # Read the button states
        current_button_states = [button.value() for button in self.btn_pins]

        # Check for changes in button states
        for i in range(len(self.btn_pins)):
            if current_button_states[i] != self.btn_states[i]:
                self.btn_last_change[i] = ticks_elapsed

        # Check if each button state has been stable for the debounce delay
        for i in range(len(self.btn_pins)):
            if time.ticks_diff(ticks_elapsed, self.btn_last_change[i]) > self.btn_debounce_delay:
                self.btn_states[i] = current_button_states[i] # Update the button state

    def update_beam_gpio(self, ticks_elapsed):
        # Read the beam states
        current_beam_states = [beam.value() for beam in self.beam_pins]

        # Check for changes in beam states
        for i in range(len(self.beam_pins)):
            if current_beam_states[i] != self.beam_states[i]:
                self.beam_last_change[i] = ticks_elapsed

        # Check if each button state has been stable for the debounce delay
        for i in range(len(self.beam_pins)):
            if time.ticks_diff(ticks_elapsed, self.beam_last_change[i]) > self.beam_debounce_delay:
                self.beam_states[i] = current_beam_states[i] # Update the button state

    def toggle_led(self):
        print("hi")
        if self.pico_led.value():
            self.pico_led.off()
        else:
            self.pico_led.on()


machine.freq(200_000_000) # boost pico clock to 200 mHz
m = MainProgram()

while True:
    m.update(time.ticks_ms())
    time.sleep_ms(1) # this essentially means we have an accuracy of ~1 ms, might need to increase this.


# -------------------------------- Initialize button pins and its interrupt triggers ----------------------------------

# Configure button pins and its interrupt triggers
btn_pin_num_list = [6, 7, 8, 9, 10, 11, 12, 13, 14]
for button_index in range(len(btn_pin_num_list)):
    btn_pin_num = btn_pin_num_list[button_index]
    btn_num = Pin(btn_pin_num, Pin.IN, Pin.PULL_UP)
    btn_num.irq(trigger=Pin.IRQ_FALLING, handler=lambda btn_pin_num=btn_pin_num, index=button_index: button_isr(index))

# Create interrupt flag list initialized with all zeros
interrupt_btn_flag_list = [0] * len(btn_pin_num_list)
debounce_time = 0  # Set debouncing time for each button

# General interrupt service routine for all nine buttons
def button_isr(button_index):
    global interrupt_btn_flag_list, debounce_time
    if (time.ticks_ms() - debounce_time) > 500:
        interrupt_btn_flag_list[button_index] = 1
        debounce_time = time.ticks_ms()


# --------------------------------------- Initialize LED Matrix Module ---------------------------------------------

spi = SPI(0, sck=Pin(18), mosi=Pin(19))
cs = Pin(17, Pin.OUT)

display = max7219.Matrix8x8(spi, cs, 8)
display.brightness(10)

display.fill(0)
display.show()
time.sleep(1)

# --------------------------------------- Initialize Addressable LEDs ----------------------------------------------

leds = Neopixel(9, 0, 15, "GRB")

blank = (0, 0, 0)
red = (255, 0, 0)
orange = (255, 50, 0)
yellow = (255, 100, 0)
green = (0, 255, 0)
blue = (0, 0, 255)
indigo = (100, 0, 90)
violet = (200, 0, 100)
colors_rgb = [red, orange, yellow, green, blue, indigo, violet]

delay = 0.5
leds.brightness(50)

leds.clear()
leds.show()

# ------------------------------------- Setup Angle values and stepper motors -----------------------------------------

# Set step and direction A4988 pins to outputs
theta_step_pin = Pin(2, Pin.OUT)
theta_dir_pin = Pin(3, Pin.OUT)
phi_step_pin = Pin(4, Pin.OUT)
phi_dir_pin = Pin(5, Pin.OUT)

# Scale factor to convert angle to total amount of steps (not decided yet)
Scale_factor = 1 / 0.225

# Angle values in lists (will change later)
PHI_list = [15, 0, 15, 20, 0, 20, 25, 0, 25]  # -90 <= PHI <= 90
THETA_list = [45, 45, 45, 45, 45, 45, 45, 45, 45]  # 45 <= THETA <= 90

# Lists to store nine different steps for each angle
AZIMUTHAL_steps_list = []
POLAR_steps_list = []

# Two for-loops that calculate the steps for each landing position and stores it in lists
for i in range(len(PHI_list)):
    AZIMUTHAL_steps = round(PHI_list[i] * Scale_factor)
    AZIMUTHAL_steps_list.append(AZIMUTHAL_steps)
for j in range(len(THETA_list)):
    POLAR_steps = round(THETA_list[j] * Scale_factor)
    POLAR_steps_list.append(POLAR_steps)


# ----------------------- Configure Beam Break Sensor Receivers -------------------------------------------------

# beam_break1 = Pin(16, Pin.IN, Pin.PULL_UP)
# beam_break2 = Pin(, Pin.IN, Pin.PULL_UP)
# beam_break3 = Pin(, Pin.IN, Pin.PULL_UP)
# beam_break4 = Pin(, Pin.IN, Pin.PULL_UP)
# beam_break5 = Pin(, Pin.IN, Pin.PULL_UP)
# beam_break6 = Pin(, Pin.IN, Pin.PULL_UP)

# IR_receiver_pin_list[16, 2, 2, 2, 2, 2, 2, 2, 2]

# for receiver_index in range(len(IR_receiver_pin_list)):
#   IR_receiver_pin = IR_receiver_pin_list[receiver_index]
#  receiver = Pin(IR_receiver_pin, Pin.IN, Pin.PULL_UP)

# ---------------------------------------------- FUNCTIONS -----------------------------------------------------------

def display_game_title():
    message = "Welcome To Tic-Tac-Toe Mortar Launcher! PRESS RED BUTTON TO CONTINUE!"
    column = (len(message) * 8)
    leds.set_pixel(4, red)
    leds.show()
    for x in range(32, -column, -1):
        if (interrupt_btn_flag_list[4] == 1):
            display.fill(0)
            display.show()
            leds.clear()
            leds.show()
            break
        display.fill(0)
        display.text(message, x, 0, 1)
        display.show()
        time.sleep(0.01)


def select_game_mode():
    message = "Select Game Mode"
    column = (len(message) * 8)
    leds.set_pixel(1, red)
    leds.set_pixel(7, red)
    leds.show()
    for x in range(32, -column, -1):
        if (interrupt_btn_flag_list[1] == 1):
            display.fill(0)
            display.show()
            leds.clear()
            leds.show()
            break
        if (interrupt_btn_flag_list[7] == 1):
            display.fill(0)
            display.show()
            leds.clear()
            leds.show()
            break
        display.fill(0)
        display.text(message, x, 0, 1)
        display.show()
        time.sleep(0.01)

    if (interrupt_btn_flag_list[1] == 1):
        message = "You chose autonomous mode. STARTING IN 3...2...1"
        column = (len(message) * 8)
        for x in range(32, -column, -1):
            display.fill(0)
            display.text(message, x, 0, 1)
            display.show()
            time.sleep(0.01)
        return True

    if (interrupt_btn_flag_list[7] == 1):
        message = "You chose manual mode. STARTING IN 3...2...1"
        column = (len(message) * 8)
        for x in range(32, -column, -1):
            display.fill(0)
            display.text(message, x, 0, 1)
            display.show()
            time.sleep(0.01)
        return False


def move_steppers_to_target():
    # Map each cup position to a stepper spin direction
    if (button_index == 0 or button_index == 3 or button_index == 6):
        phi_dir_pin.on()
    else:
        phi_dir_pin.off()
    theta_dir_pin.on()

    # Move mortar launcher to target
    for i in range(abs(AZIMUTHAL_steps_list[button_index])):
        phi_step_pin.on()
        time.sleep(0.001)
        phi_step_pin.off()
        time.sleep(0.001)

    for i in range(abs(POLAR_steps_list[button_index])):
        theta_step_pin.on()
        time.sleep(0.001)
        theta_step_pin.off()
        time.sleep(0.001)


def launch_ball():
    # --------------------------------------------------------
    # Servo code to launch ball....
    #
    #
    time.sleep(2)
    # --------------------------------------------------------


# def beam_break_detect(which_player, button_index):
#     if (which_player == True):
#         # Set addressable LED color to Red  (Player 1)
#     else:
#         # set addressable LED color to Blue (Player 2)
#    
#     if (button_index == 0):
#         if (beam_break1.value() == 0 and beam_break4.value() == 0):
#             # Turn addressable LED on for cup 1
#         else:
#             # I don't know yet
#    
#     if (button_index == 1):
#         if (beam_break1.value() == 0 and beam_break5.value() == 0):
#             # Turn addressable LED on for cup 1
#         else:
#             # I don't know yet
#    
#     for i in range(9):


def move_steppers_to_home(button_index):
    # Reverse direction of steppers to go back to home position
    if (button_index == 0 or button_index == 3 or button_index == 6):
        phi_dir_pin.off()
    else:
        phi_dir_pin.on()
    theta_dir_pin.off()

    # Move mortar launcher back to home position
    for i in range(abs(POLAR_steps_list[button_index])):
        theta_step_pin.on()
        time.sleep(0.001)
        theta_step_pin.off()
        time.sleep(0.001)
    for i in range(abs(AZIMUTHAL_steps_list[button_index])):
        phi_step_pin.on()
        time.sleep(0.001)
        phi_step_pin.off()
        time.sleep(0.001)


# ----------------------------------------------- Main Code -------------------------------------------------------

# Displays game title on LED matrix module
# Waits until a player presses red button to start game
while (interrupt_btn_flag_list[4] == 0):
    display_game_title()
interrupt_btn_flag_list = [0] * len(btn_pin_num_list)

# Displays "Select Game Mode" on LED matrix module
# Waits until a player presses either button for a game mode
# Displays "You chose autonomous/manual game mode"
while (interrupt_btn_flag_list[1] == 0 and interrupt_btn_flag_list[7] == 0):
    mode = select_game_mode()
interrupt_btn_flag_list = [0] * len(btn_pin_num_list)

P1_WINS = False
P2_WINS = False
which_player = True

display.fill(0)
display.text("PLAYER 1", 0, 0, 1)
display.show()

# -------------------------------------------

while ((P1_WINS == False) and (P2_WINS == False)):
    for button_index in range(len(interrupt_btn_flag_list)):
        if (interrupt_btn_flag_list[button_index] == 1):
            move_steppers_to_target()
            launch_ball()
            # beam_break_detect(which_player, button_index)
            move_steppers_to_home(button_index)
            interrupt_btn_flag_list[button_index] = 0