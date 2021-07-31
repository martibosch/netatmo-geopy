"""Console script for netatmo_geopy."""

import fire


def help():
    print("netatmo_geopy")
    print("=" * len("netatmo_geopy"))
    print("Pythonic package to access Netatmo CWS data")


def main():
    fire.Fire({"help": help})


if __name__ == "__main__":
    main()  # pragma: no cover
