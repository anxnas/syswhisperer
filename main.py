import platform
import psutil
import argparse
from typing import Dict, List, Optional
import subprocess
import re

VERSION = "1.0.0"


class GPUInfo:
    """
    Класс для получения информации о видеокартах в системе.
    Поддерживает работу с NVIDIA, AMD и Intel на Windows и Linux.
    """

    def __init__(self):
        """Инициализация класса с определением операционной системы."""
        self.system = platform.system()
        # Словарь для перевода ключей при выводе
        self.key_translations = {
            'name': 'Название',
            'memory_total': 'Видеопамять',
            'driver_version': 'Версия драйвера',
            'video_processor': 'Видеопроцессор',
            'video_memory_type': 'Тип видеопамяти',
            'current_resolution': 'Текущее разрешение',
            'memory_used': 'Используется памяти',
            'temperature': 'Температура'
        }

    def get_windows_gpu_info(self) -> List[Dict[str, str]]:
        """
        Получает информацию о GPU в системах Windows через WMI.

        Returns:
            List[Dict[str, str]]: Список словарей с информацией о каждом GPU
        """
        try:
            import wmi
            computer = wmi.WMI()
            gpu_info = []

            for gpu in computer.Win32_VideoController():
                # Обработка отрицательного значения памяти
                memory = gpu.AdapterRAM
                if memory:
                    memory = abs(memory)  # Преобразуем отрицательное значение в положительное
                    memory_mb = memory / (1024 ** 2)
                    memory_str = f"{memory_mb:.0f} МБ"
                else:
                    memory_str = "Н/Д"

                gpu_data = {
                    'name': gpu.Name,
                    'memory_total': memory_str,
                    'driver_version': gpu.DriverVersion,
                    'video_processor': gpu.VideoProcessor,
                    'video_memory_type': gpu.VideoMemoryType,
                    'current_resolution': f"{gpu.CurrentHorizontalResolution}x{gpu.CurrentVerticalResolution}" if gpu.CurrentHorizontalResolution else "Н/Д"
                }
                gpu_info.append(gpu_data)
            return gpu_info
        except ImportError:
            print("Не найден модуль WMI.")
            return []
        except Exception as e:
            print(f"Ошибка при получении информации о GPU в Windows: {e}")
            return []

    def get_linux_gpu_info(self) -> List[Dict[str, str]]:
        """
        Получает информацию о GPU в системах Linux.
        Поддерживает NVIDIA через nvidia-smi и AMD через системные файлы.

        Returns:
            List[Dict[str, str]]: Список словарей с информацией о каждом GPU
        """
        try:
            gpu_info = []

            # NVIDIA
            try:
                nvidia_info = subprocess.check_output(
                    ['nvidia-smi', '--query-gpu=name,memory.total,memory.used,temperature.gpu',
                     '--format=csv,noheader']).decode()
                for line in nvidia_info.strip().split('\n'):
                    name, total, used, temp = line.split(',')
                    gpu_data = {
                        'name': name.strip(),
                        'memory_total': total.strip(),
                        'memory_used': used.strip(),
                        'temperature': f"{temp.strip()}°C"
                    }
                    gpu_info.append(gpu_data)
            except:
                pass

            # AMD
            try:
                with open('/sys/class/drm/card0/device/vendor', 'r') as f:
                    vendor_id = f.read().strip()
                if vendor_id == '0x1002':
                    with open('/sys/kernel/debug/dri/0/amdgpu_pm_info', 'r') as f:
                        amd_info = f.read()
                    gpu_data = {
                        'name': 'AMD GPU',
                        'temperature': re.search(r'GPU Temperature: (\d+)', amd_info).group(1) + '°C' if re.search(
                            r'GPU Temperature: (\d+)', amd_info) else 'Н/Д'
                    }
                    gpu_info.append(gpu_data)
            except:
                pass

            if not gpu_info:
                lspci_output = subprocess.check_output(['lspci', '-v']).decode()
                vga_devices = re.findall(r'VGA compatible controller: (.*)', lspci_output)
                for device in vga_devices:
                    gpu_info.append({'name': device.strip()})

            return gpu_info
        except Exception as e:
            print(f"Ошибка при получении информации о GPU в Linux: {e}")
            return []

    def translate_keys(self, gpu_info: Dict[str, str]) -> Dict[str, str]:
        """
        Переводит ключи словаря для вывода на экран.

        Args:
            gpu_info (Dict[str, str]): Словарь с информацией о GPU

        Returns:
            Dict[str, str]: Словарь с переведенными ключами
        """
        return {self.key_translations.get(k, k): v for k, v in gpu_info.items()}

    def get_gpu_info(self, for_display: bool = False) -> List[Dict[str, str]]:
        """
        Получает информацию о GPU в зависимости от операционной системы.

        Args:
            for_display (bool): Если True, возвращает данные с русскими ключами для вывода

        Returns:
            List[Dict[str, str]]: Список словарей с информацией о каждом GPU
        """
        if self.system == 'Windows':
            gpu_info = self.get_windows_gpu_info()
        elif self.system == 'Linux':
            gpu_info = self.get_linux_gpu_info()
        else:
            gpu_info = []

        if for_display:
            return [self.translate_keys(gpu) for gpu in gpu_info]
        return gpu_info


