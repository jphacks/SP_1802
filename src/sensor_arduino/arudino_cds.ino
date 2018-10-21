int pin = 0; //センサーのピン番号
int get_a0 = 0; //センサーデータ取得
int flag = 0;
int s=0;
void setup(){
  Serial.begin(9600);

}

void loop()
{
  //Serial.println("hello world");
  get_a0 = analogRead(pin); // 照度センサーからデータを取得
  Serial.println(get_a0);
  //s = 0;
  //Serial.println(s); // シリアルモニタに出力
  if ( get_a0 > 100 ) {
    if(flag == 1){
      s = 2000;//ポストのフタOpen
      Serial.println(s); // シリアルモニタに出力
    }
    flag=1;
  } else if ( get_a0 <= 100 ) {
    if(flag == 0){
      s = 1000;//ポストのフタClose
      Serial.println(s); // シリアルモニタに出力
    }
    flag=0;
  }
  delay(1000);
}
