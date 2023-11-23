from machine import Pin


class StepperController:

    def __init__(self, mcp):
        self.mcp = mcp

        self.theta_a_step = Pin(4, Pin.OUT)
        self.theta_a_dir = Pin(5, Pin.OUT)
        self.theta_b_step = Pin(2, Pin.OUT)
        self.theta_b_dir = Pin(3, Pin.OUT)

        self.theta_pos = 0
        self.theta_goal = 0

        mcp.pin(1, mode=0, value=0)
        mcp.pin(2, mode=0, value=0)

        self.phi_step = mcp[1]
        self.phi_dir = mcp[2]

        self.phi_pos = 0
        self.phi_goal = 0

        self.switch_phi = mcp[3]
        self.switch_theta = mcp[4]

        self.theta_a_dir.off()
        self.theta_b_step.off()
        self.theta_a_dir.off()
        self.theta_b_dir.off()

        self.feed_ticks = 0
        self.feed_rate = 7

    """
        NOTE: this function expects an update every millisecond, any change to this will result in speed variation.
    """

    def update_steppers(self):
        self.feed_ticks += 1

        if self.feed_ticks >= self.feed_rate:
            if self.theta_pos != self.theta_goal:
                self.theta_a_dir.value(self.theta_pos > self.theta_goal)
                self.theta_b_dir.value(not (self.theta_pos > self.theta_goal))

                self.theta_a_step.value(int(not self.theta_a_step.value()))
                self.theta_b_step.value(int(not self.theta_a_step.value()))
                self.theta_pos += -1 if self.theta_pos > self.theta_goal else 1

            if self.phi_pos != self.phi_goal:
                self.phi_dir.output(self.phi_pos > self.phi_goal)

                self.phi_step.output(int(not self.phi_step.value()))
                self.phi_pos += -1 if self.phi_pos > self.phi_goal else 1

            self.feed_ticks = 0

    def write_theta(self, deg, microstep=8):
        self.theta_goal = round(deg * (1/(1.8 / microstep)))
        print("setting goal of ", self.theta_goal)

    def write_phi(self, deg, microstep=8):
        self.phi_goal = round(deg * (1/(1.8 / microstep)))
        print("setting goal of ", self.theta_goal)


    def override_theta(self):
        pass

    def override_phi(self):
        pass

    def home(self):
        pass
