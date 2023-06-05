char Buffer_Data[50];
uint8_t strPointer=0;

void Serial_init() {
  Serial.begin(115200);
  strPointer=0;
  Buffer_Data[strPointer]=0;

  while(!Serial){ //Wait for serial connection.
    digitalWrite(LED_RED, HIGH); //blink RED while waiting
    delay(100);
    digitalWrite(LED_RED, LOW);
    delay(100);
  }
  digitalWrite(LED_RED, LOW); //clear RED
}

void Serial_println(const char str[]) {
  Serial.println(str);
}

void Serial_println(String str) {
  Serial.println(str);
}

void Serial_input() { 
  while ((Serial.available() > 0) && (strPointer<50)) {
    Buffer_Data[strPointer] = Serial.read();
    if ((Buffer_Data[strPointer]>='a') && (Buffer_Data[strPointer]<='z')) Buffer_Data[strPointer]+='A'-'a';  //Großbuchstaben
    strPointer++;
    Buffer_Data[strPointer]=0;
  }
      
  if (strcmp(Buffer_Data,"\r\n")==0) {    //Kein Befehlt eingegeben
    Serial_println("Greetings from Max! Have fun with the Pocket LoC v1.");
    
    strPointer=0;
    Buffer_Data[strPointer]=0;
  } else if (strstr(Buffer_Data,"\r\n")>0)   {   //Befehl wurde mit Return beendet
    if (Buffer_Data[0]=='T'){ //Set sample time - "T10\r\n" = 10ms per sensor, total sample time will be 4*sample_time (40ms)      
       float sample_time = constrain(atoi(&Buffer_Data[1]),1,182);
       set_sample_time(0, sample_time);
       set_sample_time(1, sample_time);
       Serial_println("OK");
    }else if (Buffer_Data[0]=='G'){ //Set gain - "G5\r\n" Gain is set to fifth element of gain enum
       int gain_type = constrain(atoi(&Buffer_Data[1]),0,10);
       set_gain(0, gain_type);
       set_gain(1, gain_type);

       String out = "OK. Selected gain: " + String(pow(2, gain_type-1)) + "x";
       Serial_println(out);
    }else if (Buffer_Data[0]=='C'){ //Set ADC configuration - "C0100110101\r\n" Activate/Deactviate individual photo sensors. The first 6 sensors set will be connected to ADCs.
      //F1, F2, F3, F4, F5, F6, F7, F8, CLEAR, NIR
      uint8_t selection[10] = {};
      for(int i=0; i<10; i++){
        char arr[] = {Buffer_Data[i+1]};
        selection[i] = constrain(atoi(arr),0,1);
      }
      set_adc_config(0, selection);
      set_adc_config(1, selection);
      Serial_println("OK");
    }else if (strcmp(&Buffer_Data[0],"START\r\n")==0) { //Start continous data measurement and serial output
      active = true;
      Serial_println("Started");
      digitalWrite(LED_GREEN, HIGH);
    }else if (strcmp(&Buffer_Data[0],"STOP\r\n")==0) { //Stop outputting data
      active = false;
      Serial_println("Stopped");
      digitalWrite(LED_GREEN, LOW);
    }else if (strcmp(&Buffer_Data[0],"ID\r\n")==0){ //Print device id
      Serial_println(DEVICE_ID);
    }else { 
      char *p = strstr(Buffer_Data,"\r\n"); *p=0;
      Serial.print("Wrong command (");
      Serial.print(Buffer_Data);
      Serial_println(")"); 
    }
    
    strPointer = 0;
    Buffer_Data[strPointer]=0;
  }  
}
