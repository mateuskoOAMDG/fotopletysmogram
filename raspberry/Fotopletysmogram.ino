/*
  project: Fotopletysmogram
  author: mateusko O.A.M.D.G mateusko.OAMDG@outlook.com
  date:   2023-10-19
  version: 1.0.0
  sensor: MAX30102
  uC: Rapsberry PI Pico
  
  note: Data zo senzora MAX30102 sú odosielané cez seriovy port v alfanumerickom tvare: <time>,<value>
        <time> - čas, ktory uplynul od predosleho merania (standardne 40 ms),
        <value> - namerana intenzita IR ziarenia

        kazda takato dvojica dat je v samostatnom riadku

  Created according to the original sketch: 
  
  Heart beat plotting!
  By: Nathan Seidle @ SparkFun Electronics
  Date: October 20th, 2016
  https://github.com/sparkfun/MAX30105_Breakout

  Shows the user's heart beat on Arduino's serial plotter

  Instructions:
  1) Load code onto Redboard
  2) Attach sensor to your finger with a rubber band (see below)
  3) Open Tools->'Serial Plotter'
  4) Make sure the drop down is set to 115200 baud
  5) Checkout the blips!
  6) Feel the pulse on your neck and watch it mimic the blips

  It is best to attach the sensor to your finger using a rubber band or other tightening
  device. Humans are generally bad at applying constant pressure to a thing. When you
  press your finger against the sensor it varies enough to cause the blood in your
  finger to flow differently which causes the sensor readings to go wonky.

  Hardware Connections (Breakoutboard to Rapsberry Pi Pico):
  -VCC = 3.3V 
  -GND = GND
  -SDA = 4 (or SDA; GP2)
  -SCL = 5 (or SCL; GP3)
  -INT = Not connected

  The MAX30102 Breakout can handle 5V or 3.3V I2C logic. We recommend powering the board with 5V
  but it will also run at 3.3V.
*/



#include <Wire.h>
#include "MAX30105.h"
#define SEND_TIME_PERIOD 40 //v akej perióde sa odosielajú dáta (ms)
#define SAMPLE_RATE  3200; //Options: 50, 100, 200, 400, 800, 1000, 1600, 3200
MAX30105 particleSensor;
#define I2C_SDA 4
#define I2C_SCL 5
void setup()
{
  Serial.begin(115200);
   while (!Serial) {
    ;  // wait for serial port to connect. Needed for native USB port only
  }
  Serial.println("Initializing...");

  // Initialize sensor
  if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) //Use default I2C port, 400kHz speed
  {
    Serial.println("MAX30105 was not found. Please check wiring/power. ");
    while (1);
  }

  //Setup to sense a nice looking saw tooth on the plotter
  byte ledBrightness = 0x1F; //Options: 0=Off to 255=50mA
  byte sampleAverage = 8; //Options: 1, 2, 4, 8, 16, 32
  byte ledMode = 3; //Options: 1 = Red only, 2 = Red + IR, 3 = Red + IR + Green
  int sampleRate = SAMPLE_RATE; //Options: 50, 100, 200, 400, 800, 1000, 1600, 3200
  int pulseWidth = 411; //Options: 69, 118, 215, 411
  int adcRange = 4096; //Options: 2048, 4096, 8192, 16384

  particleSensor.setup(ledBrightness, sampleAverage, ledMode, sampleRate, pulseWidth, adcRange); //Configure sensor with these settings

  const byte dummyData = 20;
  for (byte x = 0 ; x < dummyData ; x++)
  {
    particleSensor.getIR(); //Read the IR value
  }
}

#define mil16 ((uint16_t)millis())

uint16_t timer = millis();
uint16_t timer_bak;
uint32_t  variable;
uint16_t deltat;
void loop()

{
  timer_bak = mil16;
  deltat = timer_bak - timer;
  if ( deltat >= SEND_TIME_PERIOD) {
    variable = particleSensor.getIR();



    Serial.print(deltat, DEC);
    Serial.print(',');
    Serial.println(variable);

    timer = timer_bak;

  }
}
