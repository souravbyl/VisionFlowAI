import os
import argparse
from vfai.main_impl import engine_loader


def main():

    def valid_file(path):
        if not os.path.isfile(path):
            raise argparse.ArgumentTypeError(f"{path} is not a valid file")
        return path
    
    # loading config file
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=valid_file, required=True)
    args = parser.parse_args()

    engine_loader(config_file=args.config)
    


if __name__ == "__main__":
    main()
