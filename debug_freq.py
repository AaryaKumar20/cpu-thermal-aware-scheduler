import copy
from tasks import generate_tasks
from scheduler import Scheduler
import power_model

tasks = generate_tasks()

for name, base in [('Baseline', True), ('EDF', False)]:
    power_model.total_energy = 0
    sched = Scheduler(copy.deepcopy(tasks), baseline=base, algorithm='edf', use_ml=True)
    
    total_work_done = 0
    total_idle_ticks = 0
    total_active_ticks = 0
    freq_sums = 0.0
    
    for _ in range(200):
        sched.step()
        for core in sched.cores:
            if core.current_task:
                total_active_ticks += 1
                freq_sums += core.freq
                total_work_done += core.freq
            else:
                total_idle_ticks += 1
                
    print(f"--- {name} ---")
    print(f"Total Work Done: {total_work_done:.2f}")
    print(f"Total Active Ticks: {total_active_ticks}")
    print(f"Total Idle Ticks: {total_idle_ticks}")
    if total_active_ticks > 0:
        print(f"Avg Freq when Active: {freq_sums/total_active_ticks:.2f}")
    print(f"Core Energy: {sum(c.energy for c in sched.cores):.2f}")
