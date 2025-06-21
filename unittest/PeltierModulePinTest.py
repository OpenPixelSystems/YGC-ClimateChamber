import sys
sys.path.append('..')
from app.backend.Modules.PeltierModule import PeltierModule, DriverType
from app.backend.Dataclasses.Config import PeltierConfig

# Create config (use your actual config values)
config = PeltierConfig(
    name="Peltier_240W",
    type="TB6612FNG",
    RPWM=18,  # GPIO 18 -> PWMA (PWM speed control)
    LPWM=22,  # GPIO 22 -> AIN2 (heating enable)
    R_EN=27,  # GPIO 27 -> AIN1 (cooling enable)
    L_EN=17,  # Not used (STBY hardwired to VCC)
    PWM_FREQUENCY=5000,
    Duty_cycle_limit=30
)

print("=== TB6612FNG Peltier Test ===")
print(f"Config: {config}")
print("\nWiring:")
print(f"  GPIO {config.RPWM} -> PWMA (PWM speed)")
print(f"  GPIO {config.LPWM} -> AIN2 (heating enable)")
print(f"  GPIO {config.R_EN} -> AIN1 (cooling enable)")
print(f"  STBY -> VCC (always enabled)")
print("\n" + "=" * 50)

# Test the peltier module
peltier = PeltierModule(config, DriverType.TB6612FNG)

print("Testing STOP...")
peltier.stop()
input("Check LEDs - both should be OFF. Press Enter to continue...")

print("Testing HEAT...")
peltier.heat(50)
input("Check LEDs - GPIO22 should be ON, GPIO27 should be OFF. Press Enter to continue...")

print("Testing COOL...")
peltier.cool(50)
input("Check LEDs - GPIO27 should be ON, GPIO22 should be OFF. Press Enter to continue...")

print("Testing STOP again...")
peltier.stop()
input("Check LEDs - both should be OFF. Press Enter to continue...")

# Clean up
peltier.cleanup()