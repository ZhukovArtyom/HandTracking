import subprocess
import json



def get_full_start_menu_with_paths():
    """Получает ВСЕ элементы меню Пуск с правильной кодировкой и командами для запуска"""

    ps_command = '''
    # Самый надежный способ собрать все элементы Пуска
    $allApps = @()
    $allPaths = @()

    # 1. Классические ярлыки
    $paths = @(
        "$env:APPDATA\\Microsoft\\Windows\\Start Menu\\Programs",
        "$env:PROGRAMDATA\\Microsoft\\Windows\\Start Menu\\Programs"
    )

    foreach ($path in $paths) {
        if (Test-Path $path) {
            Get-ChildItem -Path $path -Recurse -Filter *.lnk -ErrorAction SilentlyContinue | 
            ForEach-Object { 
                $allApps += $_.BaseName
                $allPaths += $_.FullName
            }
        }
    }

    # 2. UWP приложения (современные) с поиском команды для запуска
    try {
        $uwpApps = Get-StartApps -ErrorAction SilentlyContinue
        foreach ($app in $uwpApps) {
            # Формируем команду для запуска UWP приложения
            
            $appCommand = "$($app.AppId):"

            $allApps += $app.Name
            $allPaths += $appCommand
        }
    } catch { }

    # 3. Убираем дубликаты и сортируем
    $appMap = @{}
    for ($i=0; $i -lt $allApps.Count; $i++) {
        $name = $allApps[$i]
        $path = $allPaths[$i]
        if (-not $appMap.ContainsKey($name)) {
            $appMap[$name] = $path
        }
    }

    # Выводим в формате "имя|путь"
    $appMap.GetEnumerator() | ForEach-Object { 
        Write-Output "$($_.Key)|$($_.Value)"
    } | Sort-Object
    '''

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_command],
            capture_output=True,
            text=False,
            encoding=None
        )

        try:
            output = result.stdout.decode('cp866', errors='ignore')
        except:
            try:
                output = result.stdout.decode('utf-8', errors='ignore')
            except:
                output = result.stdout.decode('cp1251', errors='ignore')

        if result.returncode == 0 and output:
            programs_with_paths = []
            for line in output.strip().split('\r\n'):
                if line.strip() and '|' in line:
                    name, path = line.split('|', 1)
                    if len(name) > 1 and not name.isdigit():
                        programs_with_paths.append({
                            "name": name,
                            "path": path
                        })
            return programs_with_paths

    except Exception as e:
        print(f"Ошибка: {e}")

    return []


def main():
    print("🔍 Получение списка программ из меню Пуск...")
    print("   (с командами для запуска, включая UWP приложения)\n")

    programs_data = get_full_start_menu_with_paths()

    if programs_data:
        # Сохраняем результат
        output = programs_data

        with open("config/installed_programs.json", "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"✅ Сохранено в 'start_menu_programs_with_real_paths.json'")

    else:
        print("❌ Не удалось получить список программ")


if __name__ == "__main__":
    main()