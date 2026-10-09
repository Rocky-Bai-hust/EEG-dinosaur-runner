/*
  Arduino 脑电数据转发程序，用于 Chrome 小恐龙游戏联调。

  数据链路：
    TGAM / 脑电模块 --57600 硬件串口--> Arduino
    Arduino --57600 USB 串口--> Python 游戏端

  Python 端要求一行一帧文本数据：
    ATT:65,MED:48,SIG:0,BLINK:1,COUNT:3

  Arduino UNO/Nano 接线：
    TGAM TX  -> Arduino D0/RX
    TGAM RX  -> 不接
    TGAM GND -> Arduino GND
    Arduino USB -> 电脑

  注意：上传程序时先断开 TGAM TX -> D0/RX，烧录完成后再接回。
*/

// TGAM 脑电模块固定使用 57600 波特率。
// UNO/Nano 只有一个硬件串口，这里用同一个 Serial 从 D0/RX 接收 TGAM，
// 再通过 USB TX 发给电脑；电脑端 config.py 的 SERIAL_BAUD 也必须是 57600。
const unsigned long TGAM_BAUD = 57600;

const byte MAX_PAYLOAD_LENGTH = 169;
byte payloadData[MAX_PAYLOAD_LENGTH];

int signalQuality = 200;  // 信号质量 PoorSignal：0 表示好，200 通常表示未佩戴或接触差。
int attention = 0;        // 专注度 Attention，范围 0-100。
int meditation = 0;       // 放松度 Meditation，范围 0-100。
unsigned long blinkCount = 0;
int lastRawValue = 0;
long blinkStrength = 0;
bool rawWasAboveBlinkThreshold = false;
bool eegDigestReady = false;
unsigned long lastBlinkMs = 0;

const int GOOD_SIGNAL_MAX = 50;
const long BLINK_RAW_THRESHOLD = 1050;
const unsigned long BLINK_REFRACTORY_MS = 350;

int readByteBlocking(Stream &stream) {
  while (!stream.available()) {
    // 等待 TGAM 发来下一个字节；游戏主循环在电脑端运行，这里阻塞不会卡住游戏。
  }
  return stream.read();
}

bool readTgamPacket(byte *payload, byte &payloadLength) {
  // 查找 TGAM 数据包的两个同步字节：0xAA 0xAA。
  if (readByteBlocking(Serial) != 0xAA) {
    return false;
  }
  if (readByteBlocking(Serial) != 0xAA) {
    return false;
  }

  payloadLength = readByteBlocking(Serial);
  if (payloadLength == 0 || payloadLength > MAX_PAYLOAD_LENGTH) {
    return false;
  }

  int checksumSum = 0;
  for (byte i = 0; i < payloadLength; i++) {
    payload[i] = readByteBlocking(Serial);
    checksumSum += payload[i];
  }

  byte checksum = readByteBlocking(Serial);
  byte generatedChecksum = 255 - (checksumSum & 0xFF);
  return checksum == generatedChecksum;
}

void sendGameFrame(bool blink) {
  // 这里的输出格式必须和 eeg_serial_reader.py 的 parse_line() 保持一致。
  Serial.print("ATT:");
  Serial.print(attention);
  Serial.print(",MED:");
  Serial.print(meditation);
  Serial.print(",SIG:");
  Serial.print(signalQuality);
  Serial.print(",BLINK:");
  Serial.print(blink ? 1 : 0);
  Serial.print(",COUNT:");
  Serial.println(blinkCount);
}

int parseRawValue(byte highByte, byte lowByte) {
  long rawValue = ((long)highByte << 8) | lowByte;
  if (rawValue >= 32768) {
    rawValue -= 65536;
  }
  return (int)rawValue;
}

bool parseRawSmallPacket(byte *payload, byte payloadLength) {
  if (payloadLength != 0x04 || payload[0] != 0x80 || payload[1] != 0x02) {
    return false;
  }

  lastRawValue = parseRawValue(payload[2], payload[3]);

  // 信号差或 ATT/MED 还没算出来时，RAW 波形不能拿来判断眨眼。
  // 否则接触噪声、佩戴调整动作会被误认为 BLINK。
  if (signalQuality > GOOD_SIGNAL_MAX || !eegDigestReady) {
    rawWasAboveBlinkThreshold = false;
    blinkStrength = 0;
    return true;
  }

  long rawMagnitude = abs((long)lastRawValue);
  unsigned long now = millis();
  bool blinkThisFrame = false;

  if (rawMagnitude >= BLINK_RAW_THRESHOLD) {
    blinkStrength = rawMagnitude;
    if (!rawWasAboveBlinkThreshold && now - lastBlinkMs >= BLINK_REFRACTORY_MS) {
      blinkCount++;
      lastBlinkMs = now;
      blinkThisFrame = true;
    }
    rawWasAboveBlinkThreshold = true;
  } else {
    rawWasAboveBlinkThreshold = false;
  }

  if (blinkThisFrame) {
    sendGameFrame(true);
  }
  return true;
}

bool parseDigestBigPacket(byte *payload, byte payloadLength) {
  if (payloadLength != 0x20) {
    return false;
  }

  // 数据流解析格式中的固定大包:
  // [0]=0x02 [1]=Signal, [28]=0x04 [29]=Attention, [30]=0x05 [31]=Meditation
  if (payload[0] != 0x02 || payload[28] != 0x04 || payload[30] != 0x05) {
    return false;
  }

  signalQuality = payload[1];
  attention = payload[29];
  meditation = payload[31];
  eegDigestReady = signalQuality <= GOOD_SIGNAL_MAX && (attention > 0 || meditation > 0);

  // 大包本身约 1 秒一次，收到有效大包就立即发给电脑端。
  sendGameFrame(false);
  return true;
}

void parseTgamPayload(byte *payload, byte payloadLength) {
  if (parseRawSmallPacket(payload, payloadLength)) {
    return;
  }
  parseDigestBigPacket(payload, payloadLength);
}

void setup() {
  Serial.begin(TGAM_BAUD);

  // 启动后先发送一帧初始数据，方便 Python HUD 尽快显示串口状态。
  sendGameFrame(false);
}

void loop() {
  byte payloadLength = 0;
  if (readTgamPacket(payloadData, payloadLength)) {
    parseTgamPayload(payloadData, payloadLength);
  }
}
