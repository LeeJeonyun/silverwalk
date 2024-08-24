import streamlit as st
from audiorecorder import audiorecorder
from gtts import gTTS
import openai
import os
from datetime import datetime
import base64
from pydub import AudioSegment
import requests
import math

# OpenAI API 키를 직접 코드에 입력
openai.api_key = "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"  # 여기에 실제 OpenAI API 키를 입력하세요.

# ffmpeg 및 ffprobe 경로를 명시적으로 설정
AudioSegment.converter = r"C:\ffmpeg-2024-08-21-git-9d15fe77e3-full_build\bin\ffmpeg.exe"
AudioSegment.ffmpeg = r"C:\ffmpeg-2024-08-21-git-9d15fe77e3-full_build\bin\ffmpeg.exe"
AudioSegment.ffprobe = r"C:\ffmpeg-2024-08-21-git-9d15fe77e3-full_build\bin\ffprobe.exe"

class Chatbot:
    def __init__(self, model, system_role, instruction):
        self.context = [{"role": "system", "content": system_role}]
        self.model = model
        self.instruction = instruction
        self.max_token_size = 16 * 1024
        self.available_token_rate = 0.9
        self.kakao_api_key = "ba0dd8abd140a7e257f7b15cde199a68"
        self.weather_api_key = "077aea248ab980d8813b7c89c295992c"

    def add_user_message(self, user_message):
        self.context.append({"role": "user", "content": user_message})

    def _send_request(self):
        try:
            response = openai.ChatCompletion.create(
                model=self.model, 
                messages=self.context,
                temperature=0.3,
                top_p=1,
                max_tokens=1024,
                frequency_penalty=0,
                presence_penalty=0
            )
        except Exception as e:
            print(f"Exception 오류({type(e)}) 발생:{e}")
            if 'maximum context length' in str(e):
                self.context.pop()
                return "메시지 조금 짧게 보내줄래?"
            else: 
                return "[내 찐친 챗봇에 문제가 발생했습니다. 잠시 뒤 이용해주세요]"

        return response
    
    def send_request(self):
        self.context[-1]['content'] += self.instruction
        return self._send_request()        

    def add_response(self, response):
        self.context.append({
                "role" : response['choices'][0]['message']["role"],
                "content" : response['choices'][0]['message']["content"],
            }
        )

    def get_response_content(self):
        return self.context[-1]['content']

    def clean_context(self):
        for idx in reversed(range(len(self.context))):
            if self.context[idx]["role"] == "user":
                self.context[idx]["content"] = self.context[idx]["content"].split("instruction:\n")[0].strip()
                break
    
    def handle_token_limit(self, response):
        try:
            current_usage_rate = response['usage']['total_tokens'] / self.max_token_size
            exceeded_token_rate = current_usage_rate - self.available_token_rate
            if exceeded_token_rate > 0:
                remove_size = math.ceil(len(self.context) / 10)
                self.context = [self.context[0]] + self.context[remove_size+1:]
        except Exception as e:
            print(f"handle_token_limit exception:{e}")

    def get_location_from_server(self):
        url = 'http://192.168.0.8/location'
        try:
            response = requests.get(url)
            if response.status_code == 200:
                location_data = response.json()
                location = location_data.get('location', {})
                latitude = location.get('lat')
                longitude = location.get('lng')
                return latitude, longitude
            else:
                print("Failed to retrieve location data")
                return None, None
        except Exception as e:
            print(f"Exception occurred while getting location: {e}")
            return None, None

    def get_address_from_coordinates(self, latitude, longitude):
        url = f"https://dapi.kakao.com/v2/local/geo/coord2address.json?x={longitude}&y={latitude}"
        headers = {"Authorization": f"KakaoAK {self.kakao_api_key}"}
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if 'documents' in data and len(data['documents']) > 0:
                    address = data['documents'][0]['address']['address_name']
                    return address
                else:
                    return "주소를 찾을 수 없습니다."
            else:
                return "API 요청 실패"
        except Exception as e:
            print(f"Exception occurred while getting address: {e}")
            return "API 요청 중 오류 발생"

    def get_nearby_places(self, latitude, longitude, radius=500):
        url = f"https://dapi.kakao.com/v2/local/search/category.json?category_group_code=FD6&x={longitude}&y={latitude}&radius={radius}"
        headers = {"Authorization": f"KakaoAK {self.kakao_api_key}"}
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                places = []
                for place in data['documents'][:2]:
                    places.append(place['place_name'])
                return places
            else:
                return "주변 건물 정보를 가져오는 데 실패했습니다."
        except Exception as e:
            print(f"Exception occurred while getting places: {e}")
            return "주변 건물 정보를 가져오는 중 오류 발생"

    def get_weather(self, latitude, longitude, forecast=False):
        if forecast:
            url = f"https://api.openweathermap.org/data/3.0/onecall?lat={latitude}&lon={longitude}&exclude=current,minutely,daily,alerts&appid={self.weather_api_key}&units=metric&lang=kr"
        else:
            url = f"http://api.openweathermap.org/data/2.5/weather?lat={latitude}&lon={longitude}&appid={self.weather_api_key}&units=metric&lang=kr"
        
        try:
            response = requests.get(url)
            if response.status_code == 200:
                weather_data = response.json()
                if forecast:
                    weather_description = weather_data['hourly'][1]['weather'][0]['description']
                    temperature = weather_data['hourly'][1]['temp']
                else:
                    weather_description = weather_data['weather'][0]['description']
                    temperature = weather_data['main']['temp']
                
                return f"{weather_description}, 온도는 {temperature}°C"
            else:
                return "날씨 정보를 가져오는 데 실패했습니다."
        except Exception as e:
            print(f"Exception occurred while getting weather: {e}")
            return "날씨 정보를 가져오는 중 오류 발생"

    def generate_location_summary(self, forecast=False):
        latitude, longitude = self.get_location_from_server()
        if latitude and longitude:
            address = self.get_address_from_coordinates(latitude, longitude)
            nearby_places = self.get_nearby_places(latitude, longitude)
            weather = self.get_weather(latitude, longitude, forecast=forecast)
            summary = f"현재 재활자는 {address}에 있습니다. 날씨는 {weather}입니다. 근처의 건물로는 {', '.join(nearby_places)} 등이 있습니다."
        else:
            summary = "위치 정보를 가져올 수 없습니다."
        return summary

    def handle_user_query(self, user_message):
        if "재활자" in user_message and ("어디" in user_message or "위치" in user_message):
            forecast = "뒤 시간" in user_message or "미래 날씨" in user_message
            return self.generate_location_summary(forecast=forecast)
        else:
            self.add_user_message(user_message)
            response = self.send_request()
            self.add_response(response)
            response_message = self.get_response_content()
            self.handle_token_limit(response)
            self.clean_context()
            return response_message

