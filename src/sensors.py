""" Define usage of sensors 

Cameras are not listed here because they are handled in cameras.py
"""

# Author: Roberto Buelvas

from threading import Thread
import random
import math
import time

import numpy as np
import pynmea2
import serial


# Basic functions


def getMultispectralReading(device, numValues=3, is_new_model=True):
    """ Get reading from multispectral sensor

    The multispectral sensors are ACS-430 or ACS-435 from Holland Scientific
    They work the same way except that the newer model (ACS-435) outputs the
    values of proxyDistance, proxyLAI, and proxyCCC, while the older model
    doesn't.
    Neither of the models outputs CI (Chlorophyll Index), but I chose to
    compute myself from the reflectance values given because it might be useful
    for my research.
    The code currently cannot handle the older model because of the way the
    variables dictionary is defined.
    Whenever an Exception ocurrs, a value of None is given to the output.
    numValues readings are taken and then averaged to produce the output.
    Units:
        CI: dimentionless
        NDRE: dimentionless
        NDVI: dimentionless
        *proxyDistance: cm
        *proxy LAI: dimentionless
        *proxy CCC: dimentionless
        Red-Edge: dimentionless
        NIR: dimentionless
        Red: dimentionless
    *Only available in new model
    """
    if is_new_model:
        values = np.empty((numValues, 9))
        values.fill(np.nan)
        for i in range(numValues):
            try:
                message = device.readline().strip().decode()
            except Exception as e:
                pass
            else:
                measurements = message.split(",")
                if len(measurements) == 8:
                    for j, measure in enumerate(measurements):
                        try:
                            aux = float(measure)
                        except Exception as e:
                            pass
                        else:
                            values[i, j + 1] = aux
        values[:, 0] = (values[:, 7] / values[:, 6]) - 1
    else:
        values = np.empty((numValues, 6))
        values.fill(np.nan)
        for i in range(numValues):
            try:
                message = device.readline().strip().decode()
            except Exception as e:
                pass
            else:
                measurements = message.split(",")
                for j, measure in enumerate(measurements):
                    try:
                        aux = float(measure)
                    except Exception as e:
                        pass
                    else:
                        # Index is j+1 because the first column is reserved for
                        # CI, which is manually computed
                        values[i, j + 1] = aux
        values[:, 0] = (values[:, 4] / values[:, 3]) - 1
    finalMeasurement = np.nanmean(values, axis=0)
    return finalMeasurement


def getUltrasonicReading(device, numValues=3):
    """ Get reading from ultrasonic sensor

    The ultrasonic sensor is ToughSonic14 from Senix
    Calibration for this sensor is hard-coded
    For some reason, when connected to the computer by a serial monitor,
    instead of creating new messages it seems to modify the same bits over and
    over. That is why the way this sensor is read differs from the others.
    Whenever an Exception ocurrs, a value of None is given to the output.
    numValues readings are taken and then averaged to produce the output.
    Units:
        Distance: mm
    """
    try:
        values = np.empty((numValues, 1))
        values.fill(np.nan)
        count = 0
        index = 0
        message = b""
        charList = [b"0", b"0", b"0", b"0", b"0"]
        while count < numValues:
            newChar = device.read()
            if newChar == b"\r":
                message = b"".join(charList)
                measurement = 0.00875 * (int(message) - 15.3)
                if measurement >= 0:
                    values[count, 0] = measurement
                message = b""
                index = 0
                count += 1
            else:
                charList[index] = newChar
                index += 1
                if index >= 5:
                    index = 0
    except Exception as e:
        print("Skipped error in Ultrasonic reading")
        print(str(e))
        return np.array([np.nan])
    else:
        return np.nanmean(values, axis=0)


def getGPSReading(device, numValues=2):
    """ Get reading from GPS sensor

    The GPS receiver is 19x HVS from Garmin
    The sensor uses NMEA 0183 encoding for the messages
    Most of the measurements are ignored and just longitude and latitude are
    kept
    Whenever an Exception ocurrs, a value of None is given to the output.
    numValues readings are taken and then averaged to produce the output.
    Units:
        longitude, latitude: °
    """
    count = 0
    values = np.empty((numValues, 2))
    values.fill(np.nan)
    while count < numValues:
        try:
            message = device.readline().strip().decode()
            parsedMessage = pynmea2.parse(message)
            if message[0:6] == "$GPGGA":
                count += 1
                # Both longitude and latitude being 0 simultaneously is way
                # more likely to be a blank measurement than actually that
                # point
                if (parsedMessage.longitude != 0) or (parsedMessage.latitude != 0):
                    values[count, 0] = parsedMessage.longitude
                    values[count, 1] = parsedMessage.latitude
        except Exception as e:
            pass
    # Sometimes "Mean of empty slice" error happens
    finalMeasurement = np.nanmean(values, axis=0)
    return finalMeasurement


