import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import RegularPolygon
from shapely.geometry import Polygon, Point

# Параметры
radius = 54  # радиус круга в мм
step_x = 3 * np.sqrt(3) / 2  # шаг по x в мм
step_y = 1.5  # шаг по y в мм
side_length = np.sqrt(3)  # сторона шестиугольника в мм

# Создаем круг как объект Shapely для проверки пересечения
circle = Point(0, 0).buffer(radius)

# Списки для координат центров шестиугольников
centers_even = []  # четные x и y
centers_odd = []   # нечетные x и y

# Радиус шестиугольника (расстояние от центра до вершины)
hex_radius = side_length
# Максимальное расстояние от центра шестиугольника до его границы
# Это нужно для определения диапазона генерации центров
max_hex_distance = hex_radius

# Определяем диапазон индексов для покрытия всего круга
# Добавляем запас, равный радиусу шестиугольника, чтобы покрыть границы
max_index_x = int(np.ceil((radius + max_hex_distance) / step_x))
max_index_y = int(np.ceil((radius + max_hex_distance) / step_y))

# Перебираем индексы - генерируем все центры в сетке
for i in range(-max_index_x, max_index_x + 1):
    for j in range(-max_index_y, max_index_y + 1):
        # Вычисляем координаты по формуле
        x = step_x * i
        y = step_y * j
        
        # Разделяем точки по четности индексов (не проверяем, внутри ли центр круга)
        if i % 2 == 0 and j % 2 == 0:
            centers_even.append((x, y))
        elif i % 2 != 0 and j % 2 != 0:
            centers_odd.append((x, y))

# Создаем график
fig, ax = plt.subplots(figsize=(12, 12))
ax.set_aspect('equal')

# Рисуем круг
circle_patch = plt.Circle((0, 0), radius, fill=False, color='blue', linewidth=2)
ax.add_artist(circle_patch)

# Функция для проверки пересечения шестиугольника с кругом
def hexagon_intersects_circle(center, side_length):
    # Создаем шестиугольник как объект Shapely
    # Для RegularPolygon из matplotlib радиус - это расстояние от центра до вершины
    # Для шестиугольника с длиной стороны a: радиус = a
    hex_radius = side_length
    
    # Получаем координаты вершин шестиугольника (повернутого на 90 градусов)
    orientation = np.pi / 2  # 90 градусов в радианах
    angles = np.linspace(0, 2*np.pi, 7)[:-1]  # 6 вершин (без последней, которая равна первой)
    vertices = []
    for angle in angles:
        x = center[0] + hex_radius * np.cos(angle + orientation)
        y = center[1] + hex_radius * np.sin(angle + orientation)
        vertices.append((x, y))
    
    # Создаем полигон шестиугольника
    hex_polygon = Polygon(vertices)
    
    # Проверяем пересечение с кругом
    return hex_polygon.intersects(circle)

# Функция для рисования шестиугольника
def draw_hexagon(center, side_length, color):
    # Для RegularPolygon из matplotlib радиус - это расстояние от центра до вершины
    # Для шестиугольника с длиной стороны a: радиус = a
    hex_radius = side_length
    
    # Создаем и добавляем шестиугольник (повернутый на 90 градусов)
    hexagon = RegularPolygon(center, 6, radius=hex_radius, orientation=np.pi/2, 
                            fill=False, color=color, linewidth=1)
    ax.add_patch(hexagon)

# Счетчики для подсчета шестиугольников
count_even = 0
count_odd = 0

# Рисуем шестиугольники для четных центров
for center in centers_even:
    if hexagon_intersects_circle(center, side_length):
        draw_hexagon(center, side_length, 'red')
        count_even += 1

# Рисуем шестиугольники для нечетных центров
for center in centers_odd:
    if hexagon_intersects_circle(center, side_length):
        draw_hexagon(center, side_length, 'green')
        count_odd += 1

# Общее количество шестиугольников
total_count = count_even + count_odd

# Выводим информацию о количестве
print(f"Количество шестиугольников с четными индексами: {count_even}")
print(f"Количество шестиугольников с нечетными индексами: {count_odd}")
print(f"Всего шестиугольников в круге: {total_count}")

# Настройки графика
ax.axhline(0, color='black', linewidth=0.5)
ax.axvline(0, color='black', linewidth=0.5)
ax.grid(True, linestyle='--', alpha=0.5)
ax.set_xlabel('X (мм)')
ax.set_ylabel('Y (мм)')
ax.set_title('Шестиугольная сетка ячеек для линзы Люнебурга диаметром 108 мм')

# Устанавливаем одинаковый масштаб по осям
plt.xlim(-60, 60)
plt.ylim(-60, 60)

# Показать график
plt.show()