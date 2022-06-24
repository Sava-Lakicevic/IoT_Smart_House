/*
 * The point of this project is to imitate a smart home system. The smart home system consist of a cooling (dc-motor) and heating (heating resistor)
 * systems and lighting (LED diode). There are also sensors for gathering data, such as illumination and temperature.
 * There is also a button, that is supposed to be a motion detection sensor. Since the sensor would not operate as expected, it has been replaces by
 * a button.
 * There is an auto-light mode and a home-security mode that cannot be on at the same time. In addition, there is a hysterisis control
 * (auto temperature mode) that will activate the cooling and heating systems depending on the readings from the LM35 temperature sensor.
 * The heating and cooling systems cannot be on at the same time.
 * Data and notifications about changes in the system, motion detection (when home-security mode is on), etc. is sent to a python server, that
 * send/reads data to/from thingspeak. The python server can send commands (that it reads from an email address) to the microcontroller to
 * alter its functionality.
 * Data is sent in the form of DATA_TYPE_VALUE; for example DATA_TEMP_27, which corresponds to temperature is 27 degrees Celsius
 * Notifications are sent in the form of NOTI_NOTIFICATION; for example NOTI_ALM_ON, which corresponds to auto-light mode is on
 */
#include <TimerOne.h>
//temperature sensor on A0 and the photo-resistor for illumination on A1
#define TEMP A0
#define PHR A1

//digital pins for relays that control LED, cooling and heating systems
const int LED_RELAY = 13;
const int DC_RELAY = 12;
const int HEATER_RELAY = 11;
//button for the security mode
const int SECURITY = 2;

//array to take multiple illumination/temperature data and take the average. Point is to decrease big variance due to sensor malfunction
float illumination[10], temperature[10];

//counters for collecting data for the float arrays above
int illuminationCounter, temperatureCounter; 

//pause counter is for 10 minutes (seconds in simulation)
int pauseCounter;

//status of the relays, HIGH or LOW
int ledStatus, dcStatus, heaterStatus;

//counter to keep the light on for 10 seconds after last motion detected
int securityCounter;

//counters for how long the auto light system or secure mode were on
int almDuration, smDuration;

//auto light mode and secure mode booleans, used to see if the systems are on
//notifiedSecurity and movementDetected used by secure mode
//auto temp mode is for the hysterisis control of the heating and cooling systems
boolean autoLight, secureMode, autoTemp, movementDetected, notifiedSecurity, canChangeLed;

//this are used in combination with the pause counter, to control how often measurements take place
boolean measureTemperature, measureIllumination;

//This function will measure the average measurement from all the values gathered from the float arrays
float averageMeasurement(float *measurements, int counter)
{
  float sum=0;
  for (int i=0; i<counter; i++)
  {
    sum+=measurements[i];
    measurements[i]=0;
  }
  return sum/float(counter);
}

