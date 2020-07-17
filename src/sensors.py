""" Define usage of sensors """

# Author: Roberto Buelvas

import pynmea2
import serial


def openPort(port, label):
    """ Utility function to connect to serial device """
    if label[0] == "g":
        baudrate = 9600
    else:
        baudrate = 38400
    device = serial.Serial(port, baudrate)
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


def getMultispectralReading(device, numValues=10, is_new_model=True):
    """ Get reading from multispectral sensor

    The multispectral sensors are ACS-430 or ACS-435 from Holland Scientific
    They work the same way except that the newer model (ACS-435) outputs the
    values of proxyDistance, proxyLAI, and proxyCCC, while the older model
    doesn't.
    Neither of the models outputs CI (Chlorophyll Index), but I chose to
    compute myself from the reflectance values given because it might be useful
    for my research.
    The code currently cannot handle the older model because of the way the
    variables dictionary is defined
    Units:
        proxyDistance: cm
        default: dimentionless
    """
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
            message = device.readline().strip().decode()
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
            message = device.readline().strip().decode()
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
    return finalMeasurement


def getUltrasonicReading(device, numValues=10):
    """ Get reading from ultrasonic sensor

    The ultrasonic sensor is ToughSonic14 from Senix
    Calibration for this sensor is hard-coded
    For some reason, when connected to the computer by a serial monitor,
    instead of creating new messages it seems to modify the same bits over and
    over. That is why the way this sensor is read differs from the others.
    Units:
        mm
    """
    count = -1
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
            if index > 5:
                index = 0
    return [finalMeasurement / numValues]


def getGPSReading(device, numValues=3):
    """ Get reading from GPS sensor

    The GPS receiver is 19x HVS from Garmin
    The sensor uses NMEA 0183 encoding for the messages
    Most of the measurements are ignored and just longitude and latitude are
    kept
    Units:
        longitude, latitude: °
    """
    i = 0
    while i < numValues:
        message = device.readline().strip().decode()
        if message[0:6] == "$GPGGA" or message[0:6] == "$GPGLL":
            i += 1
            parsedMessage = pynmea2.parse(message)
            finalMeasurement = [parsedMessage.longitude, parsedMessage.latitude]
    return finalMeasurement


def getEnvironmentalReading(device, numValues=10):
    """ Get reading from environmental sensor

    The environmental sensor is DAS43X from Holland Scientific
    Units:
        Canopy temperature: °C
        Relative humidity: %
        Air temperature: °C
        Incident PAR: μmol quanta m**−2 s**−1
        Reflected PAR: μmol quanta m**−2 s**−1
        Atmospheric pressure: kPa
    """
    canopyT = []
    humidity = []
    airT = []
    incidentPAR = []
    reflectedPAR = []
    AtmP = []
    for i in range(numValues):
        message = device.readline().strip().decode()
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
    return finalMeasurement


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
