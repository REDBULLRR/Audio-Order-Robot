
# =========== 去除 jieba 的訊息 ==============
import jieba
import logging
jieba.setLogLevel(logging.INFO)

'''note: 想去除的訊息例
Building prefix dict from the default dictionary ...
Loading model from cache /tmp/jieba.cache
Loading model cost 0.408 seconds.
Prefix dict has been built successfully.
'''

# ===========  kill jack and alsa error message ================
# --> success on killing both jack and alsa!!!!!!!!!!!!! 
# Code by: https://github.com/spatialaudio/python-sounddevice/issues/10
import contextlib
import os
import sys

@contextlib.contextmanager
def ignore_stderr():
    devnull = os.open(os.devnull, os.O_WRONLY)
    old_stderr = os.dup(2)
    sys.stderr.flush()
    os.dup2(devnull, 2)
    os.close(devnull)
    try:
        yield
    finally:
        os.dup2(old_stderr, 2)
        os.close(old_stderr)

# ================== Audio to Text ===================
# 將標準輸出重定向到檔案
sys.stdout = open('log.txt', 'a')
import speech_recognition as sr
import audioop
import time 
# 將標準輸出還原為終端機
sys.stdout = sys.__stdout__


def listen_by_file(path):
    # 將標準輸出重定向到檔案
    sys.stdout = open('log.txt', 'a')
    r = sr.Recognizer()
    WAV = sr.AudioFile(path)
    with WAV as source:
        audio = r.record(source)
      
    customer_say = r.recognize_google(audio, language='zh-TW')
    # 將標準輸出還原為終端機
    sys.stdout = sys.__stdout__
    return customer_say


def record_audio(filename, silence_threshold=1000):
    '''聽人說話，如果沉默太久會自動停止錄音'''
    chunk = 1024
    format = pyaudio.paInt16
    channels = 1
    rate = 44100
    
    with ignore_stderr():
        p = pyaudio.PyAudio()

    stream = p.open(format=format,
                    channels=channels,
                    rate=rate,
                    input=True,
                    frames_per_buffer=chunk)

    print("聆聽中...")
    start_time = time.time()
    frames = []
    silent_frames = 0
    
    while True:
        data = stream.read(chunk)
        frames.append(data)
        rms = audioop.rms(data, 2)  # 計算聲音頻率的 RMS 級別
        
        # 計時，讓使用者有機會講話
        current_time = time.time()
        elapsed_time = current_time - start_time

        if rms < silence_threshold:
            silent_frames += 1
        else:
            silent_frames = 0

        if silent_frames >= int(rate / chunk) and elapsed_time >= 2:  # 如果連續多個塊都是靜音，則停止錄音，而且至少要聽 2 秒鐘
            break

    print("處理中....")

    stream.stop_stream()
    stream.close()
    p.terminate()

    wf = wave.open(filename, 'wb')
    wf.setnchannels(channels)
    wf.setsampwidth(p.get_sample_size(format))
    wf.setframerate(rate)
    wf.writeframes(b''.join(frames))
    wf.close()


def listen():
    path = 'humansay.wav'
    error_times_tol = 3 # 可忍受的語音輸入錯誤次數
    customer_say = ""
    trial = 0
    
    while(trial<error_times_tol):
        record_audio(path) # 錄音
        
        sys.stdout = open('log.txt', 'a') # 將標準輸出重定向到檔案

        # 解析客人講了什麼
        r = sr.Recognizer()
        WAV = sr.AudioFile(path)
        with WAV as source:
            audio = r.record(source)
        try:
            customer_say = r.recognize_google(audio, language='zh-TW')
            break
            
        except: # 無法辨認顧客說的話
            # 將標準輸出還原為終端機
            sys.stdout = sys.__stdout__
            print("[無法辨識您說的話，請等﹝聆聽中﹞字樣出現時再說一次]")
            trial +=1
            continue
            
    if customer_say=="":
        print("點單聽取失敗太多次，請重啟點餐機器人")
        os._exit(0) 
            
    
    # 將標準輸出還原為終端機
    sys.stdout = sys.__stdout__
    return customer_say
    

# ================== Text to Text =====================

# 將標準輸出重定向到檔案
sys.stdout = open('log.txt', 'a')
from opencc import OpenCC
cc = OpenCC('s2twp')

from collections import defaultdict
from collections import Counter
import pickle

# 將標準輸出還原為終端機
sys.stdout = sys.__stdout__