//This is the timer1 function that activates every half a second.
void smartHouse(){
//  If autoLight is on, then we add the duration, regardless of measurements
  if(autoLight){
    almDuration++;
  }
//  if it's time to measure illumination (10 minutes/seconds have passed) then the function will start
  if(measureIllumination){
//    5 measurements are taken from the sensor and the average is calculated
//    The point it to decrease the variance of the sensor readings
    illumination[illuminationCounter]=analogRead(A1);
    illuminationCounter++;
    if(illuminationCounter==5){
      float averageIllumination = averageMeasurement(illumination, illuminationCounter);
//      The format of all data sent to Python are in the form of DATA_TYPE_VALUE
      Serial.print("DATA_ILLU_");
      Serial.print(averageIllumination);
      Serial.print("\n");
//      resetting the counter for taking 5 measurements
      illuminationCounter = 0;
//      not reading illumination, until it's time
      measureIllumination = false;
//      this if/else will activate only if autolight mode is on
      if(averageIllumination<306 && autoLight){
        if(ledStatus == LOW){
          Serial.println("NOTI_LED_ON_ALM");
          ledStatus = HIGH;
          digitalWrite(13,ledStatus);
        }
      }else if(ledStatus == HIGH && autoLight){
          Serial.println("NOTI_LED_OFF_ALM");
          ledStatus = LOW;
          digitalWrite(LED_RELAY,ledStatus);
      }
    }
  }
//  Similar to auto-light mode, but everything is within one function
  if(secureMode){
    smDuration++;
    if(movementDetected){
//      Within one cycle of movement detection, only one notification is sent
      if(!notifiedSecurity){
        Serial.println("NOTI_MOTION_DETECTED");
        notifiedSecurity = true;
      }
//      Counter for tracking if 10 seconds had passed since last movement was detected within one cycle
      securityCounter++;
      ledStatus = HIGH;
      digitalWrite(LED_RELAY, ledStatus);
//      Only after 10 seconds had passed are the boolean variables reset and the light turned off
      if(securityCounter/2 >= 60){
        ledStatus = LOW;
        digitalWrite(LED_RELAY,ledStatus);
        movementDetected = false;
        notifiedSecurity = false;
        canChangeLed = true;
      }
    }
  }
//  Similar to measuring light, but autoTemp (hysterisis control) is always on
  if(measureTemperature){
    temperature[temperatureCounter]=analogRead(TEMP)*0.489;
    temperatureCounter++;
//    5 values are taken to eliminate/decrease the effects of sensor variance
    if(temperatureCounter==5){
      float averageTemperature = averageMeasurement(temperature,temperatureCounter);
      Serial.print("DATA_TEMP_");
      Serial.print(averageTemperature);
      Serial.print("\n");
//      Values should be 23 and 17; However, the temperatures were too low for testing purposes and sensor readings, hence 27 was used
      if(averageTemperature>=27 && autoTemp){
//        Cooling and heating systems cannot be on at the same time, hence checking only the cooling system (dcstatus) is sufficient
        if(dcStatus == LOW){
          dcStatus = HIGH;
          heaterStatus = LOW;
          digitalWrite(DC_RELAY,dcStatus);
          digitalWrite(HEATER_RELAY,heaterStatus);
          Serial.println("NOTI_COOLING_ON");
          Serial.println("NOTI_HEATING_OFF");
        }
      }
//      identical to activating cooling, but the values and notifications are reversed
      if(averageTemperature<=27 && autoTemp){
        if(heaterStatus == LOW){
          dcStatus = LOW;
          heaterStatus = HIGH;
          digitalWrite(DC_RELAY,dcStatus);
          digitalWrite(HEATER_RELAY,heaterStatus);
          Serial.println("NOTI_COOLING_OFF");
          Serial.println("NOTI_HEATING_ON");
        }
      }
//      resetting the values for measuring temperature
      temperatureCounter = 0;
      measureTemperature = false;
    }
  }
//  pause will increase regardless of measurements being taken. This is to ensure that the data is sent periodically at the same time
//  and not with a slight delay every time
  pauseCounter++;
  if(pauseCounter/2 >= 10){
//    The order of execution is very important for sending data
//    First we send data for the duration of both auto-light mode and security-modes and then we take the measurements
//    This is achieved by setting the pausecounter in the setup at a very high value, to ensure that this happens first, regardless of
//    the frequency of measurements
    measureTemperature = true;
    measureIllumination = true;
    pauseCounter = 0;
    Serial.print("DATA_DURATION_ALM_");
    Serial.print(almDuration/2);
    Serial.print("\n");
    Serial.print("DATA_DURATION_SM_");
    Serial.print(smDuration/2);
    Serial.print("\n");
  }
}


void setup() {
//  setting up pinmodes and setting all of the systems to low
  pinMode(LED_RELAY,OUTPUT);
  pinMode(DC_RELAY,OUTPUT);
  pinMode(HEATER_RELAY,OUTPUT);
  pinMode(SECURITY,INPUT);
  digitalWrite(LED_RELAY, LOW);
  digitalWrite(DC_RELAY, LOW);
  digitalWrite(HEATER_RELAY, LOW);
  Serial.begin(9600);
//  half a second; could be one second for different purposes
  Timer1.initialize(500000);
  Timer1.attachInterrupt(smartHouse);
  illuminationCounter = 0;
  temperatureCounter = 0;
//  as mentioned above, pause counter is set to a high number, to ensure the data is sent in the correct order
//  this is important for updating thingspeak through python, so that the data is decoded and process in the correct order and in the correct fields
  pauseCounter = 100;
  securityCounter = 0;
  almDuration = 0;
  smDuration = 0;
  ledStatus = LOW;
  dcStatus = LOW;
  heaterStatus = LOW;
//  autolight mode is set default to true, and secure mode to false; these two can also not be on at the same time, but can be off at the same time
  autoLight = true;
  secureMode = false;
  movementDetected = false;
//  These two are set to false in combination with Pause Control being set to a high number; this is to ensure that the data is sent
//  in the correct order from the get-go
  measureTemperature = false;
  measureIllumination = false;
//  auto temperature (hysterisis control) is currently always on; this was added for the future, to enable additional features
  autoTemp = true;
  notifiedSecurity = false;
  canChangeLed = true;
}

