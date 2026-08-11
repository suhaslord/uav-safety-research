#include <gz/msgs/image.pb.h>
#include <gz/msgs/pose_v.pb.h>
#include <gz/transport/Node.hh>

#include <atomic>
#include <chrono>
#include <cmath>
#include <csignal>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>

namespace fs = std::filesystem;

namespace {

std::atomic<bool> g_stop{false};

void HandleSignal(int) {
  g_stop.store(true);
}

struct PoseSample {
  bool valid{false};
  std::string name;
  double receive_elapsed_s{0.0};
  double x{0.0};
  double y{0.0};
  double z{0.0};
  double qx{0.0};
  double qy{0.0};
  double qz{0.0};
  double qw{1.0};
};

struct Quaternion {
  double x{0.0};
  double y{0.0};
  double z{0.0};
  double w{1.0};
};

Quaternion Normalize(Quaternion q) {
  const double norm = std::sqrt(q.x * q.x + q.y * q.y + q.z * q.z + q.w * q.w);
  if (norm < 1e-12) {
    throw std::runtime_error("Gazebo pose quaternion has zero norm");
  }
  q.x /= norm;
  q.y /= norm;
  q.z /= norm;
  q.w /= norm;
  return q;
}

Quaternion Multiply(const Quaternion &a, const Quaternion &b) {
  return Normalize({
      a.w * b.x + a.x * b.w + a.y * b.z - a.z * b.y,
      a.w * b.y - a.x * b.z + a.y * b.w + a.z * b.x,
      a.w * b.z + a.x * b.y - a.y * b.x + a.z * b.w,
      a.w * b.w - a.x * b.x - a.y * b.y - a.z * b.z,
  });
}

void RotateVector(const Quaternion &raw_q, double x, double y, double z,
                  double &out_x, double &out_y, double &out_z) {
  const Quaternion q = Normalize(raw_q);
  const double tx = 2.0 * (q.y * z - q.z * y);
  const double ty = 2.0 * (q.z * x - q.x * z);
  const double tz = 2.0 * (q.x * y - q.y * x);
  out_x = x + q.w * tx + (q.y * tz - q.z * ty);
  out_y = y + q.w * ty + (q.z * tx - q.x * tz);
  out_z = z + q.w * tz + (q.x * ty - q.y * tx);
}

std::string ExtractModelName(const std::string &image_topic) {
  const std::string marker = "/model/";
  const std::size_t begin = image_topic.find(marker);
  if (begin == std::string::npos) {
    throw std::runtime_error("camera topic does not contain /model/: " + image_topic);
  }
  const std::size_t name_begin = begin + marker.size();
  const std::size_t end = image_topic.find('/', name_begin);
  if (end == std::string::npos || end == name_begin) {
    throw std::runtime_error("camera topic does not expose a model name: " + image_topic);
  }
  return image_topic.substr(name_begin, end - name_begin);
}

bool ModelNameMatches(const std::string &pose_name, const std::string &model_name) {
  if (pose_name == model_name) {
    return true;
  }
  const std::string scoped_suffix = "::" + model_name;
  return pose_name.size() > scoped_suffix.size() &&
         pose_name.compare(pose_name.size() - scoped_suffix.size(), scoped_suffix.size(), scoped_suffix) == 0;
}

PoseSample ComposeWorldCamera(const PoseSample &world_model, const PoseSample &model_camera,
                              const std::string &model_name, double receive_elapsed_s) {
  const Quaternion q_world_model{world_model.qx, world_model.qy, world_model.qz, world_model.qw};
  const Quaternion q_model_camera{model_camera.qx, model_camera.qy, model_camera.qz, model_camera.qw};
  double rx = 0.0;
  double ry = 0.0;
  double rz = 0.0;
  RotateVector(q_world_model, model_camera.x, model_camera.y, model_camera.z, rx, ry, rz);
  const Quaternion q_world_camera = Multiply(q_world_model, q_model_camera);

  PoseSample sample;
  sample.valid = true;
  sample.name = model_name + "::" + model_camera.name;
  sample.receive_elapsed_s = receive_elapsed_s;
  sample.x = world_model.x + rx;
  sample.y = world_model.y + ry;
  sample.z = world_model.z + rz;
  sample.qx = q_world_camera.x;
  sample.qy = q_world_camera.y;
  sample.qz = q_world_camera.z;
  sample.qw = q_world_camera.w;
  return sample;
}

std::string CsvEscape(const std::string &value) {
  if (value.find_first_of(",\"\n\r") == std::string::npos) {
    return value;
  }
  std::string out = "\"";
  for (const char ch : value) {
    if (ch == '\"') {
      out += "\"\"";
    } else {
      out += ch;
    }
  }
  out += "\"";
  return out;
}

class CameraCapture {
 public:
  CameraCapture(std::string image_topic, std::string pose_topic, fs::path out_dir,
                std::size_t save_every, std::size_t max_frames)
      : image_topic_(std::move(image_topic)),
        pose_topic_(std::move(pose_topic)),
        model_name_(ExtractModelName(image_topic_)),
        out_dir_(std::move(out_dir)),
        save_every_(save_every),
        max_frames_(max_frames),
        started_(std::chrono::steady_clock::now()) {
    fs::create_directories(out_dir_ / "frames");
    metadata_.open(out_dir_ / "capture_frames.csv", std::ios::out | std::ios::trunc);
    if (!metadata_) {
      throw std::runtime_error("failed to open capture metadata output");
    }
    metadata_ << "frame_index,image_message_index,image_stamp_s,receive_elapsed_s,width,height,step,pixel_format_type,data_size,frame_path,camera_pose_valid,camera_pose_name,camera_pose_receive_elapsed_s,camera_x_m,camera_y_m,camera_z_m,camera_qx,camera_qy,camera_qz,camera_qw\n";
    metadata_.flush();
  }