class CustomerOrder():
    def __init__(self):
        self.menu_set=['嫩煎雞腿堡','麥香雞','麥香魚','雙層牛肉吉士堡','兒童餐','大麥客','大麥克','六塊雞塊']
        self.menu_drink=['可樂','雪碧','檸檬紅茶','無糖綠茶','玉米濃湯']
        self.menu_side=['薯條','中薯','大薯','沙拉','雞塊','冰炫風','蘋果派']
        self.positive=['要','可以']
        self.negative=['這樣就好','先這樣',"不要","不用","不需要"]
        self.drop=['謝謝','謝','感恩']
        self.upgrade=['加大']
        self.menu=self.menu_set+self.menu_drink+self.menu_side
        
        self.set= defaultdict(lambda:{"份數":0,"飲料":[],"副餐":[]})
        self.single=defaultdict(lambda:"default")
        self.total=0
        self.model=None
        # 將標準輸出重定向到檔案
        sys.stdout = open('log.txt', 'a')
        #with open('model.pickle', 'rb') as f:
            #modell = pickle.load(f)
            #self.model = modell
        # 將標準輸出還原為終端機
        sys.stdout = sys.__stdout__

    def setEmpty(self,mainCourse):
        if(len(self.set[mainCourse]['飲料'])<self.set[mainCourse]['份數']):
            return str("飲料")
        elif (len(self.set[mainCourse]['副餐'])<self.set[mainCourse]["份數"]):
            return str('副餐')
        return None

    def frenchfries(self,x,sentence):
      if(x=="薯條" and "加大" in sentence):
         x="大薯"
      elif((x=="薯條" and "加大" not in sentence)):
        new_speak("薯條要加大嗎")
        sentence=listen()
        ans=self.answer(sentence)
        if(ans==2):
          x="大薯"
        else:
          x="中薯"
      return x

    def add(self,sentence,mainCourse):
        quantity_list = {'一':1,'二':2,'兩':2,'三':3,'四':4
                              ,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10}
        quantity=1
        for temp in list(quantity_list.keys()):
            if temp in sentence:
                quantity=quantity_list[temp]
                
        if mainCourse!=None:
            for x in self.menu:
                if x in sentence:
                    if x in self.menu_side:
                        x=self.frenchfries(x,sentence)

                        if(quantity>1):
                            for i in range(quantity):
                                self.set[mainCourse]["副餐"].append(x)
                        else:
                            self.set[mainCourse]["副餐"].append(x)
                    if x in self.menu_drink:
                        if(quantity>1):
                            for i in range(quantity):
                                self.set[mainCourse]["飲料"].append(x)
                        else:
                            self.set[mainCourse]["飲料"].append(x)
        else:
            for x in self.menu:
                if x in sentence:
                    if x in self.menu_set:
                        self.set[x]["份數"]+=quantity
                    elif x in self.menu_drink:
                        for key in list(self.set.keys()):
                          if(len(key)>0):
                            self.set[key]["飲料"].append(x)
                    elif x in self.menu_side:
                        for key in list(self.set.keys()):
                          if(len(key)>0):
                            x=self.frenchfries(x,sentence)
                            self.set[key]["副餐"].append(x)  
                    else:
                        self.single[x]=quantity
                        
    def orderSet(self,mainCourse):
        #判斷套餐是否有空的
        if(self.setEmpty(mainCourse)=='飲料'):
            new_speak(mainCourse+"套餐飲料要配什麼呢")
        
        if(self.setEmpty(mainCourse)=='副餐'):
            new_speak(mainCourse+"套餐副餐要配什麼呢")
        
    def showOrder(self):
        print("\n\n以下為您的餐點:")
        key=list(self.set.keys())
        for x in key:
            print(self.set[x]['份數'],"份",x,"套餐")
            drink=Counter(self.set[x]['飲料'])
            side=Counter(self.set[x]['副餐'])
            
            keys=list(drink.keys())
            print("飲料是:")
            for key in keys:
                print(key,drink[key],"杯")
            
            keys=list(side.keys())
            print("副餐是:")
            for key in keys:
                print(key,side[key],"份")
                
        key=list(self.single.keys())
        for x in key:
            print("單點",x,self.single[x],"份")
    
    def ending(sentence):
        return True

    def answer(self,sentence):
      for x in self.menu:
        if x in sentence:
          return 1

      #清除禮貌性字串，避免影響正負面判定
      for x in self.drop:
        if x in sentence:
          sentence=sentence.replace(x,' ')

      for x in self.positive:
        if x in sentence:
          if "不要" in sentence:
            return 3
          else:
            return 2
          
      for x in self.negative:
        if x in sentence:
          return 3

      # 將標準輸出重定向到檔案
      sys.stdout = open('log.txt', 'a')
      #result = self.model.predict([sentence])
      result=[1,1]
      # 將標準輸出還原為終端機
      sys.stdout = sys.__stdout__
      if int(result[0]): #if the sentence is positive
        return 2
      else:
        return 3
                    
    def qa(self,stop,repeat):
        if(stop==0):
            new_speak("請看一下螢幕餐點是否正確喔")
            return False
        
        print("customer:")
        if repeat==0 :
          #path=input()
          #sentence_s=listen_by_file(path) # 使用者講話
          #sentence=cc.convert(sentence_s)
          sentence=listen()
          print(sentence)
          self.add(sentence,None)
        
            
        for my_mainCourse in list(self.set.keys()):
            self.reh(my_mainCourse)
        
        new_speak("請問還要點其他餐點嗎")
        #path=input()
        #sentence_s=listen_by_file(path) # 使用者講話
        #sentence=cc.convert(sentence_s)
        sentence=listen()
        ans=self.answer(sentence)
        if(ans==1):
          self.add(sentence,None)
          self.qa(1,1)

        elif(ans==2):
          new_speak("請問還需要什麼呢")
          self.qa(1,0)

        elif(ans==3):
          self.qa(0,0)

        
    def reh(self,mainCourse):
        if(self.setEmpty(mainCourse)==None):
            return True
        self.orderSet(mainCourse)
        print("customer: ")
        #path=input()
        #sentence_s=listen_by_file(path) # 使用者講話
        #sentence=cc.convert(sentence_s)
        sentence=listen()
        print(sentence)
        self.add(sentence,mainCourse)
        self.reh(mainCourse)
  


