import unittest
from unittest.mock import patch

from app.backend.Modules.PeltierModule import PeltierModule
from app.backend.Dataclasses.Config import PeltierConfig


class TestPeltierModule(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.config = PeltierConfig(
            name="Test Peltier",
            type="peltier",
            gpio_pin_heating=17,
            gpio_pin_cooling=27,
            gpio_pin_pwm=22,
            pwm_frequency=25000,
            max_temp=120,
            min_temp=-40
        )
        # Mock GPIO to avoid actual hardware interaction
        self.gpio_patcher = patch('app.backend.Implementations.PeltierModule.GPIO')
        self.mock_gpio = self.gpio_patcher.start()
        self.peltier = PeltierModule(self.config)

    def tearDown(self):
        """Clean up after each test method."""
        self.gpio_patcher.stop()

    def test_initialization(self):
        """Test proper initialization of PeltierModule."""
        # Verify GPIO setup
        self.mock_gpio.setmode.assert_called_once_with(self.mock_gpio.BCM)
        self.mock_gpio.setup.assert_any_call(self.config.gpio_pin_heating, self.mock_gpio.OUT)
        self.mock_gpio.setup.assert_any_call(self.config.gpio_pin_cooling, self.mock_gpio.OUT)
        self.mock_gpio.setup.assert_any_call(self.config.gpio_pin_pwm, self.mock_gpio.OUT)
        
        # Verify PWM initialization
        self.mock_gpio.PWM.assert_called_once_with(self.config.gpio_pin_pwm, self.config.pwm_frequency)
        self.peltier.pwm.start.assert_called_once_with(0)

    def test_heat(self):
        """Test heating functionality."""
        duty_cycle = 75
        self.peltier.heat(duty_cycle)
        
        # Verify correct GPIO states
        self.mock_gpio.output.assert_any_call(self.config.gpio_pin_cooling, self.mock_gpio.LOW)
        self.mock_gpio.output.assert_any_call(self.config.gpio_pin_heating, self.mock_gpio.HIGH)
        self.peltier.pwm.ChangeDutyCycle.assert_called_once_with(duty_cycle)

    def test_cool(self):
        """Test cooling functionality."""
        duty_cycle = 50
        self.peltier.cool(duty_cycle)
        
        # Verify correct GPIO states
        self.mock_gpio.output.assert_any_call(self.config.gpio_pin_heating, self.mock_gpio.LOW)
        self.mock_gpio.output.assert_any_call(self.config.gpio_pin_cooling, self.mock_gpio.HIGH)
        self.peltier.pwm.ChangeDutyCycle.assert_called_once_with(duty_cycle)

    def test_stop(self):
        """Test stopping functionality."""
        self.peltier.stop()
        
        # Verify all outputs are set to LOW
        self.mock_gpio.output.assert_any_call(self.config.gpio_pin_heating, self.mock_gpio.LOW)
        self.mock_gpio.output.assert_any_call(self.config.gpio_pin_cooling, self.mock_gpio.LOW)
        self.peltier.pwm.ChangeDutyCycle.assert_called_once_with(0)

    def test_cleanup(self):
        """Test cleanup functionality."""
        self.peltier.cleanup()
        
        # Verify PWM is stopped and GPIO is cleaned up
        self.peltier.pwm.stop.assert_called_once()
        self.mock_gpio.cleanup.assert_called_once()

    def test_duty_cycle_limits(self):
        """Test duty cycle values in heating and cooling."""
        # Test duty cycle > 100
        self.peltier.heat(150)
        self.peltier.pwm.ChangeDutyCycle.assert_called_with(150)
        
        # Test duty cycle < 0
        self.peltier.cool(-50)
        self.peltier.pwm.ChangeDutyCycle.assert_called_with(-50)


if __name__ == '__main__':
    unittest.main()