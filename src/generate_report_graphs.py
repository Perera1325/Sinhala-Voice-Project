import os
import matplotlib.pyplot as plt
import numpy as np

# Create directory for graphs
output_dir = "Report_Graphs"
os.makedirs(output_dir, exist_ok=True)

# =========================================================
# GRAPH 1: STT Accuracy vs Hardware Device Success Rate
# =========================================================
def generate_hardware_vs_stt_graph():
    # Data from our final matrix evaluation
    methods = ['Wiener', 'Bandpass', 'RNNoise', 'HighPass']
    stt_accuracy = [40.0, 25.0, 55.0, 65.0]
    device_success = [100.0, 100.0, 100.0, 90.0]

    x = np.arange(len(methods))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))
    rects1 = ax.bar(x - width/2, stt_accuracy, width, label='Google STT Accuracy', color='#1f77b4', edgecolor='black')
    rects2 = ax.bar(x + width/2, device_success, width, label='Hardware Activation Success', color='#2ca02c', edgecolor='black')

    ax.set_ylabel('Success Rate (%)', fontsize=12, fontweight='bold')
    ax.set_title('Standard STT vs Localized Hardware AI (Under 10dB Noise)', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(methods, fontsize=11)
    ax.legend()
    ax.set_ylim(0, 115)
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    # Add text labels on top of bars
    for rects in [rects1, rects2]:
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f'{height}%',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=10, fontweight='bold')

    plt.tight_layout()
    filepath = os.path.join(output_dir, 'stt_vs_hardware_accuracy.png')
    plt.savefig(filepath, dpi=300)
    print(f"Generated: {filepath}")
    plt.close()

# =========================================================
# GRAPH 2: Initial STT Degradation Analysis
# =========================================================
def generate_stt_degradation_graph():
    # Data from our initial STT degradation test
    conditions = ['Clean Audio', 'Noisy (10dB)', 'HighPass Filter', 'RNNoise', 'Bandpass']
    accuracy = [75.0, 40.0, 35.0, 30.0, 20.0]

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(conditions, accuracy, color=['#2ca02c', '#d62728', '#ff7f0e', '#ff7f0e', '#ff7f0e'], edgecolor='black')

    ax.set_ylabel('Recognition Accuracy (%)', fontsize=12, fontweight='bold')
    ax.set_title('Google STT Performance Degradation from Static Filtering', fontsize=14, fontweight='bold')
    ax.set_ylim(0, 100)
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    # Add text labels on top of bars
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, yval, f'{yval}%', va='bottom', ha='center', fontsize=11, fontweight='bold')

    plt.tight_layout()
    filepath = os.path.join(output_dir, 'stt_degradation.png')
    plt.savefig(filepath, dpi=300)
    print(f"Generated: {filepath}")
    plt.close()

if __name__ == "__main__":
    print("Generating Publication-Quality Graphs for Thesis...")
    try:
        generate_hardware_vs_stt_graph()
        generate_stt_degradation_graph()
        print("Success! Graphs are saved in the 'Report_Graphs' folder.")
    except ImportError:
        print("Error: matplotlib is not installed. Please run 'pip install matplotlib numpy' first.")
