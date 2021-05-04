import re
import os
import io
import math
from time import sleep
from pathlib import Path

import requests
from PIL import Image
import filetype

from rowdo.logging import logger, get_severity_name
import rowdo.config as config
import rowdo.database
import rowdo.exceptions as exceptions


class ResizeException(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)
        self.message = args[0]


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

        self.max_attempts = config.get('download', 'max_attempts')

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

        rows = self.db.read_file_rows(
            status=[rowdo.database.STATUS_WAITING_TO_PROCESS, rowdo.database.STATUS_WILL_RETRY],
            last_checked_timestamp=last_checked_timestamp
        )

        logger.debug([row for row in rows])
        for row in rows:
            try:
                self.process_row(row)
            except exceptions.RowdoException as exc:
                severity = exc.level if exc.level else 50
                logger.log(get_severity_name(severity), exc)
                self.db.register_error(row, exc)
                if exc.level > exceptions.WARNING:
                    # Mark file to prevent retry.
                    self.db.update_file_row(row, {
                        'status': rowdo.database.STATUS_ERROR,
                        'failed_attempts': row.failed_attempts + 1
                    })
                elif row.failed_attempts >= self.max_attempts - 1:
                    # Mark file multi tried error. It won't retry.
                    logger.error(f'Max attempts reached. ID:{row.id}')
                    self.db.update_file_row(row, {
                        'status': rowdo.database.STATUS_MAX_RETRIES_REACHED,
                        'failed_attempts': row.failed_attempts + 1
                    })
                else:
                    # Mark file error but ok to retry.
                    logger.debug(f'Mark for retry. ID:{row.id}')
                    self.db.update_file_row(row, {
                        'status': rowdo.database.STATUS_WILL_RETRY,
                        'failed_attempts': row.failed_attempts + 1
                    })
        self.db.close_session()

    def process_row(self, row):
        self.db.update_file_row(row, {
            "status": rowdo.database.STATUS_PROCESSING  # ! DEBUG ONLY rowdo.database.STATUS_PROCESSING
        })

        if row.command == rowdo.database.COMMAND_DOWNLOAD:
            downloaded_info = self.download_file(row)
            if downloaded_info:
                self.db.update_file_row(row, {
                    "status": rowdo.database.STATUS_DONE,  # ! DEBUG ONLY rowdo.database.STATUS_DONE
                    "downloaded_path": downloaded_info['relative_path'] if self.keep_relative_path else downloaded_info['full_path'],
                    "filename": downloaded_info['filename']
                })
        elif row.command == rowdo.database.COMMAND_DELETE_ROW_ONLY:
            self.db.delete_file_row(row)
        elif row.command == rowdo.database.COMMAND_DELETE_FILE_ONLY:
            self.delete_file(row)
            self.db.update_file_row(row, {
                "status": rowdo.database.STATUS_DONE,
                "downloaded_path": None,
                "filename": None
            })
        elif row.command == rowdo.database.COMMAND_DELETE:
            self.delete_file(row)
            self.db.delete_file_row(row)
        elif row.command == rowdo.database.COMMAND_IDLE:
            self.db.update_file_row(row, {
                "status": rowdo.database.STATUS_DONE
            })

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
            if not req:
                raise exceptions.RequestError('Empty Response.', level=exceptions.WARNING)
            return req
        except requests.exceptions.HTTPError:
            raise exceptions.RequestError('HTTP returned non 200 code. Make sure url is correct.', level=exceptions.WARNING)
        except requests.exceptions.RequestException:
            raise exceptions.RequestError('Request Exception. Make sure URL is correct.', level=exceptions.WARNING)

    def get_filename(self, row, req=False, return_none=False):
        if row.filename:
            if '.' not in row.filename:
                # No format, get it from URL.
                filename = f"{row.filename}.{row.url.rsplit('.', 1)[1]}"
            else:
                # Has format get it directly.
                filename = row.filename

            return filename.lstrip('~.')  # Do not allow upper directories.
        elif req:
            # No filename set at all, get from URL.
            try:
                url_last_part = row.url.rsplit('/', 1)[1]
                filename = self.get_filename_from_cd(req.headers.get('content-disposition'), url_last_part)
                return filename
            except (KeyError, IndexError) as err:
                raise exceptions.FileNameError(f'Couldn\'t get the filename for url: {row.url}. {err.message}', level=exceptions.ERROR)
                return
        else:
            if not return_none:
                raise exceptions.FileNameError('Couldn\'t obtain filename.', level=exceptions.ERROR)

    def delete_file(self, row):
        filename = self.get_filename(row, return_none=True)
        if not filename:
            return

        full_path = self.get_download_path(filename)

        if os.path.exists(full_path):
            os.remove(full_path)

    def download_file(self, row):  # noqa: C901
        if not self.url_check(row.url):
            raise exceptions.BlackListException(f'Disallowed URL or URL file format.: {row.url}', level=exceptions.ERROR)

        if not self.is_downloadable(row.url):
            raise exceptions.BlackListException(f'URL is not downloadable type.: {row.url}', level=exceptions.ERROR)

        req = self.do_request(row)  # Can throw error.

        if '*' not in self.allowed_mime_types:
            h_content_type = req.headers.get('Content-Type', False)
            if h_content_type and h_content_type not in self.allowed_mime_types and False:
                raise exceptions.BlackListException(f'URL is not downloadable mime type (found {h_content_type}).: {row.url}', level=exceptions.ERROR)

            content_type = filetype.guess_mime(req.content)
            if content_type not in self.allowed_mime_types:
                raise exceptions.BlackListException(f'Downloaded bytes is not whitelisted mime type (found {content_type}).: {row.url}', level=exceptions.ERROR)

        filename = self.get_filename(row, req)
        if not filename:
            return

        full_path = self.get_download_path(filename)
        path_dirname = os.path.dirname(full_path)

        try:
            if row.resize_mode == rowdo.database.RESIZE_NONE:
                file_to_save = req.content
            elif row.resize_mode == rowdo.database.RESIZE_PASSTHROUGH:
                file_to_save = self.resize_image(req.content, 'RATIO', 1)
            elif row.resize_mode == rowdo.database.RESIZE_RATIO:
                file_to_save = self.resize_image(req.content, 'RATIO', row.resize_ratio)
            elif row.resize_mode == rowdo.database.RESIZE_DIMENSIONS:
                file_to_save = self.resize_image(req.content, 'DIMENSIONS', row.resize_width, row.resize_height)
            else:
                raise exceptions.ResizeModeException('Invalid resize mode.', level=exceptions.ERROR)
        except exceptions.ResizeException as exc:
            raise exceptions.ResizeException(f'Resize algorithm failed: {exc.message}', level=exceptions.ERROR)

        try:
            if not os.path.exists(path_dirname):
                logger.debug(f'Creating new directory: {path_dirname}')
                os.makedirs(path_dirname)  # Create nested folders.

            if getattr(file_to_save, 'save', False):
                logger.trace(f'Saving using PIL: {full_path}')
                file_to_save.save(full_path)  # PIL
            else:
                logger.trace(f'Saving file directly: {full_path}')
                open(full_path, 'wb').write(file_to_save)
        except (OSError, ValueError) as err:
            raise exceptions.FileAccessError(f'Couldn\'t open the path {full_path}. {err}', level=exceptions.ERROR)

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
        logger.trace(f'Resize Image, Mode:{mode} Args: {args}')
        if mode == 'RATIO':
            if len(args) < 1 or not args[0]:  # In case it is None or zero.
                raise exceptions.ResizeException('Resize ratio was missing.', exceptions.ERROR)

            try:
                resize_ratio = float(args[0])
            except TypeError as err:  # Invalid row.resize_ratio
                raise exceptions.ResizeException(f"Resize ratio is not valid. {err}", exceptions.ERROR)

            width = math.ceil(img.width * resize_ratio)
            height = math.ceil(img.height * resize_ratio)
            img = img.resize((width, height))

        if mode == 'DIMENSIONS':
            if len(args) < 2:
                raise exceptions.ResizeException('Resize width or height was missing.', exceptions.ERROR)

            if not (args[0] and args[1]):
                raise exceptions.ResizeException('Resize width or height is zero.', exceptions.ERROR)

            img = img.resize((args[0], args[1]))

        return img

    def loop(self):
        run_every_seconds = int(config.get('runtime', 'run_every_seconds'))
        while self.keep_loop:
            self.routine()
            for i in range(run_every_seconds * 10):
                sleep(0.1)

    def stop(self):
        self.keep_loop = False
