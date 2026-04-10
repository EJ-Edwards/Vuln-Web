import matplotlib.pyplot as plt
import numpy as np

# Data from RedSight Budget Allocation
labels = ['Product Dev', 'Marketing & Sales', 'Founder Pay', 'Legal', 'Emergency', 'Infrastructure']
sizes = [32.0, 20.0, 18.0, 13.0, 9.0, 8.0]
colors = ['#1E88E5', '#42A5F5', '#FFC107', '#9C27B0', '#FF5722', '#4CAF50']
explode = (0.05, 0.05, 0.05, 0.05, 0.05, 0.05)

fig = plt.figure(figsize=(14, 7), facecolor='#0a0a0a')

# --- Left: 3D Pie Chart ---
ax1 = fig.add_subplot(121)
ax1.set_facecolor('#0a0a0a')

wedges, texts, autotexts = ax1.pie(
    sizes,
    explode=explode,
    labels=labels,
    colors=colors,
    autopct='%1.1f%%',
    shadow=True,
    startangle=140,
    pctdistance=0.75,
    labeldistance=1.15,
)

for t in texts:
    t.set_color('white')
    t.set_fontsize(10)
    t.set_fontweight('bold')
for t in autotexts:
    t.set_color('white')
    t.set_fontsize(9)
    t.set_fontweight('bold')


# --- Right: Investment Breakdown text ---
ax2 = fig.add_subplot(122)
ax2.set_facecolor('#0a0a0a')
ax2.axis('off')

ax2.text(0.05, 0.85, 'Investment\nBreakdown', color='white', fontsize=28, fontweight='bold',
         fontfamily='serif', va='top', transform=ax2.transAxes)

ax2.plot([0.05, 0.95], [0.58, 0.58], color='#dc2626', linewidth=2, transform=ax2.transAxes)

bullets = [
    '$250K–$400K allocation',
    'Product + marketing focused',
    'Built for efficient growth',
    'Optimized for market entry',
]
for i, text in enumerate(bullets):
    ax2.text(0.08, 0.50 - i * 0.09, f'•  {text}', color='white', fontsize=13,
             transform=ax2.transAxes, va='top')

plt.tight_layout(pad=2)
plt.savefig('investment_breakdown.png', dpi=200, facecolor='#0a0a0a', bbox_inches='tight')
plt.show()
print("Saved to investment_breakdown.png")
