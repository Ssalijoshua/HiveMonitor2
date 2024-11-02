import time
from hx711 import HX711

# Define the data and clock pins for the HX711
DT = 5  # Data pin (DT) connected to GPIO5
SCK = 6  # Clock pin (SCK) connected to GPIO6

# Initialize the HX711 object with DT and SCK pins
hx = HX711(DT, SCK)

# Define a function to read weight
def read_weight():
    # Set the reference unit to a suitable value after calibration
    hx.set_reference_unit(1)
    hx.reset()
    hx.tare()  # Tare the scale to zero
    
    print("Tare done. Place weight on the scale...")

    try:
        while True:
            # Read the current weight
            weight = hx.get_weight(5)  # Averages 5 readings for stability
            print(f"Weight: {weight:.2f} grams")  # Adjust formatting as needed

            time.sleep(1)  # Read the weight every 1 second
    except KeyboardInterrupt:
        print("Measurement stopped by the user.")
    finally:
        # Clean up the HX711
        hx.power_down()
        hx.power_up()

# Start reading weight
read_weight()
