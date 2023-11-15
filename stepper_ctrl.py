import machine

from machine import Pin
from mcp23017 import MCPController


class StepperController:

    def __init__(self, MCP: MCPController):
        self.mcp = MCP

        # theta pins are directly connected to MCU to ensure that they execute at same speed
        self.a_theta_step = Pin(2, Pin.OUT)
        self.a_theta_dir = Pin(3, Pin.OUT)

        self.b_theta_step = Pin(4, Pin.OUT)
        self.b_theta_dir = Pin(5, Pin.OUT)

        self.theta_step_deg = 0.225 # 1.8 deg @ 1/8 micro-stepping
        self.theta_pos = 0
        self.theta_steps = 0 # this is the current number of steps the MCU needs to do.

        # phi control is from the expander, as well as limit switches (STEP: A1, DIR: A2)
        self.phi_step_deg = 0.225
        self.phi_pos = 0
        self.phi_steps = 0

        self.at_home = False
        self.run = False

    def update_steppers(self):
        # if we are not at home or we are intentionally not running the motors... don't!
        if not self.at_home or not self.run:
            return

        if self.theta_steps > 0:  # this will run as fast as this updates, which is ~ 1ms (i.e. sleep(0.001))
            # do stepping
            pass

        if self.phi_steps > 0:
            # do stepping
            pass

        pass

    def write_theta_deg(self, deg):
        # if we try to write the same angle, or our current movement is not complete, exit.
        if deg == self.theta_pos or self.theta_steps > 0:
            return

        # set direction pin depending on if we need to incline or decline
        if deg > self.theta_pos:
            self.a_theta_dir.on()
            self.b_theta_dir.off()
        else:
            self.a_theta_dir.off()
            self.b_theta_dir.on()

        self.theta_steps = round(deg * (1/self.theta_step_deg))

    def write_phi_deg(self, deg):
        # if we try to write the same angle, or our current movement is not complete, exit.
        if deg == self.phi_pos or self.phi_steps > 0:
            return

        # set direction pin depending on if we need to incline or decline
        if deg > self.phi_pos:
            self.mcp.set_pin_low(2)
        else:
            self.mcp.set_pin_high(2)

        self.phi_steps = round(deg * (1/self.phi_step_deg))

    def home(self):
        # use limit switches to find home, home will be defined as straight-up looking toward center of platform.
        pass