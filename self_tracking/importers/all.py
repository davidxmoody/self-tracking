from .atracker import main as atracker_main
from .gpxroutes import main as gpxroutes_main
from .strong import main as strong_main


def main():
    atracker_main()
    gpxroutes_main()
    strong_main()


if __name__ == "__main__":
    main()
