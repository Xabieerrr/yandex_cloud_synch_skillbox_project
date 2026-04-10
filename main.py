import configparser
import logging
import os
import time

from sync_service import SyncService
from yandex_disk import YandexDiskClient


def read_config(config_path):
    parser = configparser.ConfigParser()
    if not parser.read(config_path):
        raise ValueError(f"Не найден файл настроек: {config_path}")

    if "settings" not in parser:
        raise ValueError("В config.ini отсутствует секция [settings]")

    settings = parser["settings"]

    local_folder = settings.get("local_folder", "").strip()
    remote_folder = settings.get("remote_folder", "").strip()
    token = settings.get("token", "").strip()
    sync_period_raw = settings.get("sync_period", "").strip()
    log_file = settings.get("log_file", "").strip()

    if not local_folder:
        raise ValueError("Не указан параметр local_folder")
    if not remote_folder:
        raise ValueError("Не указан параметр remote_folder")
    if not token:
        raise ValueError("Не указан параметр token")
    if not sync_period_raw:
        raise ValueError("Не указан параметр sync_period")
    if not log_file:
        raise ValueError("Не указан параметр log_file")

    try:
        sync_period = int(sync_period_raw)
    except ValueError as error:
        raise ValueError("Параметр sync_period должен быть целым числом") from error

    if sync_period <= 0:
        raise ValueError("Параметр sync_period должен быть больше 0")

    return {
        "local_folder": local_folder,
        "remote_folder": remote_folder,
        "token": token,
        "sync_period": sync_period,
        "log_file": log_file,
    }


def setup_logging(log_file):
    log_folder = os.path.dirname(log_file)
    if log_folder and not os.path.exists(log_folder):
        os.makedirs(log_folder, exist_ok=True)

    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8",
    )


def validate_local_folder(local_folder):
    if not os.path.isdir(local_folder):
        raise ValueError(f"Локальная папка не найдена: {local_folder}")


def validate_remote_access(client):
    try:
        client.get_info()
    except Exception as error:
        raise ValueError(str(error)) from error


def run_sync_loop(sync_service, sync_period):
    try:
        while True:
            sync_service.sync_once()
            time.sleep(sync_period)
    except KeyboardInterrupt:
        logging.info("Программа остановлена пользователем")
        print("Программа остановлена пользователем")


def main():
    try:
        config = read_config("config.ini")
        validate_local_folder(config["local_folder"])
        setup_logging(config["log_file"])

        disk_client = YandexDiskClient(
            token=config["token"],
            remote_folder=config["remote_folder"],
        )

        validate_remote_access(disk_client)

        logging.info("Запуск синхронизации. Локальная папка: %s", config["local_folder"])

        sync_service = SyncService(
            local_folder=config["local_folder"],
            disk_client=disk_client,
        )

        run_sync_loop(sync_service, config["sync_period"])

    except ValueError as error:
        print(f"Ошибка конфигурации: {error}")
    except Exception as error:
        print(f"Критическая ошибка запуска: {error}")


if __name__ == "__main__":
    main()
