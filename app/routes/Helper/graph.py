from datetime import datetime
from app.backend.Interfaces.IConfigManager import IConfigManager
from typing import List, Tuple, Union
import math
import bisect


def linear_interp(x, xp, fp):
    """Mimics numpy.interp: linearly interpolates a value at x based on xp, fp"""
    i = bisect.bisect_left(xp, x)
    if i == 0:
        return fp[0]
    elif i >= len(xp):
        return fp[-1]
    x0, x1 = xp[i - 1], xp[i]
    y0, y1 = fp[i - 1], fp[i]
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


class Graph:
    """Main graph model replicating original helper.py functionality"""

    def __init__(
        self,
        name,
        setpoints: List[Tuple[Union[int, float, str], Union[int, float, str]]],
        config_manager: IConfigManager,
    ):
        # Convert setpoints to float tuples
        self.name = name
        self.config = config_manager.graph_config
        self.setpoints = [(float(x), float(y)) for x, y in setpoints]
        self.valid_dataset, self.validation_message = self._validate_dataset()
        self.start_time = None

        # Create interpolated points (one per second)
        self.interpolated_setpoints = (
            self._interpolate_setpoints() if self.valid_dataset else []
        )

    def set_start_time(self, start_time):
        self.start_time = start_time

    def _validate_dataset(self) -> Tuple[bool, str]:
        """Validate the temperature profile dataset"""
        try:
            # Check if the dataset exceeds the max number of points
            if len(self.setpoints) > self.config.max_points:
                return False, "Dataset heeft te veel punten."

            # Check if all points are within the limits
            for i, (x, y) in enumerate(self.setpoints):
                if (
                    x < self.config.min_x
                    or y < self.config.min_y
                    or y > self.config.max_y
                ):
                    return False, f"Punt {i} ({x}, {y}) ligt buiten de limieten."

            # Check if time progression and slope are realistic
            for i in range(1, len(self.setpoints)):
                x1, y1 = self.setpoints[i - 1]
                x2, y2 = self.setpoints[i]
                if x2 <= x1:
                    return (
                        False,
                        f"Punten {i - 1} en {i} hebben een niet-realistische tijdssprong.",
                    )
                slope = abs((y2 - y1) / (x2 - x1))
                if slope > self.config.max_rico:
                    return (
                        False,
                        f"Helling tussen punten {i - 1} en {i} is te groot: {slope} > {self.config.max_rico}.",
                    )

            # If all checks pass
            return True, None

        except (TypeError, ValueError) as e:
            return False, f"Invalid data format: {str(e)}"

    def _interpolate_setpoints(self) -> List[Tuple[int, float]]:
        """
        Interpolate the setpoints to have one point per second.
        Returns a list of (time, temperature) tuples where time is an integer.
        """
        if not self.setpoints:
            return []

        # Extract time and temperature arrays
        times, temps = zip(*self.setpoints)

        # Get the first and last time points (rounded to integers)
        start_time = int(times[0])
        end_time = int(math.ceil(times[-1]))

        # Create array of integer seconds
        interp_times = list(range(start_time, end_time + 1))

        # Interpolate each time
        interp_temps = [linear_interp(t, times, temps) for t in interp_times]

        # Combine into tuples and return
        return [(int(t), float(temp)) for t, temp in zip(interp_times, interp_temps)]

    def get_temperature_at_time(self) -> float:
        """
        Get the target temperature at a specific time (in seconds).
        This uses the interpolated setpoints for accurate readings.
        """
        time = round((datetime.now() - self.start_time).total_seconds())
        if not self.valid_dataset or not self.interpolated_setpoints:
            return 0.0

        # If time is before the first point, return the first temperature
        if time < self.interpolated_setpoints[0][0]:
            return self.interpolated_setpoints[0][1]

        # If time is after the last point, return the last temperature
        if time > self.interpolated_setpoints[-1][0]:
            return self.interpolated_setpoints[-1][1]

        # Find the temperature at the exact second
        for t, temp in self.interpolated_setpoints:
            if t == time:
                return temp

        # Fallback to interpolation
        return linear_interp(
            time,
            [t for t, _ in self.interpolated_setpoints],
            [temp for _, temp in self.interpolated_setpoints],
        )

    def update_current_target(self, target: float):
        current_time = round((datetime.now() - self.start_time).total_seconds())
        new_setpoint = (current_time, target)
        self.setpoints.append(new_setpoint)
        self.valid_dataset, self.validation_message = self._validate_dataset()
        self.interpolated_setpoints = (
            self._interpolate_setpoints() if self.valid_dataset else []
        )
        return

    def get_current_target(self):
        elapsed_seconds = round((datetime.now() - self.start_time).total_seconds())
        if len(self.setpoints) <= elapsed_seconds:
            return self.setpoints[len(self.setpoints) - 1][1]
        else:
            return self.setpoints[elapsed_seconds][1]
