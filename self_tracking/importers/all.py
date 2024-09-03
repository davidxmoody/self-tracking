from .applehealth import main as applehealth_main
from .atracker import main as atracker_main
from .climbing import main as climbing_main
from .gpxroutes import main as gpxroutes_main
from .strong import main as strong_main

def main():
    applehealth_main()
    atracker_main()
    climbing_main()
    gpxroutes_main()
    strong_main()

if __name__ == "__main__":
    main()
