from pathlib import Path, PurePath


class Base:
    base_path = None

    def __init__(self, format: str, path: str | Path = None, base_path: str | Path = '', **kwargs):
        self.format = format
        self.path = PurePath(path) if isinstance(path, str) else path
        self.base_path = Path(base_path)

        # ensure base_path exists
        if self.base_path is not None:
            self.base_path.mkdir(parents=True, exist_ok=True)

    def __str__(self):
        return self.__class__.__name__ + ' for ' + self.path


class BaseBuilder:
    build_class = Base

    def __init__(self, build_class=None):
        self._instance = None

        if build_class is not None:
            self.build_class = build_class

    def __call__(self, values, **kwargs) -> Base:
        values = values | kwargs
        # convert dashes in kwarg keys to underscores
        kwargs = {key.replace('-', '_'): value for key, value in values.items()}
        return self.build_class(**kwargs)


class BaseProvider:
    def __init__(self, base_path: str | Path = '', fallback_key: str = 'format', fallback_method='get'):
        self._builders = {}
        self.base_path = Path(base_path)
        self.fallback_key = fallback_key
        self.fallback_method = fallback_method

    def register(self, keys: str | list[str], builder: callable) -> None:
        if isinstance(keys, str):
            keys = [keys]

        for key in keys:
            self._builders[key] = builder

    def get(self, key: str, values: dict = None) -> Base:
        if isinstance(key, dict):
            # assign "key" to values
            if values is None:
                values = key
            key = getattr(key, self.fallback_method)(self.fallback_key)

        builder = self._builders.get(key)
        if not builder:
            raise ValueError(f'No builder registered for type "{key}".')

        return builder(values, base_path=self.base_path)
