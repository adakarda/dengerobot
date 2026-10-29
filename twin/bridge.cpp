// Dijital ikiz koprusu: robot firmware'indeki RobotLogic'i stdin/stdout uzerinden MuJoCo ikizine baglar.
// Her satir bir 5 ms adimi:
//   girdi : t ax ay az gx gy gz encL encR vbat vchg irL irR motorPower gloveNew gloveCmd task
//   cikti : en dutyL dutyR mode dock thetaDeg
#include <cstdio>
#include <cstring>

#include "robot_logic.h"

int main() {
  cdtp::RobotLogic logic;
  char line[512];
  uint16_t seq = 0;
  int lastTask = -1;
  while (std::fgets(line, sizeof line, stdin)) {
    if (!std::strncmp(line, "quit", 4)) break;
    cdtp::RobotInputs in;
    int en_mp, gnew, gcmd, task;
    long eL, eR, iL, iR;
    int n = std::sscanf(line, "%f %f %f %f %f %f %f %ld %ld %f %f %ld %ld %d %d %d %d", &in.t, &in.imu.acc[0],
                        &in.imu.acc[1], &in.imu.acc[2], &in.imu.gyro[0], &in.imu.gyro[1], &in.imu.gyro[2], &eL, &eR,
                        &in.vbat, &in.vcharge, &iL, &iR, &en_mp, &gnew, &gcmd, &task);
    if (n != 17) {
      std::printf("ERR %d\n", n);
      std::fflush(stdout);
      continue;
    }
    if (task != lastTask) {
      logic.setTask((cdtp::Task)task);
      lastTask = task;
    }
    in.encL = eL;
    in.encR = eR;
    in.irL = iL;
    in.irR = iR;
    in.motorPower = en_mp != 0;
    in.gloveNew = gnew != 0;
    if (in.gloveNew) {
      cdtp::GlovePacket p{};
      p.cmd = (uint8_t)gcmd;
      p.seq = seq++;
      cdtp::sealPacket(p);
      in.glove = p;
    }
    cdtp::RobotOutputs o = logic.step(in);
    std::printf("%d %.5f %.5f %d %d %.3f\n", o.motorEnable ? 1 : 0, o.dutyL, o.dutyR, (int)logic.mode(),
                (int)logic.dockState(), logic.thetaDeg());
    std::fflush(stdout);
  }
  return 0;
}
