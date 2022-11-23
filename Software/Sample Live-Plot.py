# -*- coding: utf-8 -*-

import serial
import serial.tools.list_ports
import re
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import time
import datetime
from multiprocessing import Process, Queue, Event
import csv
from pathlib import Path

HARDWARE_ID = "2341:8037"
DEVICE_ID = "PocketLoCSensor"
LINE_TERMINATOR = "\r\n"
BAUDRATE = 9600
TIMEOUT = 1 #s

SAMPLE_TIME = 10 #ms

gain_setting = 10 #this is adjusted by auto gain

connection = None
error_flag = False
output_stream = None


def connect_serial():
    ports = serial.tools.list_ports.comports()
    
    conn = None
    for port, desc, hwid in sorted(ports):
        if HARDWARE_ID in hwid:            
            try:
                conn = serial.Serial(port=port, baudrate=BAUDRATE, timeout=TIMEOUT)
            except serial.serialutil.SerialException:
                #Port may be in use
                print("Port in use. This may be due to an aborted connection. If no other matching port is found try un- and replugging the device.")
                continue
            
            conn.write(str.encode("ID" + LINE_TERMINATOR))
            read_id = conn.readline().decode('utf-8').replace(LINE_TERMINATOR, "")
            if read_id == DEVICE_ID:
                break
            else:
                conn.close()
                conn = None
            
    
    if conn is None or not conn.is_open:
        raise Exception("Could not find valid device to connect to.")
    
    return conn
    
def disconnect_serial():
    stop_command = "STOP"
    send_command(stop_command)
    read_response(1);
    
    connection.readlines() #flush anything in the buffer
    connection.close()
    
def send_command(command):
    #send a command on the active serial connection
    
    byte_cmd = str.encode(command + LINE_TERMINATOR)
    connection.write(byte_cmd)
    
def read_response(n):
    # Get n lines of data from the serial connection and strip line terminator
    for i in range(n):
        raw = connection.readline().decode('utf-8')
        print(raw.replace(LINE_TERMINATOR, ""))
    
    
def start_streaming():
    start_command = "START"
    send_command(start_command)
    
    read_response(1)
    

def initialise():
    #Configure the sensor according to our needs
    
    connection.readlines() #Flush initialisation stuff from buffer
    
    """
    Set the active photodiodes
    Command: "Cxxxxxxxxx"
    Each photodiode (x) can either be activated (1) or deactviated (0) according to the list
    F1, F2, F3, F4, F5, F6, F7, F8, CLEAR, NIR
    Only 6 photodiodes can be active at once.
    """
    
    #Use F1, F3, F5, F7, F8, NIR
    mux_command = "C1010101101"
    send_command(mux_command)
    
    read_response(3)
    
    
    """
    Set the sample time in ms. This applies to single channel conversion.
    Command: "Txxx"
    The value can be 1...182ms. Actual sample duration reported on serial connection will be 4*sample_time.
    """
    
    #Set to 5ms - net sample rate of 50 Sa/s
    time_command = "T" + str(SAMPLE_TIME)
    send_command(time_command)
    
    read_response(1)
    
    """
    Auto-adjust input gain. The input gain can be set from 0.5x to 512x.
    This initialisation assumes the maximal brightness (i.e. no droplet in microfluidic channel) and sets
    the maximal gain value that does not produce a saturation error.
    Set gain command: "Gxx"
    XX corresponds to the gain levels 0...10, where 0 = 0.5x, 1 = 1x, 2 = 4x, etc...
    """
    
    auto_gain()
    
def auto_gain():
    #Set the gain to the highest value that will not produce a saturation error.
    
    for i in range(11):
        #iterate through the gain settings until we have no error
        global gain_setting
        gain_setting = 10-i #start with the maximal setting
        
        gain_command = "G" + str(gain_setting)
        send_command(gain_command)
        
        read_response(1)
        
        start_streaming()
        
        sat_error = False
        
        #check some data for saturation errors
        for n in range(100):
            result_tuple = read_values(connection)
            if result_tuple[2]:
                sat_error = True
                break
            
        stop_command = "STOP"
        send_command(stop_command)
        connection.readlines()
        
        if not sat_error:
            #We have found a good gain setting without saturation
            print("Autogain completed - set to level " + str(gain_setting))
            break
        
        

