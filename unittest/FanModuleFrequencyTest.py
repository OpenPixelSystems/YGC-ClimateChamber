import sys
import time

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

print("=== TB6612FNG Peltier PWM Frequency Test ===")
print(f"Config: {config}")
print("\nWiring:")
print(f"  GPIO {config.RPWM} -> PWMA (PWM speed)")
print(f"  GPIO {config.LPWM} -> AIN2 (heating enable)")
print(f"  GPIO {config.R_EN} -> AIN1 (cooling enable)")
print(f"  STBY -> VCC (always enabled)")
print("\n" + "=" * 50)

# Comprehensive frequency test list
test_frequencies = [
    # Very Low Frequencies (may cause flickering but quiet)
    100, 200, 500,

    # Low Audible Range (likely to cause noise)
    1000, 2000, 3000, 4000, 5000,

    # Mid Audible Range (most problematic)
    6000, 8000, 10000, 12000,

    # High Audible Range (transitioning to quiet)
    15000, 18000, 20000,

    # Just Above Audible (sweet spot candidates)
    22000, 25000, 28000, 30000,

    # Well Above Audible (should be silent)
    31250, 35000, 40000, 45000,

    # Very High (testing limits)
    50000, 60000
]

# Initialize peltier module
peltier = PeltierModule(config, DriverType.TB6612FNG)

print(f"\nTesting {len(test_frequencies)} different frequencies...")
print("Listen for squealing/whining sounds at each frequency")
print("Press Ctrl+C to stop the test at any time\n")

try:
    for i, freq in enumerate(test_frequencies):
        print(f"Test {i + 1}/{len(test_frequencies)}: {freq}Hz")

        # Change PWM frequency
        peltier.pwm.ChangeFrequency(freq)

        # Start heating at 50% to create load
        peltier.heat(50)

        # Test for 5 seconds
        print(f"  Running at {freq}Hz for 5 seconds...")
        time.sleep(5)

        # Stop briefly between tests
        peltier.stop()
        time.sleep(1)

        # Get user feedback
        response = input(f"  {freq}Hz - Rate noise level (0=silent, 5=very loud, s=skip): ").strip().lower()

        if response == 's':
            print("  Skipping remaining tests...")
            break
        elif response.isdigit():
            noise_level = int(response)
            if noise_level == 0:
                print(f"  ✓ {freq}Hz - SILENT! (Good candidate)")
            elif noise_level <= 2:
                print(f"  ✓ {freq}Hz - Quiet (Acceptable)")
            else:
                print(f"  ✗ {freq}Hz - Noisy (Avoid)")

        print()

except KeyboardInterrupt:
    print("\nTest interrupted by user")

except Exception as e:
    print(f"\nError during test: {e}")

finally:
    # Clean up
    print("\nCleaning up...")
    peltier.cleanup()
    print("Test complete!")

print("\n" + "=" * 50)
print("FREQUENCY SELECTION GUIDE:")
print("• 0-500Hz: May flicker but mechanically quiet")
print("• 1-15kHz: Likely audible (avoid these)")
print("• 20-25kHz: Transition zone (test carefully)")
print("• 25kHz+: Should be silent (recommended)")
print("• 40kHz+: Well above audible range")
print("\nRecommended starting points: 25000Hz, 31250Hz, 40000Hz")