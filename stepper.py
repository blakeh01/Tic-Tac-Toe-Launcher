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
        self.feed_rate = 2

        self.do_home = False

    """
        NOTE: this function expects an update every millisecond, any change to this will result in speed variation.
    """

    def update_steppers(self):
        self.feed_ticks += 1

        if self.do_home:
            if self.theta_pos == self.theta_goal:
                self.override_theta(0)

            if self.phi_goal == self.phi_pos:
                pass
                #self.step_phi()

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
        self.theta_goal = round(deg * (1/(1.8 / microstep))) * 2
        print("setting goal of ", self.theta_goal)

    def write_phi(self, deg, microstep=8):
        self.phi_goal = round(deg * (1/(1.8 / microstep))) * 2
        print("setting goal of ", self.theta_goal)

    def step_phi(self, step):
        # todo limits
        self.phi_goal = self.phi_pos + step

    def step_theta(self, step):
        self.theta_goal = max(0, min(self.theta_pos + step, 180))  # bound limits

    def override_theta(self, pos):
        self.theta_pos = pos
        self.theta_goal = pos

    def override_phi(self, pos):
        self.phi_pos = pos
        self.phi_goal = pos

    def home(self):
        self.do_home = True
        self.feed_rate = 1
        self.write_theta(110)

        # todo phi homing
