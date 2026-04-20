import logging

from dvfs import get_frequency
from power_model import calculate_power
from thermal import update_temperatures, is_overheated
from constants import CORES, THERMAL_LIMIT, FREQ_LEVELS
import math

logger = logging.getLogger(__name__)


class Core:
    def __init__(self, cid):
        self.cid = cid
        self.current_task = None
        self.freq = 0.0
        self.temperature = 35.0
        self.energy = 0.0
        self.rr_counter = 0  # ticks spent on current task (for Round Robin)


class Scheduler:
    def __init__(self, tasks, baseline=False, algorithm="edf", time_quantum=4, use_ml=False):
        self.tasks = tasks
        self.ready_queue = []
        self.cores = [Core(i) for i in range(CORES)]
        self.time = 0
        self.baseline = baseline
        self.algorithm = algorithm
        self.time_quantum = time_quantum
        self.use_ml = use_ml

        # Event logs
        self.gantt_log = []       # (tick, core_id, task_id, freq)
        self.migration_log = []   # (tick, task_id, from_core_id, reason)
        self.deadline_misses = [] # B5: (tick, task_id)
        self.total_work = 0.0     # Cumulative cycles/instructions processed

        # ML predictor (loaded lazily)
        self._predictor = None

    def _get_predictor(self):
        if self._predictor is None:
            from ml_predictor import ThermalPredictor
            self._predictor = ThermalPredictor()
            self._predictor.train()
        return self._predictor

    def admit_tasks(self):
        for task in self.tasks:
            if task.arrival == self.time:
                self.ready_queue.append(task)

    def check_deadlines(self):
        """Remove tasks that have passed their deadline without completing."""
        surviving = []
        for t in self.ready_queue:
            if t.deadline >= self.time:
                surviving.append(t)
            else:
                # B5: Record deadline miss
                self.deadline_misses.append((self.time, t.tid))
        self.ready_queue = surviving

    def _age_ready_queue(self):
        """B3: Increment wait_time for all tasks sitting in the ready queue."""
        for task in self.ready_queue:
            task.wait_time += 1

    def sort_queue(self):
        if self.algorithm == "edf":
            self.ready_queue.sort(key=lambda t: t.deadline)
        elif self.algorithm == "sjf":
            self.ready_queue.sort(key=lambda t: t.remaining)
        elif self.algorithm == "priority":
            # B3: Aging — every 10 ticks of waiting boosts effective priority by 1
            self.ready_queue.sort(key=lambda t: t.priority - (t.wait_time // 10))
        elif self.algorithm == "rr":
            pass  # FIFO order, no sort needed

    def assign_tasks(self):
        # Sort cores by temperature (coolest first) for thermal-aware assignment
        sorted_cores = sorted(self.cores, key=lambda c: c.temperature)
        for core in sorted_cores:
            if core.current_task is None and self.ready_queue:
                task = self.ready_queue.pop(0)
                core.current_task = task
                core.rr_counter = 0

                # B3: Reset wait time once scheduled
                task.wait_time = 0

                # DVFS decision
                if self.baseline:
                    core.freq = 1.0
                else:
                    base_freq = get_frequency(task.utilization)
                    
                    # Ensure frequency is high enough to meet the deadline
                    ticks_to_deadline = task.deadline - self.time
                    if ticks_to_deadline > 0:
                        for freq in sorted(FREQ_LEVELS):
                            if freq >= base_freq:
                                ticks_needed = math.ceil(task.remaining / freq)
                                if ticks_needed <= ticks_to_deadline:
                                    base_freq = freq
                                    break
                        else:
                            base_freq = 1.0
                            
                    queue_length = len(self.ready_queue)
                    if queue_length > len(self.cores) * 1.5:
                        base_freq = 1.0
                    elif queue_length > len(self.cores):
                        base_freq = max(base_freq, 0.8)
                        
                    core.freq = base_freq

                    # ML-based proactive frequency reduction
                    if self.use_ml and not self.baseline:
                        try:
                            predictor = self._get_predictor()
                            
                            # Pure power calculation to avoid mutating total_energy during prediction
                            from constants import VOLTAGE_MAP, IDLE_POWER
                            simulated_power = (VOLTAGE_MAP[core.freq] ** 2) * core.freq + IDLE_POWER if core.current_task else 0
                            
                            predicted_temp = predictor.predict(
                                core.temperature, core.freq,
                                simulated_power,
                                task.utilization
                            )
                            
                            # Deadline awareness: if task is tight on time, be less aggressive with cooling
                            ticks_to_deadline = task.deadline - self.time
                            ticks_needed = task.remaining / max(core.freq, 0.4)
                            tight_deadline = ticks_to_deadline <= ticks_needed * 1.5

                            # B2: Multi-step DVFS
                            if predicted_temp > THERMAL_LIMIT + 2:
                                # Extreme heat → step down 2 levels
                                current_idx = FREQ_LEVELS.index(core.freq)
                                step_down = 1 if tight_deadline else min(2, current_idx)
                                if step_down > 0 and current_idx - step_down >= 0:
                                    core.freq = FREQ_LEVELS[current_idx - step_down]
                            elif predicted_temp > THERMAL_LIMIT - 3:
                                # Moderate heat → step down 1 level (skip if tight deadline)
                                if not tight_deadline:
                                    current_idx = FREQ_LEVELS.index(core.freq)
                                    if current_idx > 0:
                                        core.freq = FREQ_LEVELS[current_idx - 1]
                                        
                            # Final ML predictor deadline check: did we step down too much?
                            ticks_to_deadline = task.deadline - self.time
                            if ticks_to_deadline > 0:
                                ticks_needed_after = math.ceil(task.remaining / core.freq)
                                if ticks_needed_after > ticks_to_deadline:
                                    # Undo step down to meet deadline
                                    for f in sorted(FREQ_LEVELS):
                                        if math.ceil(task.remaining / f) <= ticks_to_deadline:
                                            core.freq = f
                                            break
                                    else:
                                        core.freq = 1.0
                        except Exception as e:
                            # A3: Log the error instead of silently swallowing it
                            logger.warning("ML prediction failed: %s", e)

    def run_tick(self):
        powers = []  # collect per-core power for batch thermal update

        for core in self.cores:

            # 1. Round Robin preemption
            if (self.algorithm == "rr" and not self.baseline
                    and core.current_task and core.rr_counter >= self.time_quantum):
                self.ready_queue.append(core.current_task)
                core.current_task = None
                core.rr_counter = 0

            # 2. Thermal protection (optimized only)
            if core.current_task and not self.baseline:
                if core.temperature >= THERMAL_LIMIT:
                    # Hard eviction if critically overheated
                    self.migration_log.append(
                        (self.time, core.current_task.tid, core.cid, "Critical Thermal Eviction")
                    )
                    self.ready_queue.append(core.current_task)
                    core.current_task = None
                elif core.temperature >= THERMAL_LIMIT - 5.0:
                    # Soft throttle to maintain some throughput instead of evicting
                    if core.freq > FREQ_LEVELS[1]:
                        core.freq = FREQ_LEVELS[1]
                
                # Dynamic deadline enforcement
                if core.current_task:
                    ticks_to_deadline = core.current_task.deadline - self.time
                    if ticks_to_deadline > 0:
                        for freq in sorted(FREQ_LEVELS):
                            if freq >= core.freq:
                                ticks_needed = math.ceil(core.current_task.remaining / freq)
                                if ticks_needed <= ticks_to_deadline:
                                    core.freq = freq
                                    break
                        else:
                            core.freq = 1.0
                    
                    # Queue backlog enforcement: if tasks are waiting, speed up to free the core
                    if not self.baseline:
                        queue_length = len(self.ready_queue)
                        if queue_length > len(self.cores) * 1.5 and core.temperature < THERMAL_LIMIT - 5.0:
                            core.freq = 1.0
                        elif queue_length > len(self.cores) and core.temperature < THERMAL_LIMIT - 5.0:
                            core.freq = max(core.freq, 0.8)
                    else:
                        core.freq = 1.0

            # 3. Power calculation (Done before task execution so we account for the active tick even if task finishes)
            power = calculate_power(core)
            powers.append(power)

            # 4. Execute task
            if core.current_task:
                # B4: Record first-execution time
                if core.current_task.start_time is None:
                    core.current_task.start_time = self.time

                # NOTE: This correctly models the performance penalty of DVFS.
                # A task at 0.4 GHz takes 2.5x more ticks to finish than at 1.0 GHz.
                # We subtract core.freq (not 1.0) because lower frequencies process fewer cycles per tick.
                core.current_task.remaining -= core.freq
                core.rr_counter += 1
                self.total_work += core.freq

                # Log for Gantt chart
                self.gantt_log.append(
                    (self.time, core.cid, core.current_task.tid, core.freq)
                )

                if core.current_task.remaining <= 0:
                    # B4: Record completion time
                    core.current_task.completion_time = self.time
                    # B5: Check deadline miss on completion
                    if self.time > core.current_task.deadline:
                        self.deadline_misses.append(
                            (self.time, core.current_task.tid)
                        )
                    core.current_task = None
                    core.rr_counter = 0

        # 5. B1: Batch temperature update with core-to-core coupling and Adaptive Fan
        fan_active = update_temperatures(self.cores, powers)
        
        if fan_active:
            # Active cooling consumes additional flat power
            import power_model
            power_model.total_energy += 0.2

        # 6. Clamp all cores to ambient minimum
        for core in self.cores:
            core.temperature = max(35.0, core.temperature)

    def step(self):
        self.admit_tasks()
        self.check_deadlines()
        self._age_ready_queue()   # B3: aging before sort
        self.sort_queue()
        self.assign_tasks()
        self.run_tick()
        self.time += 1

    def simulate(self):
        while self.time < 200:
            self.step()