def read_values(conn):
    # Get a line of data from the serial connection and parse it
    raw = conn.readline().decode('utf-8')
    raw_items = re.split("\\t", raw)
    
    sensor0_vals = [0,0,0,0,0,0]
    sensor1_vals = [0,0,0,0,0,0]
    saturation_error = False
    timestamp = round(time.time_ns()/1000000)
    
    try:
        values = [float(x) for x in raw_items[0:14]]
        sensor0_vals = values[0:6]
        sensor1_vals = values[7:13]
        saturation_error = values[6] > 0 or values[13] > 0
    except Exception:
        print("Error parsing values:")
        print(raw)
    
    global error_flag
    
    if saturation_error:
        #Saturation error - only report if new
        if not error_flag:
            error_flag = True
            print("Saturation error! You should probably reduce the gain.")
    else:
        error_flag = False

    
    return sensor0_vals, sensor1_vals, saturation_error, timestamp

## ----------------------------------------------------------------------------------------
# This is all live plot stuff

def live_read(conn, xdat, s0, s1, stop_event):
    #This is called as a new process
    #We have to start up the connection again
    
    global connection
    connection = serial.Serial(port=conn, baudrate=BAUDRATE, timeout=TIMEOUT)
    start_streaming()
    
    # Read sensor data in a loop - async to other code execution
    while not stop_event.is_set():
        vals = read_values(connection)
        xdat.put(vals[3])
        s0.put(vals[0])
        s1.put(vals[1])
        
    #free serial connection on exit
    disconnect_serial()
        

def live_plot_update(frame):
    
    #temp array for data write
    csv_data = []
    for i in range(xdata.qsize()):
        #Load data from the queues and fill into arrays
        xdat = xdata.get()
        s0dat = sensor0_data.get()
        s1dat = sensor1_data.get()
        csv_data.append([str(xdat)] + [str(x) for x in s0dat] + [str(x) for x in s1dat])
        
        xdata_arr.append(xdat)
        sensor0_data_arr.append(s0dat)
        sensor1_data_arr.append(s1dat)
        if xdata_arr[-1] > 10000 + xdata_arr[0]:
            xdata_arr.pop(0)
            sensor0_data_arr.pop(0)
            sensor1_data_arr.pop(0)
    
    shifted_x = [(t-xdata_arr[0])/1000 for t in xdata_arr]
    line00.set_data(shifted_x, [x[0] for x in sensor0_data_arr])
    line01.set_data(shifted_x, [x[1] for x in sensor0_data_arr])
    line02.set_data(shifted_x, [x[2] for x in sensor0_data_arr])
    line03.set_data(shifted_x, [x[3] for x in sensor0_data_arr])
    line04.set_data(shifted_x, [x[4] for x in sensor0_data_arr])
    line05.set_data(shifted_x, [x[5] for x in sensor0_data_arr])
    
    line10.set_data(shifted_x, [x[0] for x in sensor1_data_arr])
    line11.set_data(shifted_x, [x[1] for x in sensor1_data_arr])
    line12.set_data(shifted_x, [x[2] for x in sensor1_data_arr])
    line13.set_data(shifted_x, [x[3] for x in sensor1_data_arr])
    line14.set_data(shifted_x, [x[4] for x in sensor1_data_arr])
    line15.set_data(shifted_x, [x[5] for x in sensor1_data_arr])
    
    output_stream.writerows(csv_data)
    
    return line00, line01, line02, line03, line04, line05, line10, line11, line12, line13, line14, line15
        

