import os

import requests


class YandexDiskClient:
    BASE_URL = "https://cloud-api.yandex.net/v1/disk/resources"

    def __init__(self, token, remote_folder):
        self.token = token
        self.remote_folder = remote_folder.strip("/")

    def load(self, path):
        filename = os.path.basename(path)
        upload_url = self._get_upload_link(filename)

        with open(path, "rb") as file_obj:
            response = requests.put(upload_url, data=file_obj, timeout=30)

        if response.status_code not in (201, 202):
            raise RuntimeError(
                f"Не удалось загрузить файл '{filename}'. Код: {response.status_code}"
            )

    def reload(self, path):
        self.load(path)

    def delete(self, filename):
        remote_path = self._build_remote_path(filename)
        params = {"path": remote_path, "permanently": "true"}

        response = requests.delete(
            self.BASE_URL,
            headers=self._headers(),
            params=params,
            timeout=30,
        )

        if response.status_code not in (202, 204, 404):
            raise RuntimeError(
                f"Не удалось удалить файл '{filename}'. Код: {response.status_code}"
            )

    def get_info(self):
        params = {
            "path": self._build_remote_path(),
            "limit": 1000,
            "fields": "_embedded.items.name,_embedded.items.modified,_embedded.items.type",
        }

        response = requests.get(
            self.BASE_URL,
            headers=self._headers(),
            params=params,
            timeout=30,
        )

        if response.status_code == 401:
            raise RuntimeError("Неверный токен Яндекс Диска")
        if response.status_code == 404:
            raise RuntimeError("Удалённая папка не найдена")
        if response.status_code != 200:
            raise RuntimeError(
                f"Не удалось получить список файлов. Код: {response.status_code}"
            )

        data = response.json()
        embedded = data.get("_embedded", {})
        items = embedded.get("items", [])

        files = {}
        for item in items:
            if item.get("type") != "file":
                continue
            name = item.get("name")
            modified = item.get("modified")
            if name:
                files[name] = {"modified": modified}

        return files

    def _get_upload_link(self, filename):
        params = {
            "path": self._build_remote_path(filename),
            "overwrite": "true",
        }

        response = requests.get(
            f"{self.BASE_URL}/upload",
            headers=self._headers(),
            params=params,
            timeout=30,
        )

        if response.status_code == 401:
            raise RuntimeError("Неверный токен Яндекс Диска")
        if response.status_code == 404:
            raise RuntimeError("Удалённая папка не найдена")
        if response.status_code != 200:
            raise RuntimeError(
                f"Не удалось получить ссылку загрузки. Код: {response.status_code}"
            )

        href = response.json().get("href")
        if not href:
            raise RuntimeError("Ссылка загрузки не получена")

        return href

    def _build_remote_path(self, filename=None):
        base = f"disk:/{self.remote_folder}" if self.remote_folder else "disk:/"
        if filename:
            return f"{base}/{filename}"
        return base

    def _headers(self):
        return {"Authorization": f"OAuth {self.token}"}
