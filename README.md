# IoT_Smart_House
Simulation of a smart house, that controls the temperature and illumination in a house, collects the data and sends reports.

The point of this project is to imitate a smart home system. The smart home system consist of a cooling (dc-motor) and heating (heating resistor) systems and lighting (LED diode).
There are also sensors for gathering data, such as illumination and temperature.
There is also a button, that is supposed to be a motion detection sensor.
Since the sensor would not operate as expected, it has been replaces by a button.
There is an auto-light mode and a home-security mode that cannot be on at the same time.
In addition, there is a hysterisis control (auto temperature mode) that will activate the cooling and heating systems depending on the readings from the LM35 temperature sensor.
The heating and cooling systems cannot be on at the same time.
Data and notifications about changes in the system, motion detection (when home-security mode is on), etc. is sent to a python server, that send/reads data to/from thingspeak.
The python server can send commands (that it reads from an email address) to the microcontroller to alter its functionality.
Data is sent in the form of DATA_TYPE_VALUE; for example DATA_TEMP_27, which corresponds to temperature is 27 degrees Celsius Notifications are sent in the form of NOTI_NOTIFICATION; for example NOTI_ALM_ON, which corresponds to auto-light mode is on.
