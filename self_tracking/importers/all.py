from .atracker import main as atracker_main
from .routes import main as routes_main
from .strong import main as strong_main
from .layers import main as layers_main


def main():
    atracker_main()
    routes_main()
    strong_main()
    layers_main()


if __name__ == "__main__":
    main()