# =================== Text to Audio ======================
# 將標準輸出重定向到檔案
sys.stdout = open('log.txt', 'a')

# Ref: https://github.com/maotingyang/Coffee-Bot/blob/master/voice_orderbot.py
from gtts import gTTS
#from TTS.api import TTS
import time
from pygame import mixer
import tempfile
import wave
import pyaudio
import os

# 將標準輸出還原為終端機
sys.stdout = sys.__stdout__

def play_wav_file(file_path):
    chunk = 1024
    # 將標準輸出重定向到檔案
    sys.stdout = open('log.txt', 'a')

    # 打開 WAV 檔案
    with wave.open(file_path, 'rb') as wav_file:
        # 初始化音訊播放
        with ignore_stderr():
            audio = pyaudio.PyAudio()
        stream = audio.open(format=audio.get_format_from_width(wav_file.getsampwidth()),
                            channels=wav_file.getnchannels(),
                            rate=wav_file.getframerate(),
                            output=True)

        # 播放音訊
        data = wav_file.readframes(chunk)
        while data:
            stream.write(data)
            data = wav_file.readframes(chunk)

        # 停止音訊播放
        stream.stop_stream()
        stream.close()
        audio.terminate()
        
    # 將標準輸出還原為終端機
    sys.stdout = sys.__stdout__

def speak(sentence):
    '''機器人說話'''
    # List available 🐸TTS models and choose the first one
    model_name = 'tts_models/zh-CN/baker/tacotron2-DDC-GST'
    
    # 將標準輸出重定向到檔案
    sys.stdout = open('log.txt', 'a')
    
    # Init TTS
    tts = TTS(model_name)
    wav_path = "robotsay.wav"
    tts.tts_to_file(text=sentence+"。", file_path=wav_path)
    
    # 將標準輸出還原為終端機
    sys.stdout = sys.__stdout__
    
    print("bot: "+sentence)
    play_wav_file(wav_path)

    
def new_speak(sentence):
    print("bot:"+sentence)

    with tempfile.NamedTemporaryFile(delete=True) as fp:
        tts=gTTS(text=sentence, lang='zh-TW')
        tts.save('{}.mp3'.format(fp.name))
        mixer.init()
        mixer.music.load('{}.mp3'.format(fp.name))
        mixer.music.play(1)

    # 講完話之後才聽客人講話
    while mixer.music.get_busy():
        continue
        


# ============== Main Function ===============
if __name__ == '__main__':
    print("(ﾉ>ω<)ﾉ---點餐機器人啟動---(ﾉ>ω<)ﾉ")
    print("... 啟動中，請稍候 ...")
    
    # 將標準輸出重定向到檔案
    sys.stdout = open('log.txt', 'a')
    
    #initializing customer
    customer=CustomerOrder()
    
    # 將標準輸出還原為終端機
    sys.stdout = sys.__stdout__
    
    new_speak("你好，請問今天要來點什麼")
    done=customer.qa(1,0)
    
    customer.showOrder()