def getEnvironmentalReading(device, numValues=3):
    """ Get reading from environmental sensor

    The environmental sensor is DAS43X from Holland Scientific.
    Whenever an Exception ocurrs, a value of None is given to the output.
    numValues readings are taken and then averaged to produce the output.
    Units:
        Canopy temperature: °C
        Relative humidity: %
        Air temperature: °C
        Incident PAR: μmol quanta m**−2 s**−1
        Reflected PAR: μmol quanta m**−2 s**−1
        Atmospheric pressure: kPa
    """
    values = np.empty((numValues, 6))
    values.fill(np.nan)
    for i in range(numValues):
        try:
            message = device.readline().strip().decode()
        except Exception as e:
            print("Skipped error in Environmental reading")
            print(str(e))
        else:
            measurements = message.split(",")
            if len(measurements) == 8:
                # Only care about the first 6 measurements, as the rest are not used
                for j, measure in enumerate(measurements[:6]):
                    try:
                        aux = float(measure)
                    except Exception as e:
                        pass
                    else:
                        values[i, j] = aux
    finalMeasurement = np.nanmean(values, axis=0)
    return finalMeasurement


# Dictionaries

# Dict to hold which sensor is the source for each measured variable
# m >> Multispectral
# u >> Ultrasonic
# g >> GPS
# e >> Environmental
# The order needs to match that of the getXReading functions below
variables = {
    "m": [
        "CI",
        "NDRE",
        "NDVI",
        "proxy Distance",
        "proxy LAI",
        "proxy CCC",
        "Red-Edge",
        "NIR",
        "Red",
    ],
    "u": ["Distance"],
    "g": [
        "Longitude",
        "Latitude",
        "GPS_X",
        "GPS_Y",
        "Vehicle_X",
        "Vehicle_Y",
        "Heading",
        "Velocity",
        "Time",
    ],
    "e": [
        "Canopy Temperature",
        "Air Temperature",
        "Humidity",
        "Reflected PAR",
        "Incident PAR",
        "Pressure",
    ],
}


# Dict to hold which function should be used to read from each type of sensor
targets = {
    "m": getMultispectralReading,
    "u": getUltrasonicReading,
    "g": getGPSReading,
    "e": getEnvironmentalReading,
}


# Classes


class SerialSensor:
    """ Wrapper class to control serial.Serial instances
    
    Attr:
        port (str): Name of port in 'COM3' format for Windows
        label (str): Label indicating sensor in the 'mR1' or 'gL' format
        read_function (function): Function used to read from sensor
        baudrate (int): Baudrate for serial communication. Default is 38400
        value (np.ndarray): Latest reading from the sensor
        device (serial.Serial): Core object that represents the sensor
        thread (threading.Thread): Thread used to read constantly without blocking the
            main operation of the code
        is_connected (bool): Indicator to now if connection with the port has already
            been established
        end_flag (bool): Flag to indicate when thread should end its operation
    """

    def __init__(self, port, label, baudrate=38400):
        """ Initialize attributes """
        self.port = port
        self.label = label
        self.read_function = targets[label[0]]
        self.baudrate = baudrate
        self.value = None
        self.device = None
        self.thread = None
        self.is_connected = False
        self.end_flag = True

    def open(self):
        """ Connect to port and define thread

        Returns True or False depending if it succeeds
        """
        if not self.is_connected:
            try:
                self.device = serial.Serial(self.port, self.baudrate, timeout=1)
                self.end_flag = False
                self.thread = Thread(target=self.update, name=self.label, daemon=False)
                self.thread.start()
            except Exception as e:
                print(str(e))
                self.device = None
                self.thread = None
                return False
            else:
                self.is_connected = True
                return True
        else:
            return None

    def close(self):
        """ End communication with port and kill thread

        Assumed to always succeed
        """
        if self.is_connected:
            self.end_flag = True
            if self.thread is not None:
                if self.thread.is_alive():
                    self.thread.join()
                self.thread = None
            if self.device is not None:
                if self.device.is_open:
                    self.device.close()
                self.device = None
            self.is_connected = False

    def read(self):
        """ Return latest reading """
        if self.is_connected:
            return self.value
        else:
            return None

    def update(self):
        """ Get new reading
        
        Target function of the thread """
        while not self.end_flag:
            self.value = self.read_function(self.device)