  bool Start() {
    if (!node_.Subscribe(pose_topic_, &CameraCapture::OnPose, this)) {
      std::cerr << "Failed to subscribe to pose topic: " << pose_topic_ << std::endl;
      return false;
    }
    if (!node_.Subscribe(image_topic_, &CameraCapture::OnImage, this)) {
      std::cerr << "Failed to subscribe to image topic: " << image_topic_ << std::endl;
      return false;
    }
    return true;
  }

  bool Done() const {
    return max_frames_ > 0 && captured_.load() >= max_frames_;
  }

  std::size_t Captured() const { return captured_.load(); }
  std::size_t ImageMessages() const { return image_messages_.load(); }

 private:
  double ElapsedSeconds() const {
    return std::chrono::duration<double>(std::chrono::steady_clock::now() - started_).count();
  }

  static double HeaderStampSeconds(const gz::msgs::Image &msg) {
    if (!msg.has_header()) {
      return -1.0;
    }
    const auto &stamp = msg.header().stamp();
    return static_cast<double>(stamp.sec()) + static_cast<double>(stamp.nsec()) * 1e-9;
  }

  static PoseSample FromPoseMessage(const gz::msgs::Pose &pose, double now) {
    PoseSample sample;
    sample.valid = true;
    sample.name = pose.name();
    sample.receive_elapsed_s = now;
    sample.x = pose.position().x();
    sample.y = pose.position().y();
    sample.z = pose.position().z();
    sample.qx = pose.orientation().x();
    sample.qy = pose.orientation().y();
    sample.qz = pose.orientation().z();
    sample.qw = pose.orientation().w();
    return sample;
  }

  void OnPose(const gz::msgs::Pose_V &msg) {
    const double now = ElapsedSeconds();
    std::optional<PoseSample> model_pose;
    std::optional<PoseSample> camera_local_pose;
    int camera_best_score = -1;

    for (const auto &pose : msg.pose()) {
      const std::string &name = pose.name();
      if (ModelNameMatches(name, model_name_)) {
        model_pose = FromPoseMessage(pose, now);
      }

      if (name.find("camera_link") == std::string::npos) {
        continue;
      }
      int score = 1;
      if (name.find("mono_cam") != std::string::npos) {
        score += 10;
      }
      if (name.find("x500") != std::string::npos) {
        score += 20;
      }
      if (score > camera_best_score) {
        camera_local_pose = FromPoseMessage(pose, now);
        camera_best_score = score;
      }
    }

    // The regular Gazebo PosePublisher stream contains a moving model pose and
    // fixed child-link transforms. Earlier Phase 9 diagnostics incorrectly
    // stored the fixed camera_link transform as a world pose. Fail closed until
    // both pieces are present, then explicitly compose world_T_model * model_T_camera.
    if (!model_pose || !camera_local_pose) {
      return;
    }

    const PoseSample composed = ComposeWorldCamera(*model_pose, *camera_local_pose, model_name_, now);
    bool first_pose = false;
    {
      std::lock_guard<std::mutex> lock(pose_mutex_);
      first_pose = !latest_pose_.valid;
      latest_pose_ = composed;
    }
    if (first_pose) {
      std::cout << "Phase 9 camera world pose composed from model=" << model_pose->name
                << " link=" << camera_local_pose->name
                << " scoped_camera=" << composed.name << std::endl;
    }
  }

