import matplotlib.pyplot as plt
import numpy as np

# Data based on the results of TC-01 and TC-02 (Simultaneous Overlapping Speech)
methods = ['Raw Audio', 'Wiener Filter', 'Bandpass', 'Spectral Gated\n(RNNoise)', 'High-Pass', 'Moving Average']
auth_accuracy = [100, 100, 0, 100, 100, 100]
intent_accuracy = [0, 0, 0, 100, 100, 0]

x = np.arange(len(methods))
width = 0.35

# Create the figure
fig, ax = plt.subplots(figsize=(11, 6))

# Plot the bars
rects1 = ax.bar(x - width/2, auth_accuracy, width, label='Biometric Auth Accuracy (%)', color='#2b83ba')
rects2 = ax.bar(x + width/2, intent_accuracy, width, label='Intent Classification Accuracy (%)', color='#abdda4')

# Add labels, title, and formatting
ax.set_ylabel('Accuracy / Success Rate (%)', fontsize=12, fontweight='bold')
ax.set_title('System Performance During Simultaneous Speech Scenarios (TC-01 & TC-02)', fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(methods, rotation=0, fontsize=10)
ax.legend(loc='lower left')
ax.set_ylim(0, 115) # Leave room for labels on top

# Add numbers on top of bars
def autolabel(rects):
    for rect in rects:
        height = rect.get_height()
        ax.annotate(f'{height}%',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontweight='bold')

autolabel(rects1)
autolabel(rects2)

# Add a grid for easier reading
ax.yaxis.grid(True, linestyle='--', alpha=0.7)

fig.tight_layout()

# Save the graph to a file so it can be inserted into the thesis report
plt.savefig('performance_accuracy_graph.png', dpi=300)
print("Graph successfully saved as 'performance_accuracy_graph.png'")

# Show the graph on screen
plt.show()
