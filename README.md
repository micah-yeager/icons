# Icon generator

This is a small app to deterministically generate icons from various sources via config
file, since git doesn't work well with binary file formats.

## Usage

1. Install Miniconda
2. Create a new environment with `conda env create -f environment.yml`
3. Activate the environment with `conda activate icons`
4. Install Poetry dependencies with `poetry install`
5. Run the app with `python build.py`

Generated icons will appear in the `dist` directory as defined by the `icons-config.
yaml` file.

## Configuration

The `icons-config.yaml` file contains the configuration for the app. It is a list of
sources and their corresponding outputs, with various minor transforms.

## Contributing

Please create a merge request with any additional icons that should be generated
with the default config. If contributing images, please ensure they are:

1. Placed in the `src` directory
2. Are in the `svg` (preferred) or `png` format
3. If `png`:
    - Image must not contain a border or margin around the main content (blank space
      around the image)
    - Dimensions must be 512 pixels on the longest side
    - Background must be fully transparent
    - Foreground color must be black (`#000000`), transparency is ok
    - Image must not be upscaled from a smaller image
