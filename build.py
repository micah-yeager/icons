import logging
import multiprocessing
import tempfile
from pathlib import Path

import yaml

from icons import source_provider, input_provider, output_provider


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.WARNING)
# set up console logging
logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)

# disable debug logging for other packages
logging.getLogger('PIL').setLevel(logging.INFO)
logging.getLogger('requests').setLevel(logging.INFO)


# defaults
SOURCE_FOLDER = Path('source')
OUTPUT_FOLDER = Path('output')
TEMP_FOLDER = Path(tempfile.gettempdir())


def main(
    config: str | Path,
    source_folder: str | Path = SOURCE_FOLDER,
    output_folder: str | Path = OUTPUT_FOLDER,
    single_processing: bool = False,
):
    # configure providers with base paths
    source_provider.base_path = Path(source_folder)
    # set the base_path for the output_provider down below instead of here to avoid multiprocessing issues

    # open the icons-config.yaml file
    with open(config, 'r') as f:
        icon_config = yaml.safe_load(f)

    for source_config in icon_config['sources']:
        # combine the default config with the source config
        defaulted_source_config = icon_config['source-defaults'] | source_config
        LOGGER.debug('Processing source config: %s', defaulted_source_config)
        source = source_provider.get(defaulted_source_config)

        # use multiprocessing to speed up generation
        if not single_processing:
            with multiprocessing.Pool() as pool:
                pool.starmap(
                    process_input,
                    (
                        (defaulted_source_config, source, image_path, icon_config['output-defaults'], output_folder)
                        for image_path in source.get()
                    ),
                )
        else:
            for image_path in source.get():
                process_input(
                    defaulted_source_config, source, image_path, icon_config['output-defaults'], output_folder
                )


def process_input(defaulted_source_config, source, image_path, output_config_defaults, output_folder):
    output_provider.base_path = Path(output_folder)
    LOGGER.debug('Found %s image: %s', source.format, image_path)

    # pass input as a dict since that's what the builder expects
    input_ = input_provider.get({'path': image_path, 'source': source, 'format': source.format})

    for output_config in defaulted_source_config['outputs']:
        defaulted_output_config = output_config_defaults | output_config

        # skip output if image not specified by any selectors
        selectors = defaulted_output_config.get('selectors')
        if selectors and selectors != '*' and input_.path.with_suffix('').name not in selectors:
            LOGGER.debug('Skipping output %s for %s since it is not in selectors', defaulted_output_config, input_.path)
            continue

        LOGGER.debug('Applying output config: %s', defaulted_output_config)
        output = output_provider.get(defaulted_output_config)

        for target_size, core_size in output.generate_sizes():
            LOGGER.debug('Generating %s px image with a %s px core', target_size, core_size)
            kwargs = {'color': output.color}
            if input_.is_vector:
                kwargs['size'] = core_size
            input_image = input_.ingest(**kwargs)

            # input_image will always be available, so ignore the warning
            try:
                # noinspection PyUnboundLocalVariable
                output_image, output_path = output.generate(
                    img=input_image, input=input_, target_size=target_size, core_size=core_size
                )

            except ValueError as e:
                LOGGER.warning(f'{str(e)}, skipping %s px image for %s.', target_size, input_.path)
                continue

            # save the generated image
            LOGGER.info('Saving generated image to %s', output_path)
            # ensure parent path folder has been created
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_image.save(output_path, format=output.format)


if __name__ == '__main__':
    # set up argument parsing
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='store_true', help='enable verbose logging')
    parser.add_argument('-d', '--debug', action='store_true', help='enable debug logging')
    parser.add_argument('-S', '--single-processing', action='store_true', help='enable multiprocessing')
    parser.add_argument('-c', '--config', default='icons-config.yaml', help='path to config file')
    parser.add_argument('-s', '--source-folder', default=SOURCE_FOLDER, help='path to source folder')
    parser.add_argument('-o', '--output-folder', default=OUTPUT_FOLDER, help='path to output folder')

    args = parser.parse_args().__dict__
    if args.pop('verbose'):
        LOGGER.setLevel(logging.INFO)
    if args.pop('debug'):
        LOGGER.setLevel(logging.DEBUG)

    # run the main function
    main(**args)
