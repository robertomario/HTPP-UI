""" Define usage of sensors """

# Author: Roberto Buelvas

from threading import Thread
import math
import time

import numpy as np
import pynmea2
import serial


targets = {
    "m": getMultispectralReading,
    "u": getUltrasonicReading,
    "g": getGPSReading,
    "e": getEnvironmentalReading,
}


class SerialSensor:
    def __init__(self, port, label, baudrate=38400):
        self.port = port
        self.label = label
        self.target = targets[label[0]]
        self.baudrate = baudrate
        self.device = None
        self.thread = None
        self.is_connected = False

    def openPort(self):
        """ 
        Returns True or False depending if it succeeds
        """
        try:
            self.device = serial.Serial(self.port, self.baudrate)
            self.thread = Thread(target=self.target, daemon=False)
        except Exception as e:
            return False
        else:
            self.is_connected = True
            return True

    def closePort(self):
        """ 
        Assumed to always succeed. What could go wrong?
        """
        if self.thread is not None:
            self.thread.join()
            self.thread = None
        if self.device in not None:
            self.device.close()
            self.device =None
        self.is_connected = False

class SerialHandler:
    def __init__(self):
        self.sensors = []

    def openAllPorts(self):
        for i, sensor in enumerate(self.sensors):
            is_working = sensor.openPort()
            if not is_working:
                break
        # This condition would only be True if is_working was True for all devices
        if self.sensors[-1].is_connected:
            return True
        else:
            for j in range(i):
                self.sensors[j].closePort()
            return False
    
    def addSerialSensor(self, port, label):
        self.sensors.append(SerialSensor(port, label))

    def startAllSensors(self):





def openPort(port, label, baudrate):
    """ Utility function to connect to serial device """
    device = serial.Serial(port, baudrate)
    device_thread = Thread(target=updateSensor, name=label, args=(label,), daemon=False)
    return device


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
        count = 0
        finalMeasurement = 0
        index = 0
        message = b""
        charList = [b"0", b"0", b"0", b"0", b"0"]
        while count < numValues:
            newChar = device.read()
            if newChar == b"\r":
                count += 1
                message = b"".join(charList)
                measurement = 0.003384 * 25.4 * int(message)
                finalMeasurement += measurement
                message = b""
                index = 0
            else:
                charList[index] = newChar
                index += 1
                if index >= 5:
                    index = 0
    except Exception as e:
        return np.array([np.nan])
    else:
        return np.array([finalMeasurement / numValues])


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
            print("Error in ")
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


# getOpen functions are not made to handle Exceptions yet
def getOpenMultispectralReading(port, numValues=10, is_new_model=True):
    """ Get reading from multispectral sensor

    These functions differ from the get{X}Reading() in that they open and close
    the port with the serial device themselves. Sometimes this is preferred to
    avoid errors that could be raised while the ports are open
    """
    serialCropCircle = serial.Serial(port, 38400)
    if is_new_model:
        ci = []
        ndre = []
        ndvi = []
        proxyDistance = []
        proxyLAI = []
        proxyCCC = []
        redEdge = []
        nir = []
        red = []
        for i in range(numValues):
            message = serialCropCircle.readline().strip().decode()
            measurements = message.split(",")
            measurements = [float(i) for i in measurements]
            ci.append((measurements[6] / measurements[5]) - 1)
            ndre.append(measurements[0])
            ndvi.append(measurements[1])
            proxyDistance.append(measurements[2])
            proxyLAI.append(measurements[3])
            proxyCCC.append(measurements[4])
            redEdge.append(measurements[5])
            nir.append(measurements[6])
            red.append(measurements[7])
        finalMeasurement = [
            sum(ci),
            sum(ndre),
            sum(ndvi),
            sum(proxyDistance),
            sum(proxyLAI),
            sum(proxyCCC),
            sum(redEdge),
            sum(nir),
            sum(red),
        ]
    else:
        ci = []
        ndre = []
        ndvi = []
        redEdge = []
        nir = []
        red = []
        for i in range(numValues):
            message = serialCropCircle.readline().strip().decode()
            measurements = message.split(",")
            measurements = [float(i) for i in measurements]
            ci.append((measurements[3] / measurements[2]) - 1)
            ndre.append(measurements[0])
            ndvi.append(measurements[1])
            redEdge.append(measurements[2])
            nir.append(measurements[3])
            red.append(measurements[4])
        finalMeasurement = [
            sum(ci),
            sum(ndre),
            sum(ndvi),
            sum(redEdge),
            sum(nir),
            sum(red),
        ]
    finalMeasurement = [measure / numValues for measure in finalMeasurement]
    serialCropCircle.close()
    return finalMeasurement


