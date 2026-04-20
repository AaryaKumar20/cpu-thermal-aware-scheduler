import streamlit as st
import time
import copy
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from tasks import generate_tasks
from scheduler import Scheduler
import power_model

# ─── Page Config ───
st.set_page_config(page_title="CPU Scheduler Dashboard", layout="wide")

# ─── C5: Enhanced CSS Theming ───
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.big-title {
    font-size: 42px; font-weight: 700; text-align: center;
    background: linear-gradient(90deg, #00ff9f, #00b4d8, #e040fb);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    padding: 10px 0;
}
.subtitle { text-align: center; color: #8b949e; font-size: 16px; margin-bottom: 20px; }
.glass-card {
    background: rgba(22,27,34,0.85); backdrop-filter: blur(12px);
    border: 1px solid rgba(48,54,61,0.6); border-radius: 16px;
    padding: 24px; margin: 8px 0;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}
.kpi-value { font-size: 32px; font-weight: 700; }
.kpi-label { font-size: 13px; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; }
</style>
""", unsafe_allow_html=True)

# ─── Title ───
st.markdown("<div class='big-title'>⚡ CPU Thermal-Aware Scheduler</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Real-time DVFS + Thermal Simulation with ML Prediction & Inter-Core Heat Transfer</div>", unsafe_allow_html=True)

# ─── C5: Sidebar Controls ───
with st.sidebar:
    st.markdown("## ⚙️ Simulation Controls")
    ticks = st.slider("Simulation Ticks", 50, 300, 150)
    speed = st.slider("Animation Speed", 0.01, 0.2, 0.05)
    algorithm = st.selectbox("Scheduling Algorithm", [
        "EDF (Earliest Deadline First)",
        "SJF (Shortest Job First)",
        "Priority",
        "Round Robin"
    ])
    if algorithm == "Round Robin":
        time_quantum = st.slider("RR Time Quantum", 2, 10, 4)
    else:
        time_quantum = 4
    use_ml = st.checkbox("🧠 Enable ML Thermal Predictor", value=True)
    st.markdown("---")
    st.markdown("### 📖 About")
    st.markdown(
        "This simulator models a **thermal-aware CPU scheduler** with "
        "DVFS, ML-based proactive cooling, inter-core heat transfer, "
        "task aging, and deadline-miss tracking."
    )

ALGO_MAP = {
    "EDF (Earliest Deadline First)": "edf",
    "SJF (Shortest Job First)": "sjf",
    "Priority": "priority",
    "Round Robin": "rr"
}
algo_key = ALGO_MAP[algorithm]


def run_headless(ticks_count, tasks_input, algo, baseline=False, tq=4, ml=False):
    """Run a simulation headlessly and return results."""
    power_model.total_energy = 0
    tasks_copy = copy.deepcopy(tasks_input)
    sched = Scheduler(tasks_copy, baseline=baseline, algorithm=algo,
                      time_quantum=tq, use_ml=ml)
    for core in sched.cores:
        core.energy = 0.0
    for _ in range(ticks_count):
        sched.step()
    completed = sum(1 for t in tasks_copy if t.remaining <= 0)
    total_energy = sum(c.energy for c in sched.cores)
    return completed, total_energy, sched, tasks_copy


# ─── Run Button ───
if st.button("🚀 Start Simulation", use_container_width=True):

    power_model.total_energy = 0
    tasks = generate_tasks()
    original_tasks = copy.deepcopy(tasks)

    sched = Scheduler(tasks, algorithm=algo_key, time_quantum=time_quantum, use_ml=use_ml)
    baseline_tasks = copy.deepcopy(tasks)
    baseline_sched = Scheduler(baseline_tasks, baseline=True)

    # ─── UI Placeholders (Live Monitor) ───
    status_placeholder = st.empty()
    metrics_placeholder = st.empty()
    core_placeholder = st.empty()

    st.markdown("### 📊 System Comparison")
    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("⚡ Optimized System")
        chart_opt_placeholder = st.empty()
    with col_right:
        st.subheader("🚫 Baseline System")
        chart_base_placeholder = st.empty()

    opt_history = []
    base_history = []
    opt_energy_history = []
    base_energy_history = []
    opt_work_history = []
    base_work_history = []
    opt_energy = 0
    base_energy = 0

    # ─── Simulation Loop ───
    for t in range(ticks):
        e_before = power_model.total_energy
        sched.step()
        opt_energy += power_model.total_energy - e_before

        e_before = power_model.total_energy
        baseline_sched.step()
        base_energy += power_model.total_energy - e_before

        opt_temps = [core.temperature for core in sched.cores]
        base_temps = [core.temperature for core in baseline_sched.cores]
        opt_history.append(opt_temps)
        base_history.append(base_temps)
        opt_energy_history.append(opt_energy)
        base_energy_history.append(base_energy)
        opt_work_history.append(sched.total_work)
        base_work_history.append(baseline_sched.total_work)

        from constants import THERMAL_LIMIT
        df_opt = pd.DataFrame(opt_history, columns=[f"Core {i}" for i in range(len(opt_temps))])
        df_base = pd.DataFrame(base_history, columns=[f"Core {i}" for i in range(len(base_temps))])
        
        # Add Thermal Limit to dataframes for visualization
        df_opt["Thermal Limit"] = THERMAL_LIMIT
        df_base["Thermal Limit"] = THERMAL_LIMIT

        # Reverted to original-style line charts for smooth, glitch-free updates
        chart_opt_placeholder.line_chart(df_opt)
        chart_base_placeholder.line_chart(df_base)

        completed = sum(1 for task in tasks if task.remaining <= 0)
        pending = len([task for task in tasks if task.remaining > 0])
        avg_temp = sum(opt_temps) / len(opt_temps)
        max_temp = max(opt_temps)

        if max_temp >= 60:
            status = "🔥 THERMAL THROTTLING ACTIVE"
            color = "#ff4b4b"
        else:
            status = "✅ SYSTEM STABLE"
            color = "#00ff9f"

        with status_placeholder.container():
            st.markdown(f"""
                <div style='height: 60px; display: flex; align-items: center; justify-content: center;'>
                    <h2 style='text-align:center; color:{color}; margin:0;'>{status}</h2>
                </div>
            """, unsafe_allow_html=True)

        with metrics_placeholder.container():
            st.markdown("### 📊 Live System Comparison")
            col_opt_stats, col_base_stats = st.columns(2)
            
            base_completed = sum(1 for t in baseline_tasks if t.remaining <= 0)
            base_avg_temp = sum(base_temps) / len(base_temps)
            
            with col_opt_stats:
                st.markdown("<p style='color:#00ff9f; font-weight:bold;'>⚡ Optimized</p>", unsafe_allow_html=True)
                m1, m2, m3 = st.columns(3)
                m1.metric("Completed", completed)
                m2.metric("Energy", f"{opt_energy:.1f}J")
                m3.metric("Avg Temp", f"{avg_temp:.1f}°C")
                
            with col_base_stats:
                st.markdown("<p style='color:#8b949e; font-weight:bold;'>🚫 Baseline</p>", unsafe_allow_html=True)
                b1, b2, b3 = st.columns(3)
                b1.metric("Completed", base_completed)
                b2.metric("Energy", f"{base_energy:.1f}J")
                b3.metric("Avg Temp", f"{base_avg_temp:.1f}°C")
            
            st.markdown("---")

        with core_placeholder.container():
            st.markdown("### 🧠 Core Status")
            core_cols = st.columns(len(opt_temps))
            for i, (col, temp) in enumerate(zip(core_cols, opt_temps)):
                if temp >= 60:
                    state, msg, border = "🔥 HOT", "Cooling...", "#ff4b4b"
                elif temp >= 50:
                    state, msg, border = "⚠ WARM", "Heating", "#ffaa00"
                else:
                    state, msg, border = "🟢 COOL", "Stable", "#00ff9f"
                col.markdown(f"""
                <div style="background:#161b22; padding:20px; border-radius:15px;
                    text-align:center; border:2px solid {border};
                    box-shadow: 0px 0px 15px {border};">
                    <h4>Core {i}</h4>
                    <h1>{temp:.1f}°C</h1>
                    <p>{state}</p>
                    <p style="color:{border}; font-weight:bold;">{msg}</p>
                </div>""", unsafe_allow_html=True)

        time.sleep(speed)

    # ══════════════════════════════════════════════════════════════
    # POST-SIMULATION RESULTS
    # ══════════════════════════════════════════════════════════════

    st.markdown("---")

    # ─── C1: KPI Summary Cards ───
    optimized_energy = opt_energy
    optimized_completed = completed
    baseline_completed = sum(1 for t in baseline_tasks if t.remaining <= 0)
    energy_saved = ((base_energy - optimized_energy) / base_energy) * 100 if base_energy > 0 else 0
    peak_temp = max(max(row) for row in opt_history)
    deadline_misses_count = len(sched.deadline_misses)

    # Turnaround times
    turnaround_times = []
    for t in tasks:
        if t.completion_time is not None:
            turnaround_times.append(t.completion_time - t.arrival)
    avg_turnaround = round(sum(turnaround_times) / len(turnaround_times), 1) if turnaround_times else 0

    st.markdown("## 🏁 Simulation Summary")
    
    # New Efficiency Calculations
    opt_efficiency = optimized_completed / max(optimized_energy, 1)
    base_efficiency = baseline_completed / max(base_energy, 1)
    opt_energy_per_task = optimized_energy / max(optimized_completed, 1)
    base_energy_per_task = base_energy / max(baseline_completed, 1)
    
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    kpi_data = [
        (k1, "Tasks Completed", f"{optimized_completed}", "#00ff9f"),
        (k2, "Deadline Misses", f"{deadline_misses_count}", "#ff4b4b" if deadline_misses_count > 0 else "#00ff9f"),
        (k3, "Energy Saved", f"{round(energy_saved, 1)}%", "#e040fb"),
        (k4, "Efficiency (T/J)", f"{opt_efficiency:.3f}", "#00ff9f"),
        (k5, "Energy/Task", f"{opt_energy_per_task:.2f}J", "#00b4d8"),
        (k6, "Peak Temp", f"{round(peak_temp, 1)}°C", "#ffaa00"),
    ]
    for col, label, value, clr in kpi_data:
        col.markdown(f"""
        <div class='glass-card' style='text-align:center; border-color:{clr};'>
            <div class='kpi-value' style='color:{clr};'>{value}</div>
            <div class='kpi-label'>{label}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("## 📋 Detailed Results")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "⚡ Energy Analysis",
        "📅 Gantt Chart",
        "🔄 Task Migrations",
        "🏆 Algorithm Comparison",
        "🧠 ML Predictor Info",
        "📋 Task Details"
    ])

    # ─── TAB 1: Energy Analysis + Heatmap ───
    with tab1:
        st.markdown("### ⚡ Energy Analysis")
        c1, c2, c3 = st.columns(3)
        c1.metric("Optimized Energy", f"{optimized_energy:.2f}J")
        c2.metric("Baseline Energy", f"{base_energy:.2f}J")
        c3.metric("Energy Saved (%)", f"{energy_saved:.2f}%")

        st.markdown("### 📈 Efficiency Metrics")
        ec1, ec2, ec3 = st.columns(3)
        ec1.metric("Optimized Efficiency (T/J)", f"{opt_efficiency:.4f}")
        ec2.metric("Baseline Efficiency (T/J)", f"{base_efficiency:.4f}")
        improvement = ((opt_efficiency - base_efficiency) / max(base_efficiency, 0.001)) * 100
        ec3.metric("Efficiency Gain (%)", f"{improvement:.1f}%")

        st.markdown("### 📉 Energy per Task")
        et1, et2, et3 = st.columns(3)
        et1.metric("Opt Energy/Task", f"{opt_energy_per_task:.2f} J/T")
        et2.metric("Base Energy/Task", f"{base_energy_per_task:.2f} J/T")
        reduction = ((base_energy_per_task - opt_energy_per_task) / max(base_energy_per_task, 0.001)) * 100
        et3.metric("Energy Reduction (%)", f"{reduction:.1f}%")

        # Work Done vs Energy Efficiency Curve
        st.markdown("### 📊 Work vs Energy Efficiency Curve")
        curve_df = pd.DataFrame({
            "Energy": opt_energy_history + base_energy_history,
            "Work Done": opt_work_history + base_work_history,
            "System": ["Optimized"] * len(opt_energy_history) + ["Baseline"] * len(base_energy_history)
        })
        fig_curve = px.line(curve_df, x="Energy", y="Work Done", color="System",
                           title="Cumulative Work vs Energy Consumption",
                           color_discrete_map={"Optimized": "#00ff9f", "Baseline": "#ff4b4b"})
        fig_curve.update_layout(template="plotly_dark", paper_bgcolor="#0d1117", plot_bgcolor="#161b22")
        st.plotly_chart(fig_curve, use_container_width=True)

        # Per-Core Energy Breakdown
        st.markdown("### 🔋 Per-Core Energy Breakdown")
        core_labels = [f"Core {i}" for i in range(len(sched.cores))]
        opt_core_energy = [round(c.energy, 2) for c in sched.cores]
        base_core_energy = [round(c.energy, 2) for c in baseline_sched.cores]

        fig_energy = go.Figure(data=[
            go.Bar(name="Optimized", x=core_labels, y=opt_core_energy,
                   marker_color="#00ff9f", text=opt_core_energy, textposition="auto"),
            go.Bar(name="Baseline", x=core_labels, y=base_core_energy,
                   marker_color="#ff4b4b", text=base_core_energy, textposition="auto")
        ])
        fig_energy.update_layout(
            barmode="group", template="plotly_dark",
            paper_bgcolor="#0d1117", plot_bgcolor="#161b22",
            title="Energy Consumption by Core",
            xaxis_title="Core", yaxis_title="Energy (units)",
            height=400, font=dict(color="#c9d1d9")
        )
        st.plotly_chart(fig_energy, use_container_width=True)

        # C2: Temperature Heatmap
        st.markdown("### 🌡️ Temperature Heatmap (Core × Time)")
        from constants import THERMAL_LIMIT
        heatmap_data = np.array(opt_history).T  # shape: (cores, ticks)
        fig_heat = go.Figure(data=go.Heatmap(
            z=heatmap_data,
            x=list(range(len(opt_history))),
            y=[f"Core {i}" for i in range(heatmap_data.shape[0])],
            colorscale=[[0, "#161b22"], [0.4, "#00ff9f"], [0.7, "#ffaa00"], [1, "#ff4b4b"]],
            colorbar=dict(title="°C")
        ))
        # Add Thermal Limit line to heatmap? Maybe not, but we can mention it.
        fig_heat.update_layout(
            template="plotly_dark", paper_bgcolor="#0d1117", plot_bgcolor="#161b22",
            title=f"Core Temperature Over Time (Limit: {THERMAL_LIMIT}°C)",
            xaxis_title="Tick", yaxis_title="Core",
            height=300, font=dict(color="#c9d1d9")
        )
        st.plotly_chart(fig_heat, use_container_width=True)

        # C4: Download
        df_energy_export = pd.DataFrame({
            "Core": core_labels,
            "Optimized Energy": opt_core_energy,
            "Baseline Energy": base_core_energy
        })
        st.download_button("📥 Download Energy Data (CSV)",
                           df_energy_export.to_csv(index=False), "energy_data.csv", "text/csv")

    # ─── TAB 2: Gantt Chart ───
    with tab2:
        st.markdown("### 📅 Task Execution Timeline (Gantt Chart)")
        gantt_data = sched.gantt_log
        if gantt_data:
            segments = []
            prev_tick, prev_core, prev_task, prev_freq = gantt_data[0]
            seg_start = prev_tick
            for tick, core_id, task_id, freq in gantt_data[1:]:
                if core_id == prev_core and task_id == prev_task:
                    prev_tick = tick
                else:
                    segments.append({"Task": f"T{prev_task}", "Core": f"Core {prev_core}",
                                     "Start": seg_start, "End": prev_tick + 1, "Freq": prev_freq})
                    seg_start = tick
                    prev_tick, prev_core, prev_task, prev_freq = tick, core_id, task_id, freq
            segments.append({"Task": f"T{prev_task}", "Core": f"Core {prev_core}",
                             "Start": seg_start, "End": prev_tick + 1, "Freq": prev_freq})

            df_gantt = pd.DataFrame(segments)
            fig_gantt = go.Figure()
            unique_tasks = df_gantt["Task"].unique()
            colors = px.colors.qualitative.Set3
            task_color_map = {t: colors[i % len(colors)] for i, t in enumerate(unique_tasks)}

            for _, row in df_gantt.iterrows():
                fig_gantt.add_trace(go.Bar(
                    x=[row["End"] - row["Start"]], y=[row["Core"]],
                    base=[row["Start"]], orientation="h",
                    name=row["Task"], marker_color=task_color_map[row["Task"]],
                    hovertemplate=(f"<b>{row['Task']}</b><br>Core: {row['Core']}<br>"
                                  f"Ticks: {row['Start']} → {row['End']}<br>"
                                  f"Freq: {row['Freq']}<extra></extra>"),
                    showlegend=False
                ))
            fig_gantt.update_layout(
                template="plotly_dark", paper_bgcolor="#0d1117", plot_bgcolor="#161b22",
                title="Task Execution Timeline (Gantt Chart)",
                xaxis_title="Simulation Tick", yaxis_title="Core",
                barmode="stack", height=350, font=dict(color="#c9d1d9"),
                yaxis=dict(categoryorder="array",
                           categoryarray=[f"Core {i}" for i in range(len(sched.cores))])
            )
            st.plotly_chart(fig_gantt, use_container_width=True)
            st.caption(f"Total execution segments: {len(segments)}")
        else:
            st.info("No tasks were executed during the simulation.")

    # ─── TAB 3: Task Migrations ───
    with tab3:
        st.markdown("### 🔄 Thermal Migration Log")
        migrations = sched.migration_log
        if migrations:
            st.metric("Total Migrations", len(migrations))
            df_mig = pd.DataFrame(migrations, columns=["Tick", "Task ID", "From Core", "Reason"])
            df_mig["Task ID"] = df_mig["Task ID"].apply(lambda x: f"T{x}")
            df_mig["From Core"] = df_mig["From Core"].apply(lambda x: f"Core {x}")
            st.dataframe(df_mig, use_container_width=True, height=400)

            st.markdown("### 📊 Migrations by Core")
            mig_counts = df_mig["From Core"].value_counts().reset_index()
            mig_counts.columns = ["Core", "Migrations"]
            fig_mig = px.bar(mig_counts, x="Core", y="Migrations", color="Migrations",
                             color_continuous_scale=["#00ff9f", "#ffaa00", "#ff4b4b"],
                             title="Thermal Migrations per Core")
            fig_mig.update_layout(template="plotly_dark", paper_bgcolor="#0d1117",
                                  plot_bgcolor="#161b22", height=300, font=dict(color="#c9d1d9"))
            st.plotly_chart(fig_mig, use_container_width=True)

            # C4: Download
            st.download_button("📥 Download Migration Log (CSV)",
                               df_mig.to_csv(index=False), "migration_log.csv", "text/csv")
        else:
            st.success("✅ No thermal migrations occurred — system stayed cool!")

    # ─── TAB 4: Algorithm Comparison ───
    with tab4:
        st.markdown("### 🏆 Throughput vs Energy — All Algorithms")
        st.caption("Running all 4 scheduling algorithms on the same workload...")

        algo_names = {"edf": "EDF", "sjf": "SJF", "priority": "Priority", "rr": "Round Robin"}
        algo_results = []

        with st.spinner("Running algorithm comparisons..."):
            for akey, aname in algo_names.items():
                comp, eng, s, t_copy = run_headless(ticks, original_tasks, akey,
                                                     baseline=False, tq=time_quantum, ml=use_ml)
                dm = len(s.deadline_misses)
                algo_results.append({"Algorithm": aname, "Completed Tasks": comp,
                                     "Total Energy": round(eng, 2), "Deadline Misses": dm})

            comp_b, eng_b, s_b, _ = run_headless(ticks, original_tasks, "edf", baseline=True)
            algo_results.append({"Algorithm": "Baseline (Max Freq)", "Completed Tasks": comp_b,
                                 "Total Energy": round(eng_b, 2), "Deadline Misses": len(s_b.deadline_misses)})

        df_algo = pd.DataFrame(algo_results)

        fig_tradeoff = px.scatter(
            df_algo, x="Total Energy", y="Completed Tasks", color="Algorithm",
            size=[25] * len(df_algo), text="Algorithm",
            title="Throughput vs Energy Trade-off (↗ = Better)",
            color_discrete_sequence=["#00ff9f", "#00b4d8", "#ffaa00", "#e040fb", "#ff4b4b"]
        )
        fig_tradeoff.update_traces(textposition="top center", textfont_size=12)
        fig_tradeoff.update_layout(
            template="plotly_dark", paper_bgcolor="#0d1117", plot_bgcolor="#161b22",
            height=450, font=dict(color="#c9d1d9"),
            xaxis_title="Total Energy (lower = better)",
            yaxis_title="Completed Tasks (higher = better)"
        )
        st.plotly_chart(fig_tradeoff, use_container_width=True)

        st.markdown("### 📋 Detailed Comparison")
        st.dataframe(df_algo.style.highlight_min(subset=["Total Energy"], color="#00ff9f22")
                     .highlight_max(subset=["Completed Tasks"], color="#00ff9f22"),
                     use_container_width=True)

        # C4: Download
        st.download_button("📥 Download Comparison (CSV)",
                           df_algo.to_csv(index=False), "algorithm_comparison.csv", "text/csv")

    # ─── TAB 5: ML Predictor Info ───
    with tab5:
        st.markdown("### 🧠 ML Thermal Predictor")
        st.info("💡 **Note**: The ML model is trained on synthetic thermal data for demonstration purposes.")
        if use_ml and sched._predictor is not None:
            st.success("🧠 **ML Predictor Impact**: Active")
            st.markdown("""
            The ML model proactively prevents thermal spikes by predicting temperatures **3 ticks ahead**. 
            This allows the scheduler to step down frequency **before** the thermal limit is hit, 
            avoiding aggressive throttling or task evictions.
            """)
            st.markdown("**Model**: Random Forest Regressor (50 trees, max depth 10)")
            st.markdown("**Action**: Predicted temp > 60°C → step down 2 freq levels; > 55°C → step down 1 level")

            importance = sched._predictor.get_feature_importance()
            if importance:
                st.markdown("### 📊 Feature Importance")
                df_imp = pd.DataFrame({"Feature": list(importance.keys()),
                                       "Importance": [round(v, 4) for v in importance.values()]})
                fig_imp = px.bar(df_imp, x="Feature", y="Importance", color="Importance",
                                color_continuous_scale=["#161b22", "#00ff9f"],
                                title="What drives temperature prediction?")
                fig_imp.update_layout(template="plotly_dark", paper_bgcolor="#0d1117",
                                      plot_bgcolor="#161b22", height=300, font=dict(color="#c9d1d9"))
                st.plotly_chart(fig_imp, use_container_width=True)
        elif use_ml:
            st.info("ML Predictor was enabled but no tasks triggered proactive DVFS.")
        else:
            st.warning("ML Predictor was disabled for this run. Enable it in the sidebar.")

    # ─── TAB 6: C3 Task Details ───
    with tab6:
        st.markdown("### 📋 Task Details & Timing Metrics")
        task_rows = []
        for t in tasks:
            response = (t.start_time - t.arrival) if t.start_time is not None else None
            turnaround = (t.completion_time - t.arrival) if t.completion_time is not None else None
            met = "✅" if (t.completion_time is not None and t.completion_time <= t.deadline) else "❌"
            if t.completion_time is None:
                met = "⏳ Incomplete"
            task_rows.append({
                "Task": f"T{t.tid}", "Arrival": t.arrival, "Burst": t.burst,
                "Deadline": t.deadline, "Priority": t.priority,
                "Utilization": t.utilization,
                "Start": t.start_time if t.start_time is not None else "—",
                "Completed": t.completion_time if t.completion_time is not None else "—",
                "Response Time": response if response is not None else "—",
                "Turnaround": turnaround if turnaround is not None else "—",
                "Deadline Met": met
            })
        df_tasks = pd.DataFrame(task_rows)
        st.dataframe(df_tasks, use_container_width=True, height=500)

        met_count = sum(1 for r in task_rows if r["Deadline Met"] == "✅")
        missed_count = sum(1 for r in task_rows if r["Deadline Met"] == "❌")
        incomplete = sum(1 for r in task_rows if r["Deadline Met"] == "⏳ Incomplete")
        m1, m2, m3 = st.columns(3)
        m1.metric("✅ Deadlines Met", met_count)
        m2.metric("❌ Deadlines Missed", missed_count)
        m3.metric("⏳ Incomplete", incomplete)

        # C4: Download
        st.download_button("📥 Download Task Details (CSV)",
                           df_tasks.to_csv(index=False), "task_details.csv", "text/csv")

    st.success("Simulation Complete 🚀")
