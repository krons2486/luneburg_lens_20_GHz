"""
Модуль для расчета коэффициента преломления и построения кривых n(p) и R(p)
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, AutoMinorLocator, MaxNLocator
from scipy.integrate import quad


# Константы
eps_d = 3.2  # Диэлектрическая проницаемость материала
n_оболочки = 1.034
a = 1 / n_оболочки
R1 = 1.0  # Радиус R1 по условию задачи равен 1


def q_integrand(t, p, a_val):
    """
    Подынтегральная функция для q(p, a):
    arcsin(t / a) / sqrt(t^2 - p^2)
    """
    if t <= p or t**2 - p**2 <= 0:
        return 0.0
    denominator = np.sqrt(t**2 - p**2)
    if denominator == 0:
        return 0.0
    arcsin_arg = np.clip(t / a_val, -1.0, 1.0)
    return np.arcsin(arcsin_arg) / denominator


def q(p, a_val):
    """
    q(p, a) = 1/pi * интеграл от p до 1 (arcsin(t/a) / sqrt(t^2 - p^2)) dt
    """
    if p >= 1:
        return 0.0
    
    result, _ = quad(q_integrand, p, 1, args=(p, a_val), limit=1000)
    return result / np.pi


def P(R, n_оболочки_val):
    """
    P(R) = n_оболочки * R
    R здесь - переменная интегрирования (не R(p) = p/n(p))
    """
    return n_оболочки_val * R


def Q_integrand(R, p, n_оболочки_val, a_val):
    """
    Подынтегральная функция для Q(p)
    R - переменная интегрирования (не R(p) = p/n(p))
    """
    if R < a_val or R > 1:
        return 0.0
    
    P_R = P(R, n_оболочки_val)
    # P_R = n_оболочки * R, меняется от 1 (при R = a) до n_оболочки (при R = 1)
    # При P_R = 1 знаменатель P_R^2 - 1 = 0, поэтому исключаем эту точку
    if P_R < 1:
        return 0.0
    
    numerator = 1 - p**2
    denominator = P_R**2 - 1
    
    if denominator <= 0:
        return 0.0
    
    sqrt_arg = numerator / denominator
    if sqrt_arg < 0:
        return 0.0
    
    return np.arctan(np.sqrt(sqrt_arg)) / R


def Q(p, n_оболочки_val, a_val):
    """
    Q(p) = 2/pi * интеграл от a до 1 от arctg(sqrt((1-p^2)/(P(R)^2-1))) dR/R
    R в интеграле - переменная интегрирования (не R(p) = p/n(p))
    Если a = 1, то Q(p) = 0 (оболочки нет)
    """
    if a_val >= 1:
        return 0.0
    
    result, _ = quad(Q_integrand, a_val, 1, args=(p, n_оболочки_val, a_val), limit=1000)
    return 2 * result / np.pi


def n(p, n_оболочки_val, a_val, R1_val):
    """
    n(p) = 1/a * exp(q(p, R1) - Q(p))
    """
    q_val = q(p, R1_val)
    Q_val = Q(p, n_оболочки_val, a_val)
    return (1 / a_val) * np.exp(q_val - Q_val)


def R_from_p(p, n_p):
    """
    R(p) = p / n(p)
    """
    # Избегаем деления на ноль
    n_p_safe = np.where(n_p > 0, n_p, np.finfo(float).eps)
    return p / n_p_safe


def porosity_from_n(n_values, eps_d_val):
    """
    p(R) = ((1 + eps_d) * (eps_d - n(R)^2)) / ((eps_d - 1) * (eps_d + n(R)^2))
    """
    n_sq = n_values**2
    numerator = (1 + eps_d_val) * (eps_d_val - n_sq)
    denominator = (eps_d_val - 1) * (eps_d_val + n_sq)
    with np.errstate(divide="ignore", invalid="ignore"):
        result = np.where(np.abs(denominator) > 1e-12, numerator / denominator, np.nan)
    return result


def main():
    """
    Основная функция для построения графиков
    """
    # Создаем массив p от 0 до 1 (100 элементов)
    p_array = np.linspace(0, 1, 1000)
    
    # Вычисляем n(p) для каждого значения p
    n_array = np.zeros_like(p_array)
    p_calc = p_array.copy()
    # Для p = 0 может быть особая точка, используем очень малое значение
    p_calc[p_calc == 0] = 1e-10
    
    for i, p_val in enumerate(p_calc):
        n_array[i] = n(p_val, n_оболочки, a, R1)
    
    # Вычисляем R(p) = p / n(p)
    R_array = R_from_p(p_array, n_array)
    
    # Сортируем значения по R для корректных графиков
    sort_idx = np.argsort(R_array)
    R_core = R_array[sort_idx]
    n_core = n_array[sort_idx]
    porosity_core = porosity_from_n(n_core, eps_d)

    # Расширяем данные для оболочки, если R(p) не достигает 1
    R_full = R_core
    n_full = n_core
    porosity_full = porosity_core

    if a < 1:
        R_max = R_core[-1]
        if R_max < 1:
            R_start = max(R_max, a)
            R_shell = np.linspace(R_start, 1, 50)
            n_shell = np.full_like(R_shell, n_оболочки)
            porosity_shell = porosity_from_n(n_shell, eps_d)

            # Исключаем первый элемент, если он совпадает с последним значением ядра, чтобы избежать дубликатов
            if np.isclose(R_shell[0], R_full[-1]):
                R_shell = R_shell[1:]
                n_shell = n_shell[1:]
                porosity_shell = porosity_shell[1:]

            R_full = np.concatenate([R_full, R_shell])
            n_full = np.concatenate([n_full, n_shell])
            porosity_full = np.concatenate([porosity_full, porosity_shell])

    # Построение графиков
    fig, axes = plt.subplots(2, 2, figsize=(16, 9))
    ax11, ax12 = axes[0]
    ax21, ax22 = axes[1]

    # График n(p) vs p
    ax11.plot(p_array, n_array, 'b-', linewidth=2, label='n(ρ)')
    ax11.set_xlabel('ρ', fontsize=12)
    ax11.set_ylabel('n(ρ)', fontsize=12)
    ax11.set_title('Коэффициент преломления n(ρ)', fontsize=14)
    # Устанавливаем фиксированные пределы осей
    ax11.set_xlim(0, 1.01)
    ax11.set_ylim(1.1, 1.45)
    # Перемещаем оси вниз и влево
    ax11.spines['bottom'].set_position(('data', 1.1))
    ax11.spines['left'].set_position(('data', 0))
    ax11.spines['top'].set_visible(False)
    ax11.spines['right'].set_visible(False)
    ax11.xaxis.set_major_locator(MultipleLocator(0.1))
    ax11.xaxis.set_minor_locator(MultipleLocator(0.05))
    ax11.yaxis.set_major_locator(MultipleLocator(0.05))
    ax11.yaxis.set_minor_locator(MultipleLocator(0.025))
    ax11.grid(True, which='major', alpha=0.5, linestyle='-', linewidth=0.8)
    ax11.grid(True, which='minor', alpha=0.2, linestyle='--', linewidth=0.5)
    ax11.legend(fontsize=10)

    # График R(p) vs ρ
    ax12.plot(p_array, R_array, 'r-', linewidth=2, label='R(p)')
    ax12.set_xlabel('ρ', fontsize=12)
    ax12.set_ylabel('R(ρ)', fontsize=12)
    ax12.set_title('R(ρ) = ρ / n(ρ)', fontsize=14)
    # Устанавливаем фиксированные пределы осей
    ax12.set_xlim(0, 1.01)
    ax12.set_ylim(0, 1.0)
    # Перемещаем оси вниз и влево
    ax12.spines['bottom'].set_position(('data', 0))
    ax12.spines['left'].set_position(('data', 0))
    ax12.spines['top'].set_visible(False)
    ax12.spines['right'].set_visible(False)
    ax12.xaxis.set_major_locator(MultipleLocator(0.1))
    ax12.xaxis.set_minor_locator(MultipleLocator(0.05))
    ax12.yaxis.set_major_locator(MultipleLocator(0.1))
    ax12.yaxis.set_minor_locator(MultipleLocator(0.05))
    ax12.grid(True, which='major', alpha=0.5, linestyle='-', linewidth=0.8)
    ax12.grid(True, which='minor', alpha=0.2, linestyle='--', linewidth=0.5)
    ax12.legend(fontsize=10, loc='upper left')

    # Расчет для случая без оболочки (a=1, Q=0)
    n_array_no_shell = np.zeros_like(p_array)
    
    for i, p_val in enumerate(p_calc):
        # Для случая без оболочки: n(p) = exp(q(p, R1)), так как Q=0 и a=1
        q_val = q(p_val, R1)
        n_array_no_shell[i] = np.exp(q_val)
    
    # Вычисляем R(p) = p / n(p) для случая без оболочки
    R_array_no_shell = R_from_p(p_array, n_array_no_shell)
    
    # Сортируем значения по R для корректных графиков
    sort_idx_no_shell = np.argsort(R_array_no_shell)
    R_no_shell = R_array_no_shell[sort_idx_no_shell]
    n_no_shell = n_array_no_shell[sort_idx_no_shell]
    
    # График n(R) - с оболочкой и без оболочки
    ax21.plot(R_full, n_full, 'g-', linewidth=2, label='n(R) с оболочкой')
    ax21.plot(R_no_shell, n_no_shell, 'r--', linewidth=2, label='n(R) без оболочки')
    ax21.set_xlabel('R', fontsize=12)
    ax21.set_ylabel('n(R)', fontsize=12)
    ax21.set_title('n(R) как функция радиуса', fontsize=14)
    # Устанавливаем фиксированные пределы осей
    ax21.set_xlim(0, 1.01)
    ax21.set_ylim(1, 1.45)
    # Перемещаем оси вниз и влево
    ax21.spines['bottom'].set_position(('data', 1))
    ax21.spines['left'].set_position(('data', 0))
    ax21.spines['top'].set_visible(False)
    ax21.spines['right'].set_visible(False)
    ax21.xaxis.set_major_locator(MultipleLocator(0.1))
    ax21.xaxis.set_minor_locator(MultipleLocator(0.05))
    ax21.yaxis.set_major_locator(MultipleLocator(0.05))
    ax21.yaxis.set_minor_locator(MultipleLocator(0.025))
    ax21.grid(True, which='major', alpha=0.5, linestyle='-', linewidth=0.8)
    ax21.grid(True, which='minor', alpha=0.2, linestyle='--', linewidth=0.5)
    ax21.legend(fontsize=10)

    # График пористости p(R)
    ax22.plot(R_full, porosity_full, 'm-', linewidth=2, label='p(R)')
    porosity_max = np.nanmax(porosity_full)
    porosity_ylim_top = max(0.85, porosity_max * 1.05)
    ax22.set_xlabel('R', fontsize=12)
    ax22.set_ylabel('p(R)', fontsize=12)
    ax22.set_title('Пористость p(R)', fontsize=14)
    # Устанавливаем фиксированные пределы осей
    ax22.set_xlim(0, 1.01)
    ax22.set_ylim(0, porosity_ylim_top)
    # Перемещаем оси вниз и влево
    ax22.spines['bottom'].set_position(('data', 0))
    ax22.spines['left'].set_position(('data', 0))
    ax22.spines['top'].set_visible(False)
    ax22.spines['right'].set_visible(False)
    ax22.xaxis.set_major_locator(MultipleLocator(0.1))
    ax22.xaxis.set_minor_locator(MultipleLocator(0.05))
    ax22.yaxis.set_major_locator(MultipleLocator(0.1))
    ax22.yaxis.set_minor_locator(MultipleLocator(0.05))
    ax22.grid(True, which='major', alpha=0.5, linestyle='-', linewidth=0.8)
    ax22.grid(True, which='minor', alpha=0.2, linestyle='--', linewidth=0.5)
    ax22.legend(fontsize=10)

    plt.tight_layout()
    plt.show()
    
    # Вывод информации
    print(f"Параметры:")
    print(f"n_оболочки = {n_оболочки}")
    print(f"a = 1/n_оболочки = {a}")
    print(f"R1 = {R1}")
    print(f"eps_d = {eps_d}")
    print(f"\nДиапазон значений:")
    print(f"n(p): min = {np.min(n_array):.4f}, max = {np.max(n_array):.4f}")
    print(f"R(p): min = {np.min(R_array):.4f}, max = {np.max(R_array):.4f}")
    print(f"p(R): min = {np.nanmin(porosity_full):.4f}, max = {np.nanmax(porosity_full):.4f}")


if __name__ == "__main__":
    main()

