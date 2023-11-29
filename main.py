import os
import machine
import neopixel
import time

from led_matrix import LEDMatrix
from mcp23017 import MCP23017
from stepper import StepperController
from machine import Pin, I2C

stat = os.statvfs("/")
size = stat[1] * stat[2]
free = stat[0] * stat[3]
used = size - free

print("Size : {:,} bytes, {:,} KB, {} MB".format(size, size / 1024, size / 1024 ** 2))
print("Used : {:,} bytes, {:,} KB, {} MB".format(used, used / 1024, used / 1024 ** 2))
print("Free : {:,} bytes, {:,} KB, {} MB, {} % free".format(free, free / 1024, free / 1024 ** 2,
                                                            100 - (round(used / size, 4) * 100)))

MAIN_MENU = 0
SELECT_MODE = 1
MANUAL_MODE = 2
AUTO_MODE = 3
GAME_OVER = 4

LAUNCH = 5
WAIT_SCORE = 6


class MainProgram:

    def __init__(self):
        # ----------------------------------------- CONFIGURE IO ----------------------------------------- #
        print("Starting up...")

        # configure LED
        self.pico_led = machine.Pin("LED", machine.Pin.OUT)
        self.led_timer = 0

        # configure button IO
        self.btn_idx = [6, 7, 8, 9, 10, 11, 12, 13, 14]
        self.btn_pins = [machine.Pin(pin, machine.Pin.IN, machine.Pin.PULL_UP) for pin in self.btn_idx]
        self.btn_states = [1] * len(self.btn_idx)
        self.btn_change_counter = [0 for _ in self.btn_pins]  # used in debouncing
        self.btn_debounce_delay = 50  # in millis

        # configure beam break IO, might want to put these on IRQs? (Reset state after certain amount of time)
        self.beam_idx = [20, 21, 22, 26, 27, 28]
        self.beam_pins = [machine.Pin(pin, machine.Pin.IN, machine.Pin.PULL_UP) for pin in self.beam_idx]
        self.beam_states = [1] * len(self.beam_idx)
        self.beam_reset_counter = 0

        # configure LED matrix
        self.led_matrix = LEDMatrix()
        self.led_matrix.disp_static_message("INIT")

        # configure control pad LEDs
        self.ctrl_leds = neopixel.Neopixel(9, 0, 15, "GRB")
        self.ctrl_leds.brightness(5)
        self.ctrl_leds.fill((255, 255, 255))
        self.ctrl_leds.show()

        # configure landing zone LEDs
        self.lz_leds = neopixel.Neopixel(9, 1, 16, "GRB")
        self.ctrl_leds.brightness(255)
        self.lz_leds.fill((255, 255, 255))
        self.ctrl_leds.show()

        # configure expander board
        self.mcp = MCP23017(I2C(0, scl=Pin(1), sda=Pin(0)), 0x20)

        # configure stepper controller
        self.steppers = StepperController(self.mcp)
        #self.steppers.home()

        # ----------------------------------------- PROG PARAMS ----------------------------------------- #

        self.game_state = MAIN_MENU  # game state machine - are we disp instructions? are we playing?
        self.last_game_state = MAIN_MENU  # used as a way to loop back after launching/scoring
        self.current_player = True  # true player 1, false player 2

        self.cur_board = [
            0, 0, 0,
            0, 0, 0,
            0, 0, 0
        ]

        self.launch_duration = 500  # solenoid power on duration in ms
        self.score_timeout = 5000  # how long to wait until a miss is determined (5s)

        self.aim_cd = 250  # how long to wait between aim actions
        self.manual_theta = 0
        self.manual_phi = 0

        self.action_timer = 0  # general purpose timer for game purposes.

        print("Initialization complete!")

    def update(self, ticks_elapsed):
        # ----------------------------------------- UPDATE MCU ----------------------------------------- #

        # update pico led & rgb leds
        if ticks_elapsed >= self.led_timer:
            if self.pico_led.value():
                self.pico_led.off()
                self.ctrl_leds.show()
                self.lz_leds.show()  # also notifying the led
            else:
                self.pico_led.on()
                self.ctrl_leds.show()
                self.lz_leds.show()  # also notifying the leds.
            self.led_timer = ticks_elapsed + 250

        # update LED matrix for displaying scrolling messages
        self.led_matrix.update(ticks_elapsed)

        # update GPIO states
        self.update_btn_gpio()
        self.update_beam_gpio()

        # update stepper motors
        self.steppers.update_steppers()

        # update landing zone leds
        for i in self.cur_board:
            if i == 0: self.ctrl_leds.set_pixel_nfu(i, (255, 255, 255))
            elif i == 1: self.ctrl_leds.set_pixel_nfu(i, (255, 0, 0))
            elif i == 2: self.ctrl_leds.set_pixel_nfu(i, (0, 0, 255))

        # ----------------------------------------- GAME STATE MACHINE ----------------------------------------- #

        # ------------------- MAIN MENU ------------------- #
        if self.game_state == MAIN_MENU:
            self.led_matrix.disp_scrolling_message(
                "Welcome To Tic-Tac-Toe Mortar Launcher! PRESS RED BUTTON TO CONTINUE!")
            self.ctrl_leds.set_pixel_nfu(4, (255, 0, 0))

            if self.btn_states[4] == 0:
                self.game_state = SELECT_MODE
                self.ctrl_leds.clear()

        # ------------------- SELECT MODE ------------------- #
        elif self.game_state == SELECT_MODE:
            self.led_matrix.disp_scrolling_message("SELECT GAME MODE!")
            self.ctrl_leds.set_pixel_nfu(1, (255, 0, 0))
            self.ctrl_leds.set_pixel_nfu(7, (255, 0, 0))

            if self.btn_states[1] == 0 or self.btn_states[7] == 0:
                self.game_state = AUTO_MODE if self.btn_states[1] == 0 else MANUAL_MODE
                self.ctrl_leds.clear()

        # ------------------- MANUAL MODE ------------------- #
        elif self.game_state == MANUAL_MODE:
            self.ctrl_leds.set_pixel_nfu(4, (255, 0, 0))
            self.ctrl_leds.set_pixel_nfu(1, (255, 255, 255))
            self.ctrl_leds.set_pixel_nfu(3, (255, 255, 255))
            self.ctrl_leds.set_pixel_nfu(5, (255, 255, 255))
            self.ctrl_leds.set_pixel_nfu(7, (255, 255, 255))
            self.led_matrix.disp_static_message("P1 GO!" if self.current_player else "P2 GO!")

            if self.btn_states[1] == 0 and ticks_elapsed >= self.action_timer:  # aim up
                self.manual_theta += 5
                self.steppers.write_theta(self.manual_theta)
                self.action_timer = ticks_elapsed + self.aim_cd

            elif self.btn_states[3] == 0 and ticks_elapsed >= self.action_timer:  # aim left
                self.manual_phi += 5
                self.steppers.write_phi(self.manual_phi)
                self.action_timer = ticks_elapsed + self.aim_cd

            elif self.btn_states[4] == 0:  # shoot!
                print("FIRING!")
                self.last_game_state = self.game_state
                self.game_state = LAUNCH
                self.action_timer = ticks_elapsed + self.launch_duration

            elif self.btn_states[5] == 0 and ticks_elapsed >= self.action_timer:  # aim right
                self.manual_phi -= 5
                self.steppers.write_phi(self.manual_phi)
                self.action_timer = ticks_elapsed + self.aim_cd

            elif self.btn_states[7] == 0 and ticks_elapsed >= self.action_timer: # aim down
                self.manual_theta -= 5
                self.steppers.write_theta(self.manual_theta)
                self.action_timer = ticks_elapsed + self.aim_cd

        # ------------------- AUTO MODE ------------------- #
        elif self.game_state == AUTO_MODE:

            if self.btn_states[1] == 0 and ticks_elapsed >= self.action_timer:  # aim up
                self.manual_theta += 5
                if self.manual_theta > 90:
                    self.manual_theta = 90
                self.steppers.write_theta(self.manual_theta)
                self.action_timer = ticks_elapsed + self.aim_cd

            elif self.btn_states[3] == 0 and ticks_elapsed >= self.action_timer:  # aim left
                self.manual_phi += 1
                if self.manual_phi > 180:
                    self.manual_phi = 180
                self.steppers.write_phi(self.manual_phi)
                self.action_timer = ticks_elapsed + self.aim_cd

            elif self.btn_states[4] == 0:  # shoot!
                print("FIRING!")
                self.last_game_state = self.game_state
                self.game_state = LAUNCH
                self.action_timer = ticks_elapsed + self.launch_duration

            elif self.btn_states[5] == 0 and ticks_elapsed >= self.action_timer:  # aim right
                self.manual_phi -= 1
                if self.manual_phi > 180:
                    self.manual_phi = 180
                self.steppers.write_phi(self.manual_phi)
                self.action_timer = ticks_elapsed + self.aim_cd

            elif self.btn_states[7] == 0 and ticks_elapsed >= self.action_timer: # aim down
                self.manual_theta -= 5
                if self.manual_theta < 0:
                    self.manual_theta = 0
                self.steppers.write_theta(self.manual_theta)
                self.action_timer = ticks_elapsed + self.aim_cd

            if self.btn_states[0]:  # TODO: use manual mode to find steps to make shot.
                print(self.manual_theta, self.manual_phi)

        # ------------------- LAUNCH ------------------- #
        elif self.game_state == LAUNCH:
            self.mcp[0].output(1)
            self.led_matrix.disp_flashing_message("BOOM!", 250)

            if ticks_elapsed >= self.action_timer:
                self.mcp[0].output(0)
                self.action_timer = ticks_elapsed + self.score_timeout
                self.game_state = WAIT_SCORE

        # ------------------- WAIT FOR SCORE ------------------- #
        elif self.game_state == WAIT_SCORE:

            # score_idx = self.find_position_index()
            # if score_idx is not None:
            #     self.ctrl_leds.set_pixel_nfu(score_idx, (255, 0, 0) if self.current_player else (0, 0, 255))
            #     self.led_matrix.disp_flashing_message("P1 SCORE!" if self.current_player else "P2 SCORE!", 250)

            if self.check_score():
                self.led_matrix.disp_flashing_message("P1 SCORE!" if self.current_player else "P2 SCORE!", 250)

            if ticks_elapsed >= self.action_timer:
                if self.check_winner():
                    self.game_state = GAME_OVER
                    self.action_timer = ticks_elapsed + 5000  # disp player win for 5 seconds

                self.game_state = self.last_game_state
                self.action_timer = 0
                self.current_player = not self.current_player

        # ------------------- GAME OVER ------------------- #
        elif self.game_state == GAME_OVER:
            if ticks_elapsed <= self.action_timer:
                if self.check_winner() == 1:
                    self.led_matrix.disp_flashing_message("P1 WINS!", 250)
                elif self.check_winner() == 2:
                    self.led_matrix.disp_flashing_message("P2 WINS!", 250)

            else:
                self.led_matrix.disp_scrolling_message("PRESS ANY BUTTON TO PLAY AGAIN!")
                if any(self.btn_states):
                    self.reset_game()

    def update_btn_gpio(self):
        # Read the button states
        current_button_states = [button.value() for button in self.btn_pins]

        # check for how long a change has been active, if its for as long as debounce delay, we can know that must be
        # the current state!
        for i in range(len(self.btn_pins)):
            if current_button_states[i] != self.btn_states[i]:
                self.btn_change_counter[i] += 1
                if self.btn_change_counter[i] > self.btn_debounce_delay:
                    self.btn_states[i] = current_button_states[i]
            else:
                self.btn_change_counter[i] = 0

    def update_beam_gpio(self):
        # Read the beam states
        current_beam_states = [beam.value() for beam in self.beam_pins]

        # essentially, we want to set our beam states when they are first broken
        # and we want that state to stay even after the beam is regained
        # we only reset after a short duration, this gives us the best chance at detecting the ball.

        for i in range(len(self.beam_pins)):
            if self.beam_states[i] != current_beam_states[i] and current_beam_states[i] == 1:
                self.beam_states[i] = current_beam_states[i]
                self.beam_reset_counter = 0

        self.beam_reset_counter += 1

        if self.beam_reset_counter > 500:
            self.beam_states = current_beam_states
            self.beam_reset_counter = 0

    def check_winner(self):
        # Check rows
        for i in range(0, 9, 3):
            if self.cur_board[i] == self.cur_board[i + 1] == self.cur_board[i + 2] and self.cur_board[i] in ['1', '2']:
                return self.cur_board[i]

        # Check columns
        for i in range(3):
            if self.cur_board[i] == self.cur_board[i + 3] == self.cur_board[i + 6] and self.cur_board[i] in ['1', '2']:
                return self.cur_board[i]

        # Check diagonals
        if self.cur_board[0] == self.cur_board[4] == self.cur_board[8] and self.cur_board[0] in ['1', '2']:
            return self.cur_board[0]
        if self.cur_board[2] == self.cur_board[4] == self.cur_board[6] and self.cur_board[2] in ['1', '2']:
            return self.cur_board[2]

        return None

    def check_score(self):
        pos_arr = [
            (2, 3),  # bottom right (from launcher) pos 1
            (1, 3),  # pos 2
            (0, 3),  # .
            (0, 4),
            (1, 4),
            (2, 4),
            (2, 5),
            (1, 5),  # pos 8
            (0, 5)  # pos 9
        ]

        # Find the position index
        zero_indices = [i for i, value in enumerate(self.beam_states) if value == 0]

        if len(zero_indices) == 2:
            # Check if the zero indices array is in the pos_arr
            if zero_indices in [list(index) for index in pos_arr]:
                # Define the custom mapping
                mapping = [0, 1, 2, 5, 4, 3, 6, 7, 8]

                # Update the cur_board based on the mapping and zero_indices
                self.cur_board[mapping[[list(index) for index in pos_arr].index(zero_indices)]] = 1

                return True
        return False

    # def find_position_index(self):
    #     pos_arr = [
    #         (2, 3),  # bottom right (from launcher) pos 1
    #         (1, 3),  # pos 2
    #         (0, 3),  # .
    #         (0, 4),
    #         (1, 4),
    #         (2, 4),
    #         (2, 5),
    #         (1, 5),  # pos 8
    #         (0, 5)  # pos 9
    #     ]
    #
    #     # Find indices of zeros in beam_state_ex
    #     zero_indices = [i for i, value in enumerate(self.beam_states) if value == 0]
    #
    #     # Check if there are exactly two zeros
    #     if len(zero_indices) == 2:
    #         # Check if the zero indices array is in the pos_arr
    #         if zero_indices in [list(index) for index in pos_arr]:
    #             # Return the index of the zero indices array in pos_arr
    #             return [list(index) for index in pos_arr].index(zero_indices)
    #         else:
    #             return None
    #     else:
    #         # Return None if the number of zeros is not two
    #         return None

    def reset_game(self):
        self.cur_board = [0] * 9
        self.action_timer = 0


machine.freq(250_000_000)  # boost pico clock to 250 MHz
m = MainProgram()

total_ticks = 0
tick_ref = 0
d_tick = 0

while True:
    tick_ref = time.ticks_ms()
    m.update(total_ticks)
    time.sleep_ms(1)  # this essentially means we have an accuracy of ~1 ms, might need to increase this.
    d_tick = time.ticks_diff(time.ticks_ms(), tick_ref)
    total_ticks += d_tick