  void OnImage(const gz::msgs::Image &msg) {
    const std::size_t message_index = image_messages_.fetch_add(1);
    if (save_every_ == 0 || (message_index % save_every_) != 0) {
      return;
    }
    if (Done()) {
      return;
    }

    const std::size_t frame_index = captured_.fetch_add(1);
    const fs::path relative = fs::path("frames") / (FrameName(frame_index) + ".bin");
    const fs::path path = out_dir_ / relative;
    {
      std::ofstream frame(path, std::ios::binary | std::ios::out | std::ios::trunc);
      if (!frame) {
        std::cerr << "Failed to open frame output: " << path << std::endl;
        g_stop.store(true);
        return;
      }
      frame.write(msg.data().data(), static_cast<std::streamsize>(msg.data().size()));
    }

    PoseSample pose;
    {
      std::lock_guard<std::mutex> lock(pose_mutex_);
      pose = latest_pose_;
    }

    const double receive_elapsed = ElapsedSeconds();
    metadata_ << frame_index << ','
              << message_index << ','
              << std::setprecision(17) << HeaderStampSeconds(msg) << ','
              << receive_elapsed << ','
              << msg.width() << ','
              << msg.height() << ','
              << msg.step() << ','
              << static_cast<int>(msg.pixel_format_type()) << ','
              << msg.data().size() << ','
              << CsvEscape(relative.generic_string()) << ','
              << (pose.valid ? "true" : "false") << ','
              << CsvEscape(pose.name) << ','
              << pose.receive_elapsed_s << ','
              << pose.x << ',' << pose.y << ',' << pose.z << ','
              << pose.qx << ',' << pose.qy << ',' << pose.qz << ',' << pose.qw
              << '\n';
    metadata_.flush();
  }

  static std::string FrameName(std::size_t index) {
    std::ostringstream out;
    out << "frame_" << std::setw(6) << std::setfill('0') << index;
    return out.str();
  }

  gz::transport::Node node_;
  std::string image_topic_;
  std::string pose_topic_;
  std::string model_name_;
  fs::path out_dir_;
  std::size_t save_every_;
  std::size_t max_frames_;
  std::chrono::steady_clock::time_point started_;
  std::atomic<std::size_t> captured_{0};
  std::atomic<std::size_t> image_messages_{0};
  mutable std::mutex pose_mutex_;
  PoseSample latest_pose_;
  std::ofstream metadata_;
};

}  // namespace

int main(int argc, char **argv) {
  if (argc < 4 || argc > 6) {
    std::cerr << "Usage: " << argv[0]
              << " IMAGE_TOPIC POSE_TOPIC OUT_DIR [SAVE_EVERY=30] [MAX_FRAMES=90]\n";
    return 2;
  }

  const std::string image_topic = argv[1];
  const std::string pose_topic = argv[2];
  const fs::path out_dir = argv[3];
  const std::size_t save_every = argc >= 5 ? static_cast<std::size_t>(std::stoul(argv[4])) : 30;
  const std::size_t max_frames = argc >= 6 ? static_cast<std::size_t>(std::stoul(argv[5])) : 90;
  if (save_every == 0) {
    std::cerr << "SAVE_EVERY must be >= 1\n";
    return 2;
  }

  std::signal(SIGINT, HandleSignal);
  std::signal(SIGTERM, HandleSignal);

  try {
    CameraCapture capture(image_topic, pose_topic, out_dir, save_every, max_frames);
    if (!capture.Start()) {
      return 3;
    }
    std::cout << "Phase 9 Gazebo camera capture subscribed to image=" << image_topic
              << " pose=" << pose_topic << std::endl;
    while (!g_stop.load() && !capture.Done()) {
      std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    std::cout << "Phase 9 camera capture complete: image_messages="
              << capture.ImageMessages() << " saved_frames=" << capture.Captured() << std::endl;
  } catch (const std::exception &exc) {
    std::cerr << "Camera capture failed: " << exc.what() << std::endl;
    return 4;
  }
  return 0;
}
