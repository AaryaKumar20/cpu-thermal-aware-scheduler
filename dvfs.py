from constants import FREQ_LEVELS

def get_frequency(utilization):
    required = utilization * 1.05

    for freq in FREQ_LEVELS:
        if freq >= required:
            return freq

    return 1.0