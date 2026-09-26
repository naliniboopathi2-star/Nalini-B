#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <DHT.h>

// ============================================================
// WI-FI CREDENTIALS (Must match your PC's network / hotspot)
// ============================================================
const char* ssid = "iot";
const char* password = "example 3";

ESP8266WebServer server(80);

// ============================================================
// DHT11 CONFIGURATION FOR ESP8266
// ============================================================
#define DHTPIN D5     // D5 pin on ESP8266 NodeMCU / Wemos D1 Mini
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

// ============================================================
// LIVE DASHBOARD DATA VARIABLES
// ============================================================
String current_status = "NORMAL";
String current_location = "Main Panel";
float current_power = 0.0;
float max_limit = 2500.0;
float ai_forecast = 0.0;
String last_update_time = "--:--:--";


// ============================================================
// MOBILE WEB PAGE (HTTP ROOT)
// ============================================================
void handleRoot() {
  float h = dht.readHumidity();
  float t = dht.readTemperature();
  
  if (isnan(h) || isnan(t)) {
    h = 0.0;
    t = 0.0;
  }

  String html = "<!DOCTYPE html><html><head>";
  html += "<meta name='viewport' content='width=device-width, initial-scale=1'>";
  html += "<meta http-equiv='refresh' content='3'>"; // Auto-refresh mobile view every 3 seconds
  html += "<style>";
  html += "body { font-family: Arial, sans-serif; background: #101820; color: #fff; text-align: center; margin: 0; padding: 15px; }";
  html += "h2 { color: #35d07f; font-size: 20px; }";
  html += ".card { background: #17232d; padding: 15px; margin: 10px auto; border-radius: 12px; max-width: 400px; box-shadow: 0 4px 10px rgba(0,0,0,0.4); }";
  html += ".label { font-size: 12px; color: #a9bac5; text-transform: uppercase; margin-top: 8px; }";
  html += ".val { font-size: 22px; font-weight: bold; color: #4dabf7; }";
  html += ".status-CRITICAL { color: #ff5c5c; font-size: 24px; font-weight: bold; }";
  html += ".status-WARNING { color: #ffd166; font-size: 24px; font-weight: bold; }";
  html += ".status-NORMAL { color: #35d07f; font-size: 24px; font-weight: bold; }";
  html += "</style></head><body>";
  
  html += "<h2>AI Smart Electrical Monitor</h2>";
  
  html += "<div class='card'>";
  html += "<div class='label'>Monitored Location</div>";
  html += "<div style='font-size: 18px; font-weight: bold; color: #b197fc;'>" + current_location + "</div>";
  
  html += "<div class='label'>System Status</div>";
  html += "<div class='status-" + current_status + "'>" + current_status + "</div>";
  
  html += "<div class='label'>Current Power</div>";
  html += "<div class='val'>" + String(current_power, 1) + " W</div>";

  html += "<div class='label'>AI 5-Min Forecast</div>";
  html += "<div class='val' style='color: #ffd166;'>" + String(ai_forecast, 1) + " W</div>";

  html += "<div class='label'>Maximum Limit</div>";
  html += "<div style='font-size: 16px;'>" + String(max_limit, 1) + " W</div>";
  html += "</div>";

  html += "<div class='card'>";
  html += "<div class='label'>DHT11 Environment (Pin D5)</div>";
  html += "<div style='display: flex; justify-content: space-around; margin-top: 8px;'>";
  html += "<div>Temperature<br><span style='font-size: 18px; color: #35d07f;'>" + String(t, 1) + " °C</span></div>";
  html += "<div>Humidity<br><span style='font-size: 18px; color: #4dabf7;'>" + String(h, 1) + " %</span></div>";
  html += "</div>";
  html += "<div style='font-size: 10px; color: #a9bac5; margin-top: 10px;'>Last Synced: " + last_update_time + "</div>";
  html += "</div>";

  html += "</body></html>";

  server.send(200, "text/html", html);
}


// ============================================================
// API ENDPOINT: SENSOR READINGS (Called by Python PC Code)
// ============================================================
void handleSensor() {
  float h = dht.readHumidity();
  float t = dht.readTemperature();
  
  if (isnan(h) || isnan(t)) {
    h = 0.0;
    t = 0.0;
  }

  String json = "{\"temperature\":" + String(t, 1) + ",\"humidity\":" + String(h, 1) + "}";
  server.send(200, "application/json", json);
}


// ============================================================
// API ENDPOINT: RECEIVE PYTHON DASHBOARD UPDATES
// ============================================================
void handleAlert() {
  if (server.hasArg("status")) current_status = server.arg("status");
  if (server.hasArg("power")) current_power = server.arg("power").toFloat();
  if (server.hasArg("limit")) max_limit = server.arg("limit").toFloat();
  if (server.hasArg("forecast")) ai_forecast = server.arg("forecast").toFloat();
  if (server.hasArg("time")) last_update_time = server.arg("time");
  if (server.hasArg("location")) current_location = server.arg("location");

  server.send(200, "text/plain", "OK");
}


// ============================================================
// SETUP
// ============================================================
void setup() {
  Serial.begin(115200);
  dht.begin();

  WiFi.begin(ssid, password);
  Serial.print("Connecting to Wi-Fi");
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("Wi-Fi Connected!");
  Serial.print("Mobile Web Server IP Address: http://");
  Serial.println(WiFi.localIP());

  server.on("/", handleRoot);
  server.on("/sensor", handleSensor);
  server.on("/alert", handleAlert);

  server.begin();
  Serial.println("HTTP Server started successfully.");
}


// ============================================================
// LOOP
// ============================================================
void loop() {
  server.handleClient();
}