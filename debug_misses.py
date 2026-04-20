import copy
from tasks import generate_tasks
from scheduler import Scheduler

tasks = generate_tasks()
sched = Scheduler(copy.deepcopy(tasks), baseline=False, algorithm='edf', use_ml=True)

for _ in range(200):
    sched.step()

print("EDF Misses:", len(sched.deadline_misses))
for time, tid in sched.deadline_misses:
    # Find the task
    t = next((t for t in tasks if t.tid == tid), None)
    if t:
        print(f"Task {tid} missed at time {time}. Arrival={t.arrival}, Deadline={t.deadline}, Burst={t.burst}, Remaining={t.remaining}")
        # print gantt log for this task
        runs = [log for log in sched.gantt_log if log[2] == tid]
        if runs:
            print(f"  Runs: {len(runs)} ticks. Freqs used: {set(log[3] for log in runs)}")
        else:
            print("  Never ran.")
