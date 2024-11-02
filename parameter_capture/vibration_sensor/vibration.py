import datetime
import smbus
from scipy import fftpack
import numpy as np
import sys

sys.path.append('/home/pi/Desktop/HiveMonitor2/')

from multimedia_capture.config import node_id
from multimedia_capture.config import timeString

# select the correct i2c bus for this revision of Raspberry Pi
revision = ([l[12:-1] for l in open('/proc/cpuinfo','r').readlines() if l[:8]=="Revision"]+['0000'])[0]
bus = smbus.SMBus(1 if int(revision, 16) >= 4 else 0)

# ADXL345 constants
EARTH_GRAVITY_MS2   = 9.80665
SCALE_MULTIPLIER    = 0.004

DATA_FORMAT         = 0x31 # This is used to set the sensitivity to 16g by accessing the register
BW_RATE             = 0x2C
POWER_CTL           = 0x2D

BW_RATE_1600HZ      = 0x0F # used for the bandwidth setting
BW_RATE_800HZ       = 0x0E
BW_RATE_400HZ       = 0x0D
BW_RATE_200HZ       = 0x0C
BW_RATE_100HZ       = 0x0B
BW_RATE_50HZ        = 0x0A
BW_RATE_25HZ        = 0x09

RANGE_2G            = 0x00
RANGE_4G            = 0x01
RANGE_8G            = 0x02
RANGE_16G           = 0x03

MEASURE             = 0x08
AXES_DATA           = 0x32

#other constants
samples_to_read = 10000
sample_rate = 1030

channel_1 = []
channel_2 = []
channel_3 = []

#####functions#####
def conv_str_tag(channel, tag):
    # Convert every channel from int to str, separated by a coma and adds tags at the beginning and end.
    n = len(channel)
    s_channel = '<' + tag + '>'
    for i in range(n-1):
        s_channel = s_channel + str(channel[i]) + ','
    s_channel = s_channel + str(channel[n-1]) + '</'+ tag + '>'
    return s_channel

#####Add tags and save on file#####
def record(channel_1, channel_2, channel_3, archive):
    str_channel = ''
    str_channel += conv_str_tag(channel_1, 'L1') + '\n'
    str_channel += conv_str_tag(channel_2, 'L2') + '\n'
    str_channel += conv_str_tag(channel_3, 'L3') + '\n'

    # Write to file
    arch = open("/home/pi/Desktop/HiveMonitor2/parameter_capture/vibration_sensor/text_file/"+archive, "w")
    arch.write(str_channel)
    arch.close()

class ADXL345:

    address = None

    def __init__(self, address = 0x53):        
        self.address = address
        self.setBandwidthRate(BW_RATE_1600HZ)
        self.setRange(RANGE_16G)
        self.enableMeasurement()

    def enableMeasurement(self):
        bus.write_byte_data(self.address, POWER_CTL, MEASURE)

    def setBandwidthRate(self, rate_flag):
        bus.write_byte_data(self.address, BW_RATE, rate_flag)

    # set the measurement range for 10-bit readings
    def setRange(self, range_flag):
        value = bus.read_byte_data(self.address, DATA_FORMAT)

        value &= ~0x0F;
        value |= range_flag;  
        value |= 0x08;

        bus.write_byte_data(self.address, DATA_FORMAT, value)
    
    # returns the current reading from the sensor for each axis
    #
    # parameter gforce:
    #    False (default): result is returned in m/s^2
    #    True           : result is returned in gs
    def getAxes(self, gforce = False):
        bytes = bus.read_i2c_block_data(self.address, AXES_DATA, 6)
        
        x = bytes[0] | (bytes[1] << 8)
        if(x & (1 << 16 - 1)):
            x = x - (1<<16)

        y = bytes[2] | (bytes[3] << 8)
        if(y & (1 << 16 - 1)):
            y = y - (1<<16)

        z = bytes[4] | (bytes[5] << 8)
        if(z & (1 << 16 - 1)):
            z = z - (1<<16)

        x = x * SCALE_MULTIPLIER 
        y = y * SCALE_MULTIPLIER
        z = z * SCALE_MULTIPLIER

        if gforce == False:
            x = x * EARTH_GRAVITY_MS2
            y = y * EARTH_GRAVITY_MS2
            z = z * EARTH_GRAVITY_MS2

        x = round(x, 4)
        y = round(y, 4)
        z = round(z, 4)

        return {"x": x, "y": y, "z": z}


