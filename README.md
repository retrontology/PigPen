# PigPen

## Description
Python program for interfacing a raspberry pi with a cellular modem, ip camera, and other apparatus to construct a SMS based pig trap 

## Requirements

### Hardware
You will need the following hardware:
- A Raspberry Pi (Any version as long as it has the same GPIO)
- A fenced in area with a door set to be closed by releasing a solenoid
- A Fona 3G module
- An IP camera with an ethernet cable to directly connect to the Pi
- A motion detector
- A PiFace relay plus

### Camera requirements
You will need to set up `hostapd` on the Raspberry pi to act as a network for the IP camera

### Python Requirements
1. You will need to compile and install OpenCV on the Raspberry Pi with the Python extensions
2. Simply install the python requirements as follows:
    ```
    python3 -m pip install -r requirements.txt
    ```

## Setup

1. Wire up the components as shown in the `PigPenSchematic` schematic file
2. Set up the configuration YAML file
### `config.yml`
    ```
    owner:
    - The phone number the SIM card is registered to
    camera:
        relayNumber: The index you want to use for the camera
        relayAddress: The index of the relay the camera power is hooked up to
        cameraIP: The IP address of the camera on the network you set up with `hostapd`
        user: The username required to access the camera
        password: The password required to access the camera
        port: The port the camera uses
        channel: The channel of the camera you want to use. Usually 1
        subtype: The subtype of the camera you want to use. Usually 0
        maxBytes: The maximum amount of bytes you want to use before triggering the image culling process
    gate:
        relayNumber: The index you want to use for the gate
        relayAddress: The index of the relay the gate solenoid is hooked up to
        detectionPin: The pin the solenoid state detection is hooked up to
    motion:
        pin: The pin the motion detector is hooked up to
        delay: The minimum amount of time required to pass between detection events
    ```

3. I would also recommend setting up a systemd service file that runs the program on system boot

## Usage
```
python3 PigPen.py
```