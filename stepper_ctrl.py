import machine

from machine import Pin
from mcp23017 import MCPController


class StepperController:

    def __init__(self, MCP: MCPController):

        # theta pins are directly connected to MCU to ensure that they execute at same speed
        self.a_theta_step = Pin(2, Pin.OUT)
        self.a_theta_dir = Pin(3, Pin.OUT)

        self.a_theta_step = Pin(4, Pin.OUT)
        self.a_theta_dir = Pin(5, Pin.OUT)

        self.theta_step_deg = 0.225 # 1.8 deg @ 1/8 micro-stepping
        self.theta_pos = 0

        # phi control is from the expander, as well as limit switches
        self.phi_step_deg = 0.225
        self.phi_pos = 0

    def write_theta(self):
        pass

    def write_phi(self):
        pass

    def home(self):
        # use limit switches to find home, home will be defined as straight-up looking toward center of platform.
        pass