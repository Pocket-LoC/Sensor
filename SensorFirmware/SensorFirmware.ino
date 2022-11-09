int LED_RED = 6;
int LED_GREEN = 13;

bool active = false;

void set_sample_time(int channel, float sample_time);
void set_gain(int channel, int gain);
void set_adc_config(int channel, uint8_t active_frequencies[]);

#include "Adafruit_AS7341.h"
#include "SerialInterface.h"
#include <Wire.h>

Adafruit_AS7341 sensor0;
Adafruit_AS7341 sensor1;


float DEFAULT_SAMPLE_TIME = 5; //ms
uint16_t LED_CURRENT = 4; //mA range: 4-258mA
uint8_t ATIME = 0; //0-254 //set 0 for maximal granularity with ASTEP
as7341_gain_t DEFAULT_GAIN = AS7341_GAIN_4X; //0_5, 1, 2, 4, 8, 16, 32, 64, 128, 256, 512

uint8_t DEFAULT_CONFIG[] = {1,0,1,0,1,0,1,1,0,1}; //F1, F3, F5, F7, F8, NIR

int mux_selected = -1;
Adafruit_AS7341 *sensor_selected = &sensor0;

int sensor0_saturation = 0;
uint16_t sensor0_astep = 0;
as7341_gain_t sensor0_gain = DEFAULT_GAIN;
float sensor0_sample_time = 0;

int sensor1_saturation = 0;
uint16_t sensor1_astep = 0;
as7341_gain_t sensor1_gain = DEFAULT_GAIN;
float sensor1_sample_time = 0;

unsigned long next_output_time = 0; //Variable to ensure periodic sample output
//----------------------------------------------------------------------------------------------------------------------------

//sample time range is 0.00278 - 182.19 ms (we will restrict to int 1...182)
void set_sample_time(int channel, float sample_time){
  select_sensor(channel);

  uint16_t astep = round(sample_time*1000/2.78)-1; //0-65535 //Integration time = (ATIME+1)*(ASTEP+1)*2,78us

  int saturationValue = (ATIME+1)*(astep+1)-1; //the ADC full scale value (-1)
  if(channel){
    sensor1_saturation = saturationValue;
    sensor1_astep = astep;
    sensor1_sample_time = sample_time;
  }else{
    sensor0_saturation = saturationValue;
    sensor0_astep = astep;
    sensor0_sample_time = sample_time;
  }

  sensor_selected->setASTEP(astep);
  sensor_selected->setATIME(ATIME);
}

void set_gain(int channel, int gain){
  select_sensor(channel);

  as7341_gain_t gain_type = (as7341_gain_t)gain;

  if(channel){
    sensor1_gain = gain_type;
  }else{
    sensor0_gain = gain_type;
  }
  
  sensor_selected->setGain(gain_type);
}

void set_adc_config(int channel, uint8_t active_frequencies[]){

  select_sensor(channel);
  
  //we have F1, F2, F3, F4, F5, F6, F7, F8, CLEAR, NIR as options
  //1 activates, 0 deactivates
  //These can be mapped to 6 ADCs (so 6 photodiodes can be selected from above)
  uint8_t config[10] = {};

  uint8_t adcs[] = {1, 2, 3, 4, 5, 6, 0, 0, 0, 0};
  int adc_count = 0;

  String names[] = {"F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "CLEAR", "NIR"};
  String out = "S" + String(channel) + " - Active photodiodes: ";

  for(uint8_t i = 0; i < 10; i++){
    if(active_frequencies[i] == 1){
      config[i] = adcs[adc_count++];
    }else{
      config[i] = 0;
    }

    if(config[i]){
      out = out + names[i] + ", ";
    }
  }

  sensor_selected->setSMUXCustomChannels(config);

  Serial_println(out);
}

void initialise_sensor(int channel){
  select_sensor(channel);
  if(!sensor_selected->begin(AS7341_I2CADDR_DEFAULT, &Wire, channel)){
    Serial.println("Error initialising sensor " + channel);
    digitalWrite(LED_RED, HIGH); //set RED for Error
    delay(5000);
  }
  sensor_selected->setLEDCurrent(LED_CURRENT);
  sensor_selected->enableLED(true);
  set_sample_time(channel, DEFAULT_SAMPLE_TIME);
  sensor_selected->setGain(DEFAULT_GAIN);

  set_adc_config(channel, DEFAULT_CONFIG);
}



void setup() {
  pinMode(LED_RED, OUTPUT);//init LEDs
  pinMode(LED_GREEN, OUTPUT);
  
  Serial_init();
  Wire.begin();

  initialise_sensor(0);
  initialise_sensor(1);  

  digitalWrite(LED_GREEN, LOW);
}

void select_sensor(int channel){
  if(mux_selected == channel){
    return;
  }

  mux_selected = channel;
  int base = 0;

  if(channel){
    sensor_selected = &sensor1;
    base |= 1<<1;
  }else{
    sensor_selected = &sensor0;
    base |= 1<<0;
  }
  
  Wire.beginTransmission(0b1110000); //Connect I2C Mux
  Wire.write(base); //set channel register
  Wire.endTransmission();
}

String get_dataset(){
  uint16_t readBuffer0[6];
  uint16_t readBuffer1[6];

  select_sensor(0);
  sensor_selected->enableSpectralMeasurement(true);

  select_sensor(1);
  sensor_selected->enableSpectralMeasurement(true);

  select_sensor(0);
  sensor_selected->delayForData(0);
  sensor_selected->readResults(readBuffer0);

  select_sensor(1);
  sensor_selected->delayForData(0);
  sensor_selected->readResults(readBuffer1);

  bool hitMax0 = false; //Check if we have reached saturation
  bool hitMax1 = false; //Check if we have reached saturation
  String outString = "";
  for(int i = 0; i < 6; i++){
      outString = outString + String(Adafruit_AS7341::toBasicCounts(readBuffer1[i], sensor1_gain, ATIME, sensor1_astep), 10) + "\t";
      hitMax1 = readBuffer1[i] > sensor1_saturation;
  }
  if(hitMax1){
        outString = outString + "1\t";
      }else{
        outString = outString + "0\t";
  }
  
  for(int i = 0; i < 6; i++){
      outString = outString + String(Adafruit_AS7341::toBasicCounts(readBuffer0[i], sensor0_gain, ATIME, sensor0_astep), 10) + "\t";
      hitMax0 = readBuffer0[i] > sensor0_saturation;   
  }
  if(hitMax0){
        outString = outString + "1\t";
      }else{
        outString = outString + "0\t";
  }

  if(hitMax0 || hitMax1){
    digitalWrite(LED_RED, HIGH); //Saturation warning
  }else{
    digitalWrite(LED_RED, LOW);
  }

  return outString;
}


void loop() {

  String outString = "";
  if(active){
    outString = get_dataset();
  }
  

  while(millis() < next_output_time){
    Serial_input();
    //Wait untill it is time to post our data;
  }
  //Output: <Sensor 0: F1, F3, F5, F7, F8, NIR, saturation warning><Sensor 1: F1, F3, F5, F7, F8, NIR, saturation warning>

  if(active){
    Serial_println(outString);
  }
  

  int overall_intervall = sensor0_sample_time *2 + sensor1_sample_time *2;
  next_output_time = next_output_time + overall_intervall;
}
