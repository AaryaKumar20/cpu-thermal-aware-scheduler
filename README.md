# CPU Thermal-Aware Scheduler

An energy-efficient CPU scheduling simulator that integrates:

* Dynamic Voltage and Frequency Scaling (DVFS)
* Thermal-aware scheduling and cooling
* Machine Learning-based temperature prediction(Random forest)

Built using Python and Streamlit for real-time simulation and visualization.

---

## Features

* Multi-core CPU scheduling (EDF, SJF, Priority, Round Robin)
* DVFS for energy optimization
* Thermal model with cooling and inter-core heat transfer
* ML-based temperature prediction (Random Forest)
* Baseline vs optimized comparison
* Real-time dashboard (Streamlit)
* Energy, temperature, and efficiency analysis

---

## Key Results

* ~17-18% energy reduction compared to baseline
* Controlled CPU temperature under thermal limits
* Demonstrates trade-off between performance and energy efficiency

---

## Tech Stack

* Python
* Streamlit
* NumPy, Pandas
* Scikit-learn

---

## How It Works (Detailed)

This project simulates a thermal-aware CPU scheduler using:

* DVFS (Dynamic Voltage and Frequency Scaling):
Adjusts CPU frequency based on task utilization to save energy.
* Thermal Model:
Temperature increases with power and decreases via cooling and inter-core heat transfer.
* ML Predictor:
Uses a Random Forest model to predict future CPU temperature and prevent overheating.
* Scheduling Algorithms:
EDF, SJF, Priority, and Round Robin are implemented and compared.
The system balances performance, energy efficiency, and thermal safety.

---

## How to Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## Project Insight

This project simulates how modern CPUs manage:

* Energy consumption
* Thermal constraints
* Task scheduling efficiency

It highlights the trade-off between performance and power efficiency.

---

## Note

This project was developed with the assistance of AI tools for code generation and debugging.

---

## Future Scope

* Real hardware data integration
* Reinforcement learning-based scheduling
* Advanced thermal modeling
