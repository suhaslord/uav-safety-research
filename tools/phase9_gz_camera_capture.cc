#include <gz/msgs/image.pb.h>
#include <gz/msgs/pose_v.pb.h>
#include <gz/transport/Node.hh>

#include <atomic>
#include <chrono>
#include <csignal>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <optional>
#include <sstream>
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

  void OnPose(const gz::msgs::Pose_V &msg) {
    const double now = ElapsedSeconds();
    std::optional<PoseSample> best;
    for (const auto &pose : msg.pose()) {
      const std::string &name = pose.name();
      const bool is_camera = name.find("camera_link") != std::string::npos;
      const bool is_x500 = name.find("x500") != std::string::npos;
      if (!is_camera || !is_x500) {
        continue;
      }
      PoseSample sample;
      sample.valid = true;
      sample.name = name;
      sample.receive_elapsed_s = now;
      sample.x = pose.position().x();
      sample.y = pose.position().y();
      sample.z = pose.position().z();
      sample.qx = pose.orientation().x();
      sample.qy = pose.orientation().y();
      sample.qz = pose.orientation().z();
      sample.qw = pose.orientation().w();
      best = sample;
      break;
    }
    if (best) {
      std::lock_guard<std::mutex> lock(pose_mutex_);
      latest_pose_ = *best;
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
