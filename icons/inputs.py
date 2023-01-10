import io
from abc import abstractmethod
from functools import partial

from PIL import Image
from PIL.ImageColor import getrgb
from cairosvg.colors import color as cairo_color
from cairosvg.parser import Tree
from cairosvg.surface import PNGSurface

from .base import BaseProvider, Base
from .sources import BaseSource
from .utils import register


# don't inherit from Base since we don't need path processing
class BaseInput(Base):
    @property
    @abstractmethod
    def is_vector(self) -> bool:
        pass

    def __init__(self, source: BaseSource, **kwargs):
        self.source = source
        kwargs.setdefault('format', source.format)
        super().__init__(**kwargs)

        # load the image as a byte string, so we only need to read the source file once
        with open(self.path, 'rb') as f:
            self.byte_string = f.read()

    def __str__(self):
        text = super().__str__()
        text += f' from {str(self.source)}'
        return text


class BaseLossyInput(BaseInput):
    is_vector = False

    @abstractmethod
    def ingest(self, color: str) -> Image:
        pass


class BaseLosslessInput(BaseInput):
    is_vector = True

    @abstractmethod
    def ingest(self, size: int, color: str) -> Image:
        pass


input_provider = BaseProvider()
register_input = partial(register, provider=input_provider)


@register_input('png', 'jpg', 'jpeg')
class StandardInput(BaseLossyInput):
    def ingest(self, color: str):
        # create io.BytesIO object from the new byte string, then pass it to Pillow
        img = Image.open(io.BytesIO(self.byte_string))

        # convert to RGBA if not already
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        # change the foreground color
        self._change_color(img, from_color='#000000', to_color=color)

        return img

    @staticmethod
    def _change_color(img: Image, from_color, to_color, delta_rank=10):
        from_color = getrgb(from_color)
        to_color = getrgb(to_color)

        img_data = img.load()
        for x in range(0, img.size[0]):
            for y in range(0, img.size[1]):
                r_delta = img_data[x, y][0] - from_color[0]
                g_delta = img_data[x, y][0] - from_color[0]
                b_delta = img_data[x, y][0] - from_color[0]
                if (
                    abs(r_delta) <= delta_rank
                    and abs(g_delta) <= delta_rank
                    and abs(b_delta) <= delta_rank
                ):
                    img_data[x, y] = (
                        to_color[0] + r_delta,
                        to_color[1] + g_delta,
                        to_color[2] + b_delta,
                        img_data[x, y][3],
                    )


def specify_color(rgba_map, target_color: tuple[float] = None):
    # fallback to input color if no target color is specified
    if target_color is None:
        return rgba_map

    r, g, b, a = rgba_map
    # only use the first 3 values of the target color to keep the current alpha channel
    return target_color[:3] + (a,)


@register_input('svg')
class SvgInput(BaseLosslessInput):
    def ingest(self, size, color):
        kwargs = {}

        # specify color settings as needed
        if color:
            kwargs['map_rgba'] = partial(specify_color, target_color=cairo_color(color))

        # specify output size to scale the vector as needed
        new_byte_string = self.convert(
            self.byte_string, output_width=size, output_height=size, **kwargs
        )
        # create io.BytesIO object from the new byte string, then pass it to Pillow
        return Image.open(io.BytesIO(new_byte_string))

    @staticmethod
    def convert(
        bytestring=None,
        *,
        dpi=96,
        parent_width=None,
        parent_height=None,
        scale=1,
        unsafe=False,
        background_color=None,
        map_rgba=None,
        map_image=None,
        output_width=None,
        output_height=None,
        **kwargs,
    ):
        tree = Tree(bytestring=bytestring, unsafe=unsafe, **kwargs)
        output = io.BytesIO()
        instance = PNGSurface(
            tree,
            output,
            dpi,
            None,
            parent_width,
            parent_height,
            scale,
            output_width,
            output_height,
            background_color,
            map_rgba=map_rgba,
            map_image=map_image,
        )
        instance.finish()
        return output.getvalue()
