"""
Расчёт пористости и радиусов отверстий для сферической линзы Люнебурга
по слоям с шагом 3 мм.

Для каждого из 18 слоёв рассчитывается пористость и радиус отверстия
для каждой ячейки шестиугольной сетки на основе коэффициента преломления
по закону n(r) = sqrt(2 - r^2).
"""

import json
import math
import numpy as np
from pathlib import Path
from shapely.geometry import Polygon, Point

# -----------------------------
# Геометрические параметры
# -----------------------------
LENS_RADIUS_MM = 54.0  # Радиус линзы с оболочкой
LAYER_HEIGHT_MM = 3.0  # Высота каждого слоя
NUM_LAYERS = 18  # Количество слоёв

# Параметры шестиугольной сетки (из lens_porosity_layers.py)
SIDE_LENGTH_MM = np.sqrt(3.0)  # сторона шестиугольника
STEP_X_MM = 3.0 * np.sqrt(3.0) / 2.0
STEP_Y_MM = 1.5

# Радиус шестиугольника (расстояние от центра до вершины)
HEX_RADIUS = SIDE_LENGTH_MM
# Площадь шестиугольника: A = (3√3/2) * a²
HEX_AREA_MM2 = (3.0 * np.sqrt(3.0) / 2.0) * SIDE_LENGTH_MM**2

OUTPUT_DIR = Path("layers_sphere")
OUTPUT_DIR.mkdir(exist_ok=True)

# -----------------------------
# Параметры для расчёта пористости
# -----------------------------
EPS_D = 2.56  # диэлектрическая проницаемость (из coeff_refraction.py)
n_оболочки = 1.034
a_shell = 1.0 / n_оболочки  # Толщина оболочки


def calculate_refraction_coefficient(r_norm: float) -> float:
    """
    Вычисляет коэффициент преломления по закону n(r) = sqrt(2 - r^2).
    
    Параметры:
    ----------
    r_norm : float
        Нормированный радиус (0 <= r_norm <= 1, где 1 - край линзы с оболочкой)
    
    Возвращает:
    -----------
    float
        Коэффициент преломления n(r_norm)
    """
    if r_norm < 0:
        r_norm = 0.0
    elif r_norm > 1.0:
        # За пределами линзы (в оболочке) коэффициент преломления постоянный
        return n_оболочки
    
    # n(r) = sqrt(2 - r^2)
    n_value = np.sqrt(2.0 - r_norm**2)
    
    # Проверка на валидность (2 - r^2 должно быть >= 0)
    if n_value < 0 or not np.isfinite(n_value):
        # Если значение выходит за допустимые пределы, возвращаем n_оболочки
        return n_оболочки
    
    return n_value


def calculate_porosity(n: float) -> float:
    """
    Рассчитать пористость по формуле:
    p(r) = (1 + eps_d) * (eps_d - n²) / ((eps_d - 1) * (eps_d + n²))
    
    Параметры:
    ----------
    n : float
        Коэффициент преломления
    
    Возвращает:
    -----------
    float
        Пористость (0 <= p < 1)
    """
    n_sq = n ** 2
    numerator = (1.0 + EPS_D) * (EPS_D - n_sq)
    denominator = (EPS_D - 1.0) * (EPS_D + n_sq)
    
    if denominator == 0:
        return 0.0
    
    porosity = numerator / denominator
    
    # Ограничиваем результат диапазоном [0, 1)
    return float(np.clip(porosity, 0.0, 0.999999))


def calculate_hole_radius(porosity: float) -> float:
    """
    Рассчитать радиус отверстия из пористости.
    Пористость = площадь отверстия / площадь ячейки
    p = π * r² / A_hex
    r = sqrt(p * A_hex / π)
    
    Параметры:
    ----------
    porosity : float
        Пористость ячейки
    
    Возвращает:
    -----------
    float
        Радиус отверстия в мм
    """
    if porosity <= 0:
        return 0.0
    return np.sqrt(porosity * HEX_AREA_MM2 / np.pi)


def hexagon_vertices(center: tuple, side_length: float) -> list:
    """
    Возвращает координаты вершин повёрнутого шестиугольника.
    
    Параметры:
    ----------
    center : tuple
        Координаты центра (x, y)
    side_length : float
        Длина стороны шестиугольника
    
    Возвращает:
    -----------
    list
        Список координат вершин [(x1, y1), (x2, y2), ...]
    """
    cx, cy = center
    orientation = np.pi / 2.0  # поворот на 90 градусов
    angles = np.linspace(0.0, 2.0 * np.pi, 7)[:-1]  # 6 вершин
    vertices = []
    for angle in angles:
        x = cx + side_length * np.cos(angle + orientation)
        y = cy + side_length * np.sin(angle + orientation)
        vertices.append((x, y))
    return vertices


