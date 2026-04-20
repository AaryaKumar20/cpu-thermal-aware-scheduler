import copy
from tasks import generate_tasks
from scheduler import Scheduler
import power_model

tasks = generate_tasks()

for name, base in [('Baseline', True), ('EDF', False)]:
    power_model.total_energy = 0
    sched = Scheduler(copy.deepcopy(tasks), baseline=base, algorithm='edf', use_ml=True)
    
    for core in sched.cores:
        core.energy = 0.0
        
    for _ in range(200):
        sched.step()
        
    core_energy = sum(core.energy for core in sched.cores)
    fan_energy = power_model.total_energy - core_energy
    
    print(f"--- {name} ---")
    print(f"Total Energy: {power_model.total_energy:.2f}")
    print(f"Core Energy: {core_energy:.2f}")
    print(f"Fan Energy: {fan_energy:.2f}")
