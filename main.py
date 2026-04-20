import copy
import pandas as pd
from tasks import generate_tasks
from scheduler import Scheduler
import power_model


def run_headless(ticks_count, tasks_input, algo, baseline=False):
    """Run a simulation headlessly and return results."""
    power_model.total_energy = 0
    tasks_copy = copy.deepcopy(tasks_input)
    sched = Scheduler(tasks_copy, baseline=baseline, algorithm=algo, use_ml=True)

    for core in sched.cores:
        core.energy = 0.0

    max_temp = 0.0

    for _ in range(ticks_count):
        sched.step()
        for core in sched.cores:
            if core.temperature > max_temp:
                max_temp = core.temperature

    completed = sum(1 for t in tasks_copy if t.remaining <= 0)
    total_energy = power_model.total_energy
    
    avg_temp = sum(core.temperature for core in sched.cores) / len(sched.cores)
    
    return completed, total_energy, sched, avg_temp, max_temp


if __name__ == "__main__":
    tasks = generate_tasks()
    original_tasks = copy.deepcopy(tasks)
    
    print("\n" + "="*60)
    print(" CPU Thermal-Aware Scheduler — CLI Benchmark ")
    print("="*60)
    
    algorithms = {
        "edf": "EDF (Earliest Deadline First)",
        "sjf": "SJF (Shortest Job First)",
        "priority": "Priority",
        "rr": "Round Robin"
    }
    
    results = []
    
    print("\nRunning Baseline (No DVFS, No Thermal Throttling)...")
    comp, eng, sched, avg_t, max_t = run_headless(200, original_tasks, "edf", baseline=True)
    results.append({
        "Algorithm": "Baseline",
        "Completed": comp,
        "Misses": len(sched.deadline_misses),
        "Energy": round(eng, 2),
        "Max Temp": round(max_t, 2)
    })
    
    print("Running Optimized Algorithms (DVFS, ML Predictor, Adaptive Fan)...")
    for key, name in algorithms.items():
        comp, eng, sched, avg_t, max_t = run_headless(200, original_tasks, key, baseline=False)
        results.append({
            "Algorithm": name,
            "Completed": comp,
            "Misses": len(sched.deadline_misses),
            "Energy": round(eng, 2),
            "Max Temp": round(max_t, 2)
        })
        
    df = pd.DataFrame(results)
    
    print("\n" + "="*60)
    print(" PERFORMANCE COMPARISON ")
    print("="*60)
    print(df.to_string(index=False))
    print("\nBenchmark Complete.")