def hexagon_intersects_circle(center: tuple, hex_radius: float, circle: Polygon) -> bool:
    """
    Проверить, пересекается ли шестиугольник с кругом.
    
    Параметры:
    ----------
    center : tuple
        Координаты центра шестиугольника
    hex_radius : float
        Радиус шестиугольника (расстояние от центра до вершины)
    circle : Polygon
        Круг как объект Shapely
    
    Возвращает:
    -----------
    bool
        True если шестиугольник пересекается с кругом
    """
    vertices = hexagon_vertices(center, hex_radius)
    hex_polygon = Polygon(vertices)
    return hex_polygon.intersects(circle)


# -----------------------------
# Генерация центров шестиугольной решётки
# -----------------------------
# Создаем круг как объект Shapely для проверки пересечения
circle = Point(0, 0).buffer(LENS_RADIUS_MM)

# Расширяем диапазон поиска, учитывая радиус шестиугольника
max_ix = int(math.ceil((LENS_RADIUS_MM + HEX_RADIUS) / STEP_X_MM))
max_iy = int(math.ceil((LENS_RADIUS_MM + HEX_RADIUS) / STEP_Y_MM))

# Генерируем все центры ячеек один раз
all_centers = []
for ix in range(-max_ix, max_ix + 1):
    for iy in range(-max_iy, max_iy + 1):
        # Правило чётности для шестиугольной решётки
        if (ix % 2 == 0 and iy % 2 == 0) or (ix % 2 != 0 and iy % 2 != 0):
            x = ix * STEP_X_MM
            y = iy * STEP_Y_MM
            center = (x, y)
            
            # Проверяем пересечение шестиугольника с кругом
            if hexagon_intersects_circle(center, HEX_RADIUS, circle):
                all_centers.append((x, y))

print(f"Сгенерировано {len(all_centers)} центров ячеек для сетки")
print(f"Параметры сетки:")
print(f"  Радиус линзы: {LENS_RADIUS_MM} мм")
print(f"  Сторона шестиугольника: {SIDE_LENGTH_MM:.6f} мм")
print(f"  Площадь шестиугольника: {HEX_AREA_MM2:.6f} мм²")
print(f"  Шаг по X: {STEP_X_MM:.6f} мм")
print(f"  Шаг по Y: {STEP_Y_MM:.6f} мм")
print()

# -----------------------------
# Расчёт для всех 19 слоёв
# -----------------------------
for layer_index in range(NUM_LAYERS):
    z_mm = layer_index * LAYER_HEIGHT_MM
    print(f"Обработка слоя {layer_index + 1}/{NUM_LAYERS} (z = {z_mm:6.2f} мм)...")
    
    # Радиус сечения слоя (для сферической линзы)
    if z_mm >= LENS_RADIUS_MM:
        # Слой за пределами линзы
        layer_radius = 0.0
    else:
        layer_radius = np.sqrt(LENS_RADIUS_MM**2 - z_mm**2)
    
    # Создаём круг сечения для фильтрации ячеек
    layer_circle = Point(0.0, 0.0).buffer(layer_radius)
    
    cells = []
    
    for x, y in all_centers:
        # Проверяем, пересекается ли ячейка с сечением слоя
        hex_vertices = hexagon_vertices((x, y), HEX_RADIUS)
        hex_polygon = Polygon(hex_vertices)
        
        if not hex_polygon.intersects(layer_circle):
            continue
        
        # Вычисляем 3D радиус от центра линзы
        r_xy = np.sqrt(x**2 + y**2)
        r_3d = np.sqrt(r_xy**2 + z_mm**2)
        
        # Нормированный радиус (относительно радиуса линзы с оболочкой)
        r_norm = r_3d / LENS_RADIUS_MM
        
        # Получаем коэффициент преломления
        n = calculate_refraction_coefficient(r_norm)
        
        # Вычисляем пористость
        porosity = calculate_porosity(n)
        
        # Вычисляем радиус отверстия
        hole_radius = calculate_hole_radius(porosity)
        
        cells.append({
            "x": round(x, 6),
            "y": round(y, 6),
            "z": round(z_mm, 6),
            "r_xy": round(r_xy, 6),
            "r_3d": round(r_3d, 6),
            "r_norm": round(r_norm, 6),
            "n": round(n, 6),
            "porosity": round(porosity, 6),
            "r": round(hole_radius, 6)
        })
    
    # Сохранение в JSON-файл для текущего слоя
    output_file = OUTPUT_DIR / f"layer_{layer_index + 1:02d}.json"
    output = {
        "layer": layer_index + 1,
        "z_mm": round(z_mm, 2),
        "layer_radius_mm": round(layer_radius, 6),
        "cells": cells
    }
    
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"  Сохранено {len(cells)} ячеек в {output_file}")

print(f"\nРасчёт завершён для всех {NUM_LAYERS} слоёв!")
print(f"Результаты сохранены в директории: {OUTPUT_DIR}")
