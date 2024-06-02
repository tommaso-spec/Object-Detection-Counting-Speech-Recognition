#include <Wire.h>
#include <LiquidCrystal_I2C.h>
LiquidCrystal_I2C lcd(0x27, 20, 4);

const int yellowLedPin = 8; // Pin per il LED giallo
const int redLedPin = 7; // Pin per il LED rosso
const int greenLedPin = 6; // Pin per il LED verde
const int blueLedPin = 5; // Pin per il LED blu

int redCount = 0;
int blueCount = 0;
int yellowCount = 0;
int greenCount = 0;

// Buffer per memorizzare i dati ricevuti
int bufferedRedCount = 0;
int bufferedBlueCount = 0;
int bufferedYellowCount = 0;
int bufferedGreenCount = 0;

bool shouldUpdateDisplay = false; // Flag per indicare se il display deve essere aggiornato

void setup() {
  Serial.begin(115200);
  pinMode(yellowLedPin, OUTPUT);
  pinMode(redLedPin, OUTPUT);
  pinMode(greenLedPin, OUTPUT);
  pinMode(blueLedPin, OUTPUT);
  lcd.init();
  lcd.backlight();
}

void loop() {
  if (Serial.available() > 0) {
    String received = Serial.readStringUntil('\n');
    if (received.startsWith("green:")) {
      int newGreenCount = received.substring(6).toInt();
      if (newGreenCount != bufferedGreenCount) {
        bufferedGreenCount = newGreenCount;
        shouldUpdateDisplay = true;
      }
      digitalWrite(greenLedPin, newGreenCount >= 1 ? HIGH : LOW);
    } else if (received.startsWith("blue:")) {
      int newBlueCount = received.substring(5).toInt();
      if (newBlueCount != bufferedBlueCount) {
        bufferedBlueCount = newBlueCount;
        shouldUpdateDisplay = true;
      }
      digitalWrite(blueLedPin, newBlueCount >= 1 ? HIGH : LOW);
    } else if (received.startsWith("red:")) {
      int newRedCount = received.substring(4).toInt();
      if (newRedCount != bufferedRedCount) {
        bufferedRedCount = newRedCount;
        shouldUpdateDisplay = true;
      }
      digitalWrite(redLedPin, newRedCount >= 1 ? HIGH : LOW);
    } else if (received.startsWith("yellow:")) {
      int newYellowCount = received.substring(7).toInt();
      if (newYellowCount != bufferedYellowCount) {
        bufferedYellowCount = newYellowCount;
        shouldUpdateDisplay = true;
      }
      digitalWrite(yellowLedPin, newYellowCount >= 1 ? HIGH : LOW);
    }
  }

  // Aggiorna il display solo se i valori sono cambiati
  if (shouldUpdateDisplay) {
    updateDisplay();
    shouldUpdateDisplay = false;
  }
}

void updateDisplay() {
  // Calcola il conteggio totale
  int totalCount = bufferedRedCount + bufferedBlueCount + bufferedYellowCount + bufferedGreenCount;

  // Visualizza il conteggio sul display LCD
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Total Legos: ");
  lcd.print(totalCount);
  lcd.setCursor(0, 1);
  lcd.print("Red: ");
  lcd.print(bufferedRedCount);
  lcd.setCursor(0, 2);
  lcd.print("Blue: ");
  lcd.print(bufferedBlueCount);
  lcd.setCursor(0, 3);
  lcd.print("Yellow: ");
  lcd.print(bufferedYellowCount);
  lcd.print(" Green: ");
  lcd.print(bufferedGreenCount);
}
