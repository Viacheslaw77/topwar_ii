import json
from datetime import datetime, timedelta


class TaskManager:
    def __init__(self, config_path="C:/python/topwar/scheduler.json"):
        self.config_path = config_path
        self.config = self.load_config()
        self.settings = self.config['settings']
        self.tasks = self.config['tasks']

    def load_config(self):
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_config(self):
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)

    def get_day_start(self):
        now = datetime.now()
        day_start = now.replace(
            hour=self.settings['day_start_hour'],
            minute=0, second=0, microsecond=0
        )
        if now.hour < self.settings['day_start_hour']:
            day_start -= timedelta(days=1)
        return day_start

    def calculate_next_run(self, task):
        now = datetime.now()
        day_start = self.get_day_start()

        if task['type'] == 'daily':
            frequency = task['frequency']
            hours_between = 24 / frequency

            if not task['last_run']:
                return day_start + timedelta(hours=1)

            last_run = datetime.fromisoformat(task['last_run'])

            if last_run < day_start:
                return day_start + timedelta(hours=1)

            next_run = last_run + timedelta(hours=hours_between)
            next_day_start = day_start + timedelta(days=1)

            if next_run >= next_day_start:
                return None

            return next_run

        elif task['type'] == 'hourly':
            frequency = task['frequency']

            if not task['last_run']:
                return now + timedelta(minutes=5)

            last_run = datetime.fromisoformat(task['last_run'])
            return last_run + timedelta(hours=frequency)

        return None

    def get_ready_tasks(self):
        now = datetime.now()
        ready = []

        for task in self.tasks:
            if not task['enabled']:
                continue
            next_run = self.calculate_next_run(task)
            if next_run and next_run <= now:
                ready.append(task)

        return ready

    def mark_task_completed(self, task_id):
        for task in self.tasks:
            if task['id'] == task_id:
                task['last_run'] = datetime.now().isoformat()
                break
        self.save_config()

    def log(self, message):
        log_path = f"C:/python/topwar/{self.settings['log_file']}"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")

    def print_status(self):
        print("\n" + "="*70)
        print("📋 СТАТУС ЗАДАЧ")
        print("="*70)

        now = datetime.now()

        for task in self.tasks:
            next_run = self.calculate_next_run(task)
            ready = next_run and next_run <= now
            enabled = "🟢" if task['enabled'] else "🔴"
            status = "✅" if ready else ""

            print(f"\n{status} {enabled} {task['name']}")
            print(f"   Частота: {task['frequency']} раз/сутки")
            print(f"   Последний запуск: {task['last_run'] or 'Никогда'}")
            print(f"   Следующий: {next_run.isoformat() if next_run else 'Выполнено сегодня'}")

        print("\n" + "="*70)