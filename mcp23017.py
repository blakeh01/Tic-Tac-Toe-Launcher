import machine

MCP23017_I2C_ADDR = 0x20

IODIRA = 0x00
IODIRB = 0x01
GPIOA = 0x12
GPIOB = 0x13


class MCPController:

    def __init__(self, scl=machine.Pin(1), sda=machine.Pin(0), addr=MCP23017_I2C_ADDR):
        print("Creating MCP controller instance...")
        return
        self.i2c = machine.I2C(0, scl=scl, sda=sda)
        self.address = addr

        # set direction of all pins to output
        self.i2c.writeto_mem(self.address, IODIRA, bytes([0x00]))
        self.i2c.writeto_mem(self.address, IODIRB, bytes([0x00]))

    def set_pin_high(self, pin):
        self.i2c.writeto_mem(self.address, GPIOA + (pin >> 3), bytes([(1 << (pin & 7))]))

    def set_pin_low(self, pin):
        self.i2c.writeto_mem(self.address, GPIOA + (pin >> 3), bytes([~(1 << (pin & 7)) & 0xFF]))
