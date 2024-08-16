from flask import Flask, render_template, jsonify, send_file
from ftplib import FTP
from PIL import Image
from pysstv.color import PD160, Robot36, MartinM1
import pygame
import io
import os
import threading
import time
from natsort import natsorted

app = Flask(__name__)

pygame.mixer.init()  # 初始化 pygame.mixer

# FTP server details
FTP_SERVER = ''
FTP_USER = ''
FTP_PASS = ''
FTP_FOLDER = ''
LOCAL_FOLDER = ''
first_dir = None

# Global variables to track the current state
current_image = None
current_image_converted = None
current_progress = 0
audio_file_path = None
audio_length = 0


def download_image(ftp, filename):
    try:
        local_filepath = os.path.join('images', filename)
        if not os.path.exists('images'):
            os.makedirs('images')
        with open(local_filepath, 'wb') as f:
            ftp.retrbinary(f'RETR ' + filename, f.write)
        return local_filepath
    except:
        download_image(ftp, filename)


def convert_image_to_sstv(image_path):
    # 新的调整图像尺寸的函数
    def resize_image(image_path, size):
        with Image.open(image_path) as img:
            width, height = img.size
            if width < height:
                # 旋转图像90度
                img = img.rotate(90, expand=True)
            img = img.resize(size, Image.Resampling.LANCZOS)
            return img

    image = resize_image(image_path, (320, 256))

    sstv = MartinM1(image, samples_per_sec=44100, bits=16)
    buffer = io.BytesIO()
    sstv.write_wav(buffer)
    buffer.seek(0)
    return buffer


def save_audio_file(audio_buffer):
    global audio_file_path, audio_length
    audio_file_path = 'static/sstv_audio.wav'
    with open(audio_file_path, 'wb') as f:
        f.write(audio_buffer.read())
    audio_length = pygame.mixer.Sound(audio_file_path).get_length()



def sstv_worker(LOCAL_FOLDER = 'G:\\.H\\さわや\\', root='G:\\.H\\さわや\\'):  # 定义本地文件夹路径
    global current_image, current_progress, audio_file_path, audio_length, current_image_converted, first_dir

    # 获取所有图像文件
    all_files = os.listdir(LOCAL_FOLDER)

    # 使用 natsorted 对文件列表进行自然排序
    all_files = natsorted(all_files)

    for file_path in all_files:
        print(file_path)
        if first_dir is not None and first_dir not in file_path:
            continue
        else:
            first_dir = None
        if os.path.isdir(os.path.join(LOCAL_FOLDER, file_path)):
            sstv_worker(os.path.join(LOCAL_FOLDER, file_path), root)
        else:
            current_image = os.path.basename(os.path.join(LOCAL_FOLDER, file_path))
            current_progress = 0

            audio_buffer = convert_image_to_sstv(os.path.join(LOCAL_FOLDER, file_path))
            save_audio_file(audio_buffer)
            current_image_converted = (os.path.join(LOCAL_FOLDER, file_path)).replace(root, '')

            time.sleep(int(audio_length) + 10)  # 等待当前音频播放完毕


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/status')
def status():
    return jsonify({
        'current_image': current_image_converted,
        'current_progress': current_progress,
        'audio_length': audio_length
    })


@app.route('/audio')
def audio():
    if audio_file_path is not None:
        return send_file(audio_file_path, mimetype='audio/wav')


if __name__ == '__main__':
    threading.Thread(target=sstv_worker, daemon=True).start()
    app.run(host='0.0.0.0',
            port=5001,
            debug=True)
    pygame.mixer.quit()  # 清理 pygame.mixer
