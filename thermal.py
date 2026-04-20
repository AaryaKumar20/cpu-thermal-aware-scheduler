from constants import AMBIENT_TEMP, THERMAL_LIMIT

# B1: Coupling factor for core-to-core heat transfer
COUPLING_FACTOR = 0.005


def update_temperature(core, power):
    """Update a single core's temperature (legacy single-core API)."""
    heat = power * 0.8
    cool = 0.03 * (core.temperature - AMBIENT_TEMP)
    core.temperature += heat - cool


def update_temperatures(cores, powers):
    """
    B1: Update all core temperatures with inter-core thermal coupling.
    Also implements Adaptive Cooling: if any core is > 70C, the fan kicks on,
    increasing the cooling coefficient for all cores.
    
    Returns: bool (True if fan was active this tick)
    """
    # Check if fan should be active
    fan_active = any(c.temperature > 70.0 for c in cores)
    cooling_coeff = 0.08 if fan_active else 0.03

    # Phase 1: individual thermal dynamics
    for core, power in zip(cores, powers):
        heat = power * 0.8
        cool = cooling_coeff * (core.temperature - AMBIENT_TEMP)
        core.temperature += heat - cool

    # Phase 2: core-to-core heat transfer (neighbor coupling)
    n = len(cores)
    if n > 1:
        temps_snapshot = [c.temperature for c in cores]
        for i in range(n):
            # Average temperature of adjacent cores
            neighbors = []
            if i > 0:
                neighbors.append(temps_snapshot[i - 1])
            if i < n - 1:
                neighbors.append(temps_snapshot[i + 1])
            neighbor_avg = sum(neighbors) / len(neighbors)
            cores[i].temperature += COUPLING_FACTOR * (neighbor_avg - temps_snapshot[i])

    return fan_active

def is_overheated(core):
    return core.temperature >= THERMAL_LIMIT