def mainprog():
    adxl345 = ADXL345()
    print("START")
    print("Collecting sensor readings")
    sample_counter = 0;
    while(sample_counter < samples_to_read):
        axes = adxl345.getAxes(True)    #False = m/s^2, True = g
        #put the axes into variables
        x = axes['x']
        y = axes['y']
        z = axes['z']
    	
        channel_1.append(x)
        channel_2.append(y)
        channel_3.append(z)
    	
        sample_counter = sample_counter + 1;
    
    print("Amount of samples in channel 1: %s" %len(channel_1))
    print("Amount of samples in channel 2: %s" %len(channel_2))
    print("Amount of samples in channel 3: %s" %len(channel_3))
    
    #####Calculate average value for each channel#####
    num_data = len(channel_1)
    X = range(0, num_data, 1)
    vdc_channel_1 = 0
    vdc_channel_2 = 0
    vdc_channel_3 = 0
    for indice in X:
        vdc_channel_1 += channel_1[indice]
        vdc_channel_2 += channel_2[indice]
        vdc_channel_3 += channel_3[indice]
    vdc_channel_1 = vdc_channel_1 / num_data
    vdc_channel_2 = vdc_channel_2 / num_data
    vdc_channel_3 = vdc_channel_3 / num_data
    
    print("Vdc Channel 1: ",vdc_channel_1)
    print("Vdc Channel 2: ",vdc_channel_2)
    print("Vdc Channel 3: ",vdc_channel_3)
    
    #####Subtract DC offset#####
    '''
    This operation is used to remove the DC offset from each channel, 
    resulting in a signal with its average value centered around zero.
    '''
    for indice in X:
        channel_1[indice] -= vdc_channel_1
        channel_2[indice] -= vdc_channel_2
        channel_3[indice] -= vdc_channel_3
    
    
    #####calculation of fft#####
    
    channel_fft_x = []
    channel_fft_y = []
    channel_fft_z = []
    
    N = len(channel_1) # length of the signal
    T = 1.0 / sample_rate
    xf = np.linspace(0.0, 1.0/(2.0*T), int(N/2))
    
    yf1 = fftpack.fft(channel_1)
    channel_fft_x = 2.0/N * np.abs(yf1[:int(N/2)])
    
    yf2 = fftpack.fft(channel_2)
    channel_fft_y = 2.0/N * np.abs(yf2[:int(N/2)])
    
    yf3 = fftpack.fft(channel_3)
    channel_fft_z = 2.0/N * np.abs(yf3[:int(N/2)])
    
    #####saving to CSV file#####
    # Adding headers to the CSV file and writing the data
    archive = "vibration_"+str(node_id)+ "_" + str(timeString)+".csv"
    print("Saving to %s" %archive)
    arch = open("/home/pi/Desktop/HiveMonitor2/parameter_capture/vibration_sensor/fft_log/"+archive, "w")
    arch.write("Time,Amplitude_X,Amplitude_Y,Amplitude_Z,Frequency_X,Frequency_Y,Frequency_Z,FFT_Amplitude_X,FFT_Amplitude_Y,FFT_Amplitude_Z\n")
    num_data = len(xf)
    indice = 0

    # Write data to the CSV file
    while (indice < num_data):
        arch.write(f"{indice/sample_rate},{channel_1[indice]},{channel_2[indice]},{channel_3[indice]},{xf[indice]},{xf[indice]},{xf[indice]},{channel_fft_x[indice]},{channel_fft_y[indice]},{channel_fft_z[indice]}\n")
        indice = indice + 1

    arch.close()
    fname = archive
    print("Saving complete")
    print("END")
    return(fname)
   

if __name__ == "__main__":
    mainprog()