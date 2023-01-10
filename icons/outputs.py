from functools import partial
from pathlib import Path

from PIL import Image

from .base import Base, BaseProvider
from .inputs import BaseInput
from .utils import register


def get_core_image_size(target_size: int, margin: int | str) -> int:
    """Generate the margin and image size for a given image size and margin.

    Args:
        target_size (int): The size of the image, assumes the image is square.
        margin (int | str): The margin to use.

    Returns:
        tuple[int, int]: The size of the core image and margin, respectively.
    """
    if not margin:
        return target_size

    # if an integer
    if isinstance(margin, int):
        core_size = target_size - (margin * 2)
        return core_size

    # if a string ending in px
    if isinstance(margin, str) and margin.endswith('px'):
        # get the integer value
        margin = int(margin.removesuffix('px').strip())

        # calculate the core size
        core_size = target_size - (round(margin) * 2)
        return core_size

    # if a string ending in %
    if isinstance(margin, str) and margin.endswith('%'):
        # get the float value
        margin = float(margin.removesuffix('%').strip())

        # calculate the core and margin sizes
        margin_size = round(target_size * (margin / 100) * 2)
        core_size = target_size - margin_size

        return core_size

    raise ValueError(f'Invalid margin type: {type(margin)}')


class BaseOutput(Base):
    base_path = Path(__file__).parent.parent / 'dist'

    def __init__(
        self,
        sizes: list[int],
        directory_override: str = None,
        file_prefix: str = '',
        color: bool = None,
        background: str = None,
        margin: str = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.directory_override = directory_override
        self.file_prefix = file_prefix
        self.target_sizes = sizes
        self.target_margin = margin
        self.color = color
        self.background = background

    def generate_sizes(self) -> int:
        for target_size in self.target_sizes:
            yield target_size, get_core_image_size(target_size, self.target_margin)

    def generate(
        self, img: Image, input: BaseInput, target_size: int, core_size: int
    ) -> (Image, Path):
        input_ = input

        dest_path = self._generate_path(input_, target_size)

        img = self._adjust_core(img, core_size)
        img = self._add_background(img, target_size)

        return img, dest_path

    def _generate_path(self, input_: BaseInput, target_size: int) -> Path:
        # remove the part of the path shared between the source and output base paths
        if self.directory_override:
            dest_path = self.directory_override
        else:
            dest_path = Path(
                *[
                    part
                    # use parent parts since we'll be renaming the file below
                    for part in input_.path.parent.parts
                    if part not in input_.source.base_path.parts
                ]
            )

        # rename the file and add the appropriate suffix
        filename_parts = [input_.path.with_suffix('').name, str(target_size)]
        # prepend prefix if set
        if self.file_prefix:
            filename_parts.insert(0, self.file_prefix)

        # combine the parts of the file name
        file_name = '-'.join(filename_parts) + f'.{self.format}'
        return self.base_path / dest_path / file_name

    @staticmethod
    def _adjust_core(img: Image, core_size: int) -> Image:
        # if the image dimensions aren't square, determine the longest side and scale
        # the other side while keeping the aspect ratio
        if img.width != img.height:
            if img.width > img.height:
                core_dimensions = (
                    core_size,
                    round(img.height * (core_size / img.width)),
                )
            else:
                core_dimensions = (
                    round(img.width * (core_size / img.height)),
                    core_size,
                )
        else:
            core_dimensions = (core_size, core_size)

        # ensure that the core size is smaller than the img actual size
        if core_dimensions[0] > img.width or core_dimensions[1] > img.height:
            raise ValueError(
                'The target size cannot be larger than the original image size'
            )

        # resize the image to the core size using the Hamming filter since it
        # balances downscaling performance and quality
        return img.resize(core_dimensions, resample=Image.HAMMING)

    def _add_background(self, img: Image, target_size: int) -> Image:
        target_dimensions = (target_size, target_size)

        # generate background
        if self.background == 'transparent':
            background_img = Image.new('RGBA', target_dimensions, (0, 0, 0, 0))
        else:
            background_img = Image.new('RGBA', target_dimensions, self.background)

        # paste the img onto the background centered
        background_img.alpha_composite(
            img,
            (
                (background_img.width - img.width) // 2,
                (background_img.height - img.height) // 2,
            ),
        )
        return background_img


output_provider = BaseProvider()
register_output = partial(register, provider=output_provider)


@register_output('png', 'jpg', 'jpeg')
class StandardOutput(BaseOutput):
    pass
