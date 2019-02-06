# ADS-B Arrivals Alerter
## Summary:
A quick & dirty script to watch for arriving aircraft via the "dump1090" ADS-B and send a custom MQTT message to a local broker when specific aircraft arrive.  I didn't really write this for general consuption, but a couple of people asked to see it so here it is.  ;)  No warranty, use or modify as you see fit.

## Background
I have a house near South Lake Tahoe airport.  I'd like my home automation system to be aware of my arrival at that airport.  I already have an RaspberryPi with an RTL-SDR receiver running [FlightAware](https://www.flightaware.com/)'s [PiAware](https://flightaware.com/adsb/piaware/) fork of dump1090, so I put together this quick and dirty script to watch for arriving aircraft and send a custom MQTT message when it sees the ADS-B transponder of my own aircraft landing.

It logs all the "arriving" aircraft to a file, both for my own curiousity and for tuning the parameters for determining an "arrival" to the designated airport.

While running, it also displays a "Speed Record" on the console for the 5 fastest observed groundspeeds at three different altitude blocks because why not?  ;)

## Requirements:
- Python 2.x  (Because I'm running it on an ancient distro with no Python 3, LOL)
- paho-mqtt library
- geopy library
- A host running dump1090
- An MQTT broker

## Configuration
The top of adsb_arrivals.py file has the configuration paramaters.  They're pretty self explanitory, but I'll go over how the script determines arrivals:


First and foremost, the receiver has to be in a location that it can receive the aircraft within the physical proximity of the airport where you want to detect arrivals.


**LOC = (38.893888, -119.995333)** 


Set this to the Latitude and Longitude of the airport.  It will use the distance (in nautical miles) from this point to determine arrivals.

For an aircraft to "arrive" it first has to pass through an outer "arrival" area within a prescribed altitude.  At this point that aircraft is considered an aircraft of interest and watched for arrival.

**ARM_ALT = (8000, 10000)**

**ARM_NM = 15**

*ARM_ALT* is the lower and upper altitude boundaries of aircraft that might be arriving, within *ARM_NM* of the airport.  Aircraft above or below this range are ignored.

Once an aircraft has been flagged as an aircraft of interest, it will be considered to have arrived at the airport if it passes below the *ARR_ALT* altitude withing  *ARR_NM* nautical miles of the airport:

**ARR_ALT = 7800**

**ARR_NM = 8**

Note: If these altitudes seem high, it's because South Lake Tahoe airprot is at 6268 feet MSL.  These rules for an airport with a field elevation of, say, 750 MSL might look more like *ARM_ALT = (2500, 4500)* and *ARR_ALT = 2000* or similar.  Consider the flight environment and typical profile of both arriving and transient aircraft to find parameters that work best.

All arriving aircraft are logged to the *LOG* logfile.  Aircraft IDs that are in the *AIRCRAFT* list also trigger the MQTT message.  I didn't make the MQTT message a parameter because it contains a current timestamp, but you can change it as needed in the code.  (Search for "MQTT" in the code.)

BTW - to find the ADS-B "Mode S" hex ID for any US registered aircraft, just look the tail number up in the FAA aircraft registry. They've all been pre-assigned whether the aircraft is equipped with ADS-B Out or not:

https://registry.faa.gov/aircraftinquiry/NNum_Results.aspx?nNumberTxt=N673BF

The "Mode S Code (base 16 / hex)" is the code you're looking for.


*I'll be stunned if anyone else uses this, so shoot me a message and let me know!  LOL*
