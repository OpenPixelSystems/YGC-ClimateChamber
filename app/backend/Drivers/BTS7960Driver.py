from app.backend.Dataclasses.Config import PeltierConfig
from app.backend.Interfaces.IDriver import IDriver
from app.backend.Providers.gpio_provider import GPIO


class BTS7960Driver(IDriver):
    def __init__(self, config: PeltierConfig):
        self.config = config
        self.enabled = False
        self.max_duty_cycle = config.Duty_cycle_limit or 50
        self.r_pwm = None
        self.l_pwm = None
        self.current_mode = "STOP"  # Track current state: HEAT, COOL, STOP

        # Initialize GPIO mode
        GPIO.setmode(GPIO.BCM)

        # Setup GPIO pins
        self._setup_pins()

        print(f"[BTS7960Driver] [Init] Initialized BTS7960 driver module using {config}")

    def _setup_pins(self):
        """Initialize GPIO pins for BTS7960"""
        # Setup control pins
        GPIO.setup(self.config.RPWM, GPIO.OUT)
        GPIO.setup(self.config.LPWM, GPIO.OUT)
        GPIO.setup(self.config.R_EN, GPIO.OUT)
        GPIO.setup(self.config.L_EN, GPIO.OUT)

        # Enable both sides - CRITICAL: Both must be HIGH for operation
        # Enable driver by checking box in control screen
        GPIO.output(self.config.R_EN, GPIO.LOW)
        GPIO.output(self.config.L_EN, GPIO.LOW)

        # Initialize PWM on both pins
        self.r_pwm = GPIO.PWM(self.config.RPWM, self.config.PWM_FREQUENCY)
        self.l_pwm = GPIO.PWM(self.config.LPWM, self.config.PWM_FREQUENCY)

        # Start PWM with 0% duty cycle (stopped state)
        self.r_pwm.start(0)
        self.l_pwm.start(0)

    def _validate_duty_cycle(self, duty_cycle):
        """Validate and clamp duty cycle to safe limits"""
        if duty_cycle < 0:
            duty_cycle = 0
        elif duty_cycle > self.max_duty_cycle:
            duty_cycle = self.max_duty_cycle
        return duty_cycle

    def heat(self, scaled_duty=20):
        """
        Heat mode: Current flows in one direction through Peltier
        Uses RPWM for heating, LPWM set to 0
        """
        if not self.enabled:
            print(f"[BTS7960Driver] [heat] BTS7960: Peltier module not enabled")
            return

        scaled_duty = self._validate_duty_cycle(scaled_duty)

        print(f"[BTS7960Driver] [heat] BTS7960: HEATING - RPWM={scaled_duty}%, LPWM=0%")

        # For heating: RPWM active, LPWM inactive
        # This creates current flow in one direction through the Peltier
        self.l_pwm.ChangeDutyCycle(0)  # Ensure LPWM is OFF first
        self.r_pwm.ChangeDutyCycle(scaled_duty)  # Then activate RPWM

        self.current_mode = "HEAT"

    def cool(self, scaled_duty=20):
        """
        Cool mode: Current flows in opposite direction through Peltier
        Uses LPWM for cooling, RPWM set to 0
        """
        if not self.enabled:
            print(f"[BTS7960Driver] [cool] BTS7960: Peltier module not enabled")
            return

        scaled_duty = self._validate_duty_cycle(scaled_duty)

        print(f"[BTS7960Driver] [cool] BTS7960: COOLING - RPWM=0%, LPWM={scaled_duty}%")

        # For cooling: LPWM active, RPWM inactive
        # This creates current flow in opposite direction through the Peltier
        self.r_pwm.ChangeDutyCycle(0)  # Ensure RPWM is OFF first
        self.l_pwm.ChangeDutyCycle(scaled_duty)  # Then activate LPWM

        self.current_mode = "COOL"

    def stop(self):
        """
        Stop: Both PWM channels set to 0%
        This stops current flow through the Peltier
        """
        print("[BTS7960Driver] [stop] BTS7960: STOP - Both PWM=0%")

        # Set both PWM channels to 0% - this stops the Peltier
        self.r_pwm.ChangeDutyCycle(0)
        self.l_pwm.ChangeDutyCycle(0)

        self.current_mode = "STOP"

    def set_duty_cycle_limit(self, limit: int):
        """
        Set maximum duty cycle limit
        Args:
            limit: Maximum duty cycle percentage (0-100)
        """
        self.max_duty_cycle = max(0, min(100, limit))
        print(f"[BTS7960Driver] [set_duty_cycle_limit] Duty cycle limit set to {self.max_duty_cycle}%")

    def get_current_mode(self):
        """
        Get the current operating mode
        Returns:
            str: Current mode (HEAT, COOL, STOP)
        """
        return self.current_mode

    def emergency_stop(self):
        """
        Emergency stop: Immediately disable all outputs
        Also disables the enable pins for complete shutdown
        """
        print("[BTS7960Driver] [emergency_stop] EMERGENCY STOP - All outputs disabled")

        # Stop PWM first
        self.r_pwm.ChangeDutyCycle(0)
        self.l_pwm.ChangeDutyCycle(0)

        # Disable enable pins for complete shutdown
        GPIO.output(self.config.R_EN, GPIO.LOW)
        GPIO.output(self.config.L_EN, GPIO.LOW)

        self.current_mode = "EMERGENCY_STOP"

    def resume_from_emergency(self):
        """
        Resume operation after emergency stop
        Re-enables the driver but stays in STOP mode
        """
        print("[BTS7960Driver] [resume_from_emergency] Resuming from emergency stop")

        # Re-enable both sides
        GPIO.output(self.config.R_EN, GPIO.HIGH)
        GPIO.output(self.config.L_EN, GPIO.HIGH)

        # Set to stop mode
        self.stop()

    def cleanup(self):
        """Clean up GPIO resources"""
        print("[BTS7960Driver] [cleanup] Cleaning up GPIO resources")

        # Stop all PWM activity
        self.stop()

        # Stop and clear PWM instances
        if self.r_pwm:
            self.r_pwm.stop()
            self.r_pwm = None  # Clear the reference
        if self.l_pwm:
            self.l_pwm.stop()
            self.l_pwm = None  # Clear the reference

        # Disable enable pins
        try:
            GPIO.output(self.config.R_EN, GPIO.LOW)
            GPIO.output(self.config.L_EN, GPIO.LOW)
        except:
            pass  # Ignore if pins are already cleaned up

        # Clean up GPIO pins
        try:
            GPIO.cleanup([
                self.config.RPWM,
                self.config.LPWM,
                self.config.R_EN,
                self.config.L_EN
            ])
        except:
            pass  # Ignore cleanup errors

    def disable(self):
        GPIO.output(self.config.R_EN, GPIO.LOW)
        GPIO.output(self.config.L_EN, GPIO.LOW)
        self.enabled = False


    def enable(self):
        GPIO.output(self.config.R_EN, GPIO.HIGH)
        GPIO.output(self.config.L_EN, GPIO.HIGH)
        self.enabled = True
