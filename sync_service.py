import logging
import os


class SyncService:
    def __init__(self, local_folder, disk_client):
        self.local_folder = local_folder
        self.disk_client = disk_client
        self.previous_snapshot = {}
        self.first_sync_done = False

    def sync_once(self):
        current_snapshot = self._get_local_snapshot()

        if not self.first_sync_done:
            first_sync_success = self._first_sync(current_snapshot)
            if not first_sync_success:
                return

            self.previous_snapshot = current_snapshot
            self.first_sync_done = True
            return

        new_files = self._find_new_files(current_snapshot)
        changed_files = self._find_changed_files(current_snapshot)
        deleted_files = self._find_deleted_files(current_snapshot)

        self._upload_new_files(new_files)
        self._reload_changed_files(changed_files)
        self._delete_removed_files(deleted_files)

        self.previous_snapshot = current_snapshot
        logging.info("Проверка синхронизации завершена")

    def _first_sync(self, local_snapshot):
        try:
            remote_info = self.disk_client.get_info()
        except Exception as error:
            logging.error("Ошибка получения списка удалённых файлов: %s", error)
            return False

        remote_files = set(remote_info.keys())
        local_files = set(local_snapshot.keys())

        files_to_delete = remote_files - local_files
        success = True

        for filename in files_to_delete:
            try:
                self.disk_client.delete(filename)
                logging.info("Первая синхронизация: удалён лишний файл: %s", filename)
            except Exception as error:
                logging.error(
                    "Первая синхронизация: ошибка удаления файла '%s': %s",
                    filename,
                    error,
                )
                success = False

        for filename in local_files:
            path = os.path.join(self.local_folder, filename)
            try:
                if filename in remote_files:
                    self.disk_client.reload(path)
                else:
                    self.disk_client.load(path)
                logging.info(
                    "Первая синхронизация: файл синхронизирован: %s",
                    filename,
                )
            except Exception as error:
                logging.error(
                    "Первая синхронизация: ошибка синхронизации файла '%s': %s",
                    filename,
                    error,
                )
                success = False

        if success:
            logging.info("Первая синхронизация успешно завершена")
            return True

        logging.error("Первая синхронизация завершилась с ошибками")
        return False

    def _get_local_snapshot(self):
        snapshot = {}

        try:
            names = os.listdir(self.local_folder)
        except OSError as error:
            logging.error("Ошибка чтения локальной папки: %s", error)
            return snapshot

        for name in names:
            path = os.path.join(self.local_folder, name)
            if not os.path.isfile(path):
                continue

            try:
                modified_time = os.path.getmtime(path)
            except OSError as error:
                logging.error("Ошибка чтения файла '%s': %s", path, error)
                continue

            snapshot[name] = modified_time

        return snapshot

    def _find_new_files(self, current_snapshot):
        new_files = set()
        for name in current_snapshot:
            if name not in self.previous_snapshot:
                new_files.add(name)
        return new_files

    def _find_changed_files(self, current_snapshot):
        changed_files = set()
        for name, modified in current_snapshot.items():
            old_modified = self.previous_snapshot.get(name)
            if old_modified is None:
                continue
            if modified != old_modified:
                changed_files.add(name)
        return changed_files

    def _find_deleted_files(self, current_snapshot):
        deleted_files = set()
        for name in self.previous_snapshot:
            if name not in current_snapshot:
                deleted_files.add(name)
        return deleted_files

    def _upload_new_files(self, files):
        for filename in files:
            path = os.path.join(self.local_folder, filename)
            try:
                self.disk_client.load(path)
                logging.info("Загружен новый файл: %s", filename)
            except Exception as error:
                logging.error("Ошибка загрузки файла '%s': %s", filename, error)

    def _reload_changed_files(self, files):
        for filename in files:
            path = os.path.join(self.local_folder, filename)
            try:
                self.disk_client.reload(path)
                logging.info("Обновлён файл: %s", filename)
            except Exception as error:
                logging.error("Ошибка обновления файла '%s': %s", filename, error)

    def _delete_removed_files(self, files):
        for filename in files:
            try:
                self.disk_client.delete(filename)
                logging.info("Удалён файл: %s", filename)
            except Exception as error:
                logging.error("Ошибка удаления файла '%s': %s", filename, error)
