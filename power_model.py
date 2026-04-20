from constants import VOLTAGE_MAP, IDLE_POWER

total_energy = 0  # kept for backward compatibility


def calculate_power(core):
    """
    Calculate instantaneous power for a core and accumulate energy.

    Power model: P = V² × f  (dynamic) + P_idle
    Side effects: increments core.energy and module-level total_energy.
    """
    global total_energy

    if core.current_task:
        voltage = VOLTAGE_MAP[core.freq]
        power = (voltage ** 2) * core.freq + IDLE_POWER
    else:
        power = IDLE_POWER

    total_energy += power
    core.energy += power
    return power