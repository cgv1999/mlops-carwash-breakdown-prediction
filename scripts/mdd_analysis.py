import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from scipy import stats

np.random.seed(42)

existing_system = np.random.normal(loc=3.5, scale=0.4, size=500000)
improved_system = np.random.normal(loc=2.0, scale=0.4, size=500000)

plt.figure(figsize=(10, 6))
sns.kdeplot(existing_system, label='Существующая система', fill=True, color='red')
sns.kdeplot(improved_system, label='Улучшенная система', fill=True, color='green')
plt.title('Сравнение времени отклика системы')
plt.xlabel('Время отклика (секунды)')
plt.ylabel('Плотность распределения')
plt.legend()
plt.grid(True, linestyle='--', alpha=0.7)
plt.savefig('docs/latency_comparison.png', dpi=150, bbox_inches='tight')
plt.close()

t_stat, p_value = stats.ttest_ind(existing_system, improved_system)
mean_existing = np.mean(existing_system)
mean_improved = np.mean(improved_system)
diff = mean_existing - mean_improved
improvement_pct = (diff / mean_existing) * 100

print("MDD АНАЛИЗ: СРАВНЕНИЕ ВРЕМЕНИ ОТКЛИКА СИСТЕМ")
print(f"Существующая система: среднее = {mean_existing:.2f} сек")
print(f"Улучшенная система: среднее = {mean_improved:.2f} сек")
print(f"Разница: {diff:.2f} сек")
print(f"Улучшение: {improvement_pct:.1f}%")
print()
print(f"t-статистика: {t_stat:.2f}")
print(f"p-value: {p_value:.6f}")
print()
print("Гипотезы:")
print("H0: Среднее время отклика одинаковое")
print("H1: Среднее время отклика улучшенной системы ниже")
print()
if p_value < 0.05:
    print("РЕШЕНИЕ: H0 отклоняется.")
    print("Улучшенная система статистически значимо быстрее.")
    print("Рекомендуется переход на улучшенную архитектуру.")
else:
    print("РЕШЕНИЕ: H0 не отклоняется.")
    print("Разница статистически незначима.")
    print("Рекомендуется оставить существующую систему.")