class SensorHandler:
    """ Class to control multiple SerialSensor objects at once 
    
    Attr:
        sensors (dict): Keys are labels in the 'mL1' or 'gR' format. Values are
            SerialSensor objects
        current_measurements (dict): Keys are labels in the 'mL1' or 'gR' format. Values
            are np.ndarray with the latest readings from each sensor
        previous_measurements (dict): Keys are labels in the 'mL1' or 'gR' format. Values
            are np.ndarray with the second to last readings from each sensor
        GPS_constants (list): Values used to project GPS reading to planar coordinates
            [origin_time, origin_longitude, origin_latitude, F_lon, F_lat]
    """

    def __init__(self):
        """ Define empty attributes """
        self.sensors = {}
        self.measurements = {}
        self.previous_measurements = {}
        self.GPS_constants = None

    def add(self, port, label):
        """ Appends items to the sensors dict """
        new_sensor = SerialSensor(port, label)
        self.sensors[label] = new_sensor

    def openAll(self):
        """ Connects to all the sensors added so far 

        If at some point it encounters an error, it will cancel the operation and
        disconnect from the sensor that it had connected until that point.
        Returns True if operation was successful, False otherwise.      
        """
        labels = list(self.sensors.keys())
        for i, label in enumerate(labels):
            try:
                success = self.sensors[label].open()
                if label[0] == "g":
                    self.setupGPS(label)
            except Exception as e:
                print(label)
                print(str(e))
                break
            else:
                if not success:
                    print(label)
                    break
        # This condition would only be True if is_working was True for all devices
        if self.sensors[labels[-1]].is_connected:
            return True
        else:
            for j in range(i):
                self.sensors[labels[j]].close()
            return False

    def closeAll(self):
        """ Disconnect from all sensors """
        for sensor in self.sensors.values():
            sensor.close()

    def simulate(self, label, num_readings, cfg):
        """ Produces output that represents the readings of a sensor 
        
        For GPS, it simulates a predefined curve. For every other sensor, it produces
            random numbers
        Args:
            label (str): Label in 'mL1' or 'gR' format indicating which sensor to read
            num_readings(int): Number of readings performed so far. Only relevant for GPS
                readings
            cfg (wx.Config): Only relevant for GPS readings. Interface to config file of
                the wx App. Contains values like distances between sensors used for
                processing the GPS reading
        Return:
            reading (np.ndarray): Simulated reading from sensor
        """
        self.previous_measurements = self.measurements.copy()
        if label[0] == "g":
            reading = [
                -73.939830 + 0.0001 * num_readings,
                45.423804 + 0.0001 * num_readings,
            ]
            # reading = [
            #     -73.939830 + 0.0001 * random.random(),
            #     45.423804 + 0.0001 * random.random(),
            # ]
            # reading = [
            #     -73.939830 + 0.0001,
            #     45.423804 + 0.0001,
            # ]
            reading = processGPS(
                reading,
                label,
                self.GPS_constants,
                self.previous_measurements,
                num_readings,
                cfg,
            )
        else:
            reading = []
            for i in range(len(variables[label[0]])):
                reading.append(random.random())
        for i, variable_name in enumerate(variables[label[0]]):
            self.measurements[label + "/" + variable_name] = reading[i]
        return np.array(reading)

    def read(self, label, num_readings, cfg=None):
        """ Produces the readings of a sensor 
        
        Args:
            label (str): Label in 'mL1' or 'gR' format indicating which sensor to read.
                If the label hasn't been added previously, the reading is None
            num_readings(int): Number of readings performed so far. Only relevant for GPS
                readings
            cfg (wx.Config): Only relevant for GPS readings. Interface to config file of
                the wx App. Contains values like distances between sensors used for
                processing the GPS reading
        Return:
            reading (np.ndarray): Reading from sensor
        """
        self.previous_measurements = self.measurements.copy()
        if label in self.sensors.keys():
            reading = self.sensors[label].read()
            if label[0] == "g":
                if cfg is not None:
                    reading = processGPS(
                        reading,
                        label,
                        self.GPS_constants,
                        self.previous_measurements,
                        num_readings,
                        cfg,
                    )
                    for i, variable_name in enumerate(variables[label[0]]):
                        self.measurements[label + "/" + variable_name] = reading[i]
            else:
                for i, variable_name in enumerate(variables[label[0]]):
                    self.measurements[label + "/" + variable_name] = reading[i]
            return reading
        else:
            return None

    def hasLabel(self, label):
        """ Check if a specific sensor has been added before """
        return label in self.sensors.keys()

    def setupGPS(self, label):
        """ Produce GPS constants to convert to planar coordinates
        
        Before finding the values of the constants, it repeats reading from the sensor
            until a 'good' reading happens i.e. no NaN values
        """
        reading = np.array([np.nan, np.nan])
        while True:
            reading = self.read(label, 0, None)
            if reading is not None:
                if not any(np.isnan(reading)):
                    break
        self.GPS_constants = setupGPSProjection(reading)


# Other functions


