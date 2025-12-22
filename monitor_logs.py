"""
Скрипт для мониторинга логов бота с цветным выводом
Показывает только ERROR и WARNING логи
"""
import subprocess
import sys
import re
from pathlib import Path

# ANSI цветовые коды
class Colors:
    RED = '\033[91m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'


def colorize_log_level(line: str) -> str:
    """Раскрасить строку лога в зависимости от уровня"""
    if "ERROR" in line:
        return f"{Colors.RED}{Colors.BOLD}{line}{Colors.RESET}"
    elif "WARNING" in line:
        return f"{Colors.YELLOW}{line}{Colors.RESET}"
    elif "INFO" in line:
        return f"{Colors.GREEN}{line}{Colors.RESET}"
    elif "DEBUG" in line:
        return f"{Colors.DIM}{line}{Colors.RESET}"
    else:
        return line


def extract_error_info(line: str) -> dict:
    """Извлечь информацию об ошибке"""
    info = {
        'timestamp': None,
        'module': None,
        'level': None,
        'message': None
    }
    
    # Формат: 2025-12-22 13:30:29,590 - aiogram.dispatcher - ERROR - Message
    pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+) - ([\w.]+) - (\w+) - (.+)'
    match = re.match(pattern, line)
    
    if match:
        info['timestamp'] = match.group(1)
        info['module'] = match.group(2)
        info['level'] = match.group(3)
        info['message'] = match.group(4)
    
    return info


def print_header():
    """Напечатать заголовок"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*80}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'🔍 МОНИТОРИНГ ЛОГОВ БОТА':^80}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'='*80}{Colors.RESET}\n")
    print(f"{Colors.WHITE}Отображаются только {Colors.RED}ERROR{Colors.WHITE} и {Colors.YELLOW}WARNING{Colors.WHITE} логи{Colors.RESET}")
    print(f"{Colors.DIM}Нажмите Ctrl+C для остановки{Colors.RESET}\n")


def print_error_summary(error_count: int, warning_count: int):
    """Напечатать итоговую статистику"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*80}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'📊 СТАТИСТИКА':^80}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'='*80}{Colors.RESET}\n")
    print(f"{Colors.RED}❌ Ошибок (ERROR): {error_count}{Colors.RESET}")
    print(f"{Colors.YELLOW}⚠️  Предупреждений (WARNING): {warning_count}{Colors.RESET}")
    print()


def monitor_logs():
    """Запустить бота и мониторить логи"""
    print_header()
    
    error_count = 0
    warning_count = 0
    last_errors = []
    
    # Путь к проекту
    project_dir = Path(__file__).parent
    
    # Команда запуска бота
    cmd = [
        "python", "-m", "bot.main"
    ]
    
    try:
        # Запускаем бот
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=project_dir
        )
        
        print(f"{Colors.GREEN}✅ Бот запущен (PID: {process.pid}){Colors.RESET}\n")
        print(f"{Colors.DIM}{'─'*80}{Colors.RESET}\n")
        
        # Читаем логи построчно
        for line in process.stdout:
            line = line.strip()
            
            if not line:
                continue
            
            # Фильтруем только ERROR и WARNING
            if "ERROR" in line or "WARNING" in line:
                colored_line = colorize_log_level(line)
                print(colored_line)
                
                # Подсчитываем ошибки
                if "ERROR" in line:
                    error_count += 1
                    info = extract_error_info(line)
                    if info['message']:
                        last_errors.append(info)
                        # Храним только последние 10 ошибок
                        if len(last_errors) > 10:
                            last_errors.pop(0)
                
                elif "WARNING" in line:
                    warning_count += 1
                
                # Добавляем пустую строку после каждого лога для читаемости
                print()
        
        process.wait()
        
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}⚠️  Остановка бота...{Colors.RESET}")
        if process:
            process.terminate()
            process.wait(timeout=5)
        print(f"{Colors.GREEN}✅ Бот остановлен{Colors.RESET}")
    
    except Exception as e:
        print(f"\n{Colors.RED}❌ Ошибка запуска: {e}{Colors.RESET}")
        return 1
    
    finally:
        # Печатаем статистику
        print_error_summary(error_count, warning_count)
        
        # Показываем последние ошибки
        if last_errors:
            print(f"{Colors.CYAN}{Colors.BOLD}{'='*80}{Colors.RESET}")
            print(f"{Colors.CYAN}{Colors.BOLD}{'🔥 ПОСЛЕДНИЕ ОШИБКИ':^80}{Colors.RESET}")
            print(f"{Colors.CYAN}{Colors.BOLD}{'='*80}{Colors.RESET}\n")
            
            for i, error in enumerate(last_errors[-5:], 1):  # Показываем последние 5
                print(f"{Colors.RED}{Colors.BOLD}[{i}] {error['timestamp']}{Colors.RESET}")
                print(f"    {Colors.DIM}Модуль:{Colors.RESET} {error['module']}")
                print(f"    {Colors.DIM}Сообщение:{Colors.RESET} {error['message']}\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(monitor_logs())