def get_system_info(show_cpu: bool = True,
                    show_memory: bool = True,
                    show_gpu: bool = True,
                    export_file: Optional[str] = None) -> Dict:
    """
    Собирает информацию о системе в соответствии с указанными параметрами.

    Args:
        show_cpu (bool): Показывать информацию о процессоре
        show_memory (bool): Показывать информацию о памяти
        show_gpu (bool): Показывать информацию о видеокарте
        export_file (Optional[str]): Путь к файлу для экспорта данных

    Returns:
        Dict: Словарь с информацией о системе
    """

    system_info = {
        'system': f"{platform.system()} {platform.release()}"
    }

    # Вывод информации
    print(f"Система: {system_info['system']}")

    if show_cpu:
        cpu_cores = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        cpu_usage = psutil.cpu_percent(interval=1)
        system_info['cpu'] = {
            'cores': cpu_cores,
            'frequency': f"{cpu_freq.current:.2f} МГц",
            'usage': f"{cpu_usage}%"
        }

    if show_memory:
        memory = psutil.virtual_memory()
        system_info['memory'] = {
            'total': f"{memory.total // (1024 ** 3)} ГБ",
            'used': f"{memory.used // (1024 ** 3)} ГБ",
            'percent': f"{memory.percent}%"
        }

    if show_gpu:
        gpu_handler = GPUInfo()
        # Для JSON используем английские ключи
        system_info['gpu'] = gpu_handler.get_gpu_info(for_display=False)

        # Для вывода на экран используем русские ключи
        display_gpu_info = gpu_handler.get_gpu_info(for_display=True)

        print("\nВидеокарта(ы):")
        if display_gpu_info:
            for idx, gpu in enumerate(display_gpu_info, 1):
                print(f"\nGPU {idx}:")
                for key, value in gpu.items():
                    if value and value != "Н/Д":
                        print(f"- {key}: {value}")
        else:
            print("- Информация о GPU недоступна")

    if show_cpu and 'cpu' in system_info:
        print(f"\nПроцессор:")
        print(f"- Количество ядер: {system_info['cpu']['cores']}")
        print(f"- Текущая частота: {system_info['cpu']['frequency']}")
        print(f"- Загрузка CPU: {system_info['cpu']['usage']}")

    if show_memory and 'memory' in system_info:
        print(f"\nОперативная память:")
        print(f"- Всего: {system_info['memory']['total']}")
        print(f"- Используется: {system_info['memory']['used']}")
        print(f"- Загрузка памяти: {system_info['memory']['percent']}")

    # Экспорт в файл если указан
    if export_file:
        import json
        with open(export_file, 'w', encoding='utf-8') as f:
            json.dump(system_info, f, ensure_ascii=False, indent=4)
            print(f"\nДанные экспортированы в файл: {export_file}")

    return system_info


def main():
    """Основная функция для обработки аргументов командной строки."""
    parser = argparse.ArgumentParser(
        description='Утилита для получения информации о системе',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s --no-cpu --no-memory  # Показать только информацию о GPU
  %(prog)s --export result.json  # Экспортировать все данные в JSON файл
  %(prog)s --version            # Показать версию программы
        """
    )

    parser.add_argument('--version', action='version',
                        version=f'%(prog)s {VERSION}',
                        help='Показать версию программы')
    parser.add_argument('--no-cpu', action='store_false', dest='show_cpu',
                        help='Не показывать информацию о процессоре')
    parser.add_argument('--no-memory', action='store_false', dest='show_memory',
                        help='Не показывать информацию о памяти')
    parser.add_argument('--no-gpu', action='store_false', dest='show_gpu',
                        help='Не показывать информацию о видеокарте')
    parser.add_argument('--export', type=str, metavar='FILE',
                        help='Экспортировать данные в JSON файл')

    args = parser.parse_args()

    get_system_info(
        show_cpu=args.show_cpu,
        show_memory=args.show_memory,
        show_gpu=args.show_gpu,
        export_file=args.export
    )


if __name__ == "__main__":
    main()