chatbot = Chatbot(model="gpt-3.5-turbo", system_role="You are a helpful assistant.", instruction="")

def STT(audio):
    filename = 'input_test.mp3'
    audio.export(filename, format="mp3")
    print(f"오디오 파일 {filename}가 생성되었습니다.")

    try:
        with open(filename, "rb") as audio_file:
            transcript = openai.Audio.transcribe(
                model="whisper-1",
                file=audio_file
            )
        os.remove(filename)
        print(f"STT 변환 결과: {transcript['text']}")
        return transcript["text"]
    except Exception as e:
        print(f"STT 변환 중 오류 발생: {e}")
        return f"STT 변환 중 오류 발생: {e}"

def ask_gpt_or_location_info(question):
    location_response = chatbot.handle_user_query(question)
    if location_response:
        return location_response
    else:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": question}]
        )
        return response['choices'][0]['message']['content']

def TTS(response):
    filename = "output.mp3"
    tts = gTTS(text=response, lang="ko")
    tts.save(filename)
    with open(filename, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        md = f"""
            <audio autoplay="True">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
        st.markdown(md, unsafe_allow_html=True)
    os.remove(filename)

def main():
    st.set_page_config(page_title="음성 비서 프로그램", layout="wide")

    if "chat" not in st.session_state:
        st.session_state["chat"] = []

    if "messages" not in st.session_state:
        st.session_state["messages"] = [{"role": "system", "content": "You are a thoughtful assistant. Respond to all input in 25 words and answer in korean."}]

    if "check_reset" not in st.session_state:
        st.session_state["check_reset"] = False

    st.header("음성 비서 프로그램")
    st.markdown("---")

    with st.expander("음성비서 프로그램에 관하여", expanded=True):
        st.write(
            """     
            - 음성비서 프로그램의 UI는 스트림릿을 활용했습니다.
            - STT(Speech-To-Text)는 OpenAI의 Whisper AI를 활용했습니다. 
            - 답변은 OpenAI의 GPT 모델을 활용했습니다. 
            - TTS(Text-To-Speech)는 구글의 Google Translate TTS를 활용했습니다.
            """
        )
        st.markdown("")

    if st.button(label="초기화"):
        st.session_state["chat"] = []
        st.session_state["messages"] = [{"role": "system", "content": "You are a thoughtful assistant. Respond to all input in 25 words and answer in korean."}]
        st.session_state["check_reset"] = True

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("질문하기")
        audio = audiorecorder("클릭하여 녹음하기", "녹음중...")
        if (audio.duration_seconds > 0) and (st.session_state["check_reset"] == False):
            st.audio(audio.export().read())
            question = STT(audio)

            now = datetime.now().strftime("%H:%M")
            st.session_state["chat"] = st.session_state["chat"] + [("user", now, question)]
            st.session_state["messages"] = st.session_state["messages"] + [{"role": "user", "content": question}]

    with col2:
        st.subheader("질문/답변")
        if (audio.duration_seconds > 0) and (st.session_state["check_reset"] == False):
            response = ask_gpt_or_location_info(st.session_state["messages"][-1]["content"])

            st.session_state["messages"] = st.session_state["messages"] + [{"role": "system", "content": response}]

            now = datetime.now().strftime("%H:%M")
            st.session_state["chat"] = st.session_state["chat"] + [("bot", now, response)]

            for sender, time, message in st.session_state["chat"]:
                if sender == "user":
                    st.write(f'<div style="display:flex;align-items:center;"><div style="background-color:#007AFF;color:white;border-radius:12px;padding:8px 12px;margin-right:8px;">{message}</div><div style="font-size:0.8rem;color:gray;">{time}</div></div>', unsafe_allow_html=True)
                    st.write("")
                else:
                    st.write(f'<div style="display:flex;align-items:center;justify-content:flex-end;"><div style="background-color:lightgray;border-radius:12px;padding:8px 12px;margin-left:8px;">{message}</div><div style="font-size:0.8rem;color:gray;">{time}</div></div>', unsafe_allow_html=True)
                    st.write("")

            TTS(response)
        else:
            st.session_state["check_reset"] = False

if __name__ == "__main__":
    main()
