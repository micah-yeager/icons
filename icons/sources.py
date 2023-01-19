import tempfile
import zipfile
from abc import abstractmethod
from functools import partial
from pathlib import Path, PurePath, PurePosixPath
from typing import Generator

import requests

from .base import Base, BaseBuilder, BaseProvider
from .utils import register


class BaseSource(Base):
    requires_fetching = False

    @abstractmethod
    def get(self) -> Generator[Path, None, None]:
        pass


source_provider = BaseProvider(fallback_key='type', fallback_method='pop')
register_source = partial(register, provider=source_provider)


@register_source('file')
class FileSource(BaseSource):
    def get(self):
        if self.path.suffix != self.format:
            raise ValueError('Path {} does not have the correct extension for {}'.format(self.path, self.format))

        yield self.base_path / self.path


class FileSourceBuilder(BaseBuilder):
    build_class = FileSource


@register_source('directory', 'folder')
class DirectorySource(BaseSource):
    def __init__(self, recurse: bool = False, target_folders: list[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.recurse = recurse

        if target_folders is None:
            target_folders = []
        self.target_folders = [PurePath(folder) for folder in target_folders]

    def get(self):
        path = self.base_path / self.path
        # set glob pattern based on recursion
        pattern = '**/*' if self.recurse else '*'
        pattern += f'.{self.format}'

        # get all files in the path that match the pattern
        if not self.target_folders:
            yield from path.glob(pattern)
        else:
            for folder in self.target_folders:
                yield from (path / folder).glob(pattern)


@register_source('url')
class UrlSource(DirectorySource, FileSource):
    requires_fetching = True

    def __init__(self, **kwargs):
        # keep the url as a string to avoid issues with pathlib with double slashes
        self.url = kwargs['path']
        self.url_path = PurePosixPath(self.url)
        super().__init__(**kwargs)
        self.path = PurePath(self.url_path.name)
        self.base_path = Path(tempfile.gettempdir())

    def get(self):
        # get the file, downloading it if necessary
        download_path = self.base_path / self.path
        if not download_path.exists():
            request = requests.get(self.url)
            request.raise_for_status()
            with open(download_path, 'wb') as f:
                f.write(request.content)

        # check if the file is an archive and extract it if needed
        if zipfile.is_zipfile(download_path):
            with zipfile.ZipFile(download_path, 'r') as zip_ref:
                zip_ref.extractall(self.base_path)

            # run the DirectorySource super get method
            self.path = self.base_path / self.path.stem
            return super().get()
        else:
            # run the FileSource super get method
            return super(DirectorySource, self).get()