def getOpenUltrasonicReading(port, numValues=10):
    """ Get reading from ultrasonic sensor """
    serialUltrasonic = serial.Serial(port, 38400)
    count = -1
    finalMeasurement = 0
    index = 0
    message = b""
    charList = [b"0", b"0", b"0", b"0", b"0"]
    while count < numValues:
        newChar = serialUltrasonic.read()
        if newChar == b"\r":
            count += 1
            message = b"".join(charList)
            measurement = 0.003384 * 25.4 * int(message)
            finalMeasurement += measurement
            message = b""
            index = 0
        else:
            charList[index] = newChar
            index += 1
            if index > 5:
                index = 0
    serialUltrasonic.close()
    return [finalMeasurement / numValues]


def getOpenGPSReading(port, numValues=3):
    """ Get reading from GPS sensor """
    serialGPS = serial.Serial(port, 9600)
    i = 0
    while i < numValues:
        message = serialGPS.readline().strip().decode()
        if message[0:6] == "$GPGGA" or message[0:6] == "$GPGLL":
            i += 1
            parsedMessage = pynmea2.parse(message)
            finalMeasurement = [parsedMessage.longitude, parsedMessage.latitude]
    serialGPS.close()
    return finalMeasurement


def getOpenEnvironmentalReading(port, numValues=10):
    """ Get reading from environmental sensor """
    serialDAS = serial.Serial(port, 38400)
    canopyT = []
    humidity = []
    airT = []
    incidentPAR = []
    reflectedPAR = []
    AtmP = []
    for i in range(numValues):
        message = serialDAS.readline().strip().decode()
        measurements = message.split(",")
        measurements = [float(i) for i in measurements]
        canopyT.append(measurements[0])
        humidity.append(measurements[1])
        airT.append(measurements[2])
        incidentPAR.append(measurements[3])
        reflectedPAR.append(measurements[4])
        AtmP.append(measurements[5])
    finalMeasurement = [
        sum(canopyT),
        sum(humidity),
        sum(airT),
        sum(incidentPAR),
        sum(reflectedPAR),
        sum(AtmP),
    ]
    finalMeasurement = [measure / numValues for measure in finalMeasurement]
    serialDAS.close()
    return finalMeasurement


def setupGPSProjection(reading):
    """ Use 1 GPS reading to compute constants for projection to planar coordinates 
    
    The elevation has been temporarily hard-coded, but it should be made
    adjustable as a setting
    """
    origin_time = time.time()
    origin_latitude = math.pi * reading[1] / 180
    origin_longitude = math.pi * reading[0] / 180
    a = 6378137  # Earth's semimajor axis
    b = 6356752.3142  # Earth's semiminor axis
    h = 20  # Current elevation over sea level
    c = math.sqrt(
        (a * math.cos(origin_latitude)) ** 2 + (b * math.sin(origin_latitude)) ** 2
    )
    F_lon = math.cos(origin_latitude) * ((a ** 2 / c) + h)
    F_lat = ((a * b) ** 2 / c ** 3) + h
    return [origin_time, origin_longitude, origin_latitude, F_lon, F_lat]


def processGPS(
    someValue, label, GPS_constants, num_readings, previous_measurements, cfg
):
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
    if (label[1] == "L") and cfg.HasEntry("DGLX"):
        dgx = cfg.ReadFloat("DGLX") / 100
        dgy = cfg.ReadFloat("DGLY") / 100
        vehicle_x = (
            gps_x + dgx * math.sin(heading_radians) - dgy * math.cos(heading_radians)
        )
        vehicle_y = (
            gps_y - dgx * math.cos(heading_radians) - dgy * math.sin(heading_radians)
        )
    elif (label[1] == "R") and cfg.HasEntry("DGRX"):
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
