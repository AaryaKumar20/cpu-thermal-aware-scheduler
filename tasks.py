import random
from constants import TASK_COUNT, SIM_TICKS


class Task:
    def __init__(self, tid, burst, arrival, deadline, priority, utilization):
        self.tid = tid
        self.burst = burst
        self.remaining = burst
        self.arrival = arrival
        self.deadline = deadline
        self.priority = priority
        self.utilization = utilization

        # B3: Starvation prevention — tracks ticks spent waiting in ready queue
        self.wait_time = 0

        # B4: Timing metrics for turnaround / response time analysis
        self.start_time = None       # tick when first executed
        self.completion_time = None  # tick when remaining <= 0

    def __repr__(self):
        return f"T{self.tid}(rem={self.remaining}, dl={self.deadline})"


def generate_tasks():
    random.seed(42)
    tasks = []

    for i in range(TASK_COUNT):
        arrival = random.randint(0, SIM_TICKS - 20)
        burst = random.randint(4, 20)
        deadline = arrival + int(burst / 0.7) + random.randint(5, 30)
        priority = random.choice([1, 1, 2, 2, 3])
        utilization = round(random.uniform(0.3, 1.0), 2)

        tasks.append(Task(i, burst, arrival, deadline, priority, utilization))

    return tasks