def setupGPSProjection(reading):
    """ Use 1 GPS reading to compute constants for projection to planar coordinates 
    
    The elevation has been temporarily hard-coded, but it should be made
    adjustable as a setting, if not read from the GPS
    """
    origin_time = time.time()
    origin_longitude = math.pi * reading[0] / 180
    origin_latitude = math.pi * reading[1] / 180
    a = 6378137  # Earth's semimajor axis
    b = 6356752.3142  # Earth's semiminor axis
    h = 20  # Current elevation over sea level
    c = math.sqrt(
        (a * math.cos(origin_latitude)) ** 2 + (b * math.sin(origin_latitude)) ** 2
    )
    F_lon = math.cos(origin_latitude) * ((a ** 2 / c) + h)
    F_lat = ((a * b) ** 2 / c ** 3) + h
    return [origin_time, origin_longitude, origin_latitude, F_lon, F_lat]


def processGPS(someValue, label, GPS_constants, previous_measurements, num_readings, cfg):
    """ Estimates heading and velocity from GPS readings

    Project the measurements to planar coordinates and use the immediately previous
    measurement to estimate heading and velocity
    The reported X and Y values are of the vehicle defined as the middle
    point of the toolbar that holds the sensors
    """
    origin_time = GPS_constants[0]
    origin_longitude = GPS_constants[1]
    origin_latitude = GPS_constants[2]
    F_lon = GPS_constants[3]
    F_lat = GPS_constants[4]
    new_longitude = math.pi * someValue[0] / 180
    new_latitude = math.pi * someValue[1] / 180
    new_time = time.time() - origin_time
    gps_x = (new_longitude - origin_longitude) * F_lon
    gps_y = (new_latitude - origin_latitude) * F_lat
    if num_readings == 0:
        old_time = 0
        old_x = 0
        old_y = 0
    else:
        old_time = previous_measurements[label + "/Time"]
        old_x = previous_measurements[label + "/GPS_X"]
        old_y = previous_measurements[label + "/GPS_Y"]
    heading_radians = math.atan2(gps_y - old_y, gps_x - old_x)
    velocity = math.sqrt((gps_x - old_x) ** 2 + (gps_y - old_y) ** 2) / (
        new_time - old_time
    )
    heading = 180 * heading_radians / math.pi
    if (label[1] == "L") and cfg.HasEntry("DGLX") and cfg.HasEntry("DGLY"):
        dgx = cfg.ReadFloat("DGLX") / 100
        dgy = cfg.ReadFloat("DGLY") / 100
        vehicle_x = (
            gps_x + dgx * math.sin(heading_radians) - dgy * math.cos(heading_radians)
        )
        vehicle_y = (
            gps_y - dgx * math.cos(heading_radians) - dgy * math.sin(heading_radians)
        )
    elif (label[1] == "R") and cfg.HasEntry("DGRX") and cfg.HasEntry("DGRY"):
        dgx = cfg.ReadFloat("DGRX") / 100
        dgy = cfg.ReadFloat("DGRY") / 100
        vehicle_x = (
            gps_x - dgx * math.sin(heading_radians) - dgy * math.cos(heading_radians)
        )
        vehicle_y = (
            gps_y + dgx * math.cos(heading_radians) - dgy * math.sin(heading_radians)
        )
    else:
        return None
    return np.array(
        [
            someValue[0],
            someValue[1],
            gps_x,
            gps_y,
            vehicle_x,
            vehicle_y,
            heading,
            velocity,
            new_time,
        ]
    )


# Deprecated
def openPort(port, label, baudrate):
    """ Utility function to connect to serial device """
    device = serial.Serial(port, baudrate)
    device_thread = Thread(target=updateSensor, name=label, args=(label,), daemon=False)
    return device


# Deprecated
def getSensorReading(device_port, label, is_device_ready=True):
    """ Utility function to select proper function given label

    Args:
        device_port (Serial or str): Either pointer to serial device or name of
                                     port. is_device_ready needs to match
        label (str): Label of the style mL1 or gR to know which type of sensor
                     is being used
        is_device_ready (boolean): If True, device_port should be a serial
                                   device e.g. output from openPort(). If
                                   False, device_port should be the name of the
                                   port e.g. 'COM3' in Windows
    Returns:
        reading (list): Output from one of the get{X}Reading() functions
    """
    if is_device_ready:
        device_port.reset_input_buffer()
        if label[0] == "m":
            return getMultispectralReading(device_port)
        if label[0] == "u":
            return getUltrasonicReading(device_port)
        if label[0] == "g":
            return getGPSReading(device_port)
        if label[0] == "e":
            return getEnvironmentalReading(device_port)
    else:
        if label[0] == "m":
            return getOpenMultispectralReading(device_port)
        if label[0] == "u":
            return getOpenUltrasonicReading(device_port)
        if label[0] == "g":
            return getOpenGPSReading(device_port)
        if label[0] == "e":
            return getOpenEnvironmentalReading(device_port)
