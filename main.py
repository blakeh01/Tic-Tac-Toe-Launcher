import os
import machine
import neopixel
import time

from led_matrix import LEDMatrix
from mcp23017 import MCP23017
from stepper_ctrl import StepperController
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
        self.beam_states = [0] * len(self.beam_idx)
        self.beam_change_counter = [0 for _ in self.beam_pins]  # used in debouncing
        self.beam_debounce_delay = 1  # in millis

        # configure LED matrix
        self.led_matrix = LEDMatrix()
        self.led_matrix.disp_static_message("INITIALIZING...")

        # configure control pad LEDs
        self.ctrl_leds = neopixel.Neopixel(9, 0, 15, "GRB")
        self.ctrl_leds.brightness(50)
        self.ctrl_leds.fill((255, 255, 255))

        # configure landing zone LEDs
        self.lz_leds = neopixel.Neopixel(9, 1, 16, "GRB")
        self.ctrl_leds.brightness(255)
        self.lz_leds.fill((255, 255, 255))

        # configure expander board
        self.mcp = MCP23017(I2C(0, scl=Pin(1), sda=Pin(0)), 0x20)

        # configure stepper controller
        self.steppers = StepperController(self.mcp)

        # ----------------------------------------- PROG PARAMS ----------------------------------------- #

        self.game_state = MAIN_MENU  # game state machine - are we disp instructions? are we playing?
        self.current_player = True  # true player 1, false player 2

        self.cur_board = [
            0, 0, 0,
            0, 0, 0,
            0, 0, 0
        ]

        self.has_announced_mode = False

        self.launch_flag = False
        self.launch_duration = 250  # solenoid power on duration in ms

        self.score_flag = False
        self.score_celebration_duration = 3000  # how long to wait before continuing game after a score

        self.aim_cd = 250  # how long to wait between aim actions
        self.aim_long_press = 3  # how many btn updates before turbo mode tbd
        self.manual_theta = 0
        self.manual_phi = 0

        self.action_timer = 0

        print("Initialization complete!")

    def update(self, ticks_elapsed):
        # ----------------------------------------- UPDATE MCU ----------------------------------------- #

        # update pico led
        if ticks_elapsed >= self.led_timer:
            if self.pico_led.value():
                self.pico_led.off()
            else:
                self.pico_led.on()
            self.led_timer = ticks_elapsed + 250

        # update LED matrix for displaying scrolling messages
        self.led_matrix.update(ticks_elapsed)

        # update GPIO states
        self.update_btn_gpio()
        self.update_beam_gpio()

        # ----------------------------------------- HANDLE FLAGS ----------------------------------------- #
        if self.launch_flag and self.action_timer > 0:
            self.mcp[0].output(1)
            if self.action_timer >= ticks_elapsed:
                self.mcp[0].output(0)
                self.action_timer = 0

        # ----------------------------------------- GAME STATE MACHINE ----------------------------------------- #

        # ------------------- MAIN MENU ------------------- #
        if self.game_state == MAIN_MENU:
            self.led_matrix.disp_scrolling_message(
                "Welcome To Tic-Tac-Toe Mortar Launcher! PRESS RED BUTTON TO CONTINUE!")
            self.ctrl_leds.set_pixel(4, (255, 0, 0))
            self.ctrl_leds.show()

            if self.btn_states[4] == 0:
                self.game_state = SELECT_MODE
                self.ctrl_leds.clear()
                self.ctrl_leds.show()

        # ------------------- SELECT MODE ------------------- #
        elif self.game_state == SELECT_MODE:
            self.led_matrix.disp_scrolling_message("SELECT GAME MODE!")
            self.ctrl_leds.set_pixel(1, (255, 0, 0))
            self.ctrl_leds.set_pixel(7, (255, 0, 0))
            self.ctrl_leds.show()

            if self.btn_states[1] == 0 or self.btn_states[7] == 0:
                self.game_state = AUTO_MODE if self.btn_states[1] == 0 else MANUAL_MODE
                self.ctrl_leds.clear()
                self.ctrl_leds.show()
                self.action_timer = ticks_elapsed + 3000  # 3 seconds

        # ------------------- MANUAL MODE ------------------- #
        elif self.game_state == MANUAL_MODE:
            # announce that the game has started and set current player
            if not self.has_announced_mode:
                self.ctrl_leds.fill((0, 150, 255))
                self.ctrl_leds.show()
                self.led_matrix.disp_scrolling_message("STARTING MANUAL MODE IN 3...2...1")
                if self.action_timer > ticks_elapsed:
                    self.has_announced_mode = True
                    self.action_timer = 0
                    self.ctrl_leds.clear()
                    self.ctrl_leds.show()
                    self.led_matrix.disp_static_message("PLAYER 1")  # todo randomize first player?
                    self.current_player = True
            else:
                if not self.launch_flag and self.action_timer == 0:
                    if self.btn_states[1] == 0:  # aim up
                        self.manual_theta += 5
                        if self.manual_theta > 90: self.manual_theta = 90
                        self.steppers.write_theta(self.manual_theta)
                        self.action_timer = ticks_elapsed + self.aim_cd

                    elif self.btn_states[3] == 0:  # aim left
                        pass
                        self.action_timer = ticks_elapsed + self.aim_cd

                    elif self.btn_states[4] == 0 and not self.launch_flag:  # shoot!
                        print("FIRING!")
                        self.launch_flag = True
                        self.action_timer = ticks_elapsed + self.launch_duration

                    elif self.btn_states[5] == 0:  # aim right
                        pass
                        self.action_timer = ticks_elapsed + self.aim_cd

                    elif self.btn_states[7] == 0:
                        self.manual_theta -= 5
                        if self.manual_theta < 0: self.manual_theta = 0

                        self.steppers.write_theta(self.manual_theta)
                        self.action_timer = ticks_elapsed + self.aim_cd

                if self.action_timer <= ticks_elapsed:
                    self.action_timer = 0

        # ------------------- AUTO MODE ------------------- #
        elif self.game_state == AUTO_MODE:
            pass

        # ------------------- GAME OVER ------------------- #
        elif self.game_state == GAME_OVER:
            pass

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
        current_beam_states = [button.value() for button in self.beam_pins]

        # check for how long a change has been active, if its for as long as debounce delay, we can know that must be
        # the current state!
        for i in range(len(self.beam_pins)):
            if current_beam_states[i] != self.beam_states[i]:
                self.beam_change_counter[i] += 1
                if self.beam_change_counter[i] > self.beam_debounce_delay:
                    self.beam_states[i] = current_beam_states[i]
            else:
                self.beam_change_counter[i] = 0

    def toggle_led(self):
        print("hi")
        if self.pico_led.value():
            self.pico_led.off()
        else:
            self.pico_led.on()


machine.freq(200_000_000)  # boost pico clock to 200 MHz
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
