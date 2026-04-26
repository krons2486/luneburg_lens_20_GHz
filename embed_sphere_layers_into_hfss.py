import json
import math
from pathlib import Path

"""
Скрипт для однократного запуска ВНЕ HFSS.

Назначение:
- Прочитать все 19 JSON-файлов из каталога `layers_sphere/layer_XX.json`
- Отфильтровать ячейки только для одного квадранта (x >= 0 и y >= 0) 
  для использования осевой симметрии (2 оси симметрии)
- Отфильтровать только ячейки, которые пересекаются со сферой без оболочки
  (радиус = 54 / 1.034)
- Упаковать данные в компактный JSON (список слоёв с массивами [x, y, r])
- Вставить этот JSON во встроенную строку EMBEDDED_LAYERS_JSON в `hfss_import_spheres.py`

После запуска:
- `hfss_import_spheres.py` будет содержать все данные слоёв внутри себя
- HFSS больше не будет читать внешние JSON-файлы
- Будут созданы цилиндры только для одного квадранта линзы, пересекающиеся со сферой
"""


PROJECT_ROOT = Path(__file__).resolve().parent
LAYERS_DIR = PROJECT_ROOT / "layers_sphere"
HFSS_SCRIPT_PATH = PROJECT_ROOT / "hfss_import_spheres.py"

BEGIN_MARKER = "# BEGIN_EMBEDDED_LAYERS"
END_MARKER = "# END_EMBEDDED_LAYERS"

# Параметры линзы
LENS_RADIUS_MM = 54.0  # Радиус линзы с оболочкой
n_оболочки = 1.034
CORE_RADIUS_MM = LENS_RADIUS_MM / n_оболочки  # Радиус линзы без оболочки

# Параметры сетки
LAYER_HEIGHT_MM = 3.0  # Высота каждого слоя
SIDE_LENGTH_MM = math.sqrt(3.0)  # сторона шестиугольника
HEX_RADIUS = SIDE_LENGTH_MM  # Радиус шестиугольника (расстояние от центра до вершины)


def cell_intersects_core_sphere(x, y, z, hex_radius, core_radius):
    """
    Проверяет, пересекается ли ячейка со сферой без оболочки.
    
    Параметры:
    ----------
    x, y, z : float
        Координаты центра ячейки
    hex_radius : float
        Радиус шестиугольника (расстояние от центра до вершины)
    core_radius : float
        Радиус сферы без оболочки
    
    Возвращает:
    -----------
    bool
        True если ячейка пересекается со сферой
    """
    # 3D радиус от центра линзы до центра ячейки
    r_3d = math.sqrt(x**2 + y**2 + z**2)
    
    # Минимальное расстояние от центра линзы до ячейки
    # (расстояние до ближайшей точки ячейки)
    min_distance = max(0.0, r_3d - hex_radius)
    
    # Ячейка пересекается со сферой, если минимальное расстояние <= радиус сферы
    return min_distance <= core_radius


def load_layers():
    """Считать все слои из JSON-файлов в каталоге `layers_sphere` и отфильтровать только квадрант и пересекающиеся со сферой."""
    layers_data = []

    for layer_idx in range(1, 19):  # 18 слоёв для сферической линзы
        filename = LAYERS_DIR / f"layer_{layer_idx:02d}.json"
        if not filename.exists():
            raise FileNotFoundError(f"Не найден файл слоя: {filename}")

        with filename.open("r", encoding="utf-8") as f:
            data = json.load(f)

        layer_num = int(data.get("layer", layer_idx))
        cells_raw = data.get("cells", [])
        if not cells_raw:
            raise RuntimeError(f"В файле {filename} нет массива 'cells'")

        # Высота слоя
        z_mm = (layer_num - 1) * LAYER_HEIGHT_MM

        # Фильтруем ячейки:
        # 1. Только для квадранта (x >= 0 и y >= 0) - осевая симметрия
        # 2. Только пересекающиеся со сферой без оболочки
        cells_filtered = []
        for c in cells_raw:
            x = float(c["x"])
            y = float(c["y"])
            
            # Проверка квадранта
            if x < 0.0 or y < 0.0:
                continue
            
            # Проверка пересечения со сферой без оболочки
            if cell_intersects_core_sphere(x, y, z_mm, HEX_RADIUS, CORE_RADIUS_MM):
                cells_filtered.append(c)

        # Преобразуем к компактному виду: [x, y, r]
        # где x, y - координаты центра в плоскости слоя, r - радиус отверстия
        # z не нужен, т.к. цилиндры размещаются по номеру слоя
        cells_compact = [
            [
                float(c["x"]),
                float(c["y"]),
                float(c["r"])
            ]
            for c in cells_filtered
        ]

        layers_data.append({"layer": layer_num, "cells": cells_compact})
        print(f"Слой {layer_num}: {len(cells_raw)} ячеек всего, {len(cells_compact)} в квадранте и пересекаются со сферой (R={CORE_RADIUS_MM:.3f} мм)")

    # Один объект со всеми слоями
    packed = {"layers": layers_data}

    # Компактный JSON без лишних пробелов/переводов строк
    json_text = json.dumps(packed, separators=(",", ":"))
    return json_text


def update_hfss_script(embedded_json: str):
    """Вставить новый JSON в блок EMBEDDED_LAYERS_JSON внутри hfss_import_spheres.py."""
    if not HFSS_SCRIPT_PATH.exists():
        raise FileNotFoundError(f"Не найден скрипт HFSS: {HFSS_SCRIPT_PATH}")

    original_text = HFSS_SCRIPT_PATH.read_text(encoding="utf-8")

    begin_idx = original_text.find(BEGIN_MARKER)
    end_idx = original_text.find(END_MARKER)

    if begin_idx == -1 or end_idx == -1:
        raise RuntimeError(
            f"Не найдены маркеры {BEGIN_MARKER!r} / {END_MARKER!r} в файле {HFSS_SCRIPT_PATH}"
        )

    # Найдём границы строки EMBEDDED_LAYERS_JSON между маркерами
    before_block, _, rest = original_text.partition(BEGIN_MARKER)
    _, _, after_block = rest.partition(END_MARKER)

    # Собираем новый блок с маркерами и встроенным JSON
    embedded_block = (
        f"{BEGIN_MARKER}\n"
        f'EMBEDDED_LAYERS_JSON = r"""{embedded_json}"""\n'
        f"{END_MARKER}"
    )

    new_text = before_block + embedded_block + after_block

    HFSS_SCRIPT_PATH.write_text(new_text, encoding="utf-8")


def main():
    print("Чтение слоёв из каталога 'layers_sphere'...")
    print(f"Фильтрация: квадрант (x >= 0, y >= 0) и пересечение со сферой (R = {CORE_RADIUS_MM:.3f} мм)")
    embedded_json = load_layers()
    print("Всего символов в упакованных данных:", len(embedded_json))

    print(f"Обновление файла {HFSS_SCRIPT_PATH}...")
    update_hfss_script(embedded_json)

    print("Готово. Теперь запустите `hfss_import_spheres.py` внутри HFSS.")
    print("Будут созданы цилиндры только для одного квадранта линзы, пересекающиеся со сферой без оболочки.")


if __name__ == "__main__":
    main()
