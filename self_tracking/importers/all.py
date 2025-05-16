from .apple_health import main as apple_health_main
from .atracker import main as atracker_main
from .layers import main as layers_main
from .routes import main as routes_main
from .strong import main as strong_main
from .workouts import main as workouts_main


def main():
    atracker_main()
    workouts_main()
    routes_main()
    strong_main()
    apple_health_main()
    layers_main()


if __name__ == "__main__":
    main()
