/*
 *  ISS Pointer - Runs a Stepper and Servo to move in AZIMUTH and ALTITUDE 
 *  When used in conjunction with iss_tracker.py on a Raspberry Pi, it will
 *  point to the International Space Station as it flys overhead.
 *  
 *  This sketch can also be used to point to anything in above the horizon Azimuth/Altitude
 *  Azimuth = -200 to 200 horizontal steps 
 *  Altitude= 0 to 90 degrees angle
 *  
 *  This sketch sets up a web server on port 80 which controls a Stepper motor and a Servo
 *  The web server will control the Adafruit TB6612 Driver board depending on the request
 *  See http://server_ip/ for usage (or see docs for more info)
 *  The server_ip is the IP address of the ESP8266 module which will be 
 *  printed to Serial Monitor port.
 *  When turned on, the internal LED blinks when the module is connected to your WiFi.
 *  
 *  The features are controlled by externally calling the HTTP URLs below:
 *  
 * Stepper usage:
 *  http://{ip_address}/stepper/stop
 *  http://{ip_address}/stepper/start
 *  http://{ip_address}/stepper/rpm?[1 to 60]
 *  http://{ip_address}/stepper/steps?[-200 to 200]
 * 
 * Servo usage:
 *  http://{ip_address}/servo/value?[0 to 90]
 *  
 * External LED usage:
 *  http://{ip_address}/led/on
 *  http://{ip_address}/led/off
 *  
 *  Note: This controller has no security, so don't expose to Internet unless you
 *  don't mind someone playing with your servos! 
 *  
 *  Version 1.1 2015.12.13 R. Grokett
 *  - Initial 
 */

// Requires: arduino-cli lib install Stepper
#include <ESP8266WiFi.h>
#include <Stepper.h>
#include <Servo.h>
#include <stdlib.h>
#include <string.h>

// -- USER EDIT -- 
const char* ssid     = "YOUR_SSID";  // YOUR WIFI SSID
const char* password = "YOUR_PSWD";  // YOUR WIFI PASSWORD

// change this to your motor if not NEMA-17 200 step
#define STEPS 200  // Max steps for one revolution
#define RPM 60     // Max RPM
#define DELAY 1    // Delay to allow Wifi to work
// -- END USER EDIT --

const uint8_t SVRO = 15;    // GPIO 15 Servo Control; boot strap pin, keep hardware from pulling it high at boot
const uint8_t STBY = 5;     // GPIO 5 TB6612 Standby
const uint8_t LEDIN = LED_BUILTIN; // Built-in LED, board-specific
const uint8_t LEDEX = 4;    // GPIO 4 External LED

const unsigned long WIFI_CONNECT_TIMEOUT_MS = 30000;
const unsigned long CLIENT_READ_TIMEOUT_MS = 2000;
const size_t REQUEST_LINE_MAX = 120;

// GPIO Pins for Motor Driver board
Stepper stepper(STEPS, 16, 14, 12, 13);

// Create an instance of the server
// specify the port to listen on as an argument
WiFiServer server(80);

Servo myservo;

// Initialize 
void setup() {
  Serial.begin(115200);
  delay(10);

  // prepare onboard LED
  pinMode(LEDIN, OUTPUT);
  digitalWrite(LEDIN, HIGH);

  // prepare external LED
  pinMode(LEDEX, OUTPUT);
  digitalWrite(LEDEX, LOW);

  // prepare STBY GPIO and set Stepper motors
  pinMode(STBY, OUTPUT);
  digitalWrite(STBY, HIGH);
  
  // Set default speed to Max (doesn't move motor)
  stepper.setSpeed(RPM);


  // Connect to WiFi network
  Serial.println();
  Serial.println();
  Serial.print("ISSPointer: Connecting to ");
  Serial.println(ssid);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  unsigned long wifiStart = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - wifiStart < WIFI_CONNECT_TIMEOUT_MS) {
    delay(500);
    Serial.print(".");
  }
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("");
    Serial.println("WiFi connection timed out; restarting");
    delay(1000);
    ESP.restart();
  }
  Serial.println("");
  Serial.println("WiFi connected");
  
  // Start the server
  server.begin();
  Serial.println("Server started");

  // Print the IP address
  Serial.println(WiFi.localIP());

  // Blink onboard LED to signify its connected
  blink();
  blink();
  blink();
  blink();

  // prepare Servo GPIO
  myservo.attach(SVRO, 544, 2400);
  myservo.write(0);
}

