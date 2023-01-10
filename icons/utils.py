from icons.base import BaseBuilder


def register(*keys, provider=None):
    """
    Register the given model(s) classes and wrapped ModelAdmin class with
    admin site:

    @register(Author)
    class AuthorAdmin(admin.ModelAdmin):
        pass

    The `site` kwarg is an admin site to use instead of the default admin site.
    """

    def _service_wrapper(build_class):
        if not keys:
            raise ValueError('At least one service must be passed to register.')

        if not provider:
            raise ValueError('A provider must be passed to register.')

        builder = BaseBuilder(build_class=build_class)
        provider.register(keys, builder=builder)

        return build_class

    return _service_wrapper
