import machine
import math

from machine import Pin

from mcp23017 import MCP23017


class StepperController:

    def __init__(self, mcp: MCP23017):
        self.mcp = mcp
        self.switch_phi = mcp[3]
        self.switch_theta = mcp[4]

        self.theta_sps = 400
        self.stepper_theta_a = Stepper(2, 3, steps_per_rev=200,
                                       speed=self.theta_sps)  # 1600 steps / rev @ 400 sps = 4 s / rev
        self.stepper_theta_b = Stepper(4, 5, invert_dir=True, steps_per_rev=200,
                                       speed=self.theta_sps)  # 1600 steps / rev @ 400 sps = 4 s / rev

        self.at_home = False
        self.run = False

        # self.home()

    def update_steppers(self, ticks_elapsed):
        if not self.at_home or not self.run:
            return

    def write_theta(self, deg):
        self.stepper_theta_a.target_deg(deg)
        self.stepper_theta_b.target_deg(deg)

    def write_phi(self, deg):
        self.stepper_phi.target_deg(deg)

    def home(self):
        # this function is BLOCKING... do NOT use when unless you need to.

        self.stepper_phi.speed(self.theta_sps/4)  # in steps per second
        self.stepper_phi.free_run(-1)   # continuously step motor

        while self.switch_phi.value():
            pass  # stall here until switch is triggered

        self.stepper_phi.stop()  # stop motor
        self.stepper_phi.overwrite_pos(0)  # set motor position to 0 (i.e. home)
        self.stepper_phi.speed(self.theta_sps)  # set back to default speed
        self.stepper_phi.track_target()  # re-enable stepper

        self.at_home = True


class Stepper:
    def __init__(self, step_pin: int, dir_pin: int, en_pin=None, steps_per_rev=200, speed=10, invert_dir=False, timer_id=-1):

        if not isinstance(step_pin, machine.Pin):
            step_pin = machine.Pin(step_pin, machine.Pin.OUT)
        if not isinstance(dir_pin, machine.Pin):
            dir_pin = machine.Pin(dir_pin, machine.Pin.OUT)
        if (en_pin != None) and (not isinstance(en_pin, machine.Pin)):
            en_pin = machine.Pin(en_pin, machine.Pin.OUT)

        self.step_value_func = step_pin.value
        self.dir_value_func = dir_pin.value
        self.en_pin = en_pin
        self.invert_dir = invert_dir

        self.timer = machine.Timer(timer_id)
        self.timer_is_running = False
        self.free_run_mode = 0
        self.enabled = True

        self.target_pos = 0
        self.pos = 0
        self.steps_per_sec = speed
        self.steps_per_rev = steps_per_rev

        self.track_target()

    def speed(self, sps):
        self.steps_per_sec = sps
        if self.timer_is_running:
            self.track_target()

    def speed_rps(self, rps):
        self.speed(rps * self.steps_per_rev)

    def target(self, t):
        self.target_pos = t

    def target_deg(self, deg):
        self.target(self.steps_per_rev * deg / 360.0)

    def target_rad(self, rad):
        self.target(self.steps_per_rev * rad / (2.0 * math.pi))

    def get_pos(self):
        return self.pos

    def get_pos_deg(self):
        return self.get_pos() * 360.0 / self.steps_per_rev

    def get_pos_rad(self):
        return self.get_pos() * (2.0 * math.pi) / self.steps_per_rev

    def overwrite_pos(self, p):
        self.pos = 0

    def overwrite_pos_deg(self, deg):
        self.overwrite_pos(deg * self.steps_per_rev / 360.0)

    def overwrite_pos_rad(self, rad):
        self.overwrite_pos(rad * self.steps_per_rev / (2.0 * math.pi))

    def step(self, d):
        if d > 0:
            if self.enabled:
                self.dir_value_func(1 ^ self.invert_dir)
                self.step_value_func(1)
                self.step_value_func(0)
            self.pos += 1
        elif d < 0:
            if self.enabled:
                self.dir_value_func(0 ^ self.invert_dir)
                self.step_value_func(1)
                self.step_value_func(0)
            self.pos -= 1

    def _timer_callback(self, t):
        if self.free_run_mode > 0:
            self.step(1)
        elif self.free_run_mode < 0:
            self.step(-1)
        elif self.target_pos > self.pos:
            self.step(1)
        elif self.target_pos < self.pos:
            self.step(-1)

    def free_run(self, d):
        self.free_run_mode = d
        if self.timer_is_running:
            self.timer.deinit()
        if d != 0:
            self.timer.init(period=int((1/self.steps_per_sec)*1000), callback=self._timer_callback)
            self.timer_is_running = True
        else:
            self.dir_value_func(0)

    def track_target(self):
        self.free_run_mode = 0
        if self.timer_is_running:
            self.timer.deinit()
        self.timer.init(period=int((1/self.steps_per_sec)*1000), callback=self._timer_callback)
        self.timer_is_running = True

    def stop(self):
        self.free_run_mode = 0
        if self.timer_is_running:
            self.timer.deinit()
        self.timer_is_running = False
        self.dir_value_func(0)

    def enable(self, e):
        if self.en_pin:
            self.en_pin.value(e)
        self.enabled = e
        if not e:
            self.dir_value_func(0)

    def is_enabled(self):
        return self.enabled