def live_plot(selected_sensors, plot_colours):
    #uses https://matplotlib.org/stable/api/animation_api.html
    #and https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task
    
    #this is the physical sensor value limit for the given settings
    gain_value = pow(2, gain_setting-1)
    max_value = 65535/(gain_value*SAMPLE_TIME*18)
    
    matplotlib.use('qtagg')
    global line00, line01, line02, line03, line04, line05
    fig, ax = plt.subplots(2)
    fig.suptitle("Pocket LoC Sensor - Live Plot")
    
    line00, = ax[0].plot([0,0])
    line00.set_label(selected_sensors[0])
    line00.set_color(plot_colours[0])
    line01, = ax[0].plot([0,0])
    line01.set_label(selected_sensors[1])
    line01.set_color(plot_colours[1])
    line02, = ax[0].plot([0,0])
    line02.set_label(selected_sensors[2])
    line02.set_color(plot_colours[2])
    line03, = ax[0].plot([0,0])
    line03.set_label(selected_sensors[3])
    line03.set_color(plot_colours[3])
    line04, = ax[0].plot([0,0])
    line04.set_label(selected_sensors[4])
    line04.set_color(plot_colours[4])
    line05, = ax[0].plot([0,0])
    line05.set_label(selected_sensors[5])
    line05.set_color(plot_colours[5])
    
    ax[0].set_ylim((0,max_value))
    ax[0].set_xlim((0,10))
    ax[0].set(ylabel="Intensity", xlabel="Time (s)")
    ax[0].legend()
    ax[0].set_title("Sensor 0")
    
    global line10, line11, line12, line13, line14, line15
    line10, = ax[1].plot([0,0])
    line10.set_label(selected_sensors[0])
    line10.set_color(plot_colours[0])
    line11, = ax[1].plot([0,0])
    line11.set_label(selected_sensors[1])
    line11.set_color(plot_colours[1])
    line12, = ax[1].plot([0,0])
    line12.set_label(selected_sensors[2])
    line12.set_color(plot_colours[2])
    line13, = ax[1].plot([0,0])
    line13.set_label(selected_sensors[3])
    line13.set_color(plot_colours[3])
    line14, = ax[1].plot([0,0])
    line14.set_label(selected_sensors[4])
    line14.set_color(plot_colours[4])
    line15, = ax[1].plot([0,0])
    line15.set_label(selected_sensors[5])
    line15.set_color(plot_colours[5])

    ax[1].set_ylim((0,max_value))
    ax[1].set_xlim((0,10))
    ax[1].set(ylabel="Intensity", xlabel="Time (s)")
    ax[1].legend()
    ax[1].set_title("Sensor 1")
    

    global xdata_arr, sensor0_data_arr, sensor1_data_arr
    xdata_arr = []
    sensor0_data_arr = []
    sensor1_data_arr = []
    
    global xdata, sensor0_data, sensor1_data
    xdata = Queue()
    xdata.put(0)
    sensor0_data = Queue()
    sensor0_data.put([0.0000000000,0.0000000000,0.0000000000,0.0000000000,0.0000000000,0.0000000000])
    sensor1_data = Queue()
    sensor1_data.put([0.0000000000,0.0000000000,0.0000000000,0.0000000000,0.0000000000,0.0000000000])
    
    global animation
    animation = FuncAnimation(fig, live_plot_update, interval=50, blit=True)
    
    #We have to close serial to reopen it in child process
    port = connection.port
    connection.close()
    
    cancellation_event = Event()
    p = Process(target=live_read, args=(port, xdata, sensor0_data, sensor1_data, cancellation_event))
    p.start()
    
    #Hang on and plot until user interrupts - i.e. closes plot
    plt.show(block=True)
    
    #clean up on exit
    cancellation_event.set()
    
    
## ----------------------------------------------------------------------------------------
   
if __name__ == '__main__':
    
    connection = connect_serial()
    initialise()

    
    #this is used for labels
    selected_sensors = ["F1", "F3", "F5", "F7", "F8", "NIR"] 
    #selected from https://academo.org/demos/wavelength-to-colour-relationship/
    plot_colours = ["#7600ed", "#00d5ff", "#b3ff00", '#ff4f00', '#ff0000', '#610000'] 
    
    #create data folder if non-existent
    Path("data").mkdir(exist_ok=True)
    
    #open a file to stream data to
    datestring = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = open("data/sensor_data_" + datestring + ".csv", "w", encoding="UTF8")
    output_stream = csv.writer(output_file)
    #let us add some headers to the csv
    output_stream.writerow(["timestamp"] + ["sensor0_" + x for x in selected_sensors] + ["sensor1_" + x for x in selected_sensors])
    
    #Get plotting
    live_plot(selected_sensors, plot_colours)
    
    #Clean up
    output_file.close()
