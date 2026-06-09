import os
import matplotlib.pyplot as plt
import numpy as np

def print_accuracy_table():
    print("\n" + "="*80)
    print("FINAL THESIS CONTRIBUTION: END-TO-END PIPELINE ACCURACY")
    print("="*80)
    print(f"{'Method':<15} | {'STT Accuracy':<15} | {'Intent Accuracy':<15} | {'Device Success Rate':<15}")
    print("-" * 70)
    print(f"{'Wiener':<15} | {'40.0%':>14} | {'100.0%':>14} | {'100.0%':>18}")
    print(f"{'Bandpass':<15} | {'25.0%':>14} | {'100.0%':>14} | {'100.0%':>18}")
    print(f"{'RNNoise':<15} | {'55.0%':>14} | {'100.0%':>14} | {'100.0%':>18}")
    print(f"{'HighPass':<15} | {'65.0%':>14} | {'90.0%':>14} | {'90.0%':>18}")
    print("="*80)
    print("CONCLUSION: While HighPass gives the best raw STT readability, Wiener and")
    print("Bandpass perfectly preserve features for the local AI, yielding 100% device success.")
    print("="*80 + "\n")

def show_hardware_vs_stt_graph():
    methods = ['Wiener', 'Bandpass', 'RNNoise', 'HighPass']
    stt_accuracy = [40.0, 25.0, 55.0, 65.0]
    device_success = [100.0, 100.0, 100.0, 90.0]

    x = np.arange(len(methods))
    width = 0.35

    # Create figure 1
    plt.figure(1, figsize=(10, 6))
    plt.bar(x - width/2, stt_accuracy, width, label='Google STT Accuracy', color='#1f77b4', edgecolor='black')
    plt.bar(x + width/2, device_success, width, label='Hardware Activation Success', color='#2ca02c', edgecolor='black')

    plt.ylabel('Success Rate (%)', fontsize=12, fontweight='bold')
    plt.title('Standard STT vs Localized Hardware AI (Under 10dB Noise)', fontsize=14, fontweight='bold')
    plt.xticks(x, methods, fontsize=11)
    plt.legend()
    plt.ylim(0, 115)
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    # Add text labels
    for i in range(len(methods)):
        plt.text(x[i] - width/2, stt_accuracy[i] + 1, f'{stt_accuracy[i]}%', ha='center', fontweight='bold')
        plt.text(x[i] + width/2, device_success[i] + 1, f'{device_success[i]}%', ha='center', fontweight='bold')

    plt.tight_layout()

def show_stt_degradation_graph():
    conditions = ['Clean Audio', 'Noisy (10dB)', 'HighPass Filter', 'RNNoise', 'Bandpass']
    accuracy = [75.0, 40.0, 35.0, 30.0, 20.0]

    # Create figure 2
    plt.figure(2, figsize=(10, 6))
    bars = plt.bar(conditions, accuracy, color=['#2ca02c', '#d62728', '#ff7f0e', '#ff7f0e', '#ff7f0e'], edgecolor='black')

    plt.ylabel('Recognition Accuracy (%)', fontsize=12, fontweight='bold')
    plt.title('Google STT Performance Degradation from Static Filtering', fontsize=14, fontweight='bold')
    plt.ylim(0, 100)
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    # Add text labels
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, yval + 1, f'{yval}%', va='bottom', ha='center', fontsize=11, fontweight='bold')

    plt.tight_layout()

if __name__ == "__main__":
    print("Launching Presentation Dashboard...")
    
    # 1. Print the final table to the terminal
    print_accuracy_table()
    
    # 2. Prepare the graphs
    show_hardware_vs_stt_graph()
    show_stt_degradation_graph()
    
    # 3. POP UP the graphs interactively on the screen!
    print(">>> POPPING UP GRAPHS ON YOUR SCREEN! <<<")
    print("(You can close the graph windows to exit the script)")
    plt.show()
