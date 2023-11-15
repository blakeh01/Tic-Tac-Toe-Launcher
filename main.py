import os
import machine
import neopixel
import time

from led_matrix import LEDMatrix
from mcp23017 import MCPController

stat = os.statvfs("/")
size = stat[1] * stat[2]
free = stat[0] * stat[3]
used = size - free

print("Size : {:,} bytes, {:,} KB, {} MB".format(size, size / 1024, size / 1024**2))
print("Used : {:,} bytes, {:,} KB, {} MB".format(used, used / 1024, used / 1024**2))
print("Free : {:,} bytes, {:,} KB, {} MB, {} % free".format(free, free / 1024, free / 1024**2, 100 - (round(used / size, 4) * 100)))


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
        self.btn_states = [0] * len(self.btn_idx)
        self.btn_last_change = [time.ticks_ms() for _ in self.btn_pins]  # used in debouncing
        self.btn_debounce_delay = 50  # in millis

        # configure beam break IO, might want to put these on IRQs? (Reset state after certain amount of time)
        self.beam_idx = [20, 21, 22, 26, 27, 28]
        self.beam_pins = [machine.Pin(pin, machine.Pin.IN, machine.Pin.PULL_UP) for pin in self.beam_idx]
        self.beam_states = [0] * len(self.beam_idx)
        self.beam_last_change = [time.ticks_ms() for _ in self.beam_pins]  # used in debouncing
        self.beam_debounce_delay = 1  # in millis

        # configure LED matrix
        self.led_matrix = LEDMatrix()
        self.led_matrix.disp_scrolling_message("Hello World", 10)

        # configure control pad LEDs
        self.ctrl_leds = neopixel.Neopixel(9, 0, 15, "GRB")
        self.ctrl_leds.brightness(50)
        self.ctrl_leds.fill((255, 255, 255))

        # configure landing zone LEDs
        self.lz_leds = neopixel.Neopixel(9, 1, 16, "GRB")
        self.ctrl_leds.brightness(255)
        self.lz_leds.fill((255, 255, 255))

        # configure expander board
        self.mcp = MCPController()

        # ----------------------------------------- PROG PARAMS ----------------------------------------- #

        self.game_state = 0  # game state machine - are we disp instructions? are we playing?
        self.current_player = 1

        self.cur_board = [
            0, 0, 0,
            0, 0, 0,
            0, 0, 0
        ]

        print("Initialization complete!")

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
                self.btn_states[i] = current_button_states[i]  # Update the button state

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
                self.beam_states[i] = current_beam_states[i]  # Update the button state

    def toggle_led(self):
        print("hi")
        if self.pico_led.value():
            self.pico_led.off()
        else:
            self.pico_led.on()


machine.freq(200_000_000)  # boost pico clock to 200 MHz
m = MainProgram()

while True:
    m.update(time.ticks_ms())
    time.sleep_ms(1)  # this essentially means we have an accuracy of ~1 ms, might need to increase this.
