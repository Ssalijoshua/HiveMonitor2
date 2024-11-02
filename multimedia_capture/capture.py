import os
import time
import config
import datetime
import subprocess
import soundfile as sf
import sounddevice as sd
from os import path, mkdir
from subprocess import call
from datetime import datetime
from picamera import PiCamera
from PIL import Image

class Capture:
    def __init__(self):
        self.camera = None
        self.picamera_version = config.picamera_version

        # setting  file paths for storing media files
        self.video_dir = config.base_dir+"multimedia/videos/"
        self.audio_dir = config.base_dir+"multimedia/audios/"
        self.image_dir = config.base_dir+"multimedia/images/"

        self.ensure_directories_exist()

    def ensure_directories_exist(self):
        # Ensure multimedia directories exist or create them
        self.recursive_mkdir(self.video_dir)
        self.recursive_mkdir(self.audio_dir)
        self.recursive_mkdir(self.image_dir)

    def recursive_mkdir(self, given_path):
        # Recursive directory creation
        directories = given_path.split("/")
        length = len(directories)
        given_path, start_index = ("/" + directories[1], 2) if given_path[0] == '/' else (directories[0], 1)
        if not path.isdir(given_path):
            mkdir(given_path)

        for index in range(start_index, length):
            if len(directories[index]) > 0:
                given_path = given_path + '/' + directories[index]
                if not path.isdir(given_path):
                    mkdir(given_path)

    def change_format(self, file_path):
        new_file_path = file_path
        if file_path.endswith(".h264"):
            new_file_path = file_path[:-5] + ".mp4"
            call("MP4Box -fps 30 -add " + file_path + " " + new_file_path, shell=True)
            call("rm " + file_path, shell=True)

        return new_file_path
    

    def init_camera(self):
        if self.camera is None:
            self.camera = PiCamera()
            self.camera.resolution = (640, 480)

    def capture_photo(self):
        time.sleep(2)
        img_path = self.image_dir + str(config.node_id) + '_' + config.timeString + '.jpg'
        if(config.picamera_version == 2):
            self.init_camera()
            self.camera.capture(img_path)
        elif(config.picamera_version == 3):
            image_result = subprocess.run(["libcamera-jpeg", "-o", img_path, "--width", "1920", "--height", "1080", "-n"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # print(image_result.stdout.decode("utf-8")) # Print the output as camera takes photo(if any)
            print(image_result.stderr.decode("utf-8"))   # Print the errors (if any)

        self.change_format(img_path)
        return img_path
    
    def capture_rotated_photo(self, angle):
        img_path = self.capture_photo()
        img = Image.open(img_path)
        # Rotate the image by the specified angle
        img = img.rotate(angle)
        # Save the rotated image back to the file
        img.save(img_path)
        return img_path

    def capture_video(self, capture_duration=10):
        vid_path = self.video_dir + str(config.node_id) + '_' + config.timeString + ".h264"
        if(config.picamera_version == 2):
            self.init_camera()
            self.camera.start_recording(vid_path)
            self.camera.wait_recording(capture_duration)
            self.camera.stop_recording()
        elif(config.picamera_version == 3):
            video_result = subprocess.run(["libcamera-vid", "-t",str(capture_duration * 1000), "-o", vid_path , "--width", "1280", "--height", "720", "-n"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # print(video_result.stdout.decode("utf-8")) # Print the output as camera takes videos(if any)
            print(video_result.stderr.decode("utf-8"))   # Print the errors (if any)
        print(vid_path)

        self.change_format(vid_path)
        vid_path = self.video_dir + str(config.node_id) + '_' + config.timeString + '.mp4'
        return vid_path
    
    def capture_rotated_video(self, vid_path):
        # Rotate the video by 90 degrees counterclockwise
        rotated_vid_path = self.video_dir + str(config.node_id) + '_' + config.timeString + "_rotated.h264"
        cmd = ["ffmpeg", "-i", vid_path, "-vf", "transpose=2", "-c:a", "copy", rotated_vid_path]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Delete the original video
        os.remove(vid_path)

        # Rename the rotated video to have the same name as the original video
        os.rename(rotated_vid_path, vid_path)

        self.change_format(vid_path)
        vid_path = self.video_dir + str(config.node_id) + '_' + config.timeString + '.mp4'
        return vid_path

    def capture_audio(self, capture_seconds=10):
        if config.pi_version == 0:
            return self.pizero_capture_audio(capture_seconds)
        else:
            sample_rate = 44100
            channels = 2
            duration = capture_seconds
            frames = int(duration * sample_rate)
            recording = sd.rec(frames, samplerate=sample_rate, channels=channels)
            sd.wait()
            aud_path = self.audio_dir + str(config.node_id) + '_' + config.timeString + '.wav'
            sf.write(aud_path, recording, sample_rate)
            return aud_path
    
    def merge_audio_video(self, video_path, audio_path):
        output_path = self.video_dir + str(config.node_id) + '_' + config.timeString + "_with_audio.mp4"
        cmd = ["ffmpeg", "-i", video_path, "-i", audio_path, "-c:v", "copy", "-c:a", "aac", "-strict", "experimental", output_path]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        # print(stderr.decode())

        # Delete the old video without audio
        os.remove(video_path)

        # Rename the final video to have the same name as the deleted video
        os.rename(output_path, video_path)

        return video_path
    
    def capture_video_with_audio(self, capture_duration=10):
        video_path = self.capture_video(capture_duration)
        audio_path = self.capture_audio(capture_duration)
        return self.merge_audio_video(video_path, audio_path)

    #for pi zero
    def pizero_capture_audio(self, capture_seconds=10):  
        audio_dir = "/home/pi/Desktop/HiveMonitor2/multimedia_capture/multimedia/audios/"
        filename = f"{audio_dir}{config.node_id}_{config.timeString}.wav"
        command = f"arecord -D plughw:0 -c1 -r 48000 -d {capture_seconds} -V mono -f S32_LE {filename}"
        
        try:
            subprocess.run(command, shell=True, check=True)
            return filename
        except subprocess.CalledProcessError as e:
            print(f"Failed to record audio: {e}")
            return None
    

    def run_capture(self):
        print("\n\n")

        timeString = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        print("DATE:", timeString)
        print()

        try:
            print("TAKING PHOTOS")
            print()
            image_path = self.capture_photo()
            print("New image taken at:", image_path)
            print()
        except Exception as e:
            print("Error capturing photos:", e)
        
        try:
            print("CAPTURING VIDEO")
            print()
            video_path = self.capture_video()
            print("New video taken at:", video_path)
            print()
        except Exception as e:
            print("Error capturing video:", e)
        
        try:
            print("CAPTURING AUDIO")
            print()
            audio_path = self.capture_audio()
            print("New audio taken at:", audio_path)
            print()
        except Exception as e:
            print("Error capturing audio:", e)
        
        print("\n\n")



if __name__ == "__main__":
    capture = Capture()
    capture.run_capture()