//********************************************************************
//*超音波センサをを用いて不在票の投函を検知するプログラム
//********************************************************************
int trig = 8; // 出力ピン
int echo = 9; // 入力ピン
int s = 0;

const int led_pin_sensor_on = 13;
const int led_pin_detection = 12;

void setup() {
  Serial.println("Auruino start");
  Serial.begin(9600);
  pinMode(trig,OUTPUT);
  pinMode(echo,INPUT);
  pinMode(led_pin_detection, OUTPUT);
  pinMode(led_pin_sensor_on, OUTPUT);
  digitalWrite(led_pin_sensor_on, HIGH);
  delay(1500);
  digitalWrite(led_pin_detection,LOW);
  digitalWrite(led_pin_sensor_on, LOW);
}
void loop() {
    delay(50);
    digitalWrite(led_pin_detection, LOW);
    digitalWrite(led_pin_sensor_on, LOW);
    //digitalWrite(led_pin_sensor_on, LOW);
    // 超音波の出力終了
    digitalWrite(trig,LOW);
    delayMicroseconds(1);
    // 超音波を出力
    digitalWrite(trig,HIGH);
    delayMicroseconds(11);
    // 超音波を出力終了
    digitalWrite(trig,LOW);
    // 出力した超音波が返って来る時間を計測
    int t = pulseIn(echo,HIGH);
    // 計測した時間と音速から反射物までの距離を計算
    float distance = t*0.017;
    // 計算結果をシリアル通信で出力
    //Serial.print(distance);
    //Serial.println(" cm");
    delay(50);
      if ((0 < distance) && (distance < 6.0)){// ポストのフタOpen
      //s = 2000;
      digitalWrite(led_pin_detection, HIGH);
      digitalWrite(led_pin_sensor_on, HIGH);
      Serial.println("O"); // シリアルモニタに出力
      delay(50);
    }else if ((distance >= 6) || (distance <-50)){// ポストのフタClose
      //s = 1000;
      //digitalWrite(led_pin_sensor_on, HIGH);
      Serial.println("C"); // シリアルモニタに出力
      delay(50);  
    }else{
      Serial.println("E");
    }
    delay(500);
}