void loop() {
  // Check if a client has connected
  WiFiClient client = server.available();
  if (!client) {
    return;
  }

  String respMsg = "";    // HTTP Response Message
  
  // Wait until the client sends some data
  Serial.println("new client");
  unsigned long clientStart = millis();
  while(!client.available() && client.connected() && millis() - clientStart < CLIENT_READ_TIMEOUT_MS){
    delay(1);
  }
  if (!client.available()) {
    Serial.println("Client request timed out");
    client.stop();
    return;
  }
  
  // Read the first line of the request
  char req[REQUEST_LINE_MAX];
  if (!readRequestLine(client, req, sizeof(req))) {
    Serial.println("Invalid or empty request");
    client.stop();
    return;
  }
  Serial.println(req);
  client.flush();

  // CONTROL STEPPER
  if (strstr(req, "/led/off") != NULL) {
    digitalWrite(LEDEX, LOW);
    respMsg = "OK: LED OFF";
  } 
  else if (strstr(req, "/led/on") != NULL) {
    digitalWrite(LEDEX, HIGH);
    respMsg = "OK: LED ON";
  } 
  // CONTROL SERVO 
  else if (strstr(req, "/servo/value") != NULL) {
    int al = getValue(req);
    if ((al < 0) || (al > 90)) {
      respMsg = "ERROR: servo out of range 0 to 90";
    } else {      
      myservo.write(al);
      respMsg = "OK: ALTITUDE = "+String(al);
    }
  }
  // CONTROL STEPPER
  else if (strstr(req, "/stepper/stop") != NULL) {
    digitalWrite(STBY, LOW);
    respMsg = "OK: MOTORS OFF";
  } 
  else if (strstr(req, "/stepper/start") != NULL) {
    digitalWrite(STBY, HIGH);
    blink();
    respMsg = "OK: MOTORS ON";
  } 
  else if (strstr(req, "/stepper/rpm") != NULL) {
    int rpm = getValue(req);
    if ((rpm < 1) || (rpm > RPM)) {
      respMsg = "ERROR: rpm out of range 1 to "+ String(RPM);
    } else {
      stepper.setSpeed(rpm);
      respMsg = "OK: RPM = "+String(rpm);
    }
  }
  // This is just a simplistic method of handling + or - number steps...
  else if (strstr(req, "/stepper/steps") != NULL) {
    int steps = getValue(req);
    if ((steps == 0) || (steps < 0 - STEPS) || ( steps > STEPS )) {
      respMsg = "ERROR: steps out of range ";
    } else {  
      digitalWrite(STBY, HIGH);       // Make sure motor is on
      respMsg = "OK: STEPS = "+String(steps);
      delay(DELAY); 
      if ( steps > 0) { // Forward
        for (int i=0;i<steps;i++) {   // This loop is needed to allow Wifi to not be blocked by step
          stepper.step(1);
          delay(DELAY);   
        }
      } else {         // Reverse
          for (int i=0;i>steps;i--) {   // This loop is needed to allow Wifi to not be blocked by step
            stepper.step(-1);
            delay(DELAY); 
          }  
      }
    }
  }
  else {
    respMsg = printUsage();
  }
    
  client.flush();

  // Prepare the response
  String s = "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\n";
  if (respMsg.length() > 0)
    s += respMsg;
  else
    s += "OK";
   
  s += "\n";

  // Send the response to the client
  client.print(s);
  delay(1);
  Serial.println("Client disconnected");

  // The client will actually be disconnected 
  // when the function returns and 'client' object is detroyed
}

bool readRequestLine(WiFiClient &client, char *buffer, size_t length) {
  size_t pos = 0;
  unsigned long readStart = millis();

  while (client.connected() && millis() - readStart < CLIENT_READ_TIMEOUT_MS) {
    while (client.available()) {
      char c = client.read();
      if (c == '\r' || c == '\n') {
        buffer[pos] = '\0';
        return pos > 0;
      }
      if (pos < length - 1) {
        buffer[pos++] = c;
      }
    }
    delay(1);
  }

  buffer[pos] = '\0';
  return pos > 0;
}

int getValue(const char *req) {
  const char *val_start = strchr(req, '?');
  const char *val_end = val_start == NULL ? NULL : strchr(val_start + 1, ' ');
  if (val_start == NULL || val_end == NULL) {
    Serial.print("Invalid request: ");
    Serial.println(req);
    return(0);
  }

  char value[12];
  size_t valueLength = val_end - val_start - 1;
  if (valueLength >= sizeof(value)) {
    valueLength = sizeof(value) - 1;
  }
  memcpy(value, val_start + 1, valueLength);
  value[valueLength] = '\0';

  Serial.print("Request: ");
  Serial.println(value);
   
  return(atoi(value));
}

String printUsage() {
  // Prepare the usage response
  String s = "Stepper usage:\n";
  s += "http://{ip_address}/stepper/stop\n";
  s += "http://{ip_address}/stepper/start\n";
  s += "http://{ip_address}/stepper/rpm?[1 to " + String(RPM) + "]\n";
  s += "http://{ip_address}/stepper/steps?[-" + String(STEPS) + " to " + String(STEPS) +"]\n";
  s += "\n";
  s += "Servo usage:\n";
  s += "http://{ip_address}/servo/value?[0 to 90]\n";
  s += "\n";
  s += "LED usage:\n";
  s += "http://{ip_address}/led/on\n";
  s += "http://{ip_address}/led/off\n"; 
  return(s);
}
void blink() {
  digitalWrite(LEDIN, LOW);
  delay(100); 
  digitalWrite(LEDIN, HIGH);
  delay(100);
}
