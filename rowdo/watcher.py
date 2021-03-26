import re
import os
from pathlib import Path

import requests

from rowdo.logging import logger
import rowdo.config as config
import rowdo.database


class Watcher:
    def __init__(self, db: rowdo.database.Database):
        self.db = db

        allow_from = config.get('download', 'allow_from').split(',')
        disallow_from = config.get('download', 'disallow_from').split(',')
        allow_formats = config.get('download', 'allow_formats_url').split(',')
        self.allowed_urls_r = self.create_url_regexes(allow_from, allow_formats)
        self.disallowed_urls_r = self.create_url_regexes(disallow_from)

        self.download_path = config.get('download', 'path')
        Path(self.download_path).mkdir(parents=True, exist_ok=True)

        self.keep_relative_path = config.get('download', 'keep_relative_path')

    @staticmethod
    def strip_list(list_to_strip):
        new_list = []
        for item in list_to_strip:
            new_list.appned(item.strip())

        return new_list

    def create_url_regexes(self, urls, formats=None):
        regexes = []
        for url in urls:
            if url.isspace() or url == '':
                continue

            if url == '*':
                regexes = [re.compile('(.*)')]
                break

            if not formats or '*' in formats:
                regexes.append(
                    re.compile(
                        f'^{url}(.*)$'
                    )
                )
                continue

            for form in formats:
                regexes.append(
                    re.compile(
                        f'^{url}(.*).{form}$'
                    )
                )

        return regexes

    def routine(self):
        runtime = self.db.get_runtime()

        last_checked_timestamp = None
        if runtime:
            last_checked_timestamp = runtime.get('last_checked_timestamp')

        rows = self.db.read_file_rows(status=0, last_checked_timestamp=last_checked_timestamp)

        for row in rows:
            self.db.update_file_row(row['id'], {
                "status": rowdo.database.STATUS_PROCESSING
            })

            if row['command'] == rowdo.database.COMMAND_DOWNLOAD:
                downloaded_info = self.download_file(row)
                if downloaded_info:
                    self.db.update_file_row(row['id'], {
                        "status": 0,  # ! DEBUG ONLY rowdo.database.STATUS_DONE
                        "path": downloaded_info['relative_path'] if self.keep_relative_path else downloaded_info['full_path']
                    })

            self.db.set_runtime({
                'last_checked_timestamp': row['updated_at'].isoformat()
            })

    def url_check(self, url):
        for rx in self.disallowed_urls_r:
            if re.search(rx, url):
                return False

        for rx in self.allowed_urls_r:
            if re.search(rx, url):
                return True

        return False  # Not allowed, not disallowed

    def do_request(self, row):
        try:
            req = requests.get(row['url'], allow_redirects=True)
            req.raise_for_status()
            return req
        except requests.exceptions.HTTPError as err:
            self.register_error(row, description='HTTP ERROR', mark_error=False)
            self.register_error(row, err, mark_error=False)
        except requests.exceptions.RequestException as err:
            self.register_error(row, description='REQUESTS ERROR')
            self.register_error(row, err)

    def get_filename(self, row, req):
        if row['filename']:
            filename = f"{row['filename']}.{row['url'].rsplit('.', 1)[1]}"
            return filename
        else:
            try:
                url_last_part = row['url'].rsplit('/', 1)[1]
                filename = self.get_filename_from_cd(req.headers.get('content-disposition'), url_last_part)
                return filename
            except (KeyError, IndexError) as err:
                self.register_error(row, description=f'Couldn\'t get the filename for url: {row["url"]}')
                self.register_error(row, err)
                return

    def download_file(self, row):
        if not self.url_check(row['url']):
            self.register_error(row, f'Disallowed URL or URL file format.: {row["url"]}')
            return

        if not self.is_downloadable(row['url']):
            self.register_error(row, f'URL is not downloadable type.: {row["url"]}')
            return

        req = self.do_request(row)
        if not req:
            return

        filename = self.get_filename(row, req)
        if not filename:
            return

        if ':' in self.download_path or '~' in self.download_path:
            full_path = os.path.join(self.download_path, filename)
        else:
            full_path = os.path.join(os.getcwd(), self.download_path, filename)

        try:
            open(full_path, 'wb').write(req.content)
        except OSError as err:
            self.register_error(row, description=f'Couldn\'t open the path {full_path}', mark_error=False)
            self.register_error(row, err, mark_error=False)
            return

        return {
            "filename": filename,
            "full_path": full_path,
            "relative_path": f"{self.download_path}/{filename}"
        }

    @staticmethod
    def is_downloadable(url):
        """
        Does the url contain a downloadable resource
        """
        h = requests.head(url, allow_redirects=True)
        header = h.headers
        content_type = header.get('content-type')
        if 'text' in content_type.lower():
            return False
        if 'html' in content_type.lower():
            return False
        return True

    @staticmethod
    def get_filename_from_cd(cd, default):
        """
        Get filename from content-disposition
        """
        if not cd:
            return default
        file_name = re.findall('filename=(.+)', cd)
        if len(file_name) == 0:
            return default
        return file_name[0]

    def register_error(self, row, description='', mark_error=True):
        logger.error(description)
        if mark_error:
            self.db.update_file_row(row['id'], {
                'status': rowdo.database.STATUS_ERROR
            })
