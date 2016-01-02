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

#include <ESP8266WiFi.h>
#include <Stepper.h>
#include <Servo.h>

// -- USER EDIT -- 
const char* ssid     = "YOUR_SSID";  // YOUR WIFI SSID
const char* password = "YOUR_PSWD";  // YOUR WIFI PASSWORD

// change this to your motor if not NEMA-17 200 step
#define STEPS 200  // Max steps for one revolution
#define RPM 60     // Max RPM
#define DELAY 1    // Delay to allow Wifi to work
// -- END USER EDIT --

int SVRO = 15;    // GPIO 15 Servo Control
int STBY = 5;     // GPIO 5 TB6612 Standby
int LEDIN = 0;    // GPIO 0 (built-in LED)
int LEDEX = 4;    // GPIO 4 External LED

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
  
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
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
  myservo.attach(SVRO);
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
  while(!client.available()){
    delay(1);
  }
  
  // Read the first line of the request
  String req = client.readStringUntil('\r');
  Serial.println(req);
  client.flush();

  // CONTROL STEPPER
  if (req.indexOf("/led/off") != -1) {
    digitalWrite(LEDEX, LOW);
    respMsg = "OK: LED OFF";
  } 
  else if (req.indexOf("/led/on") != -1) {
    digitalWrite(LEDEX, HIGH);
    respMsg = "OK: LED ON";
  } 
  // CONTROL SERVO 
  else if (req.indexOf("/servo/value") != -1) {
    int az = getValue(req);
    if ((az < 0) || (az > 90)) {
      respMsg = "ERROR: servo out of range 0 to 90";
    } else {      
      myservo.write(az);
      respMsg = "OK: ALTITUDE = "+String(az);
    }
  }
  // CONTROL STEPPER
  else if (req.indexOf("/stepper/stop") != -1) {
    digitalWrite(STBY, LOW);
    respMsg = "OK: MOTORS OFF";
  } 
  else if (req.indexOf("/stepper/start") != -1) {
    digitalWrite(STBY, HIGH);
    blink();
    respMsg = "OK: MOTORS ON";
  } 
  else if (req.indexOf("/stepper/rpm") != -1) {
    int rpm = getValue(req);
    if ((rpm < 1) || (rpm > RPM)) {
      respMsg = "ERROR: rpm out of range 1 to "+ String(RPM);
    } else {
      stepper.setSpeed(rpm);
      respMsg = "OK: RPM = "+String(rpm);
    }
  }
  // This is just a simplistic method of handling + or - number steps...
  else if (req.indexOf("/stepper/steps") != -1) {
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

int getValue(String req) {
  int val_start = req.indexOf('?');
  int val_end   = req.indexOf(' ', val_start + 1);
  if (val_start == -1 || val_end == -1) {
    Serial.print("Invalid request: ");
    Serial.println(req);
    return(0);
  }
  req = req.substring(val_start + 1, val_end);
  Serial.print("Request: ");
  Serial.println(req);
   
  return(req.toInt());
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
