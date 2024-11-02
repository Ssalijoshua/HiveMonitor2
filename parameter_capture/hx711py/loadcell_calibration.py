#!/usr/bin/env python3

import time
import sys
import RPi.GPIO as GPIO
from hx711 import HX711
 

#supress GPIO warnings
GPIO.setwarnings(False)

# GPIO pins for HX711
DOUT = 2
SCK = 3

# Initialize HX711
hx = HX711(DOUT, SCK)

# Calibration parameters
cal_weight = 5000  # Known weight in grams
scale_factor = 1.0
scale_offset = 1

def clean_and_exit():
    print("Cleaning up...")
    GPIO.cleanup()
    print("Bye!")
    sys.exit()

def reset_scale():
    hx.set_reference_unit(scale_factor)
    hx.reset()
    hx.tare()

def calibrate_scale():
    global scale_factor, scale_offset
    sum = 0.0
    times = 10
    for _ in range(times):
        raw_weight = hx.get_weight(1)
        sum += (raw_weight / cal_weight)
        print(".", end="", flush=True)
        time.sleep(0.5)
    scale_factor = sum / times
    scale_offset = hx.get_offset()
    print("\nOffset:", scale_offset, "ScaleFactor:", scale_factor)
    print("Calibration finished. Remove weight!")

def measure():
    return hx.get_weight(10) / 1000.0

def menu():
    print("\n1 - Set known weight | current:", cal_weight, "g")
    print("2 - Calibrate")
    print("3 - Measure")
    print("q - Show menu")
    print("Choice (1-3): ", end="", flush=True)

def main():
    global cal_weight
    hx.set_reading_format("MSB", "MSB")
    hx.set_reference_unit(1)
    hx.reset()
    hx.tare()
    print("Tare done! Add weight now...")

    menu()
    while True:
        try:
            choice = input().strip()
            if choice == "1":
                cal_weight = float(input("Known weight (g): ").strip())
                print(cal_weight, "g")
            elif choice == "2":
                reset_scale()
                print("Place weight and enter 'w' to calibrate.")
                if input().strip().lower() == 'w':
                    calibrate_scale()
                menu()
            elif choice == "3":
                reset_scale()
                hx.set_offset(scale_offset)
                print("\nOffset:", scale_offset, "ScaleFactor:", scale_factor)
                while True:
                    print(measure(), "kg")
                    time.sleep(1)
            elif choice == "q":
                menu()
            else:
                menu()
        except (KeyboardInterrupt, SystemExit):
            clean_and_exit()

if __name__ == "__main__":
    main()
