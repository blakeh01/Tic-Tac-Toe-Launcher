import max7219
from machine import Pin, SPI


class LEDMatrix:

    def __init__(self, pin_sck=18, pin_mosi=19, pin_cs=17):
        # ----------------------------------------- CONFIGURE IO ----------------------------------------- #

        self.display = max7219.Matrix8x8(SPI(0, sck=Pin(pin_sck), mosi=Pin(pin_mosi)), Pin(pin_cs, Pin.OUT), 8)

        # ----------------------------------------- INITIALIZE ----------------------------------------- #

        self.display.brightness(10)
        self.reset_disp()

        # ----------------------------------------- PROG PARAMS ----------------------------------------- #

        self.scroll_speed = 10  # ms (accuracy of 10 ms)
        self.next_update = 0
        self.cur_message = ""

        self.flash = False
        self.flash_rate = 0
        self.disp_empty = False

        self.column = 0
        self.buf_x = 0
        self.buf_start = 32

    def update(self, ticks_elapsed):
        if self.cur_message == "" or self.cur_message is None:
            self.reset_disp()
        else:
            if ticks_elapsed >= self.next_update and self.column > 0:
                if self.buf_x > -self.column:
                    self.display.fill(0)
                    self.display.text(self.cur_message, self.buf_x, 0, 1)
                    self.display.show()

                    self.buf_x = self.buf_x - 1
                    self.next_update = ticks_elapsed + self.scroll_speed
                else:
                    self.buf_x = self.buf_start

            if self.flash and self.column == 0:
                if ticks_elapsed >= self.next_update:
                    if not self.disp_empty:
                        self.display.fill(0)
                        self.display.text(self.cur_message, 0, 0, 1)
                        self.display.show()
                        self.disp_empty = True
                    else:
                        self.display.fill(0)
                        self.display.show()
                        self.disp_empty = False

                    self.next_update = ticks_elapsed + self.flash_rate  # 250 ms flash

    def disp_flashing_message(self, message, rate):
        if message == self.cur_message:
            return

        self.reset_disp()
        self.flash = True
        self.flash_rate = rate
        self.cur_message = message
        self.display.fill(0)
        self.display.text(self.cur_message, 0, 0, 1)
        self.display.show()

    def disp_static_message(self, message):
        if message == self.cur_message:
            return

        self.reset_disp()
        self.cur_message = message
        self.display.fill(0)
        self.display.text(self.cur_message, 0, 0, 1)
        self.display.show()

    def disp_scrolling_message(self, message, scroll_speed=10):
        if message == self.cur_message:
            return

        self.reset_disp()
        self.cur_message = message
        self.scroll_speed = scroll_speed
        self.column = len(message) * 8
        self.buf_x = self.buf_start

    def reset_disp(self):
        self.column = 0
        self.flash = False
        self.flash_rate = 0
        self.next_update = 0
        self.display.fill(0)
        self.display.show()
