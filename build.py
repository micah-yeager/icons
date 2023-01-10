import logging
import multiprocessing

import yaml

from icons import source_provider, input_provider, output_provider


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.WARNING)
# set up console logging
logging.basicConfig(
    format='%(asctime)s %(name)s %(levelname)s - %(message)s',
    level=logging.DEBUG,
)

# disable debug logging for Pillow
logging.getLogger('PIL').setLevel(logging.INFO)


def main(enable_multiprocessing=True):
    # open the icons-config.yaml file
    with open('icons-config.yaml', 'r') as f:
        icon_config = yaml.safe_load(f)

    for config in icon_config['sources']:
        LOGGER.debug('Processing source config: %s', config)
        source = source_provider.get(config)

        # use multiprocessing to speed up generation
        if enable_multiprocessing:
            with multiprocessing.Pool() as pool:
                pool.starmap(
                    process_input,
                    ((config, source, image_path) for image_path in source.get()),
                )
        else:
            for image_path in source.get():
                process_input(config, source, image_path)


def process_input(config, source, image_path):
    LOGGER.debug('Found %s image: %s', source.format, image_path)

    # pass input as a dict since that's what the builder expects
    input_ = input_provider.get(
        {'path': image_path, 'source': source, 'format': source.format}
    )

    for output_config in config['outputs']:
        # skip output if image not specified by any selectors
        selectors = output_config.get('selectors')
        if (
            selectors
            and selectors != '*'
            and input_.path.with_suffix('').name not in selectors
        ):
            LOGGER.debug(
                'Skipping output %s for %s since it is not in selectors',
                output_config,
                input_.path,
            )
            continue

        LOGGER.debug('Applying output config: %s', output_config)
        output = output_provider.get(output_config)

        for target_size, core_size in output.generate_sizes():
            LOGGER.debug(
                'Generating %s px image with a %s px core',
                target_size,
                core_size,
            )
            kwargs = {'color': output.color}
            if input_.is_vector:
                kwargs['size'] = core_size
            input_image = input_.ingest(**kwargs)

            # input_image will always be available, so ignore the warning
            try:
                # noinspection PyUnboundLocalVariable
                output_image, output_path = output.generate(
                    img=input_image,
                    input=input_,
                    target_size=target_size,
                    core_size=core_size,
                )
            except ValueError as e:
                LOGGER.warning(
                    f'{str(e)}, skipping %s px image for %s.', target_size, input_.path
                )
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
    parser.add_argument(
        '-v', '--verbose', action='store_true', help='enable verbose logging'
    )
    parser.add_argument(
        '-d', '--debug', action='store_true', help='enable debug logging'
    )
    parser.add_argument(
        '-s', '--single-processing', action='store_true', help='enable multiprocessing'
    )

    args = parser.parse_args()
    if args.verbose:
        LOGGER.setLevel(logging.INFO)
    if args.debug:
        LOGGER.setLevel(logging.DEBUG)

    # run the main function
    main(enable_multiprocessing=not args.single_processing)
