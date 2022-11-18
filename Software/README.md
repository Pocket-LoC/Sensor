## Pocket LoC Sensor

### Sample Software
This is a software sample to help you getting started with the sensor firmware. The sample uses Python to establish a serial connection, configure the sensor parameters and then stream data over the serial connection. The measured values are displayed in two live plots, one for each spectral sensor.

#### Getting Started
To run this code you will need to install Python (3.7+). Typically, it is easiest to use an IDE such as Spyder or Visual Studio. Depending on your setup you may have to install some of the used packages (see "import" statements at the top of the file or just run and wait for errors). Packages are usually instaleld using pip or conda, depending on your installation.

Connect the Pocket LoC Sensor (with the [firmware](https://github.com/Pocket-LoC/Sensor/tree/main/Firmware) loaded). The blue LED should be on, the red light should be flashing.

You can now run the Python code. The software will try to establish a connection to the first "Arduino Micro" it can find. This will only work reliably if no other Arduino Micro is connected to the PC (if you need to use multiple Arduinos in paralell set the correct port manually). It will then configure the sensors and perform an automatic gain adjustment, setting the highest gain that does not produce a saturation error. For a successful gain adjustment, you should ensure the sensor is exposed to the maximal brightness it will experience during the experiment (usually a clear channel). Finally, a live plot will show with the values recorded from the two spectral sensors.

#### Reading Data Stream
When streaming, the sensor will periodically write data to the serial connection. To correctly retrieve data, avoiding losses (e.g. by overfilling the connection buffer), you must ensure that you read the data from the serial connection at at least the speed it is beeing written to (4*sample_time). In the software sample this is achieved using a seperate process for reading the data. If a lower sample rate is sufficient for your application, you should also increase the sample_time (has the positive side effect of increasing sensitivity).

If the input buffer overflows you will receive corrupt data packages that are missing leading or trailing symbols.