void loop() {
//  if security mode is active and the button registers something, then movement detected is true
//  security counter will always be reset to 0 if 10 seconds have not passed from the last movement
  if(digitalRead(SECURITY)==0 && secureMode){
    movementDetected = true;
    canChangeLed = false;
    securityCounter = 0;
  }
//  These are all the different commands and some of the notifications that can be sent to/from python by email
//  They control the LED, heating and cooling systems, auto-light and home security modes, etc.
  if(Serial.available() > 0) {
     String data = Serial.readString();
     if((data == "LED_ON" || data == "LED_ON\n") && canChangeLed){
      if(ledStatus == HIGH){
        Serial.println("NOTI_LED_WAS_ON");
      }else{
        Serial.println("NOTI_LED_IS_ON");
        ledStatus = HIGH;
        digitalWrite(LED_RELAY,ledStatus);
      }
//      if(autoLight){
//        autoLight = false;
//        Serial.println("NOTI_ALM_OFF");
//      }if(secureMode){
//        secureMode = false;
//        Serial.println("NOTI_SM_OFF");
//      }
     }else if ((data == "LED_OFF" || data == "LED_OFF\n") && canChangeLed){
      if(ledStatus == LOW){
        Serial.println("NOTI_LED_WAS_OFF");
      }else{
        Serial.println("NOTI_LED_IS_OFF");
        ledStatus = LOW;
        digitalWrite(LED_RELAY,ledStatus);
      }
//      if(autoLight){
//        autoLight = false;
//        Serial.println("NOTI_ALM_OFF");
//      }
//      if(secureMode){
//        secureMode = false;
//        Serial.println("NOTI_SM_OFF");
//      }
     } else if (data == "AUTO_LIGHT_ON" || data == "AUTO_LIGHT_ON\n"){
      illuminationCounter = 0;
      autoLight = true;
      Serial.println("NOTI_ALM_ON");
      if(secureMode){
        secureMode = false;
        Serial.println("NOTI_SM_OFF");
      }
     }
     else if (data == "AUTO_LIGHT_OFF" || data == "AUTO_LIGHT_OFF\n"){
      autoLight = false;
      Serial.println("NOTI_ALM_OFF");
     }
     else if (data == "SECURE_MODE_ON" || data == "SECURE_MODE_ON\n"){
      secureMode = true;
      ledStatus = LOW;
      digitalWrite(LED_RELAY,ledStatus);
      Serial.println("NOTI_SM_ON");
      if(autoLight){
        autoLight = false;
        Serial.println("NOTI_ALM_OFF");
      }
     }
     else if (data == "SECURE_MODE_OFF" || data == "SECURE_MODE_OFF\n"){
      secureMode = true;
      Serial.println("NOTI_SM_OFF");
      ledStatus = LOW;
      digitalWrite(LED_RELAY,ledStatus);
     }else if (data == "HEAT_ON" || data == "HEAT_ON\n"){
      if(heaterStatus == HIGH){
        Serial.println("NOTI_HEATER_WAS_ON");
      }else{
        heaterStatus = HIGH;
        digitalWrite(HEATER_RELAY,heaterStatus);
        Serial.println("NOTI_HEATER_IS_ON");
        dcStatus = LOW;
        digitalWrite(DC_RELAY,dcStatus);
        Serial.println("NOTI_COOLING_IS_OFF");
        
      }
     }else if (data == "HEAT_OFF" || data == "HEAT_OFF\n"){
      if(heaterStatus == LOW){
        Serial.println("NOTI_HEATER_WAS_OFF");
      }else{
        heaterStatus = LOW;
        digitalWrite(HEATER_RELAY,heaterStatus);
        Serial.println("NOTI_HEATER_IS_OFF");
      }
     }
     else if (data == "COOLING_ON" || data == "COOLING_ON\n"){
      if(dcStatus == HIGH){
        Serial.println("NOTI_COOLING_WAS_ON");
      }else{
        heaterStatus = LOW;
        digitalWrite(HEATER_RELAY,heaterStatus);
        Serial.println("NOTI_HEATER_IS_OFF");
        dcStatus = HIGH;
        digitalWrite(DC_RELAY,dcStatus);
        Serial.println("NOTI_COOLING_IS_ON");
      }
     }else if (data == "COOLING_OFF" || data == "COOLING_OFF\n"){
      if(dcStatus == LOW){
        Serial.println("NOTI_COOLING_WAS_OFF");
      }else{
        dcStatus = LOW;
        digitalWrite(DC_RELAY,heaterStatus);
        Serial.println("NOTI_COOLING_IS_OFF");
      }
     }
  }
}
