import json
import time
import base64
import requests
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from PIL import Image
from io import BytesIO
import pyautogui
import random
from datetime import datetime
from task_manager import TaskManager


class TopWarBot:
    def __init__(self):
        self.base_dir = "C:/python/topwar"
        self.config_path = os.path.join(self.base_dir, "config.json")
        self.screenshot_dir = os.path.join(self.base_dir, "screenshots")
        os.makedirs(self.screenshot_dir, exist_ok=True)

        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        self.driver = None
        self.task_manager = TaskManager()

    def start_browser(self):
        print("🦊 Запускаю Firefox с профилем Top War...")
        
        options = Options()
        profile_path = r"C:\Users\Admin\AppData\Roaming\Mozilla\Firefox\Profiles\6egxe08i.topwar"
        
        options.add_argument("-profile")
        options.add_argument(profile_path)
        
        options.set_preference("extensions.autoDisableScopes", 0)
        options.set_preference("extensions.enabledScopes", 15)
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("useAutomationExtension", False)
        options.set_preference("webgl.disabled", False)
        options.set_preference("layers.acceleration.force-enabled", True)
        options.set_preference("browser.tabs.remote.autostart", False)
        
        options.add_argument(f"--width={self.config['browser_width']}")
        options.add_argument(f"--height={self.config['browser_height']}")
        
        print(f"📂 Профиль: {profile_path}")
        print(f"📐 Размер окна: {self.config['browser_width']}x{self.config['browser_height']}")
        
        self.driver = webdriver.Firefox(options=options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print(f"🌐 Открываю {self.config['game_url']}")
        self.driver.get(self.config['game_url'])
        
        print("✅ Браузер запущен. Ожидаю загрузки игры...")
        
        self.wait_for_game_load()
        self.close_popup_ads()
        self.ensure_base_mode()

    def wait_for_game_load(self, max_attempts=4):
        print("\n⏳ Проверка загрузки игры...")
        
        for attempt in range(1, max_attempts + 1):
            print(f"   Попытка {attempt}/{max_attempts}...")
            time.sleep(15)
            
            screenshot, path = self.save_screenshot("load_check_")
            print(f"   💾 Скриншот: {path}")
            
            prompt = """
На скриншоте игра Top War. Определи, загрузилась ли игра полностью:

ЗАГРУЖЕНА если видно:
- Аватар игрока в левом верхнем углу
- Ресурсы (золото, энергия, кристаллы)
- Здания на карте или интерфейс базы/мира
- Кнопки меню (Построить, Мир, База и т.д.)

НЕ ЗАГРУЖЕНА если:
- Черный/белый экран
- Экран загрузки с прогресс-баром
- Пустой экран без UI элементов

Верни JSON:
{"loaded": true/false, "description": "что видно на экране"}
"""
            result = self.query_ai(screenshot, prompt)
            loaded = result.get('loaded', False)
            description = result.get('description', 'неизвестно')
            
            print(f"   🤖 ИИ: {description}")
            
            if loaded:
                print("✅ Игра загрузилась!")
                return True
            else:
                print(f"   ⏳ Игра еще не загрузилась. Жду еще 15 сек...")
        
        print("❌ Игра не загрузилась после максимального числа попыток")
        self.task_manager.log("Игра не загрузилась после 4 попыток")
        return False

    def close_popup_ads(self):
        print("\n🔍 Проверка на рекламные окна...")
        screenshot, path = self.save_screenshot("popup_check_")
        
        prompt = """
На скриншоте игра Top War. Есть ли на экране рекламное окно, модальное окно или всплывающее предложение, которое закрывает игру?

Признаки:
- Большое окно по центру экрана с предложением купить набор
- Крестик (X) в правом верхнем углу окна
- Кнопка "Закрыть" или "Позже"

Верни JSON:
{"has_popup": true/false, "close_button": {"x": int, "y": int}} или {"has_popup": false}
"""
        result = self.query_ai(screenshot, prompt)
        
        if result.get('has_popup'):
            close_btn = result.get('close_button')
            if close_btn:
                print(f"   🚫 Найдено рекламное окно. Закрываю...")
                self.click_coords(close_btn['x'], close_btn['y'], "Закрытие рекламы", variance=10)
                time.sleep(2)
                self.task_manager.log("Закрыто рекламное окно")
            else:
                print("   ⚠️ Рекламное окно есть, но крестик не найден")
        else:
            print("   ✅ Рекламных окон нет")

    def ensure_base_mode(self):
        print("\n🏠 Проверка режима игры...")
        screenshot, path = self.save_screenshot("mode_check_")
        
        prompt = """
На скриншоте игра Top War. Определи текущий режим:

БАЗА если видно:
- Остров с зданиями игрока по центру
- Кнопка "Мир" внизу справа
- Мало других игроков на экране

МИР если видно:
- Много баз других игроков
- Карта с множеством зданий
- Кнопка "База" внизу справа

Верни JSON:
{"mode": "BASE" или "WORLD"}
"""
        result = self.query_ai(screenshot, prompt)
        mode = result.get('mode', 'UNKNOWN')
        
        print(f"   🤖 Текущий режим: {mode}")
        
        if mode == "WORLD":
            print("   🔄 Переключаюсь на режим БАЗА...")
            self.switch_to_base(screenshot)
        elif mode == "BASE":
            print("   ✅ Уже в режиме БАЗА")
        else:
            print("   ⚠️ Не удалось определить режим")

    def switch_to_base(self, screenshot_bytes):
        prompt = """
На скриншоте игра Top War в режиме МИР.
Найди кнопку "БАЗА" или "Base" внизу экрана (обычно справа).

Верни JSON:
{"base_button": {"x": int, "y": int}} или {"base_button": null}
"""
        result = self.query_ai(screenshot_bytes, prompt)
        btn = result.get('base_button')
        
        if btn:
            self.click_coords(btn['x'], btn['y'], "Переключение на БАЗУ", variance=8)
            time.sleep(3)
            print("   ✅ Переключено на БАЗУ")
            self.task_manager.log("Переключено на режим БАЗА")
        else:
            print("   ❌ Кнопка БАЗА не найдена")
            self.task_manager.log("Не удалось переключиться на БАЗУ")

    def click_coords(self, x, y, description="", variance=None):
        if variance is None:
            variance = self.config['click_variance']

        canvas = self.driver.find_element(By.TAG_NAME, "canvas")
        rect = canvas.rect

        click_x = rect['x'] + x + random.randint(-variance, variance)
        click_y = rect['y'] + y + random.randint(-variance, variance)

        print(f"🖱️ {description}: ({click_x}, {click_y})")
        pyautogui.moveTo(click_x, click_y, duration=random.uniform(0.3, 0.6))
        time.sleep(random.uniform(0.1, 0.3))
        pyautogui.click()
        time.sleep(1.5)

    def take_screenshot(self):
        canvas = self.driver.find_element(By.TAG_NAME, "canvas")
        return canvas.screenshot_as_png

    def save_screenshot(self, prefix=""):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}{timestamp}.png"
        path = os.path.join(self.screenshot_dir, filename)
        screenshot = self.take_screenshot()
        with open(path, 'wb') as f:
            f.write(screenshot)
        return screenshot, path

    def query_ai(self, screenshot_bytes, prompt):
        img = Image.open(BytesIO(screenshot_bytes))
        img_resized = img.resize(
            (self.config['ai_width'], self.config['ai_height']),
            Image.Resampling.LANCZOS
        )

        buffered = BytesIO()
        img_resized.save(buffered, format="PNG")
        img_b64 = base64.b64encode(buffered.getvalue()).decode()

        payload = {
            "model": self.config['model'],
            "prompt": prompt,
            "images": [img_b64],
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1, "num_predict": 400}
        }

        resp = requests.post(
            self.config['ollama_url'], json=payload, timeout=60
        )
        resp.raise_for_status()
        result_text = resp.json().get('response', '{}')
        result_text = result_text.replace("```json", "").replace("```", "").strip()
        return json.loads(result_text)

    # === UI КНОПКИ ===

    def open_shop_menu(self):
        print("\n🛒 Открытие меню наборов...")
        self.click_coords(1850, 320, "Кнопка Наборы", variance=10)
        time.sleep(2)

    def close_shop_menu(self):
        print("\n🚪 Выход из меню наборов...")
        screenshot, _ = self.save_screenshot("exit_")

        prompt = """
На скриншоте меню "Наборы" игры Top War.
Найди СТРЕЛКУ НАЗАД (<) в левом верхнем углу для выхода.
Верни JSON: {"exit_button": {"x": int, "y": int}} или {"exit_button": null}
"""
        result = self.query_ai(screenshot, prompt)
        btn = result.get('exit_button')

        if btn:
            self.click_coords(btn['x'], btn['y'], "Стрелка выхода")
        else:
            print("⚠️ Стрелка не найдена, использую запасную координату")
            self.click_coords(620, 180, "Запасной выход")
        time.sleep(1.5)

    def close_reward_menu(self):
        print("\n❌ Закрытие меню наград...")
        screenshot, _ = self.save_screenshot("close_")

        prompt = """
На скриншоте меню "Рекламные привилегии" игры Top War.
Найди КРЕСТИК (X) для закрытия в правом верхнем углу.
Верни JSON: {"close_button": {"x": int, "y": int}} или {"close_button": null}
"""
        result = self.query_ai(screenshot, prompt)
        btn = result.get('close_button')

        if btn:
            self.click_coords(btn['x'], btn['y'], "Крестик закрытия")
        else:
            print("⚠️ Крестик не найден, использую запасную координату")
            self.click_coords(1100, 200, "Запасной крестик")
        time.sleep(1.5)

    # === ПОИСК ВКЛАДКИ ===

    def find_target_tab(self, screenshot_bytes):
        prompt = """
На скриншоте открыто меню "Наборы" игры Top War.
В верхней части окна есть горизонтальный ряд вкладок.

ЗАДАЧА: Найди вкладку с иконкой красного сундука/подарка или текстом "Высшая привилегия".
Игнорируй вкладки "30%", "Снабжение", "Ежедневные".

Верни JSON:
{"tab_found": true/false, "coords": {"x": int, "y": int}}
"""
        return self.query_ai(screenshot_bytes, prompt)

    def swipe_tabs_left(self):
        canvas = self.driver.find_element(By.TAG_NAME, "canvas")
        rect = canvas.rect

        start_x = rect['x'] + 1150
        end_x = rect['x'] + 750
        y_pos = rect['y'] + 200

        print("   🖱️ Протягиваю вкладки влево...")
        pyautogui.moveTo(start_x, y_pos, duration=0.1)
        pyautogui.mouseDown()
        time.sleep(0.1)
        pyautogui.moveTo(end_x, y_pos, duration=0.6)
        time.sleep(0.1)
        pyautogui.mouseUp()
        time.sleep(1.5)

    def find_and_open_target_tab(self):
        print("\n🔍 Поиск вкладки 'Высшая привилегия'...")
        max_swipes = 4

        for attempt in range(max_swipes):
            screenshot, _ = self.save_screenshot(f"tab_search_{attempt}_")
            result = self.find_target_tab(screenshot)

            if result.get('tab_found') and result.get('coords'):
                x, y = result['coords']['x'], result['coords']['y']

                if 150 < y < 280:
                    print(f"✅ Вкладка найдена на ({x}, {y}). Кликаю...")
                    self.click_coords(x, y, "Переключение вкладки", variance=5)
                    time.sleep(2)
                    return True
                else:
                    print(f"⚠️ Координаты ({x}, {y}) вне зоны вкладок. Игнорирую.")

            if attempt < max_swipes - 1:
                self.swipe_tabs_left()
            else:
                print("❌ Вкладка не найдена после максимального числа пролистываний.")

        return False

    # === ПОИСК СУНДУКА ===

    def find_red_chest(self, screenshot_bytes):
        prompt = """
На скриншоте меню игры Top War.
Найди КРАСНЫЙ СУНДУК с подарком (обычно в правой части).
Это кнопка "Рекламные привилегии" или "Совершенство".

Верни JSON:
{"chest": {"x": int, "y": int}} или {"chest": null}
"""
        return self.query_ai(screenshot_bytes, prompt)

    # === СБОР АЛМАЗОВ ===

    def check_diamond_button(self, screenshot_bytes):
        prompt = """
Найди кнопку "Беспл." в меню "Рекламные привилегии".
Определи её состояние:
1. ACTIVE: Кнопка СИНЯЯ, есть красное число (количество нажатий).
2. INACTIVE: Кнопка СЕРАЯ (с таймером обратного отсчета или без него).

Верни JSON:
{"state": "ACTIVE" или "INACTIVE", "coords": {"x": int, "y": int}, "clicks": int}
"""
        return self.query_ai(screenshot_bytes, prompt)

    def claim_diamonds(self):
        print("\n💎 Проверка кнопки 'Беспл.'...")
        screenshot, path = self.save_screenshot("diamond_check_")

        result = self.check_diamond_button(screenshot)
        state = result.get('state', 'UNKNOWN')
        coords = result.get('coords')
        clicks_needed = result.get('clicks', 0)

        if not coords:
            print("❌ Кнопка не найдена на экране.")
            self.task_manager.log("Алмазы: кнопка не найдена")
            return False

        if state == "ACTIVE":
            print(f"✅ Кнопка активна (синяя). Нужно нажатий: {clicks_needed}")

            for i in range(1, clicks_needed + 1):
                print(f"   [{i}/{clicks_needed}] Клик...")
                self.click_coords(
                    coords['x'], coords['y'],
                    f"Алмаз #{i}", variance=5
                )

                if i < clicks_needed:
                    wait_time = 15 + random.uniform(1, 3)
                    print(f"   ⏳ Жду {wait_time:.1f} сек...")
                    time.sleep(wait_time)

            print("✅ Цикл нажатий завершен.")
            self.task_manager.log(f"Алмазы: собрано {clicks_needed} нажатий")
            return True

        elif state == "INACTIVE":
            print("⏳ Кнопка неактивна (серая). Уже собрано или кулдаун.")
            self.task_manager.log("Алмазы: уже собраны или на кулдауне. Пропуск.")
            return False

        else:
            print(f"⚠️ Неизвестное состояние: {state}")
            self.task_manager.log(f"Алмазы: неизвестное состояние {state}")
            return False

    # === VIP ПОДАРОК ===

    def click_vip_indicator(self):
        print("\n👑 Поиск индикатора VIP...")
        screenshot, _ = self.save_screenshot("vip_indicator_")

        prompt = """
На скриншоте игра Top War. В ЛЕВОМ ВЕРХНЕМ УГЛУ под аватаром игрока 
найдется надпись "VIP 5" или "VIP 6" и т.д. (золотая/оранжевая иконка).

Найди эту кнопку VIP статуса.

Верни JSON:
{"vip_button": {"x": int, "y": int}} или {"vip_button": null}
"""
        result = self.query_ai(screenshot, prompt)
        btn = result.get('vip_button')

        if btn:
            print(f"✅ VIP индикатор найден на ({btn['x']}, {btn['y']})")
            self.click_coords(btn['x'], btn['y'], "Открытие VIP меню", variance=8)
            time.sleep(2)
            return True
        else:
            print("❌ VIP индикатор не найден")
            self.task_manager.log("VIP: индикатор не найден на экране")
            return False

    def check_vip_gift_status(self):
        print("\n🔍 Проверка статуса VIP подарка...")
        screenshot, path = self.save_screenshot("vip_status_")
        print(f"💾 Скриншот: {path}")

        prompt = """
На скриншоте открыто VIP меню игры Top War.

ЗАДАЧА: Определи состояние VIP подарка:

1. Если видишь ТАЙМЕР обратного отсчета (красные цифры формата 09:32:44) 
   рядом с сундуком/подарком → состояние "CLAIMED" (уже собран, ждем)
   
2. Если видишь кнопку "ПОЛУЧИТЬ" или "GET" или зеленую кнопку → 
   состояние "AVAILABLE" (можно собрать)
   
3. Если видишь таймер "00:00:00" или очень маленький → 
   состояние "AVAILABLE" (можно собрать)

Верни JSON:
{
  "status": "AVAILABLE" или "CLAIMED",
  "timer_text": "09:32:44" или null,
  "collect_button": {"x": int, "y": int} или null
}
"""
        result = self.query_ai(screenshot, prompt)
        return result

    def collect_vip_gift(self):
        print("\n🎁 Сбор VIP подарка...")
        screenshot, _ = self.save_screenshot("vip_collect_")

        prompt = """
На скриншоте VIP меню. Найди кнопку для получения подарка.
Это может быть кнопка "ПОЛУЧИТЬ", "GET", зеленая кнопка, 
или кнопка рядом с сундуком.

Верни JSON:
{"button": {"x": int, "y": int}} или {"button": null}
"""
        result = self.query_ai(screenshot, prompt)
        btn = result.get('button')

        if btn:
            print(f"✅ Кнопка получения найдена на ({btn['x']}, {btn['y']})")
            self.click_coords(btn['x'], btn['y'], "Получить VIP подарок", variance=8)
            time.sleep(2)
            
            screenshot, _ = self.save_screenshot("vip_reward_")
            prompt_close = """
Если на скриншоте открылось окно с наградой и кнопкой "OK" или крестиком,
найди кнопку закрытия. Если окна нет - верни null.

Верни JSON: {"close_button": {"x": int, "y": int}} или {"close_button": null}
"""
            close_result = self.query_ai(screenshot, prompt_close)
            close_btn = close_result.get('close_button')
            
            if close_btn:
                self.click_coords(close_btn['x'], close_btn['y'], "Закрыть окно награды")
                time.sleep(1)
            
            self.task_manager.log("VIP: подарок успешно собран")
            return True
        else:
            print("❌ Кнопка получения не найдена")
            self.task_manager.log("VIP: кнопка получения не найдена")
            return False

    def close_vip_menu(self):
        print("\n🚪 Закрытие VIP меню...")
        screenshot, _ = self.save_screenshot("vip_close_")

        prompt = """
На скриншоте VIP меню игры Top War.
Найди СТРЕЛКУ НАЗАД (<) в левом верхнем углу для закрытия меню.

Верни JSON: {"back_button": {"x": int, "y": int}} или {"back_button": null}
"""
        result = self.query_ai(screenshot, prompt)
        btn = result.get('back_button')

        if btn:
            self.click_coords(btn['x'], btn['y'], "Стрелка назад (VIP)")
            time.sleep(1.5)
        else:
            print("⚠️ Стрелка не найдена, использую запасную координату")
            self.click_coords(620, 180, "Запасной выход (VIP)")
            time.sleep(1.5)

    def task_vip_gift(self):
        print("\n" + "="*60)
        print("👑 ЗАДАЧА: VIP-подарок")
        print("="*60)

        try:
            if not self.click_vip_indicator():
                return False

            status_info = self.check_vip_gift_status()
            status = status_info.get('status', 'UNKNOWN')
            timer_text = status_info.get('timer_text')

            if status == "CLAIMED":
                print(f"⏳ VIP подарок уже собран. Следующий через: {timer_text or 'неизвестно'}")
                self.task_manager.log(f"VIP: уже собран, следующий через {timer_text or 'неизвестно'}")
                self.close_vip_menu()
                return True

            elif status == "AVAILABLE":
                print("✅ VIP подарок доступен к получению!")
                self.task_manager.log("VIP: подарок доступен, начинаю сбор")
                
                if self.collect_vip_gift():
                    self.close_vip_menu()
                    return True
                else:
                    self.close_vip_menu()
                    return False

            else:
                print(f"⚠️ Неизвестное состояние: {status}")
                self.task_manager.log(f"VIP: неизвестное состояние {status}")
                self.close_vip_menu()
                return False

        except Exception as e:
            print(f"❌ Ошибка: {e}")
            self.task_manager.log(f"VIP: ошибка {e}")
            try:
                self.close_vip_menu()
            except:
                pass
            return False

    # === ГЛАВНАЯ ЗАДАЧА: АЛМАЗЫ ===

    def task_shop_gifts(self):
        print("\n" + "="*60)
        print("💎 ЗАДАЧА: Сбор алмазов (Рекламные привилегии)")
        print("="*60)

        try:
            self.open_shop_menu()

            if not self.find_and_open_target_tab():
                self.close_shop_menu()
                return False

            screenshot, _ = self.save_screenshot("chest_search_")
            chest_result = self.find_red_chest(screenshot)

            if not chest_result.get('chest'):
                print("❌ Красный сундук не найден на этой вкладке.")
                self.task_manager.log("Алмазы: сундук не найден")
                self.close_shop_menu()
                return False

            cx, cy = chest_result['chest']['x'], chest_result['chest']['y']
            self.click_coords(cx, cy, "Открытие сундука привилегий", variance=10)
            time.sleep(2)

            self.claim_diamonds()

            self.close_reward_menu()
            self.close_shop_menu()

            print("\n✅ Задача выполнена")
            return True

        except Exception as e:
            print(f"❌ Ошибка: {e}")
            self.task_manager.log(f"Алмазы: ошибка {e}")
            try:
                self.close_reward_menu()
                self.close_shop_menu()
            except:
                pass
            return False

    # === ЗАГЛУШКИ ДЛЯ ДРУГИХ ЗАДАЧ ===

    def task_regular_events(self):
        print("\n🎪 ЗАДАЧА: Регулярные события (не реализовано)")
        self.task_manager.log("Регулярные события: задача не реализована")
        return False

    def task_valuable_events(self):
        print("\n💎 ЗАДАЧА: Ценные события (не реализовано)")
        self.task_manager.log("Ценные события: задача не реализована")
        return False

    def task_production_collect(self):
        print("\n🏭 ЗАДАЧА: Сбор производства (не реализовано)")
        self.task_manager.log("Сбор производства: задача не реализована")
        return False

    def execute_task(self, task_id):
        task_map = {
            'shop_gifts': self.task_shop_gifts,
            'vip_gift': self.task_vip_gift,
            'regular_events': self.task_regular_events,
            'valuable_events': self.task_valuable_events,
            'production_collect': self.task_production_collect
        }

        if task_id in task_map:
            try:
                result = task_map[task_id]()
                self.task_manager.mark_task_completed(task_id)
                return result
            except Exception as e:
                print(f"❌ Ошибка выполнения задачи {task_id}: {e}")
                self.task_manager.log(f"Ошибка задачи {task_id}: {e}")
                return False
        else:
            print(f"❌ Неизвестная задача: {task_id}")
            return False

    # === ПЛАНИРОВЩИК ===

    def run_scheduler(self):
        print("\n" + "="*70)
        print("🤖 TOP WAR BOT - ПЛАНИРОВЩИК ЗАДАЧ")
        print("="*70)

        self.task_manager.print_status()
        self.start_browser()
        
        print("\n⏳ Жду 10 сек перед началом цикла задач...")
        time.sleep(10)

        try:
            while True:
                ready_tasks = self.task_manager.get_ready_tasks()

                if ready_tasks:
                    print(f"\n🔔 Готовы задачи: {len(ready_tasks)}")
                    for task in ready_tasks:
                        print(f"   - {task['name']}")

                    for task in ready_tasks:
                        print(f"\n▶️ Выполняю: {task['name']}")
                        self.execute_task(task['id'])
                        time.sleep(5)
                else:
                    next_tasks = []
                    for task in self.task_manager.tasks:
                        if task['enabled']:
                            next_run = self.task_manager.calculate_next_run(task)
                            if next_run:
                                next_tasks.append((task['name'], next_run))

                    if next_tasks:
                        next_tasks.sort(key=lambda x: x[1])
                        earliest = next_tasks[0]
                        wait_time = (earliest[1] - datetime.now()).total_seconds()

                        print(f"\n💤 Следующая задача: {earliest[0]}")
                        print(f"   Время: {earliest[1].strftime('%H:%M:%S')}")
                        print(f"   Жду: {wait_time/60:.1f} минут")

                        time.sleep(min(wait_time, 60))
                    else:
                        print("\n✅ Все задачи на сегодня выполнены")
                        print("💤 Жду начала новых суток (2:00)...")
                        time.sleep(3600)

                if datetime.now().minute == 0:
                    self.task_manager.print_status()

        except KeyboardInterrupt:
            print("\n\n🛑 Остановлено пользователем")
        finally:
            if self.driver:
                print("🚪 Закрываю браузер...")
                self.driver.quit()


if __name__ == "__main__":
    bot = TopWarBot()
    bot.run_scheduler()