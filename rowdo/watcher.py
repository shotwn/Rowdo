import re
import os
import io
import math
from time import sleep
from pathlib import Path

import requests
from PIL import Image
import filetype

from rowdo.logging import logger
import rowdo.config as config
import rowdo.database


class ResizeException(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)
        self.msg = args[0]


class Watcher:
    def __init__(self, db: rowdo.database.Database):
        self.db = db
        self.keep_loop = True

        allow_from = config.get('download', 'allow_from').split(',')
        disallow_from = config.get('download', 'disallow_from').split(',')
        allow_formats = config.get('download', 'allow_formats_url').split(',')
        allow_mimes = config.get('download', 'allow_mime_types').split(',')
        self.allowed_urls_r = self.create_url_regexes(allow_from, allow_formats)
        self.disallowed_urls_r = self.create_url_regexes(disallow_from)
        self.allowed_mime_types = allow_mimes

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
        logger.debug('Running routine.')
        runtime = self.db.get_runtime()

        last_checked_timestamp = None
        if runtime:
            last_checked_timestamp = runtime.last_checked_timestamp

        rows = self.db.read_file_rows(status=rowdo.database.STATUS_WAITING_TO_PROCESS, last_checked_timestamp=last_checked_timestamp)
        logger.debug([row for row in rows])
        for row in rows:
            self.db.update_file_row(row, {
                "status": 0  # ! DEBUG ONLY rowdo.database.STATUS_PROCESSING
            })

            if row.command == rowdo.database.COMMAND_DOWNLOAD:
                downloaded_info = self.download_file(row)
                if downloaded_info:
                    self.db.update_file_row(row, {
                        "status": 0,  # ! DEBUG ONLY rowdo.database.STATUS_DONE
                        "path": downloaded_info['relative_path'] if self.keep_relative_path else downloaded_info['full_path'],
                        "filename": downloaded_info['filename']
                    })
            elif row.command == rowdo.database.COMMAND_DELETE_ROW_ONLY:
                self.db.delete_file_row(row)
            elif row.command == rowdo.database.COMMAND_DELETE_FILE_ONLY:
                self.delete_file(row)
                self.db.update_file_row(row, {
                    "status": rowdo.database.STATUS_DONE,
                    "path": None,
                    "filename": None
                })
            elif row.command == rowdo.database.COMMAND_DELETE:
                self.delete_file(row)
                self.db.delete_file_row(row)
            elif row.command == rowdo.database.COMMAND_IDLE:
                self.db.update_file_row(row, {
                    "status": rowdo.database.STATUS_DONE
                })
            print('here')
            self.db.set_runtime({
                'last_checked_timestamp': row.updated_at.isoformat()
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
            req = requests.get(row.url, allow_redirects=True)
            req.raise_for_status()
            return req
        except requests.exceptions.HTTPError as err:
            self.register_error(row, description='HTTP ERROR', mark_error=False)
            self.register_error(row, err, mark_error=False)
        except requests.exceptions.RequestException as err:
            self.register_error(row, description='REQUESTS ERROR')
            self.register_error(row, err)

    def get_filename(self, row, req=False):
        if row.filename:
            if '.' not in row.filename:
                filename = f"{row.filename}.{row.url.rsplit('.', 1)[1]}"
            else:
                filename = row.filename

            return filename
        elif req:
            try:
                url_last_part = row.url.rsplit('/', 1)[1]
                filename = self.get_filename_from_cd(req.headers.get('content-disposition'), url_last_part)
                return filename
            except (KeyError, IndexError) as err:
                self.register_error(row, description=f'Couldn\'t get the filename for url: {row["url"]}')
                self.register_error(row, err)
                return
        else:
            raise Exception('Cannot obtain filename.')

    def delete_file(self, row):
        filename = self.get_filename(row)
        if not filename:
            return

        full_path = self.get_download_path(filename)

        if os.path.exists(full_path):
            os.remove(full_path)

    def download_file(self, row):
        if not self.url_check(row.url):
            self.register_error(row, f'Disallowed URL or URL file format.: {row["url"]}')
            return

        if not self.is_downloadable(row.url):
            self.register_error(row, f'URL is not downloadable type.: {row["url"]}')
            return

        req = self.do_request(row)
        if not req:
            return

        if '*' not in self.allowed_mime_types:
            h_content_type = req.headers.get('Content-Type', False)
            if h_content_type and h_content_type not in self.allowed_mime_types and False:
                self.register_error(row, f'URL is not downloadable mime type (found {h_content_type}).: {row["url"]}')
                return

            content_type = filetype.guess_mime(req.content)
            if content_type not in self.allowed_mime_types:
                self.register_error(row, f'Downloaded bytes is not whitelisted mime type (found {content_type}).: {row["url"]}')
                return

        filename = self.get_filename(row, req)
        if not filename:
            return

        full_path = self.get_download_path(filename)

        try:
            if row.resize_mode == rowdo.database.RESIZE_NONE:
                file_to_save = req.content
            elif row.resize_mode == rowdo.database.RESIZE_PASSTHROUGH:
                file_to_save = self.resize_image(req.content, 'RATIO', 1)
            elif row.resize_mode == rowdo.database.RESIZE_RATIO:
                file_to_save = self.resize_image(req.content, 'RATIO', float(row.resize_ratio))
            elif row.resize_mode == rowdo.database.RESIZE_DIMENSIONS:
                file_to_save = self.resize_image(req.content, 'DIMENSIONS', row.resize_width, row.resize_height)
            else:
                self.register_error(row, description='Invalid resize mode.', mark_error=True)
        except ResizeException as exc:
            self.register_error(row, exc)
            return

        try:
            if getattr(file_to_save, 'save', False):
                file_to_save.save(full_path)  # PIL
            else:
                open(full_path, 'wb').write(file_to_save)
        except OSError as err:
            self.register_error(row, description=f'Couldn\'t open the path {full_path}', mark_error=False)
            self.register_error(row, err, mark_error=False)
            return

        return {
            "filename": filename,
            "full_path": full_path,
            "relative_path": f"{self.download_path}/{filename}"
        }

    def get_download_path(self, filename):
        if ':' in self.download_path or '~' in self.download_path:
            full_path = os.path.join(self.download_path, filename)
        else:
            full_path = os.path.join(os.getcwd(), self.download_path, filename)

        return full_path

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

    @staticmethod
    def resize_image(image_bytes, mode, *args):
        img = Image.open(io.BytesIO(image_bytes))
        print(args)
        if mode == 'RATIO':
            if len(args) < 1 or not args[0]:  # In case it is None or zero.
                raise ResizeException('Resize ratio was missing.')

            width = math.ceil(img.width * args[0])
            height = math.ceil(img.height * args[0])
            img = img.resize((width, height))

        if mode == 'DIMENSIONS':
            if len(args) < 2:
                raise ResizeException('Resize width or height was missing.')

            if not (args[0] and args[1]):
                raise ResizeException('Resize width or height is zero.')

            img = img.resize((args[0], args[1]))

        return img

    def register_error(self, row, description='', mark_error=True):
        logger.error(description)
        if mark_error:
            self.db.update_file_row(row, {
                'status': rowdo.database.STATUS_ERROR
            })

    def loop(self):
        run_every_seconds = int(config.get('runtime', 'run_every_seconds'))
        while self.keep_loop:
            self.routine()
            self.db.close_session()
            for i in range(run_every_seconds * 10):
                sleep(0.1)
