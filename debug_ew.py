import copy
from tasks import generate_tasks
from scheduler import Scheduler
import power_model
from constants import VOLTAGE_MAP

tasks = generate_tasks()

power_model.total_energy = 0
sched = Scheduler(copy.deepcopy(tasks), baseline=False, algorithm='edf', use_ml=True)

for tick in range(200):
    sched.step()
    for core in sched.cores:
        if core.current_task:
            voltage = VOLTAGE_MAP[core.freq]
            power = (voltage ** 2) * core.freq + 0.05
            ew = power / core.freq
            if ew > 1.5:
                print(f"Tick {tick}: Core {core.cid} freq={core.freq} power={power:.3f} E/W={ew:.3f}")
